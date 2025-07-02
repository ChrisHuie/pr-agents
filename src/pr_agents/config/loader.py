"""
Configuration loader for repository structures.
"""

import json
from pathlib import Path

from .models import (
    DetectionStrategy,
    FetchStrategy,
    ModuleCategory,
    ModulePattern,
    RepositoryConfig,
    RepositoryRelationship,
    RepositoryStructure,
    VersionConfig,
)


class ConfigurationLoader:
    """Loads repository configuration from JSON files."""

    def __init__(self, config_file: str = "config/repository_structures.json"):
        self.config_file = Path(config_file)

    def load_config(self) -> RepositoryConfig:
        """Load all repository configurations from JSON file."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")

        with open(self.config_file) as f:
            data = json.load(f)

        config = RepositoryConfig()

        for repo_name, repo_data in data.items():
            repo_structure = self._parse_repository(repo_name, repo_data)
            config.repositories[repo_name] = repo_structure

        return config

    def _parse_repository(self, repo_name: str, data: dict) -> RepositoryStructure:
        """Parse a single repository configuration."""
        repo = RepositoryStructure(
            repo_name=repo_name,
            repo_type=data.get("repo_type", ""),
            description=data.get("description"),
        )

        # Parse detection and fetch strategies
        if "default_detection_strategy" in data:
            repo.default_detection_strategy = DetectionStrategy(
                data["default_detection_strategy"]
            )

        if "fetch_strategy" in data:
            repo.fetch_strategy = FetchStrategy(data["fetch_strategy"])

        # Parse module categories
        if "module_categories" in data:
            repo.module_categories = self._parse_module_categories(
                data["module_categories"]
            )

        # Parse version configs
        if "version_configs" in data:
            repo.version_configs = self._parse_version_configs(data["version_configs"])

        # Parse default version
        repo.default_version = data.get("default_version")

        # Parse paths
        repo.core_paths = data.get("core_paths", [])
        repo.test_paths = data.get("test_paths", [])
        repo.doc_paths = data.get("doc_paths", [])
        repo.exclude_paths = data.get("exclude_paths", [])

        # Parse relationships
        if "relationships" in data:
            repo.relationships = self._parse_relationships(data["relationships"])

        # Parse metadata
        repo.metadata = data.get("metadata", {})

        return repo

    def _parse_module_categories(
        self, categories_data: dict
    ) -> dict[str, ModuleCategory]:
        """Parse module categories from configuration."""
        categories = {}

        for cat_name, cat_data in categories_data.items():
            category = ModuleCategory(
                name=cat_data.get("name", cat_name),
                display_name=cat_data.get("display_name", ""),
                paths=cat_data.get("paths", []),
                patterns=self._parse_patterns(cat_data.get("patterns", [])),
            )

            # Parse detection strategy
            if "detection_strategy" in cat_data:
                category.detection_strategy = DetectionStrategy(
                    cat_data["detection_strategy"]
                )

            # Parse metadata fields for metadata-based detection
            category.metadata_field = cat_data.get("metadata_field")
            category.metadata_value = cat_data.get("metadata_value")

            categories[cat_name] = category

        return categories

    def _parse_patterns(self, patterns_data: list[dict]) -> list[ModulePattern]:
        """Parse module patterns from configuration."""
        patterns = []

        for pattern_data in patterns_data:
            pattern = ModulePattern(
                pattern=pattern_data.get("pattern", ""),
                pattern_type=pattern_data.get("pattern_type", "glob"),
                name_extraction=pattern_data.get("name_extraction"),
                exclude_patterns=pattern_data.get("exclude_patterns", []),
            )
            patterns.append(pattern)

        return patterns

    def _parse_version_configs(self, versions_data: list[dict]) -> list[VersionConfig]:
        """Parse version-specific configurations."""
        versions = []

        for ver_data in versions_data:
            version = VersionConfig(
                version=ver_data.get("version", ""),
                version_range=ver_data.get("version_range"),
                metadata_path=ver_data.get("metadata_path"),
                metadata_pattern=ver_data.get("metadata_pattern"),
                notes=ver_data.get("notes"),
            )

            # Parse module categories for this version
            if "module_categories" in ver_data:
                version.module_categories = self._parse_module_categories(
                    ver_data["module_categories"]
                )

            versions.append(version)

        return versions

    def _parse_relationships(
        self, relationships_data: list[dict]
    ) -> list[RepositoryRelationship]:
        """Parse repository relationships."""
        relationships = []

        for rel_data in relationships_data:
            relationship = RepositoryRelationship(
                relationship_type=rel_data.get("relationship_type", ""),
                target_repo=rel_data.get("target_repo", ""),
                description=rel_data.get("description"),
            )
            relationships.append(relationship)

        return relationships
