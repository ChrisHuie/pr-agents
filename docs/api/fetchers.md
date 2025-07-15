# PR Fetchers API Documentation

## Overview

The PR Agents library provides a modular fetching system for retrieving Pull Requests from GitHub repositories. The system follows a strict component isolation pattern with specialized fetchers for different query dimensions.

## Architecture

```
BasePRFetcher (abstract)
├── ReleasePRFetcher      # Release-based queries
├── DateRangePRFetcher    # Date-based queries  
├── LabelPRFetcher        # Label-based queries
└── MultiRepoPRFetcher    # Cross-repo coordination

PREnricher                # Adds computed metadata
```

## Core Components

### BasePRFetcher

Abstract base class for all PR fetchers.

```python
from src.pr_agents.pr_processing.fetchers import BasePRFetcher

class BasePRFetcher(ABC):
    def __init__(self, github_token: str) -> None
    
    @abstractmethod
    def fetch(self, **kwargs) -> list[dict[str, Any]]
```

All fetchers return a standardized PR data structure:
```python
{
    "url": str,              # PR URL
    "number": int,           # PR number
    "title": str,            # PR title
    "author": str,           # Author username
    "merged_at": str | None, # ISO timestamp
    "labels": list[str],     # Label names
    "created_at": str,       # ISO timestamp
    "updated_at": str,       # ISO timestamp
    "state": str,            # open/closed
}
```

### DateRangePRFetcher

Fetches PRs based on date ranges.

```python
from src.pr_agents.pr_processing.fetchers import DateRangePRFetcher

fetcher = DateRangePRFetcher(github_token)

# Fetch by specific date range
prs = fetcher.fetch(
    repo_name="owner/repo",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
    state="merged"  # merged/closed/open/all
)

# Fetch last N days
prs = fetcher.fetch(
    repo_name="owner/repo",
    last_n_days=30,
    state="merged"
)

# Fetch last calendar month
prs = fetcher.fetch(
    repo_name="owner/repo",
    last_month=True,
    state="merged"
)

# Fetch by quarter
prs = fetcher.get_prs_by_quarter(
    "owner/repo",
    year=2024,
    quarter=1,  # 1-4
    state="merged"
)
```

### ReleasePRFetcher

Fetches PRs based on release tags and versions.

```python
from src.pr_agents.pr_processing.fetchers import ReleasePRFetcher

fetcher = ReleasePRFetcher(github_token)

# Fetch PRs in a specific release
prs = fetcher.fetch(
    repo_name="owner/repo",
    release_tag="v1.2.3"
)

# Fetch PRs between releases
prs = fetcher.fetch(
    repo_name="owner/repo",
    from_tag="v1.0.0",
    to_tag="v1.2.0"
)

# Fetch unreleased PRs
prs = fetcher.fetch(
    repo_name="owner/repo",
    unreleased=True,
    base_branch="main"
)
```

### LabelPRFetcher

Fetches PRs based on labels.

```python
from src.pr_agents.pr_processing.fetchers import LabelPRFetcher

fetcher = LabelPRFetcher(github_token)

# Fetch PRs with any of the labels
prs = fetcher.fetch(
    repo_name="owner/repo",
    labels=["bug", "enhancement"],
    state="all"
)

# Fetch PRs with ALL specified labels
prs = fetcher.fetch(
    repo_name="owner/repo",
    labels_all=["critical", "security"],
    state="open"
)

# Fetch PRs without specific labels
prs = fetcher.fetch(
    repo_name="owner/repo",
    labels_none=["wip", "draft"],
    state="merged"
)

# Fetch by label pattern
prs = fetcher.get_prs_by_label_pattern(
    "owner/repo",
    label_pattern="priority-*",
    state="all"
)
```

### MultiRepoPRFetcher

Coordinates fetching across multiple repositories.

```python
from src.pr_agents.pr_processing.fetchers import MultiRepoPRFetcher

fetcher = MultiRepoPRFetcher(github_token)

# Fetch from multiple repos with date range
prs = fetcher.fetch(
    repo_names=["owner/repo1", "owner/repo2"],
    fetch_type="date",
    last_n_days=30,
    grouped=False,  # True returns dict grouped by repo
    parallel=True,
    max_workers=5
)

# Get multi-repo summary
summary = fetcher.get_multi_repo_summary(
    repo_names=["owner/repo1", "owner/repo2"],
    fetch_type="date",
    last_n_days=30
)
```

### PREnricher

Adds computed metadata to fetched PRs.

```python
from src.pr_agents.pr_processing.enrichers import PREnricher

enricher = PREnricher(github_token)

# Enrich PRs with all metadata
enriched_prs = enricher.enrich(
    prs,
    add_release_status=True,
    add_time_metrics=True,
    add_repo_context=True
)

# Add only release status
enriched_prs = enricher.add_release_status("owner/repo", prs)
```

