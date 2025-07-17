"""
Base PR Fetcher interface and abstract implementation.
"""

from abc import ABC, abstractmethod
from typing import Any

from github import Github, RateLimitExceededException
from loguru import logger

from src.pr_agents.utilities.rate_limit_manager import RateLimitManager


class BasePRFetcher(ABC):
    """
    Abstract base class for all PR fetchers.

    Follows the single responsibility principle - each fetcher
    focuses on one dimension of PR retrieval.
    """

    def __init__(self, github_token: str) -> None:
        """
        Initialize the fetcher with GitHub client.

        Args:
            github_token: GitHub API token for authentication
        """
        self.github_client = Github(github_token)
        self.rate_limit_manager = RateLimitManager()
        self.rate_limit_manager.set_github_client(self.github_client)
        logger.info(f"🔧 Initialized {self.__class__.__name__}")

    @abstractmethod
    def fetch(self, **kwargs) -> list[dict[str, Any]]:
        """
        Fetch PRs based on specific criteria.

        Returns:
            List of PR data dictionaries with minimal fields:
            - url: PR URL
            - number: PR number
            - title: PR title
            - author: PR author username
            - merged_at: Merge timestamp (ISO format)
            - labels: List of label names
            - Additional fields specific to the fetcher
        """
        pass

    def _build_pr_data(self, pr) -> dict[str, Any]:
        """
        Build standardized PR data dictionary from GitHub API response.

        Args:
            pr: GitHub PR object from search or direct API call

        Returns:
            Standardized PR data dictionary
        """
        return {
            "url": pr.html_url,
            "number": pr.number,
            "title": pr.title,
            "author": pr.user.login,
            "merged_at": (
                pr.pull_request.merged_at.isoformat()
                if hasattr(pr, "pull_request")
                and pr.pull_request
                and pr.pull_request.merged_at
                else None
            ),
            "labels": [label.name for label in pr.labels],
            "created_at": pr.created_at.isoformat(),
            "updated_at": pr.updated_at.isoformat(),
            "state": pr.state,
        }

    def _execute_with_rate_limit(self, func, *args, **kwargs):
        """
        Execute a function with rate limit handling.

        Args:
            func: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the function call
        """
        # Check rate limit before making the call
        self.rate_limit_manager.wait_if_needed()

        try:
            result = func(*args, **kwargs)
            self.rate_limit_manager.track_request()
            return result
        except RateLimitExceededException as e:
            self.rate_limit_manager.handle_rate_limit_exception(e)
            # Retry after waiting
            return func(*args, **kwargs)
