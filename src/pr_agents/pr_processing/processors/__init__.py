"""
Processors for analyzing extracted PR components in isolation.
"""

from .base import BaseProcessor
from .code_processor import CodeProcessor
from .metadata_processor import MetadataProcessor
from .repo_processor import RepoProcessor

__all__ = [
    "BaseProcessor",
    "MetadataProcessor",
    "CodeProcessor",
    "RepoProcessor",
]
