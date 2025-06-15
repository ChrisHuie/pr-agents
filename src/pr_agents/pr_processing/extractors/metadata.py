"""
Metadata extractor - handles PR title, description, labels, etc.
"""

from typing import Any

from github.PullRequest import PullRequest

from ..models import PRMetadata
from .base import BaseExtractor


class MetadataExtractor(BaseExtractor):
    """Extracts PR metadata without any code or review context."""

    @property
    def component_name(self) -> str:
        return "metadata"

    def extract(self, pr: PullRequest) -> dict[str, Any] | None:
        """Extract PR metadata only."""
        try:
            metadata = PRMetadata(
                title=pr.title,
                description=pr.body,
                author=pr.user.login,
                state=pr.state,
                labels=[label.name for label in pr.labels],
                milestone=pr.milestone.title if pr.milestone else None,
                assignees=[assignee.login for assignee in pr.assignees],
                created_at=pr.created_at,
                updated_at=pr.updated_at,
                merged_at=pr.merged_at,
                pr_number=pr.number,
                url=pr.html_url,
            )

            return metadata.model_dump()

        except Exception:
            return None
