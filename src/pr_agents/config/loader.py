"""
Configuration loader for repository structures with multi-file support.
"""

import json
from pathlib import Path

from loguru import logger

from .exceptions import ConfigurationValidationError
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
from .validator import ConfigurationValidator


class ConfigurationLoader:
    """Loads repository configuration from JSON files with multi-file and inheritance support."""

    def __init__(self, config_path: str = "config", strict_mode: bool = False):
        """
        Initialize the configuration loader.

        Args:
            config_path: Path to the config directory, master config file, or legacy single file
            strict_mode: If True, fail fast on any validation errors (useful for CI/CD)
        """
        self.config_path = Path(config_path)
        self.strict_mode = strict_mode
        self._loaded_configs: dict[str, dict] = {}  # Cache for loaded JSON files
        self._resolved_repos: dict[str, RepositoryStructure] = (
            {}
        )  # Cache for resolved repos
        self._validator = self._initialize_validator()

    def _initialize_validator(self) -> ConfigurationValidator | None:
        """Initialize the configuration validator if schema exists."""
        # Look for schema file relative to config path
        if self.config_path.is_dir():
            schema_path = self.config_path / "schema" / "repository.schema.json"
        else:
            schema_path = self.config_path.parent / "schema" / "repository.schema.json"

        if schema_path.exists():
            try:
                return ConfigurationValidator(str(schema_path))
            except Exception as e:
                logger.warning(f"Failed to initialize validator: {e}")
        return None

    def load_config(self) -> RepositoryConfig:
        """
        Load all repository configurations.

        Supports:
        1. New multi-file format with config directory
        2. Legacy single file format (repository_structures.json)
        """
        # Check for legacy single file first
        legacy_file = Path("config/repository_structures.json")
        if not self.config_path.exists() and legacy_file.exists():
            logger.info("Using legacy configuration file")
            return self._load_from_single_file(legacy_file)

        # Check if config_path is a directory or file
        if self.config_path.is_dir():
            # Look for repositories.json in the directory
            master_file = self.config_path / "repositories.json"
            if master_file.exists():
                return self._load_from_master_file(master_file)
            else:
                # Fall back to loading all JSON files in repositories/ subdirectory
                return self._load_from_directory(self.config_path / "repositories")
        elif self.config_path.is_file():
            # Load from single file (backward compatibility)
            return self._load_from_single_file(self.config_path)
        else:
            raise FileNotFoundError(f"Configuration path not found: {self.config_path}")

    def _load_from_master_file(self, master_file: Path) -> RepositoryConfig:
        """Load configurations referenced in a master file."""
        with open(master_file) as f:
            master_data = json.load(f)

        config = RepositoryConfig()
        base_dir = master_file.parent

        # Load all referenced repository files
        for repo_path in master_data.get("repositories", []):
            full_path = base_dir / repo_path
            if full_path.exists():
                try:
                    repo_data = self._load_json_file(full_path)
                    repo_structure = self._parse_repository_with_inheritance(
                        repo_data, full_path.parent
                    )
                    if repo_structure and repo_structure.repo_name:
                        config.repositories[repo_structure.repo_name] = repo_structure
                        logger.info(f"Loaded config for {repo_structure.repo_name}")
                except Exception as e:
                    logger.error(f"Error loading {full_path}: {e}")
            else:
                logger.warning(f"Referenced file not found: {full_path}")

        return config

    def _load_from_directory(self, directory: Path) -> RepositoryConfig:
        """Load all JSON files from a directory structure."""
        config = RepositoryConfig()

        # Recursively find all JSON files
        for json_file in directory.rglob("*.json"):
            # Skip schema files and base configs
            if "schema" in str(json_file) or "base" in json_file.name:
                continue

            try:
                repo_data = self._load_json_file(json_file)
                if "repo_name" in repo_data:  # Only process if it's a repo config
                    repo_structure = self._parse_repository_with_inheritance(
                        repo_data, json_file.parent
                    )
                    if repo_structure and repo_structure.repo_name:
                        config.repositories[repo_structure.repo_name] = repo_structure
                        logger.info(f"Loaded config for {repo_structure.repo_name}")
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

        return config

    def _load_from_single_file(self, file_path: Path) -> RepositoryConfig:
        """Load configuration from a single file (backward compatibility)."""
        with open(file_path) as f:
            data = json.load(f)

        config = RepositoryConfig()

        # Check if it's a new format single repo file
        if "repo_name" in data and "repo_type" in data:
            # New format: single repository definition
            repo_structure = self._parse_repository_with_inheritance(
                data, file_path.parent
            )
            if repo_structure:
                config.repositories[repo_structure.repo_name] = repo_structure
        else:
            # Old format: repos at the root level
            for repo_name, repo_data in data.items():
                if isinstance(repo_data, dict) and repo_name != "$schema":
                    repo_structure = self._parse_repository(repo_name, repo_data)
                    config.repositories[repo_name] = repo_structure

        return config

    def _load_json_file(self, file_path: Path) -> dict:
        """Load and cache a JSON file."""
        str_path = str(file_path)
        if str_path not in self._loaded_configs:
            with open(file_path) as f:
                data = json.load(f)

            # Validate if this looks like a repository config and we have a validator
            if self._validator and self._should_validate(data):
                is_valid, errors = self._validator.validate_config(data)
                if not is_valid:
                    error_msg = f"Validation failed for {file_path}:\n" + "\n".join(
                        errors
                    )
                    if self.strict_mode:
                        raise ConfigurationValidationError(error_msg)
                    else:
                        logger.warning(error_msg)

            self._loaded_configs[str_path] = data
        return self._loaded_configs[str_path]

    def _should_validate(self, data: dict) -> bool:
        """Check if data should be validated as a repository config."""
        # Validate if it has repository config fields
        return any(
            key in data for key in ["repo_name", "repo_type", "module_categories"]
        )

    def _parse_repository_with_inheritance(
        self, data: dict, base_dir: Path
    ) -> RepositoryStructure | None:
        """Parse a repository configuration with inheritance support."""
        # Handle inheritance
        if "extends" in data:
            base_path = base_dir / data["extends"]
            if base_path.exists():
                base_data = self._load_json_file(base_path)
                # Deep merge base data with current data
                merged_data = self._deep_merge(base_data, data)
                data = merged_data
            else:
                logger.warning(f"Base config not found: {base_path}")

        # Parse the repository
        repo_name = data.get("repo_name", "")
        if not repo_name:
            return None

        return self._parse_repository(repo_name, data)

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries, with override taking precedence."""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively merge dictionaries
                result[key] = self._deep_merge(result[key], value)
            elif (
                key in result
                and isinstance(result[key], list)
                and isinstance(value, list)
            ):
                # For lists, override completely (don't append)
                result[key] = value
            else:
                # Override value
                result[key] = value

        return result

    def _parse_repository(self, repo_name: str, data: dict) -> RepositoryStructure:
        """Parse a single repository configuration."""
        repo = RepositoryStructure(
            repo_name=repo_name,
            repo_type=data.get("repo_type", ""),
            description=data.get("description"),
        )

        # Parse detection and fetch strategies
        if "detection_strategy" in data:
            repo.default_detection_strategy = DetectionStrategy(
                data["detection_strategy"]
            )
        elif "default_detection_strategy" in data:  # Support old format
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

        # Parse version overrides (new format)
        if "version_overrides" in data:
            repo.version_configs = self._parse_version_overrides(
                data["version_overrides"]
            )
        # Also support old version_configs format
        elif "version_configs" in data:
            repo.version_configs = self._parse_version_configs(data["version_configs"])

        # Parse default version
        repo.default_version = data.get("default_version")

        # Parse paths (new structure)
        if "paths" in data:
            paths = data["paths"]
            repo.core_paths = paths.get("core", [])
            repo.test_paths = paths.get("test", [])
            repo.doc_paths = paths.get("docs", [])
            repo.exclude_paths = paths.get("exclude", [])
        else:
            # Support old format
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
                pattern_type=pattern_data.get(
                    "type", pattern_data.get("pattern_type", "glob")
                ),
                name_extraction=pattern_data.get("name_extraction"),
                exclude_patterns=pattern_data.get(
                    "exclude", pattern_data.get("exclude_patterns", [])
                ),
            )
            patterns.append(pattern)

        return patterns

    def _parse_version_overrides(self, overrides_data: dict) -> list[VersionConfig]:
        """Parse version overrides from new format."""
        from .version_utils import extract_version_and_range

        versions = []

        for version_key, version_data in overrides_data.items():
            # Extract version and range from key
            version, version_range = extract_version_and_range(version_key)

            version_config = VersionConfig(
                version=version,
                version_range=version_range,
            )

            # Parse module categories for this version
            if "module_categories" in version_data:
                version_config.module_categories = self._parse_module_categories(
                    version_data["module_categories"]
                )

            versions.append(version_config)

        return versions

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
                relationship_type=rel_data.get(
                    "type", rel_data.get("relationship_type", "")
                ),
                target_repo=rel_data.get("target", rel_data.get("target_repo", "")),
                description=rel_data.get("description"),
            )
            relationships.append(relationship)

        return relationships
