"""
Repository extractor - handles repo info, branches, etc.
"""

from typing import Any

from github.PullRequest import PullRequest

from ..models import RepositoryInfo
from .base import BaseExtractor


class RepositoryExtractor(BaseExtractor):
    """Extracts repository information without any PR-specific context."""

    @property
    def component_name(self) -> str:
        return "repository"

    def extract(self, pr: PullRequest) -> dict[str, Any] | None:
        """Extract repository information only."""
        try:
            repo = pr.base.repo

            # Get languages (this is a separate API call, so handle gracefully)
            languages = {}
            try:
                languages = repo.get_languages()
            except Exception:
                pass

            # Get topics
            topics = []
            try:
                topics = repo.get_topics()
            except Exception:
                pass

            # Check if this is a fork
            fork_info = None
            if repo.fork and repo.parent:
                fork_info = {
                    "parent_full_name": repo.parent.full_name,
                    "parent_owner": repo.parent.owner.login,
                }

            repo_info = RepositoryInfo(
                name=repo.name,
                full_name=repo.full_name,
                owner=repo.owner.login,
                description=repo.description,
                is_private=repo.private,
                default_branch=repo.default_branch,
                language=repo.language,
                languages=languages,
                topics=topics,
                base_branch=pr.base.ref,
                head_branch=pr.head.ref,
                fork_info=fork_info,
            )

            return repo_info.model_dump()

        except Exception:
            return None
