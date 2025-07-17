# API Models Reference

This document provides a comprehensive reference for all models used in PR Agents, including Pydantic models for external API data and dataclasses for internal processing results.

## Overview

PR Agents uses two types of models:

1. **Pydantic Models** (`models.py`) - For validating and parsing external data from GitHub API
2. **Dataclasses** (`analysis_models.py`) - For internal processing results with better performance

## Pydantic Models (External API Data)

### PRMetadata

Represents isolated PR metadata including title, description, labels, and other basic information.

```python
class PRMetadata(BaseModel):
    title: str                           # PR title
    description: str | None              # PR description/body
    author: str                          # PR author username
    state: str                           # "open", "closed", or "merged"
    labels: list[str]                    # PR labels
    milestone: str | None                # Associated milestone
    assignees: list[str]                 # Assigned users
    created_at: datetime                 # PR creation timestamp
    updated_at: datetime                 # Last update timestamp
    merged_at: datetime | None           # Merge timestamp (if merged)
    pr_number: int                       # PR number
    url: str                             # PR URL
```

### CodeChanges

Represents code changes in the PR including diffs and file modifications.

```python
class CodeChanges(BaseModel):
    total_additions: int                 # Total lines added
    total_deletions: int                 # Total lines removed
    total_changes: int                   # Total lines changed
    changed_files: int                   # Number of files changed
    file_diffs: list[FileDiff]           # Individual file changes
    base_sha: str                        # Base commit SHA
    head_sha: str                        # Head commit SHA
    merge_base_sha: str | None           # Merge base SHA
```

### FileDiff

Represents changes to an individual file.

```python
class FileDiff(BaseModel):
    filename: str                        # File path
    status: str                          # "added", "modified", "removed", "renamed"
    additions: int                       # Lines added in this file
    deletions: int                       # Lines removed in this file
    changes: int                         # Total lines changed
    patch: str | None                    # Git diff patch
    previous_filename: str | None        # Previous name if renamed
```

### RepositoryInfo

Contains isolated repository information.

```python
class RepositoryInfo(BaseModel):
    name: str                            # Repository name
    full_name: str                       # Owner/repository
    owner: str                           # Repository owner
    description: str | None              # Repository description
    is_private: bool                     # Privacy status
    default_branch: str                  # Default branch name
    language: str | None                 # Primary language
    languages: dict[str, int]            # Language breakdown (bytes)
    topics: list[str]                    # Repository topics
    base_branch: str                     # PR base branch
    head_branch: str                     # PR head branch
    fork_info: dict[str, Any] | None     # Fork information if applicable
```

### ReviewData

Contains PR review and comment information.

```python
class ReviewData(BaseModel):
    reviews: list[Review]                # PR reviews
    comments: list[ReviewComment]        # Review comments
    requested_reviewers: list[str]       # Requested reviewer usernames
    approved_by: list[str]               # Users who approved
    changes_requested_by: list[str]      # Users who requested changes
```

### Review

Individual PR review.

```python
class Review(BaseModel):
    author: str                          # Review author username
    state: str                           # "APPROVED", "CHANGES_REQUESTED", "COMMENTED"
    body: str | None                     # Review body text
    submitted_at: datetime               # Review submission timestamp
```

### ReviewComment

Individual review comment.

```python
class ReviewComment(BaseModel):
    author: str                          # Comment author username
    body: str                            # Comment text
    created_at: datetime                 # Creation timestamp
    updated_at: datetime                 # Last update timestamp
    position: int | None                 # Position in diff
    path: str | None                     # File path
    commit_sha: str | None               # Associated commit SHA
```

### PRData

Complete PR data container with all isolated components.

```python
class PRData(BaseModel):
    metadata: PRMetadata | None          # PR metadata component
    code_changes: CodeChanges | None     # Code changes component
    repository_info: RepositoryInfo | None  # Repository info component
    review_data: ReviewData | None       # Reviews component
```

### ProcessingResult

Result from processing a specific component.

```python
class ProcessingResult(BaseModel):
    component: str                       # Component name
    success: bool                        # Processing success status
    data: dict[str, Any]                 # Processing results
    errors: list[str]                    # Error messages if any
    processing_time_ms: int | None       # Processing duration
```

## Dataclass Models (Internal Processing)

### Metadata Analysis Models

#### TitleAnalysis

Analysis of PR title characteristics.

```python
@dataclass
class TitleAnalysis:
    length: int                          # Title character length
    word_count: int                      # Number of words
    has_emoji: bool                      # Contains emojis
    has_prefix: bool                     # Has conventional prefix
    has_ticket_reference: bool           # Contains ticket/issue reference
    is_question: bool                    # Is phrased as question
    is_wip: bool                         # Is work-in-progress
```

#### DescriptionAnalysis

Analysis of PR description characteristics.

```python
@dataclass
class DescriptionAnalysis:
    has_description: bool                # Has non-empty description
    length: int                          # Description character length
    line_count: int                      # Number of lines
    sections: list[str]                  # Section headers found
    has_checklist: bool                  # Contains checklist
    has_links: bool                      # Contains links
    has_code_blocks: bool                # Contains code blocks
```

