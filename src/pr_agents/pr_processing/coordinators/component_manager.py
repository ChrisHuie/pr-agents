"""
Component manager for extractor and processor lifecycle management.
"""

from pathlib import Path
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
from ..extractors.modules import ModuleExtractor
from ..processors import BaseProcessor, CodeProcessor, MetadataProcessor, RepoProcessor
from ..processors.accuracy_validator import AccuracyValidator
from ..processors.module_processor import ModuleProcessor


class ComponentManager:
    """
    Manages the lifecycle and registry of extractors and processors.

    Provides centralized component initialization and lookup.
    """

    def __init__(
        self, github_client: Github, config_dir: Path | str | None = None
    ) -> None:
        """
        Initialize component manager with GitHub client.

        Args:
            github_client: Authenticated GitHub client
            config_dir: Optional configuration directory path
        """
        self.github_client = github_client
        self._extractors: dict[str, BaseExtractor] = {}
        self._processors: dict[str, BaseProcessor] = {}
        self.config_dir = Path(config_dir) if config_dir else None
        self._knowledge_loader = None

        # Lazy load knowledge loader if config dir provided
        if self.config_dir and self.config_dir.exists():
            try:
                from src.pr_agents.config.knowledge_loader import (
                    RepositoryKnowledgeLoader,
                )

                self._knowledge_loader = RepositoryKnowledgeLoader(self.config_dir)
            except ImportError:
                logger.warning("Knowledge loader not available")

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
            "modules": ModuleExtractor(self.github_client),
        }

        log_processing_step(f"Initialized {len(self._extractors)} extractors")

    def _initialize_processors(self) -> None:
        """Initialize all available processors."""
        logger.info("Initializing processors")

        self._processors = {
            "metadata": MetadataProcessor(),
            "code_changes": CodeProcessor(),
            "repository": RepoProcessor(),
            "accuracy_validation": AccuracyValidator(),
            "modules": ModuleProcessor(),
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

    def configure_for_repository(self, repo_full_name: str) -> None:
        """
        Configure components for a specific repository.

        Args:
            repo_full_name: Full repository name (e.g., "prebid/Prebid.js")
        """
        if not self._knowledge_loader:
            logger.debug(f"No knowledge loader available for {repo_full_name}")
            return

        try:
            # Load enriched configuration
            config = self._knowledge_loader.load_repository_config(repo_full_name)

            # Configure module extractor if available
            module_extractor = self._extractors.get("modules")
            if module_extractor and hasattr(module_extractor, "set_repository_config"):
                module_extractor.set_repository_config(config)
                logger.info(f"Configured module extractor for {repo_full_name}")

        except Exception as e:
            logger.error(f"Error configuring for repository {repo_full_name}: {e}")

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
            "modules": pr_data.modules,
        }

        # Special handling for modules processor
        if component_name == "modules" and pr_data.modules is not None:
            # Modules processor needs repository info for context
            modules_data = (
                pr_data.modules.copy() if isinstance(pr_data.modules, dict) else {}
            )
            if pr_data.repository_info:
                repo_info = pr_data.repository_info
                if hasattr(repo_info, "model_dump"):
                    modules_data["repository"] = repo_info.model_dump()
                elif isinstance(repo_info, dict):
                    modules_data["repository"] = repo_info
            return modules_data

        # Special handling for AI summaries processor
        if component_name == "ai_summaries":
            # AI processor needs multiple components
            # Extract repo URL from metadata if available
            repo_url = ""
            if pr_data.metadata:
                # Extract repository URL from PR URL
                # Handle both object and dict cases
                if hasattr(pr_data.metadata, "url"):
                    pr_url = pr_data.metadata.url
                elif isinstance(pr_data.metadata, dict) and "url" in pr_data.metadata:
                    pr_url = pr_data.metadata["url"]
                else:
                    pr_url = ""
                if "github.com" in pr_url:
                    # Convert PR URL to repo URL
                    # https://github.com/owner/repo/pull/123 -> https://github.com/owner/repo
                    parts = pr_url.split("/")
                    if len(parts) >= 5:
                        repo_url = f"https://github.com/{parts[3]}/{parts[4]}"
                else:
                    repo_url = pr_url

            return {
                "code": pr_data.code_changes,
                "metadata": pr_data.metadata,
                "repo_url": repo_url,
            }

        data = component_map.get(component_name)
        return data if data is not None else None
