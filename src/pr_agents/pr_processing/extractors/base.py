"""
Base extractor interface for PR component extraction.
"""

from abc import ABC, abstractmethod
from typing import Any

from github import Github
from github.PullRequest import PullRequest


class BaseExtractor(ABC):
    """Base class for all PR component extractors."""

    def __init__(self, github_client: Github) -> None:
        self.github_client = github_client

    @abstractmethod
    def extract(self, pr: PullRequest) -> dict[str, Any] | None:
        """
        Extract specific component data from a PR.

        Args:
            pr: GitHub PR object

        Returns:
            Dictionary containing extracted data or None if extraction fails
        """
        pass

    @property
    @abstractmethod
    def component_name(self) -> str:
        """Name of the component this extractor handles."""
        pass
