# Quick Start Guide

## Installation

### Prerequisites

- Python 3.13 or higher
- GitHub account and personal access token
- `uv` package manager (recommended) or `pip`

### Install with uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/ChrisHuie/pr-agents.git
cd pr-agents

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Install with pip

```bash
# Clone the repository
git clone https://github.com/ChrisHuie/pr-agents.git
cd pr-agents

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Configuration

### 1. Set up GitHub Token

Create a `.env` file in the project root:

```bash
GITHUB_TOKEN=your_github_personal_access_token
```

To create a GitHub token:
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token"
3. Select scopes: `repo` (full control of private repositories)
4. Copy the generated token

### 2. Verify Installation

```python
from src.pr_agents.pr_processing.coordinator import PRCoordinator

# This should not raise any errors
coordinator = PRCoordinator(github_token="your-token")
print("Installation successful!")
```

## Basic Usage

### Analyze a Pull Request

```python
from src.pr_agents.pr_processing.coordinator import PRCoordinator

# Initialize coordinator
coordinator = PRCoordinator(github_token="your-token")

# Analyze a PR
results = coordinator.process_pr(
    "https://github.com/prebid/Prebid.js/pull/123"
)

# View results
print(f"Metadata Quality: {results['metadata']['processed']['quality_score']}")
print(f"Code Risk Level: {results['code_changes']['processed']['risk_assessment']['risk_level']}")
```

### Extract Specific Components

```python
# Extract only metadata and code changes
data = coordinator.extract_pr_components(
    "https://github.com/prebid/Prebid.js/pull/123",
    components=["metadata", "code_changes"]
)

# Access extracted data
print(f"PR Title: {data['metadata']['title']}")
print(f"Files Changed: {data['code_changes']['changed_files']}")
```

### Process with Custom Configuration

```python
# Use custom extractors or processors
from src.pr_agents.pr_processing.extractors import MetadataExtractor
from src.pr_agents.pr_processing.processors import MetadataProcessor

custom_extractors = {
    "metadata": MetadataExtractor()
}

custom_processors = {
    "metadata": MetadataProcessor()
}

coordinator = PRCoordinator(
    github_token="your-token",
    extractors=custom_extractors,
    processors=custom_processors
)
```

## Common Use Cases

### 1. PR Quality Check

```python
def check_pr_quality(pr_url: str) -> dict:
    """Check if a PR meets quality standards."""
    coordinator = PRCoordinator(github_token="your-token")
    results = coordinator.process_pr(pr_url, components=["metadata"])
    
    metadata = results["metadata"]["processed"]
    quality_score = metadata["quality_score"]
    
    return {
        "passes": quality_score >= 70,
        "score": quality_score,
        "suggestions": metadata.get("suggestions", [])
    }

# Usage
quality = check_pr_quality("https://github.com/owner/repo/pull/123")
if quality["passes"]:
    print("PR meets quality standards!")
else:
    print(f"PR needs improvement: {quality['suggestions']}")
```

### 2. Risk Assessment

```python
def assess_pr_risk(pr_url: str) -> str:
    """Assess the risk level of PR changes."""
    coordinator = PRCoordinator(github_token="your-token")
    results = coordinator.process_pr(pr_url, components=["code_changes"])
    
    risk_data = results["code_changes"]["processed"]["risk_assessment"]
    return risk_data["risk_level"]

# Usage
risk = assess_pr_risk("https://github.com/owner/repo/pull/456")
print(f"PR Risk Level: {risk}")
```

### 3. Batch Analysis

```python
def analyze_multiple_prs(pr_urls: list[str]) -> dict:
    """Analyze multiple PRs and summarize results."""
    coordinator = PRCoordinator(github_token="your-token")
    
    results = {}
    for url in pr_urls:
        try:
            pr_results = coordinator.process_pr(url)
            results[url] = {
                "quality": pr_results["metadata"]["processed"]["quality_score"],
                "risk": pr_results["code_changes"]["processed"]["risk_assessment"]["risk_level"]
            }
        except Exception as e:
            results[url] = {"error": str(e)}
    
    return results

# Usage
urls = [
    "https://github.com/owner/repo/pull/123",
    "https://github.com/owner/repo/pull/124",
    "https://github.com/owner/repo/pull/125"
]
summary = analyze_multiple_prs(urls)
```

## Command Line Usage

### Using the Configuration CLI

```bash
# Validate repository configurations
python -m src.pr_agents.config.cli validate

# Test configuration loading
python -m src.pr_agents.config.cli test

# Migrate old configuration format
python -m src.pr_agents.config.cli migrate old_config.json config/
```

### Creating a Simple CLI Script

```python
#!/usr/bin/env python
"""analyze_pr.py - Simple PR analysis CLI"""

import sys
import os
from src.pr_agents.pr_processing.coordinator import PRCoordinator

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_pr.py <pr_url>")
        sys.exit(1)
    
    pr_url = sys.argv[1]
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set")
        sys.exit(1)
    
    coordinator = PRCoordinator(github_token=token)
    results = coordinator.process_pr(pr_url)
    
    # Display summary
    metadata = results["metadata"]["processed"]
    code = results["code_changes"]["processed"]
    
    print(f"\nPR Analysis for: {pr_url}")
    print(f"Quality Score: {metadata['quality_score']}/100")
    print(f"Risk Level: {code['risk_assessment']['risk_level']}")
    print(f"Files Changed: {code['size_analysis']['files_changed']}")

if __name__ == "__main__":
    main()
```

## Troubleshooting

### Common Issues

1. **ImportError**: Make sure you're in the project directory and have activated the virtual environment
2. **GitHub API Rate Limit**: Use a personal access token to increase rate limits
3. **Permission Denied**: Ensure your token has the necessary scopes (`repo` for private repos)

### Debug Mode

Enable detailed logging:

```python
from loguru import logger

# Set debug level
logger.add("debug.log", level="DEBUG")

# Now run your code - detailed logs will be in debug.log
```

## Next Steps

- [Add custom repositories](./adding-repositories.md)
- [Create custom processors](./custom-processors.md)
- [Explore the full API](../api/)
- [Understand the architecture](../architecture/overview.md)