"""
Base coordinator interface for PR processing coordination.
"""

from abc import ABC, abstractmethod
from typing import Any

from github import Github


class BaseCoordinator(ABC):
    """
    Abstract base class for coordinators.

    Defines the interface for components that coordinate parts of the PR analysis pipeline.
    """

    def __init__(self, github_client: Github) -> None:
        """
        Initialize base coordinator.

        Args:
            github_client: Authenticated GitHub client
        """
        self.github_client = github_client

    @abstractmethod
    def coordinate(self, *args, **kwargs) -> Any:
        """
        Main coordination method to be implemented by subclasses.

        Returns:
            Coordination results (type depends on specific coordinator)
        """
        pass
