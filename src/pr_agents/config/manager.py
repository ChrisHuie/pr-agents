"""
Repository structure configuration manager.
"""

import fnmatch
import re
from pathlib import Path
from typing import Any

from loguru import logger

from .exceptions import ConfigurationLoadError
from .loader import ConfigurationLoader
from .models import (
    DetectionStrategy,
    ModuleCategory,
    RepositoryConfig,
    RepositoryStructure,
)
from .pattern_matcher import PatternMatcher
from .watcher import ConfigurationWatcher


class RepositoryStructureManager:
    """Manages repository structure configurations."""

    def __init__(self, config_path: str = "config", enable_hot_reload: bool = False):
        """
        Initialize the repository structure manager.

        Args:
            config_path: Path to configuration directory or file
            enable_hot_reload: Enable automatic configuration reloading
        """
        self.config_path = config_path
        self.loader = ConfigurationLoader(config_path)
        self.config: RepositoryConfig | None = None
        self.pattern_matcher = PatternMatcher()
        self.enable_hot_reload = enable_hot_reload
        self._watcher: ConfigurationWatcher | None = None
        self._load_config()

        # Start watcher if hot reload is enabled
        if enable_hot_reload:
            self._start_watcher()

    def _load_config(self):
        """Load configuration from file."""
        try:
            self.config = self.loader.load_config()
            logger.info(
                f"Loaded {len(self.config.repositories)} repository configurations"
            )
        except Exception as e:
            logger.error(f"Error loading repository config: {e}")
            # Initialize with empty config but raise error
            self.config = RepositoryConfig()
            raise ConfigurationLoadError(
                f"Failed to load repository config: {e}"
            ) from e

    def get_repository(self, repo_url: str) -> RepositoryStructure | None:
        """Get repository structure for a given URL."""
        repo_name = self._extract_repo_name(repo_url)
        return self.config.get_repository(repo_name)

    def get_config_for_url(self, repo_url: str) -> dict[str, Any]:
        """
        Get enriched configuration for a repository URL.

        This method combines the base repository structure with knowledge
        from YAML files to provide a complete context for AI and other processors.

        Args:
            repo_url: Repository URL (e.g., https://github.com/owner/repo)

        Returns:
            Dictionary containing enriched repository configuration
        """
        repo = self.get_repository(repo_url)
        if not repo:
            logger.warning(f"No configuration found for repository: {repo_url}")
            return {}

        # Convert model to dict
        config = repo.model_dump(exclude_none=True)

        # Extract repository name for knowledge loading
        repo_name = self._extract_repo_name(repo_url)

        # Try to load and merge knowledge if available
        try:
            from .knowledge_loader import RepositoryKnowledgeLoader

            knowledge_loader = RepositoryKnowledgeLoader(self.config_path)
            enriched_config = knowledge_loader.load_repository_config(repo_name)

            # Merge knowledge into base config
            if enriched_config:
                # Preserve base config and overlay knowledge
                config.update(enriched_config)
                logger.debug(
                    f"Enriched configuration for {repo_name} with knowledge base"
                )
        except Exception as e:
            logger.warning(f"Could not load knowledge for {repo_name}: {e}")

        return config

    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL."""
        # Handle various URL formats
        # https://github.com/prebid/Prebid.js -> prebid/Prebid.js
        # git@github.com:prebid/Prebid.js.git -> prebid/Prebid.js

        # Remove protocol and domain
        if "github.com" in repo_url:
            if repo_url.startswith("git@"):
                # SSH format
                parts = repo_url.split(":")[-1]
            else:
                # HTTPS format
                parts = repo_url.split("github.com/")[-1]

            # Remove .git suffix
            if parts.endswith(".git"):
                parts = parts[:-4]

            return parts

        # Default: return as-is
        return repo_url

    def categorize_file(
        self, repo_url: str, filepath: str, version: str | None = None
    ) -> dict[str, Any]:
        """Categorize a file based on repository structure."""
        repo = self.get_repository(repo_url)
        if not repo:
            return {
                "categories": [],
                "module_type": None,
                "is_core": False,
                "is_test": False,
                "is_doc": False,
            }

        result = {
            "categories": [],
            "module_type": None,
            "is_core": self._is_path_type(filepath, repo.core_paths),
            "is_test": self._is_path_type(filepath, repo.test_paths),
            "is_doc": self._is_path_type(filepath, repo.doc_paths),
            "metadata": {},
        }

        # Check if file should be excluded
        if self._is_path_type(filepath, repo.exclude_paths):
            return result

        # Find matching module categories
        for cat_name, category in repo.module_categories.items():
            if self._matches_category(filepath, category, repo, version):
                result["categories"].append(cat_name)
                if not result["module_type"]:
                    result["module_type"] = category.display_name

        # Check version-specific categories
        if version and repo.version_configs:
            for ver_config in repo.version_configs:
                if repo._version_matches(version, ver_config):
                    for cat_name, category in ver_config.module_categories.items():
                        if self._matches_category(filepath, category, repo, version):
                            if cat_name not in result["categories"]:
                                result["categories"].append(cat_name)
                            if not result["module_type"]:
                                result["module_type"] = category.display_name

        return result

    def _matches_category(
        self,
        filepath: str,
        category: ModuleCategory,
        repo: RepositoryStructure,
        version: str | None = None,
    ) -> bool:
        """Check if a file matches a module category."""
        # First check if file is in one of the category paths
        in_path = False
        for path in category.paths:
            if filepath.startswith(path):
                in_path = True
                break

        if not in_path and category.paths:
            return False

        # For metadata-based detection in v10+ Prebid.js
        if category.detection_strategy == DetectionStrategy.METADATA_FILE:
            # File should be in metadata directory and match pattern
            for pattern in category.patterns:
                if self._matches_pattern(filepath, pattern):
                    return True
            return False

        # Check patterns
        for pattern in category.patterns:
            if self._matches_pattern(filepath, pattern):
                return True

        return False

    def _matches_pattern(self, filepath: str, pattern) -> bool:
        """Check if filepath matches a pattern."""
        # Handle exclusions first
        for exclude in pattern.exclude_patterns:
            if self._simple_match(filepath, exclude, pattern.pattern_type):
                return False

        # Check main pattern
        return self._simple_match(filepath, pattern.pattern, pattern.pattern_type)

    def _simple_match(self, filepath: str, pattern_str: str, pattern_type: str) -> bool:
        """Simple pattern matching based on type."""
        if pattern_type == "suffix":
            # Extract filename and check suffix
            filename = Path(filepath).name
            return filename.endswith(pattern_str.replace("*", ""))
        elif pattern_type == "prefix":
            filename = Path(filepath).name
            return filename.startswith(pattern_str.replace("*", ""))
        elif pattern_type == "glob":
            return fnmatch.fnmatch(filepath, pattern_str)
        elif pattern_type == "regex":
            return bool(re.match(pattern_str, filepath))
        elif pattern_type == "directory":
            # Check if file is in specified directory
            return filepath.startswith(pattern_str.replace("*", ""))
        else:
            # Default to glob
            return fnmatch.fnmatch(filepath, pattern_str)

    def _is_path_type(self, filepath: str, paths: list[str]) -> bool:
        """Check if filepath matches any of the given paths."""
        for path in paths:
            if "*" in path:
                if fnmatch.fnmatch(filepath, path):
                    return True
            elif filepath.startswith(path):
                return True
        return False

    def get_module_info(
        self, repo_url: str, filepath: str, version: str | None = None
    ) -> dict[str, Any]:
        """Get detailed module information for a file."""
        repo = self.get_repository(repo_url)
        if not repo:
            return {}

        categorization = self.categorize_file(repo_url, filepath, version)

        # Extract module name if applicable
        module_name = None
        if categorization["categories"]:
            # Check version-specific categories first
            if version and repo.version_configs:
                for ver_config in repo.version_configs:
                    if repo._version_matches(version, ver_config):
                        for cat_name in categorization["categories"]:
                            category = ver_config.module_categories.get(cat_name)
                            if category:
                                for pattern in category.patterns:
                                    if self._matches_pattern(filepath, pattern):
                                        module_name = self._extract_module_name(
                                            filepath, pattern
                                        )
                                        break
                                if module_name:
                                    break

            # Fall back to default categories
            if not module_name:
                for cat_name in categorization["categories"]:
                    category = repo.module_categories.get(cat_name)
                    if category:
                        for pattern in category.patterns:
                            if self._matches_pattern(filepath, pattern):
                                module_name = self._extract_module_name(
                                    filepath, pattern
                                )
                                break
                        if module_name:
                            break

        return {
            **categorization,
            "module_name": module_name,
            "repo_type": repo.repo_type,
        }

    def _extract_module_name(self, filepath: str, pattern) -> str | None:
        """Extract clean module name from filepath."""
        filename = Path(filepath).stem  # Remove extension

        if pattern.name_extraction:
            if pattern.name_extraction.startswith("remove_suffix:"):
                suffix = pattern.name_extraction.split(":", 1)[1]
                if filename.endswith(suffix):
                    return filename[: -len(suffix)]
            elif pattern.name_extraction.startswith("remove_prefix:"):
                prefix = pattern.name_extraction.split(":", 1)[1]
                if filename.startswith(prefix):
                    return filename[len(prefix) :]

        return filename

    def get_related_repositories(self, repo_url: str) -> list[tuple[str, str]]:
        """Get repositories related to the given repository."""
        repo = self.get_repository(repo_url)
        if not repo:
            return []

        related = []
        for relationship in repo.relationships:
            related.append((relationship.target_repo, relationship.relationship_type))

        return related

    def _start_watcher(self):
        """Start the configuration watcher."""
        from .watcher import ConfigurationWatcher

        self._watcher = ConfigurationWatcher(
            self.config_path, callback=self._on_config_reload
        )
        self._watcher.start()
        logger.info("Configuration hot-reloading enabled")

    def _on_config_reload(self, new_config: RepositoryConfig):
        """Handle configuration reload."""
        self.config = new_config
        logger.info(
            f"Configuration reloaded: {len(new_config.repositories)} repositories"
        )

    def stop_watching(self):
        """Stop watching for configuration changes."""
        if self._watcher:
            self._watcher.stop()
            self._watcher = None

    def reload_config(self):
        """Manually reload the configuration."""
        self._load_config()
        logger.info("Configuration manually reloaded")
