"""
Builder pattern for creating repository configurations programmatically.
"""

from typing import Any

from .models import (
    DetectionStrategy,
    FetchStrategy,
    ModuleCategory,
    ModulePattern,
    RepositoryRelationship,
    RepositoryStructure,
    VersionConfig,
)


class ModulePatternBuilder:
    """Builder for ModulePattern objects."""

    def __init__(self, pattern: str):
        self._pattern = pattern
        self._pattern_type = "glob"
        self._name_extraction: str | None = None
        self._exclude_patterns: list[str] = []

    def with_type(self, pattern_type: str) -> "ModulePatternBuilder":
        """Set pattern type."""
        self._pattern_type = pattern_type
        return self

    def with_name_extraction(self, extraction: str) -> "ModulePatternBuilder":
        """Set name extraction rule."""
        self._name_extraction = extraction
        return self

    def exclude(self, *patterns: str) -> "ModulePatternBuilder":
        """Add exclusion patterns."""
        self._exclude_patterns.extend(patterns)
        return self

    def build(self) -> ModulePattern:
        """Build the pattern."""
        return ModulePattern(
            pattern=self._pattern,
            pattern_type=self._pattern_type,
            name_extraction=self._name_extraction,
            exclude_patterns=self._exclude_patterns,
        )


class ModuleCategoryBuilder:
    """Builder for ModuleCategory objects."""

    def __init__(self, name: str):
        self._name = name
        self._display_name = name
        self._paths: list[str] = []
        self._patterns: list[ModulePattern] = []
        self._detection_strategy = DetectionStrategy.FILENAME_PATTERN
        self._metadata_field: str | None = None
        self._metadata_value: str | None = None

    def display_name(self, name: str) -> "ModuleCategoryBuilder":
        """Set display name."""
        self._display_name = name
        return self

    def with_paths(self, *paths: str) -> "ModuleCategoryBuilder":
        """Add paths."""
        self._paths.extend(paths)
        return self

    def with_pattern(
        self, pattern: str | ModulePattern | ModulePatternBuilder
    ) -> "ModuleCategoryBuilder":
        """Add a pattern."""
        if isinstance(pattern, str):
            self._patterns.append(ModulePattern(pattern=pattern))
        elif isinstance(pattern, ModulePatternBuilder):
            self._patterns.append(pattern.build())
        else:
            self._patterns.append(pattern)
        return self

    def with_detection(self, strategy: DetectionStrategy) -> "ModuleCategoryBuilder":
        """Set detection strategy."""
        self._detection_strategy = strategy
        return self

    def with_metadata(self, field: str, value: str) -> "ModuleCategoryBuilder":
        """Set metadata detection."""
        self._metadata_field = field
        self._metadata_value = value
        return self

    def build(self) -> ModuleCategory:
        """Build the category."""
        return ModuleCategory(
            name=self._name,
            display_name=self._display_name,
            paths=self._paths,
            patterns=self._patterns,
            detection_strategy=self._detection_strategy,
            metadata_field=self._metadata_field,
            metadata_value=self._metadata_value,
        )


class RepositoryBuilder:
    """Builder for RepositoryStructure objects."""

    def __init__(self, repo_name: str):
        self._repo_name = repo_name
        self._repo_type = ""
        self._description: str | None = None
        self._detection_strategy = DetectionStrategy.FILENAME_PATTERN
        self._fetch_strategy = FetchStrategy.FILENAMES_ONLY
        self._module_categories: dict[str, ModuleCategory] = {}
        self._version_configs: list[VersionConfig] = []
        self._core_paths: list[str] = []
        self._test_paths: list[str] = []
        self._doc_paths: list[str] = []
        self._exclude_paths: list[str] = []
        self._relationships: list[RepositoryRelationship] = []
        self._metadata: dict[str, Any] = {}

    def of_type(self, repo_type: str) -> "RepositoryBuilder":
        """Set repository type."""
        self._repo_type = repo_type
        return self

    def with_description(self, description: str) -> "RepositoryBuilder":
        """Set description."""
        self._description = description
        return self

    def with_strategies(
        self,
        detection: DetectionStrategy | None = None,
        fetch: FetchStrategy | None = None,
    ) -> "RepositoryBuilder":
        """Set strategies."""
        if detection:
            self._detection_strategy = detection
        if fetch:
            self._fetch_strategy = fetch
        return self

    def add_module_category(
        self, category: ModuleCategory | ModuleCategoryBuilder
    ) -> "RepositoryBuilder":
        """Add a module category."""
        if isinstance(category, ModuleCategoryBuilder):
            category = category.build()
        self._module_categories[category.name] = category
        return self

    def add_version_config(self, version_config: VersionConfig) -> "RepositoryBuilder":
        """Add version configuration."""
        self._version_configs.append(version_config)
        return self

    def with_paths(
        self,
        core: list[str] | None = None,
        test: list[str] | None = None,
        docs: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> "RepositoryBuilder":
        """Set various paths."""
        if core:
            self._core_paths = core
        if test:
            self._test_paths = test
        if docs:
            self._doc_paths = docs
        if exclude:
            self._exclude_paths = exclude
        return self

    def add_relationship(
        self, rel_type: str, target: str, description: str | None = None
    ) -> "RepositoryBuilder":
        """Add a relationship."""
        self._relationships.append(
            RepositoryRelationship(
                relationship_type=rel_type,
                target_repo=target,
                description=description,
            )
        )
        return self

    def with_metadata(self, **metadata: Any) -> "RepositoryBuilder":
        """Add metadata."""
        self._metadata.update(metadata)
        return self

    def build(self) -> RepositoryStructure:
        """Build the repository structure."""
        return RepositoryStructure(
            repo_name=self._repo_name,
            repo_type=self._repo_type,
            description=self._description,
            default_detection_strategy=self._detection_strategy,
            fetch_strategy=self._fetch_strategy,
            module_categories=self._module_categories,
            version_configs=self._version_configs,
            core_paths=self._core_paths,
            test_paths=self._test_paths,
            doc_paths=self._doc_paths,
            exclude_paths=self._exclude_paths,
            relationships=self._relationships,
            metadata=self._metadata,
        )


# Convenience functions
def pattern(pattern_str: str) -> ModulePatternBuilder:
    """Create a pattern builder."""
    return ModulePatternBuilder(pattern_str)


def category(name: str) -> ModuleCategoryBuilder:
    """Create a category builder."""
    return ModuleCategoryBuilder(name)


def repository(name: str) -> RepositoryBuilder:
    """Create a repository builder."""
    return RepositoryBuilder(name)
