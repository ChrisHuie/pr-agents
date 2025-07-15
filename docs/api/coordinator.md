# PRCoordinator API Reference

## Overview

The `PRCoordinator` is the central orchestrator for PR analysis, managing the extraction and processing pipeline with strict component isolation. It now includes support for batch processing and release-based PR analysis.

## Class: PRCoordinator

```python
from src.pr_agents.pr_processing import PRCoordinator

coordinator = PRCoordinator(github_token="your-token")
```

### Constructor

```python
PRCoordinator(github_token: str) -> None
```

**Parameters:**
- `github_token`: GitHub personal access token with repo access

## Core Methods

### analyze_pr

Analyzes a single PR with component isolation.

```python
def analyze_pr(
    pr_url: str,
    extract_components: set[str] | None = None,
    run_processors: list[str] | None = None
) -> dict[str, Any]
```

**Parameters:**
- `pr_url`: GitHub PR URL
- `extract_components`: Components to extract (default: all)
- `run_processors`: Processors to run (default: all available)

**Returns:**
Dictionary with extracted data, processing results, and summary

### extract_pr_components

Extracts specific PR components without processing.

```python
def extract_pr_components(
    pr_url: str,
    components: set[str] | None = None
) -> PRData
```

**Parameters:**
- `pr_url`: GitHub PR URL
- `components`: Set of components to extract
  - Valid: `{"metadata", "code_changes", "repository", "reviews"}`

### process_components

Processes extracted PR data with specified processors.

```python
def process_components(
    pr_data: PRData,
    processors: list[str] | None = None
) -> list[ProcessingResult]
```

**Parameters:**
- `pr_data`: Extracted PR data
- `processors`: List of processors to run
  - Valid: `["metadata", "code_changes", "repository"]`

## Batch Processing Methods

### analyze_prs_batch

Analyzes multiple PRs in batch.

```python
def analyze_prs_batch(
    pr_urls: list[str],
    extract_components: set[str] | None = None,
    run_processors: list[str] | None = None,
    parallel: bool = False
) -> dict[str, Any]
```

**Parameters:**
- `pr_urls`: List of GitHub PR URLs
- `extract_components`: Components to extract
- `run_processors`: Processors to run
- `parallel`: Whether to process in parallel (future enhancement)

**Returns:**
```python
{
    "total_prs": int,
    "successful": int,
    "failed": int,
    "pr_results": dict[str, Any],  # Results keyed by PR URL
    "summary": dict[str, Any]       # Batch statistics
}
```

### analyze_release_prs

Analyzes all PRs included in a specific release.

```python
def analyze_release_prs(
    repo_name: str,
    release_tag: str,
    extract_components: set[str] | None = None,
    run_processors: list[str] | None = None
) -> dict[str, Any]
```

**Parameters:**
- `repo_name`: Repository name (e.g., "owner/repo")
- `release_tag`: Release tag name (e.g., "v1.2.3")
- `extract_components`: Components to extract
- `run_processors`: Processors to run

**Returns:**
Dictionary with batch results plus release metadata

**Example:**
```python
results = coordinator.analyze_release_prs(
    "prebid/Prebid.js",
    "8.20.0",
    extract_components={"metadata", "code_changes"}
)

print(f"Total PRs in release: {results['release_info']['total_prs']}")
print(f"Risk distribution: {results['summary']['by_risk_level']}")
```

### analyze_unreleased_prs

Analyzes all merged PRs that haven't been included in a release.

```python
def analyze_unreleased_prs(
    repo_name: str,
    base_branch: str = "main",
    extract_components: set[str] | None = None,
    run_processors: list[str] | None = None
) -> dict[str, Any]
```

**Parameters:**
- `repo_name`: Repository name
- `base_branch`: Base branch to check (default: "main")
- `extract_components`: Components to extract
- `run_processors`: Processors to run

**Returns:**
Dictionary with batch results plus unreleased PR metadata

**Example:**
```python
results = coordinator.analyze_unreleased_prs(
    "owner/repo",
    base_branch="master"  # Some repos use master
)

# Find high-risk unreleased changes
for pr_url, pr_result in results["pr_results"].items():
    if pr_result.get("success"):
        for proc in pr_result["processing_results"]:
            if (proc["component"] == "code_changes" and 
                proc["data"]["risk_assessment"]["risk_level"] == "high"):
                print(f"High risk PR pending release: {pr_url}")
```

### analyze_prs_between_releases

Analyzes PRs merged between two release tags.

```python
def analyze_prs_between_releases(
    repo_name: str,
    from_tag: str,
    to_tag: str,
    extract_components: set[str] | None = None,
    run_processors: list[str] | None = None
) -> dict[str, Any]
```

**Parameters:**
- `repo_name`: Repository name
- `from_tag`: Starting release tag (exclusive)
- `to_tag`: Ending release tag (inclusive)
- `extract_components`: Components to extract
- `run_processors`: Processors to run

**Returns:**
Dictionary with batch results plus version range metadata

**Example:**
```python
# Analyze changes between versions
results = coordinator.analyze_prs_between_releases(
    "owner/repo",
    from_tag="v1.0.0",
    to_tag="v1.1.0"
)

# Check quality trends
summary = results["summary"]
total = summary["total_analyzed"]
good_titles = (summary["by_title_quality"]["excellent"] + 
               summary["by_title_quality"]["good"])
quality_pct = (good_titles / total) * 100 if total > 0 else 0
print(f"PR title quality: {quality_pct:.1f}%")
```

## Batch Summary Statistics

All batch processing methods return a summary with these statistics:

```python
{
    "total_analyzed": int,
    "by_risk_level": {
        "minimal": int,
        "low": int,
        "medium": int,
        "high": int
    },
    "by_title_quality": {
        "poor": int,
        "fair": int,
        "good": int,
        "excellent": int
    },
    "by_description_quality": {
        "poor": int,
        "fair": int,
        "good": int,
        "excellent": int
    },
    "average_files_changed": float,
    "total_additions": int,
    "total_deletions": int
}
```

## PRFetcher

The `PRFetcher` class provides the underlying functionality for fetching groups of PRs. It can be accessed directly for custom queries:

```python
from src.pr_agents.pr_processing import PRFetcher

fetcher = PRFetcher(github_token)

# Get PRs with specific label
prs = fetcher.get_prs_by_label(
    "owner/repo",
    label="bug",
    state="closed"
)

# Get all merged PRs for custom analysis
for pr in prs:
    print(f"PR #{pr['number']}: {pr['title']}")
```

### Available Methods

- `get_prs_by_release(repo_name, release_tag)`
- `get_prs_between_releases(repo_name, from_tag, to_tag)`
- `get_unreleased_prs(repo_name, base_branch)`
- `get_prs_by_label(repo_name, label, state)`

## Error Handling

All batch methods handle individual PR failures gracefully:

```python
results = coordinator.analyze_prs_batch(pr_urls)

# Check for failures
if results["failed"] > 0:
    for pr_url, result in results["pr_results"].items():
        if not result.get("success", True):
            print(f"Failed to analyze {pr_url}: {result.get('error')}")
```

## Performance Considerations

- Batch processing is currently sequential
- GitHub API rate limits apply (5000 requests/hour for authenticated requests)
- Large releases may take time to process
- Consider using component selection to reduce processing time

## Best Practices

1. **Component Selection**: Only extract/process needed components
2. **Error Handling**: Always check for failed PRs in batch results
3. **Rate Limiting**: Be mindful of GitHub API limits for large batches
4. **Caching**: Results are not cached; store them if needed
5. **Memory**: Large batches may consume significant memory