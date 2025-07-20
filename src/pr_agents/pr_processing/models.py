"""
Pydantic models for PR processing with strict data isolation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PRMetadata(BaseModel):
    """Isolated PR metadata - title, description, labels, etc."""

    title: str
    description: str | None = None
    author: str
    state: str = Field(..., description="open, closed, merged")
    labels: list[str] = Field(default_factory=list)
    milestone: str | None = None
    assignees: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    merged_at: datetime | None = None
    pr_number: int
    url: str


class FileDiff(BaseModel):
    """Individual file changes."""

    filename: str
    status: str = Field(..., description="added, modified, removed, renamed")
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: str | None = None
    previous_filename: str | None = None


class CodeChanges(BaseModel):
    """Isolated code changes - diffs, file modifications, etc."""

    total_additions: int = 0
    total_deletions: int = 0
    total_changes: int = 0
    changed_files: int = 0
    file_diffs: list[FileDiff] = Field(default_factory=list)
    base_sha: str
    head_sha: str
    merge_base_sha: str | None = None


class RepositoryInfo(BaseModel):
    """Isolated repository information."""

    name: str
    full_name: str
    owner: str
    description: str | None = None
    is_private: bool = False
    default_branch: str = "main"
    language: str | None = None
    languages: dict[str, int] = Field(default_factory=dict)
    topics: list[str] = Field(default_factory=list)
    base_branch: str
    head_branch: str
    fork_info: dict[str, Any] | None = None


class ReviewComment(BaseModel):
    """Individual review comment."""

    author: str
    body: str
    created_at: datetime
    updated_at: datetime
    position: int | None = None
    path: str | None = None
    commit_sha: str | None = None


class Review(BaseModel):
    """Individual PR review."""

    author: str
    state: str = Field(..., description="APPROVED, CHANGES_REQUESTED, COMMENTED")
    body: str | None = None
    submitted_at: datetime


class ReviewData(BaseModel):
    """Isolated review and discussion data."""

    reviews: list[Review] = Field(default_factory=list)
    comments: list[ReviewComment] = Field(default_factory=list)
    requested_reviewers: list[str] = Field(default_factory=list)
    approved_by: list[str] = Field(default_factory=list)
    changes_requested_by: list[str] = Field(default_factory=list)


class PRData(BaseModel):
    """Complete PR data with isolated components."""

    metadata: PRMetadata | None = None
    code_changes: CodeChanges | None = None
    repository_info: RepositoryInfo | None = None
    review_data: ReviewData | None = None
    modules: dict[str, Any] | None = None  # Module extraction data


class ProcessingResult(BaseModel):
    """Result from processing a specific component."""

    component: str = Field(
        ..., description="metadata, code_changes, repository, reviews"
    )
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    processing_time_ms: int | None = None