Enriched PR data includes:
```python
{
    # Original fields...
    
    # Release status
    "is_released": bool,
    "release_tag": str | None,
    "release_date": str | None,
    "releases_since_merge": list[dict],
    
    # Time metrics
    "age_days": int,
    "age_category": str,  # fresh/recent/moderate/old/ancient
    "merge_time_hours": float,
    "merge_time_category": str,  # rapid/quick/normal/slow/delayed
    "time_to_release_days": int,
    
    # Repository context
    "repo_full_name": str,
    "repo_name": str,
    "repo_owner": str,
    "repo_default_branch": str,
    "repo_language": str,
    "repo_is_fork": bool,
    "repo_stars": int,
}
```

## Enhanced Coordinator

The `EnhancedPRCoordinator` integrates all fetchers and enrichers:

```python
from src.pr_agents.pr_processing.coordinator_enhanced import EnhancedPRCoordinator

coordinator = EnhancedPRCoordinator(github_token)

# Fetch and analyze by date
results = coordinator.fetch_and_analyze_by_date(
    repo_name="owner/repo",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
    extract_components={"metadata", "code_changes"},
    run_processors=["metadata", "code"],
    enrich=True
)

# Multi-repo analysis
results = coordinator.fetch_and_analyze_multi_repo(
    repo_names=["owner/repo1", "owner/repo2"],
    fetch_type="date",
    last_n_days=30,
    extract_components={"metadata"},
    enrich=True
)

# Release comparison
comparison = coordinator.get_release_comparison(
    repo_name="owner/repo",
    days=30
)

# PR velocity analysis
velocity = coordinator.analyze_pr_velocity(
    repo_names=["owner/repo1", "owner/repo2"],
    days=90
)
```

## Usage Examples

### Example 1: Get all unreleased PRs from last month

```python
from datetime import datetime
from src.pr_agents.pr_processing.fetchers import DateRangePRFetcher
from src.pr_agents.pr_processing.enrichers import PREnricher

# Initialize
date_fetcher = DateRangePRFetcher(github_token)
enricher = PREnricher(github_token)

# Fetch PRs from last 30 days
prs = date_fetcher.fetch(
    repo_name="prebid/Prebid.js",
    last_n_days=30,
    state="merged"
)

# Enrich with release status
enriched_prs = enricher.enrich(prs, add_release_status=True)

# Filter unreleased
unreleased_prs = [pr for pr in enriched_prs if not pr.get("is_released", False)]

print(f"Found {len(unreleased_prs)} unreleased PRs")
```

### Example 2: Compare PR velocity across repositories

```python
from src.pr_agents.pr_processing.coordinator_enhanced import EnhancedPRCoordinator

coordinator = EnhancedPRCoordinator(github_token)

# Analyze velocity for multiple repos
velocity = coordinator.analyze_pr_velocity(
    repo_names=[
        "prebid/Prebid.js",
        "prebid/prebid-server",
        "prebid/prebid-mobile-ios"
    ],
    days=90
)

# Display results
for repo, stats in velocity["by_repository"].items():
    print(f"\n{repo}:")
    print(f"  PRs/day: {stats['average_prs_per_day']}")
    print(f"  Avg merge time: {stats['merge_time_stats']['average_hours']}h")
```

### Example 3: Track releases across multiple repositories

```python
from src.pr_agents.pr_processing.fetchers import MultiRepoPRFetcher

multi_fetcher = MultiRepoPRFetcher(github_token)

# Get release summary
summary = multi_fetcher.get_multi_repo_summary(
    repo_names=[
        "prebid/Prebid.js",
        "prebid/prebid-server",
        "prebid/prebid-mobile-ios"
    ],
    fetch_type="release",
    unreleased=True
)

# Display summary
print(f"Total unreleased PRs: {summary['total_prs']}")
for repo, info in summary['by_repository'].items():
    print(f"{repo}: {info['pr_count']} PRs waiting for release")
```

## Best Practices

1. **Use appropriate fetchers**: Each fetcher is optimized for its specific query type
2. **Enable parallel fetching**: When querying multiple repos, use `parallel=True`
3. **Cache release data**: The enricher caches release data per repository
4. **Limit analysis scope**: When analyzing PRs, limit components to what you need
5. **Handle errors gracefully**: Multi-repo fetchers continue even if one repo fails

## Performance Considerations

- **API Rate Limits**: The system respects GitHub API rate limits
- **Parallel Processing**: Multi-repo fetcher supports concurrent requests
- **Caching**: Release data is cached within enricher instances
- **Batch Operations**: Use batch methods when analyzing multiple PRs

## Error Handling

All fetchers follow consistent error handling:
- Invalid parameters raise `ValueError`
- API errors are logged and re-raised
- Multi-repo operations continue on individual failures
- Results include error information for failed operations