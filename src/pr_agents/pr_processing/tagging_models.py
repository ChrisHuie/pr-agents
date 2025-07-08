"""
Data models for PR tagging processor.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ImpactLevel(Enum):
    """Impact level of changes."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


@dataclass
class HierarchicalTag:
    """Represents a tag with hierarchical structure."""

    primary: str  # e.g., "source", "build", "dev"
    secondary: str | None = None  # e.g., "libraries", "core", "webpack"
    tertiary: str | None = None  # For deeper nesting if needed

    def to_string(self) -> str:
        """Convert to string representation."""
        parts = [self.primary]
        if self.secondary:
            parts.append(self.secondary)
        if self.tertiary:
            parts.append(self.tertiary)
        return ".".join(parts)

    @classmethod
    def from_path(cls, tag_path: list[str]) -> "HierarchicalTag":
        """Create from a path of tags."""
        primary = tag_path[0] if len(tag_path) > 0 else ""
        secondary = tag_path[1] if len(tag_path) > 1 else None
        tertiary = tag_path[2] if len(tag_path) > 2 else None
        return cls(primary=primary, secondary=secondary, tertiary=tertiary)


@dataclass
class FileTag:
    """Tags and metadata for a single file."""

    filepath: str
    hierarchical_tags: list[HierarchicalTag] = field(default_factory=list)
    flat_tags: list[str] = field(
        default_factory=list
    )  # Flattened version for easy access
    module_categories: list[str] = field(default_factory=list)
    module_name: str | None = None
    impact_level: ImpactLevel = ImpactLevel.MINIMAL
    is_core: bool = False
    is_test: bool = False
    is_doc: bool = False
    is_new_file: bool = False  # True if ++ pattern matched (new addition)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_hierarchical_tag(
        self,
        primary: str,
        secondary: str | None = None,
        tertiary: str | None = None,
    ):
        """Add a hierarchical tag."""
        tag = HierarchicalTag(primary, secondary, tertiary)
        self.hierarchical_tags.append(tag)
        self.flat_tags.append(tag.to_string())


@dataclass
class RuleMatch:
    """Represents a matched rule from YAML registry."""

    rule_name: str
    rule_class: str
    description: str
    scope: str = "per_file"  # per_file, per_pr, etc.
    matched_files: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    hierarchical_tags: list[HierarchicalTag] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaggingResult:
    """Complete result of PR tagging analysis."""

    # File-level analysis
    file_tags: dict[str, FileTag] = field(default_factory=dict)  # filepath -> FileTag

    # PR-level analysis
    pr_tags: set[str] = field(default_factory=set)  # Unique tags across all files
    pr_hierarchical_tags: list[HierarchicalTag] = field(default_factory=list)
    pr_impact_level: ImpactLevel = ImpactLevel.MINIMAL

    # Tag hierarchy summary
    tag_hierarchy: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    # e.g., {"source": {"libraries": ["file1.js"], "core": ["file2.js"]}}

    # Module analysis
    affected_modules: dict[str, list[str]] = field(
        default_factory=dict
    )  # module_type -> [module_names]
    module_categories: list[str] = field(default_factory=list)

    # Rule matches from YAML
    rule_matches: list[RuleMatch] = field(default_factory=list)

    # Summary statistics
    stats: dict[str, Any] = field(default_factory=dict)

    # Repository metadata
    repo_type: str | None = None
    repo_version: str | None = None

    def add_file_to_hierarchy(
        self, filepath: str, primary: str, secondary: str | None = None
    ):
        """Add a file to the tag hierarchy structure."""
        if primary not in self.tag_hierarchy:
            self.tag_hierarchy[primary] = {}

        if secondary:
            if secondary not in self.tag_hierarchy[primary]:
                self.tag_hierarchy[primary][secondary] = []
            self.tag_hierarchy[primary][secondary].append(filepath)
        else:
            if "_root" not in self.tag_hierarchy[primary]:
                self.tag_hierarchy[primary]["_root"] = []
            self.tag_hierarchy[primary]["_root"].append(filepath)


@dataclass
class YAMLRegistryStructure:
    """Structure from YAML registry file."""

    repo_url: str
    structure: dict[str, Any] = field(default_factory=dict)
    definitions: list[dict[str, Any]] = field(default_factory=list)
    rules: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class YAMLPattern:
    """Pattern definition from YAML structure."""

    path_components: list[str]  # e.g., ["source", "libraries"]
    pattern_type: str  # "++", "dir", "file", or specific pattern
    pattern_value: str | None = None  # The actual pattern if not "++"
    tags: list[str] = field(default_factory=list)
    impact: str | None = None

    def matches_new_addition(self) -> bool:
        """Check if this pattern is for new additions."""
        return self.pattern_type == "++"

    def get_hierarchical_tag(self) -> HierarchicalTag:
        """Get the hierarchical tag for this pattern."""
        return HierarchicalTag.from_path(self.path_components)
