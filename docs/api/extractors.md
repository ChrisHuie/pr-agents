# Extractors API Reference

## Overview

Extractors are responsible for fetching specific data from GitHub Pull Requests using the PyGithub API. Each extractor focuses on a single aspect of PR data, maintaining strict component isolation.

## Base Extractor

All extractors inherit from the base class:

```python
from abc import ABC, abstractmethod
from typing import Any

class BaseExtractor(ABC):
    """Base class for all PR data extractors."""
    
    @abstractmethod
    def extract(self, pr_data: Any) -> dict[str, Any]:
        """
        Extract specific component data from PR.
        
        Args:
            pr_data: GitHub PR object from PyGithub
            
        Returns:
            Dictionary containing extracted data
        """
        pass
```

## Available Extractors

### MetadataExtractor

Extracts basic PR metadata.

```python
from src.pr_agents.pr_processing.extractors.metadata import MetadataExtractor

extractor = MetadataExtractor()
data = extractor.extract(pr)
```

**Extracted Data:**
- `title`: PR title
- `body`: PR description
- `state`: open/closed
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `merged_at`: Merge timestamp (if merged)
- `author`: Author information
- `labels`: List of label names
- `assignees`: List of assignee logins
- `requested_reviewers`: List of requested reviewer logins

**Example Output:**
```python
{
    "title": "Add new bid adapter",
    "body": "## Description\nThis PR adds...",
    "state": "open",
    "created_at": "2024-01-15T10:30:00Z",
    "author": {
        "login": "developer",
        "type": "User"
    },
    "labels": ["enhancement", "bid-adapter"]
}
```

### CodeChangesExtractor

Extracts information about code changes.

```python
from src.pr_agents.pr_processing.extractors.code_changes import CodeChangesExtractor

extractor = CodeChangesExtractor()
data = extractor.extract(pr)
```

**Extracted Data:**
- `changed_files`: Number of files changed
- `additions`: Total lines added
- `deletions`: Total lines deleted
- `commits`: Number of commits
- `files`: List of file details
  - `filename`: File path
  - `status`: added/modified/removed
  - `additions`: Lines added in file
  - `deletions`: Lines removed in file
  - `changes`: Total changes
  - `patch`: Diff patch (if available)

**Example Output:**
```python
{
    "changed_files": 3,
    "additions": 150,
    "deletions": 20,
    "files": [
        {
            "filename": "modules/newBidAdapter.js",
            "status": "added",
            "additions": 140,
            "deletions": 0,
            "patch": "@@ -0,0 +1,140 @@\n+export function..."
        }
    ]
}
```

### RepositoryExtractor

Extracts repository information.

```python
from src.pr_agents.pr_processing.extractors.repository import RepositoryExtractor

extractor = RepositoryExtractor()
data = extractor.extract(pr)
```

**Extracted Data:**
- `name`: Repository name
- `full_name`: Full repository name (owner/repo)
- `description`: Repository description
- `language`: Primary language
- `languages`: All languages with byte counts
- `topics`: Repository topics
- `default_branch`: Default branch name
- `visibility`: public/private
- `fork`: Whether it's a fork
- `created_at`: Repository creation date
- `updated_at`: Last update date

**Example Output:**
```python
{
    "name": "Prebid.js",
    "full_name": "prebid/Prebid.js",
    "description": "Setup and manage header bidding...",
    "language": "JavaScript",
    "languages": {
        "JavaScript": 2500000,
        "HTML": 50000
    },
    "topics": ["advertising", "header-bidding"],
    "default_branch": "master"
}
```

### ReviewsExtractor

Extracts review and comment information.

```python
from src.pr_agents.pr_processing.extractors.reviews import ReviewsExtractor

extractor = ReviewsExtractor()
data = extractor.extract(pr)
```

**Extracted Data:**
- `reviews`: List of reviews
  - `user`: Reviewer login
  - `state`: APPROVED/CHANGES_REQUESTED/COMMENTED
  - `body`: Review comment
  - `submitted_at`: Review timestamp
- `review_comments`: Inline code comments
  - `user`: Commenter login
  - `body`: Comment text
  - `path`: File path
  - `line`: Line number
  - `created_at`: Comment timestamp
- `comments`: General PR comments
  - `user`: Commenter login
  - `body`: Comment text
  - `created_at`: Comment timestamp

**Example Output:**
```python
{
    "reviews": [
        {
            "user": "reviewer1",
            "state": "APPROVED",
            "body": "LGTM!",
            "submitted_at": "2024-01-15T11:00:00Z"
        }
    ],
    "review_comments": [
        {
            "user": "reviewer2",
            "body": "Consider using const here",
            "path": "modules/adapter.js",
            "line": 42
        }
    ]
}
```

## Using Extractors

### Basic Usage

```python
from github import Github
from src.pr_agents.pr_processing.extractors import (
    MetadataExtractor,
    CodeChangesExtractor
)

# Initialize GitHub client
g = Github(auth=Github.Auth.Token("your-token"))
pr = g.get_repo("owner/repo").get_pull(123)

# Extract metadata
metadata_extractor = MetadataExtractor()
metadata = metadata_extractor.extract(pr)

# Extract code changes
code_extractor = CodeChangesExtractor()
code_changes = code_extractor.extract(pr)
```

### Using with Coordinator

```python
from src.pr_agents.pr_processing.coordinator import PRCoordinator

# Coordinator handles extractor initialization
coordinator = PRCoordinator(github_token="your-token")

# Extract specific components
data = coordinator.extract_pr_components(
    "https://github.com/owner/repo/pull/123",
    components=["metadata", "code_changes"]
)
```

### Error Handling

Extractors handle errors gracefully:

```python
try:
    data = extractor.extract(pr)
except Exception as e:
    # Extractors log errors and return partial data when possible
    print(f"Extraction error: {e}")
```

## Creating Custom Extractors

To create a new extractor:

```python
from src.pr_agents.pr_processing.extractors.base import BaseExtractor

class CustomExtractor(BaseExtractor):
    """Extract custom PR data."""
    
    def extract(self, pr_data: Any) -> dict[str, Any]:
        """Extract custom information."""
        try:
            # Your extraction logic here
            custom_data = {
                "custom_field": pr_data.some_property,
                "analyzed_at": datetime.now().isoformat()
            }
            return custom_data
        except Exception as e:
            # Log error and return empty dict
            logger.error(f"Custom extraction failed: {e}")
            return {}
```

## Best Practices

1. **Single Responsibility**: Each extractor handles one data type
2. **Error Resilience**: Continue extraction even if some fields fail
3. **No Side Effects**: Extractors should only read data
4. **Consistent Output**: Always return a dictionary
5. **Type Hints**: Use type hints for clarity
6. **Documentation**: Document extracted fields clearly

## Performance Tips

1. **Minimize API Calls**: Batch requests when possible
2. **Lazy Loading**: Only fetch data that's needed
3. **Caching**: Cache repeated API calls
4. **Pagination**: Handle large result sets properly

```python
# Example: Efficient file extraction
def extract_files_efficiently(pr):
    # Only fetch file list, not full patches
    files = []
    for file in pr.get_files():
        files.append({
            "filename": file.filename,
            "status": file.status,
            "additions": file.additions,
            "deletions": file.deletions,
            # Don't fetch patch unless needed
        })
    return files
```