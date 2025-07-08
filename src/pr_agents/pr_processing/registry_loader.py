"""
YAML registry loader for PR tagging.
"""

from pathlib import Path
from typing import Any

import yaml

from .tagging_models import YAMLPattern, YAMLRegistryStructure


class RegistryLoader:
    """Loads and manages YAML registry configurations."""

    def __init__(self, registry_path: str = "registry/prebid/"):
        self.registry_path = Path(registry_path)
        self.registry_cache: dict[str, YAMLRegistryStructure] = {}
        self._load_all_registries()

    def _load_all_registries(self):
        """Load all YAML files from the registry directory."""
        if not self.registry_path.exists():
            return

        for yaml_file in self.registry_path.glob("*.yaml"):
            try:
                registry = self._load_registry_file(yaml_file)
                if registry:
                    # Use filename as key for now
                    repo_key = yaml_file.stem
                    self.registry_cache[repo_key] = registry
            except Exception as e:
                # Log error but continue loading others
                print(f"Error loading {yaml_file}: {e}")

    def _load_registry_file(self, filepath: Path) -> YAMLRegistryStructure | None:
        """Load a single YAML registry file."""
        with open(filepath) as f:
            data = yaml.safe_load(f)

        if not data or "repo" not in data:
            return None

        registry = YAMLRegistryStructure(
            repo_url=data["repo"],
            structure=data.get("structure", {}),
            definitions=data.get("definitions", []),
            rules=data.get("rules", []),
        )

        return registry

    def get_repo_registry(self, repo_url: str) -> YAMLRegistryStructure | None:
        """Get registry for a specific repository."""
        # Try to match by URL
        for _key, registry in self.registry_cache.items():
            if registry.repo_url == repo_url or repo_url.endswith(registry.repo_url):
                return registry

        # Try to match by repo name
        repo_name = self._extract_repo_name(repo_url)
        for key, registry in self.registry_cache.items():
            if key.replace("-", ".").lower() == repo_name.replace("-", ".").lower():
                return registry

        return None

    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL."""
        if "/" in repo_url:
            return repo_url.split("/")[-1].replace(".git", "")
        return repo_url

    def parse_structure_patterns(
        self, structure: dict[str, Any], parent_path: list[str] = None
    ) -> list[YAMLPattern]:
        """Parse hierarchical structure into patterns."""
        if parent_path is None:
            parent_path = []

        patterns = []

        # Special pattern keys that indicate pattern types
        pattern_types = ["++", "endsWith", "includes", "dir", "file", "files", "path"]

        for key, value in structure.items():
            if key in pattern_types:
                # This is a pattern definition, not a path component
                if isinstance(value, dict):
                    # Pattern with metadata (tags, impact)
                    tags = value.get("tags", [])
                    impact = value.get("impact")

                    if key == "++":
                        pattern = YAMLPattern(
                            path_components=parent_path,
                            pattern_type="++",
                            pattern_value=None,
                            tags=tags,
                            impact=impact,
                        )
                        patterns.append(pattern)
                    elif key == "endsWith":
                        # endsWith can have nested patterns
                        for pattern_value, pattern_meta in value.items():
                            if isinstance(pattern_meta, dict):
                                tags = pattern_meta.get("tags", [])
                                impact = pattern_meta.get("impact")
                                pattern = YAMLPattern(
                                    path_components=parent_path,
                                    pattern_type="endsWith",
                                    pattern_value=pattern_value,
                                    tags=tags,
                                    impact=impact,
                                )
                                patterns.append(pattern)
                    elif key == "files":
                        # files can be a list or dict - handle dict case here
                        # For dict case, it contains pattern definitions
                        for pattern_value, pattern_meta in value.items():
                            if isinstance(pattern_meta, dict):
                                tags = pattern_meta.get("tags", [])
                                impact = pattern_meta.get("impact")
                                pattern = YAMLPattern(
                                    path_components=parent_path,
                                    pattern_type="file",
                                    pattern_value=pattern_value,
                                    tags=tags,
                                    impact=impact,
                                )
                                patterns.append(pattern)
                elif isinstance(value, list):
                    # Pattern is a list
                    if key == "files":
                        # Handle files: [{name: "*.go", tags: [...]}]
                        for item in value:
                            if isinstance(item, dict):
                                name = item.get("name", "")
                                tags = item.get("tags", [])
                                impact = item.get("impact")
                                pattern = YAMLPattern(
                                    path_components=parent_path,
                                    pattern_type="file",
                                    pattern_value=name,
                                    tags=tags,
                                    impact=impact,
                                )
                                patterns.append(pattern)
                            else:
                                # Simple string pattern
                                pattern = YAMLPattern(
                                    path_components=parent_path,
                                    pattern_type="file",
                                    pattern_value=str(item),
                                    tags=[],
                                    impact=None,
                                )
                                patterns.append(pattern)
                    else:
                        # Other list patterns
                        for item in value:
                            pattern = self._parse_pattern_item(item, parent_path)
                            if pattern:
                                patterns.append(pattern)
            else:
                # Regular path component
                current_path = parent_path + [key]

                if isinstance(value, dict):
                    # Nested structure - recurse
                    patterns.extend(self.parse_structure_patterns(value, current_path))
                elif isinstance(value, list):
                    # Could be a list of files patterns
                    if key == "files":
                        # Special handling for files list
                        for item in value:
                            if isinstance(item, dict):
                                name = item.get("name", "")
                                tags = item.get("tags", [])
                                impact = item.get("impact")
                                pattern = YAMLPattern(
                                    path_components=parent_path,  # adapters path
                                    pattern_type="file",
                                    pattern_value=name,
                                    tags=tags,
                                    impact=impact,
                                )
                                patterns.append(pattern)
                            else:
                                # Simple file pattern
                                pattern = YAMLPattern(
                                    path_components=parent_path,
                                    pattern_type="file",
                                    pattern_value=str(item),
                                    tags=[],
                                    impact=None,
                                )
                                patterns.append(pattern)
                    else:
                        # Regular list at this level
                        for item in value:
                            pattern = self._parse_pattern_item(item, current_path)
                            if pattern:
                                patterns.append(pattern)
                else:
                    # Single value
                    pattern = self._parse_pattern_item(value, current_path)
                    if pattern:
                        patterns.append(pattern)

        return patterns

    def _parse_pattern_item(
        self, item: Any, path_components: list[str]
    ) -> YAMLPattern | None:
        """Parse a single pattern item."""
        if isinstance(item, str):
            # Simple string pattern
            if item == "++":
                return YAMLPattern(
                    path_components=path_components,
                    pattern_type="++",
                    pattern_value=None,
                )
            elif item.startswith("dir:"):
                return YAMLPattern(
                    path_components=path_components,
                    pattern_type="dir",
                    pattern_value=item[4:].strip(),
                )
            elif item.startswith("file:"):
                return YAMLPattern(
                    path_components=path_components,
                    pattern_type="file",
                    pattern_value=item[5:].strip(),
                )
            else:
                # Complex pattern with functions
                return self._parse_complex_pattern(item, path_components)

        return None

    def _parse_complex_pattern(
        self, pattern_str: str, path_components: list[str]
    ) -> YAMLPattern | None:
        """Parse complex patterns like 'files(".ext")' or 'endsWith("pattern", file)'."""
        pattern = YAMLPattern(path_components=path_components, pattern_type="complex")

        # Check for various pattern types
        if "files(" in pattern_str:
            # Extract extension from files('.ext')
            import re

            match = re.search(r"files\(['\"](.+?)['\"]\)", pattern_str)
            if match:
                pattern.pattern_type = "files"
                pattern.pattern_value = match.group(1)
        elif "endsWith(" in pattern_str:
            # Extract suffix from endsWith('suffix', file)
            import re

            match = re.search(r"endsWith\(['\"](.+?)['\"]\s*,", pattern_str)
            if match:
                pattern.pattern_type = "endsWith"
                pattern.pattern_value = match.group(1)
        elif "includes(" in pattern_str:
            # Extract search string from includes('string', file, i)
            import re

            match = re.search(r"includes\(['\"](.+?)['\"]\s*,", pattern_str)
            if match:
                pattern.pattern_type = "includes"
                pattern.pattern_value = match.group(1)
        else:
            # Direct path pattern
            pattern.pattern_type = "path"
            pattern.pattern_value = pattern_str

        return pattern

    def get_impact_for_path(
        self, registry: YAMLRegistryStructure, path_components: list[str]
    ) -> str | None:
        """Determine impact level based on path hierarchy."""
        # Map certain paths to impact levels
        impact_mapping = {
            ("source", "core"): "high",
            ("source", "libraries"): "medium",
            ("source", "adapters"): "medium",
            ("build",): "high",
            ("testing",): "low",
            ("docs",): "minimal",
            ("dev",): "low",
        }

        # Check for matching impact
        for i in range(len(path_components), 0, -1):
            path_tuple = tuple(path_components[:i])
            if path_tuple in impact_mapping:
                return impact_mapping[path_tuple]

        return None
