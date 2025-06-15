"""
Code changes extractor - handles diffs, file modifications, etc.
"""

from typing import Any

from github.PullRequest import PullRequest

from ..models import CodeChanges, FileDiff
from .base import BaseExtractor


class CodeChangesExtractor(BaseExtractor):
    """Extracts code changes without any metadata or review context."""

    @property
    def component_name(self) -> str:
        return "code_changes"

    def extract(self, pr: PullRequest) -> dict[str, Any] | None:
        """Extract code changes and diffs only."""
        try:
            files = list(pr.get_files())

            file_diffs = []
            total_additions = 0
            total_deletions = 0

            for file in files:
                file_diff = FileDiff(
                    filename=file.filename,
                    status=file.status,
                    additions=file.additions,
                    deletions=file.deletions,
                    changes=file.changes,
                    patch=file.patch,
                    previous_filename=file.previous_filename,
                )
                file_diffs.append(file_diff)
                total_additions += file.additions
                total_deletions += file.deletions

            code_changes = CodeChanges(
                total_additions=total_additions,
                total_deletions=total_deletions,
                total_changes=total_additions + total_deletions,
                changed_files=len(files),
                file_diffs=file_diffs,
                base_sha=pr.base.sha,
                head_sha=pr.head.sha,
                merge_base_sha=pr.merge_commit_sha,
            )

            return code_changes.model_dump()

        except Exception:
            return None
