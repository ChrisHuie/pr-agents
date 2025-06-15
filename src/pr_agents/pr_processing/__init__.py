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

__all__ = [
    "PRCoordinator",
    "PRData",
    "PRMetadata",
    "CodeChanges",
    "RepositoryInfo",
    "ReviewData",
    "ProcessingResult",
]
