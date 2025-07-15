"""
PR Processing module for analyzing GitHub Pull Requests with strict component isolation.
"""

from .coordinator import PRCoordinator
from .models import (
    CodeChanges,
    PRData,
    PRMetadata,
    ProcessingResult,
    RepositoryInfo,
    ReviewData,
)
from .pr_fetcher import PRFetcher

__all__ = [
    "PRCoordinator",
    "PRFetcher",
    "PRData",
    "PRMetadata",
    "CodeChanges",
    "RepositoryInfo",
    "ReviewData",
    "ProcessingResult",
]