#### TitleQuality & DescriptionQuality

Quality assessments on 1-100 scale.

```python
@dataclass
class TitleQuality:
    score: int                           # 1-100 quality score
    quality_level: str                   # "poor", "fair", "good", "excellent"
    issues: list[str]                    # Identified issues

@dataclass
class DescriptionQuality:
    score: int                           # 1-100 quality score
    quality_level: str                   # "poor", "fair", "good", "excellent"
    issues: list[str]                    # Identified issues
```

### Code Analysis Models

#### ChangeStats

Basic change statistics.

```python
@dataclass
class ChangeStats:
    total_additions: int                 # Total lines added
    total_deletions: int                 # Total lines removed
    total_changes: int                   # Total lines changed
    changed_files: int                   # Number of files changed
    net_lines: int                       # Net lines added/removed
    change_ratio: float                  # Addition/deletion ratio
```

#### RiskAssessment

Risk assessment of code changes.

```python
@dataclass
class RiskAssessment:
    risk_score: int                      # 0-6+ risk score
    risk_level: str                      # "minimal", "low", "medium", "high"
    risk_factors: list[str]              # Contributing risk factors
    recommendations: list[str]           # Risk mitigation recommendations
```

### Repository Analysis Models

#### RepoHealth

Repository health assessment.

```python
@dataclass
class RepoHealth:
    health_score: int                    # 0-70 health score
    health_level: str                    # Health category
    health_factors: list[str]            # Positive factors
    issues: list[str]                    # Health issues
    max_possible_score: int              # Maximum achievable score
    recommendations: list[str]           # Improvement recommendations
```

### AI Analysis Models

#### PersonaSummary

Summary for a specific persona.

```python
@dataclass
class PersonaSummary:
    persona: str                         # "executive", "product", "developer"
    summary: str                         # Generated summary text
    confidence: float                    # Model confidence score
```

#### AISummaries

Complete AI-generated summaries.

```python
@dataclass
class AISummaries:
    executive_summary: PersonaSummary    # Executive-level summary
    product_summary: PersonaSummary      # Product manager summary
    developer_summary: PersonaSummary    # Developer-focused summary
    model_used: str                      # LLM model identifier
    generation_timestamp: datetime       # When generated
    cached: bool                         # Whether from cache
    total_tokens: int                    # Token usage
    generation_time_ms: int              # Generation duration
```

### Accuracy Validation Models

#### AccuracyScore

Complete accuracy validation result.

```python
@dataclass
class AccuracyScore:
    total_score: float                   # Weighted average 0-100
    component_scores: AccuracyComponents # Individual component scores
    recommendations: list[AccuracyRecommendation]  # Improvement suggestions
    accuracy_level: str                  # "excellent", "good", "fair", "poor"
    files_mentioned_ratio: float         # Ratio of files mentioned
    modules_mentioned_ratio: float       # Ratio of modules mentioned
```

## Model Usage Examples

### Working with Pydantic Models

```python
from src.pr_agents.pr_processing.models import PRMetadata, CodeChanges

# Parse GitHub API response
pr_metadata = PRMetadata(
    title="feat: Add new authentication module",
    description="This PR adds OAuth2 authentication...",
    author="johndoe",
    state="open",
    labels=["enhancement", "security"],
    created_at=datetime.now(),
    updated_at=datetime.now(),
    pr_number=123,
    url="https://github.com/owner/repo/pull/123"
)

# Serialize to dict
metadata_dict = pr_metadata.model_dump()

# Exclude None values
metadata_dict = pr_metadata.model_dump(exclude_none=True)
```

### Working with Dataclasses

```python
from src.pr_agents.pr_processing.analysis_models import TitleAnalysis, TitleQuality

# Create analysis result
title_analysis = TitleAnalysis(
    length=35,
    word_count=5,
    has_emoji=False,
    has_prefix=True,
    has_ticket_reference=True,
    is_question=False,
    is_wip=False
)

# Convert to dict
from dataclasses import asdict
analysis_dict = asdict(title_analysis)
```

## Model Design Principles

1. **Strict Isolation**: Each model represents a single, isolated component
2. **Type Safety**: All fields are properly typed with Python type hints
3. **Immutability**: Dataclasses are used for internal results to ensure immutability
4. **Validation**: Pydantic models validate external data automatically
5. **Performance**: Dataclasses provide better performance for internal processing
6. **Extensibility**: Easy to add new fields while maintaining backward compatibility

## Best Practices

1. **Use Pydantic models** for:
   - External API data parsing
   - Data validation
   - Serialization/deserialization

2. **Use dataclasses** for:
   - Internal processing results
   - Performance-critical operations
   - Simple data containers

3. **Always handle None values** appropriately when working with optional fields

4. **Use model_dump()** for Pydantic models and `asdict()` for dataclasses when converting to dictionaries

5. **Keep models focused** - each model should represent a single concept or component