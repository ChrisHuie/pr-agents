"""
Component manager for extractor and processor lifecycle management.
"""

from typing import Any

from github import Github
from loguru import logger

from ...logging_config import log_processing_step
from ..extractors import (
    BaseExtractor,
    CodeChangesExtractor,
    MetadataExtractor,
    RepositoryExtractor,
    ReviewsExtractor,
)
from ..processors import BaseProcessor, CodeProcessor, MetadataProcessor, RepoProcessor


class ComponentManager:
    """
    Manages the lifecycle and registry of extractors and processors.

    Provides centralized component initialization and lookup.
    """

    def __init__(self, github_client: Github) -> None:
        """
        Initialize component manager with GitHub client.

        Args:
            github_client: Authenticated GitHub client
        """
        self.github_client = github_client
        self._extractors: dict[str, BaseExtractor] = {}
        self._processors: dict[str, BaseProcessor] = {}

        # Initialize components
        self._initialize_extractors()
        self._initialize_processors()

    def _initialize_extractors(self) -> None:
        """Initialize all available extractors."""
        logger.info("Initializing extractors")

        self._extractors = {
            "metadata": MetadataExtractor(self.github_client),
            "code_changes": CodeChangesExtractor(self.github_client),
            "repository": RepositoryExtractor(self.github_client),
            "reviews": ReviewsExtractor(self.github_client),
        }

        log_processing_step(f"Initialized {len(self._extractors)} extractors")

    def _initialize_processors(self) -> None:
        """Initialize all available processors."""
        logger.info("Initializing processors")

        self._processors = {
            "metadata": MetadataProcessor(),
            "code_changes": CodeProcessor(),
            "repository": RepoProcessor(),
        }

        log_processing_step(f"Initialized {len(self._processors)} processors")

    def get_extractor(self, name: str) -> BaseExtractor | None:
        """
        Get an extractor by name.

        Args:
            name: Name of the extractor

        Returns:
            Extractor instance or None if not found
        """
        return self._extractors.get(name)

    def get_processor(self, name: str) -> BaseProcessor | None:
        """
        Get a processor by name.

        Args:
            name: Name of the processor

        Returns:
            Processor instance or None if not found
        """
        return self._processors.get(name)

    def get_extractors(self, names: set[str] | None = None) -> dict[str, BaseExtractor]:
        """
        Get multiple extractors by name.

        Args:
            names: Set of extractor names (None for all)

        Returns:
            Dictionary of extractors
        """
        if names is None:
            return self._extractors.copy()

        return {
            name: extractor
            for name, extractor in self._extractors.items()
            if name in names
        }

    def get_processors(
        self, names: list[str] | None = None
    ) -> dict[str, BaseProcessor]:
        """
        Get multiple processors by name.

        Args:
            names: List of processor names (None for all)

        Returns:
            Dictionary of processors
        """
        if names is None:
            return self._processors.copy()

        return {
            name: processor
            for name, processor in self._processors.items()
            if name in names
        }

    def list_extractors(self) -> list[str]:
        """Get list of available extractor names."""
        return list(self._extractors.keys())

    def list_processors(self) -> list[str]:
        """Get list of available processor names."""
        return list(self._processors.keys())

    def register_processor(self, name: str, processor: BaseProcessor) -> None:
        """
        Register a new processor.

        Args:
            name: Name for the processor
            processor: Processor instance
        """
        logger.info(f"Registering processor: {name}")
        self._processors[name] = processor

    def get_component_data(
        self, pr_data: Any, component_name: str
    ) -> dict[str, Any] | None:
        """
        Get component data for processing.

        Args:
            pr_data: PR data object
            component_name: Name of the component

        Returns:
            Component data or None if not available
        """
        component_map = {
            "metadata": pr_data.metadata,
            "code_changes": pr_data.code_changes,
            "repository": pr_data.repository_info,
            "reviews": pr_data.review_data,
        }

        # Special handling for AI summaries processor
        if component_name == "ai_summaries":
            # AI processor needs multiple components
            # Extract repo URL from metadata if available
            repo_url = ""
            if pr_data.metadata and hasattr(pr_data.metadata, "url"):
                repo_url = pr_data.metadata.url

            return {
                "code": pr_data.code_changes,
                "metadata": pr_data.metadata,
                "repo_url": repo_url,
            }

        data = component_map.get(component_name)
        return data if data is not None else None
