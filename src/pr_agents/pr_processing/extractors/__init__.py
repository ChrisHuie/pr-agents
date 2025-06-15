"""
Extractors for different PR components with strict isolation.
"""

from .base import BaseExtractor
from .code_changes import CodeChangesExtractor
from .metadata import MetadataExtractor
from .repository import RepositoryExtractor
from .reviews import ReviewsExtractor

__all__ = [
    "BaseExtractor",
    "MetadataExtractor",
    "CodeChangesExtractor",
    "RepositoryExtractor",
    "ReviewsExtractor",
]
