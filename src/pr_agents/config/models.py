"""
Data models for repository structure configuration.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DetectionStrategy(Enum):
    """Strategy for detecting modules in a repository."""

    FILENAME_PATTERN = "filename_pattern"
    DIRECTORY_BASED = "directory_based"
    METADATA_FILE = "metadata_file"
    HYBRID = "hybrid"  # Combination of strategies


class FetchStrategy(Enum):
    """Strategy for fetching repository content."""

    FULL_CONTENT = "full_content"
    FILENAMES_ONLY = "filenames_only"
    DIRECTORY_NAMES = "directory_names"


@dataclass
class ModulePattern:
    """Pattern for identifying a specific type of module."""

    pattern: str  # e.g., "*BidAdapter.js" or "adapters/*"
    pattern_type: str  # "suffix", "prefix", "glob", "regex"
    name_extraction: str | None = None  # How to extract clean module name
    exclude_patterns: list[str] = field(default_factory=list)


@dataclass
class ModuleCategory:
    """Definition of a module category in a repository."""

    name: str  # e.g., "bid_adapter", "analytics_adapter"
    display_name: str  # e.g., "Bid Adapters"
    paths: list[str]  # Where to find these modules
    patterns: list[ModulePattern]  # Patterns to identify modules
    detection_strategy: DetectionStrategy = DetectionStrategy.FILENAME_PATTERN
    metadata_field: str | None = (
        None  # For metadata-based detection (e.g., "componentType")
    )
    metadata_value: str | None = (
        None  # Expected value in metadata field (e.g., "bidder")
    )


@dataclass
class VersionConfig:
    """Version-specific configuration for a repository."""

    version: str  # e.g., "v10.0"
    version_range: str | None = None  # e.g., ">=10.0"
    module_categories: dict[str, ModuleCategory] = field(default_factory=dict)
    metadata_path: str | None = None  # e.g., "metadata/modules/"
    metadata_pattern: str | None = None  # e.g., "*.json"
    notes: str | None = None


@dataclass
class RepositoryRelationship:
    """Defines relationships between repositories."""

    relationship_type: str  # e.g., "uses_modules_from", "extends", "documents"
    target_repo: str  # e.g., "prebid/prebid-server"
    description: str | None = None


@dataclass
class RepositoryStructure:
    """Complete structure definition for a repository."""

    # Basic info
    repo_name: str  # e.g., "prebid/Prebid.js"
    repo_type: str  # e.g., "prebid-js", "prebid-server-go"
    description: str | None = None

    # Detection configuration
    default_detection_strategy: DetectionStrategy = DetectionStrategy.FILENAME_PATTERN
    fetch_strategy: FetchStrategy = FetchStrategy.FILENAMES_ONLY

    # Module configuration
    module_categories: dict[str, ModuleCategory] = field(default_factory=dict)

    # Version-specific configurations
    version_configs: list[VersionConfig] = field(default_factory=list)
    default_version: str | None = None

    # Paths
    core_paths: list[str] = field(default_factory=list)
    test_paths: list[str] = field(default_factory=list)
    doc_paths: list[str] = field(default_factory=list)
    exclude_paths: list[str] = field(default_factory=list)

    # Relationships
    relationships: list[RepositoryRelationship] = field(default_factory=list)

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_module_category(
        self, category_name: str, version: str | None = None
    ) -> ModuleCategory | None:
        """Get module category configuration for a specific version."""
        # First check version-specific configs
        if version and self.version_configs:
            for ver_config in self.version_configs:
                if self._version_matches(version, ver_config):
                    if category_name in ver_config.module_categories:
                        return ver_config.module_categories[category_name]

        # Fall back to default
        return self.module_categories.get(category_name)

    def _version_matches(self, version: str, ver_config: VersionConfig) -> bool:
        """Check if a version matches a version configuration."""
        # Import here to avoid circular dependency
        from .version_utils import version_matches_range

        # Exact match
        if version == ver_config.version:
            return True

        # Version range check
        if ver_config.version_range:
            return version_matches_range(version, ver_config.version_range)

        return False


@dataclass
class RepositoryConfig:
    """Container for all repository configurations."""

    repositories: dict[str, RepositoryStructure] = field(default_factory=dict)

    def get_repository(self, repo_name: str) -> RepositoryStructure | None:
        """Get configuration for a specific repository."""
        return self.repositories.get(repo_name)

    def get_repositories_by_type(self, repo_type: str) -> list[RepositoryStructure]:
        """Get all repositories of a specific type."""
        return [
            repo for repo in self.repositories.values() if repo.repo_type == repo_type
        ]
