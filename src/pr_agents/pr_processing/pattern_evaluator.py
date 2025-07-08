"""
Pattern evaluation system for PR tagging.
"""

import fnmatch
from pathlib import Path
from typing import Any

from .tagging_models import YAMLPattern


class PatternEvaluator:
    """Evaluates file paths against YAML patterns."""

    def __init__(self):
        self.pattern_cache = {}

    def evaluate_file(
        self, filepath: str, patterns: list[YAMLPattern], file_status: str = "modified"
    ) -> list[tuple[YAMLPattern, dict[str, Any]]]:
        """
        Evaluate a file against all patterns and return matches.

        Args:
            filepath: The file path to evaluate
            patterns: List of patterns to check
            file_status: Status of the file (added, modified, removed)

        Returns:
            List of tuples (pattern, match_info)
        """
        matches = []

        for pattern in patterns:
            match_info = self._match_pattern(filepath, pattern, file_status)
            if match_info["matches"]:
                matches.append((pattern, match_info))

        return matches

    def _match_pattern(
        self, filepath: str, pattern: YAMLPattern, file_status: str
    ) -> dict[str, Any]:
        """Check if a file matches a specific pattern."""
        # Build the expected path prefix from pattern components
        path_prefix = "/".join(pattern.path_components)

        # Check if file is under the expected path
        if not self._is_under_path(filepath, path_prefix):
            return {"matches": False}

        match_info = {
            "matches": False,
            "is_new_addition": False,
            "match_type": pattern.pattern_type,
            "hierarchical_tag": pattern.get_hierarchical_tag(),
        }

        # Handle different pattern types
        if pattern.pattern_type == "++":
            # Any new file under this path
            if file_status == "added":
                match_info["matches"] = True
                match_info["is_new_addition"] = True
            else:
                # For modified/removed files, still match but not as new addition
                match_info["matches"] = True

        elif pattern.pattern_type == "dir":
            # Check if file is in specified directory
            if pattern.pattern_value:
                full_pattern = f"{path_prefix}/{pattern.pattern_value}"
                if self._is_under_path(filepath, full_pattern):
                    match_info["matches"] = True

        elif pattern.pattern_type == "file":
            # Check for specific file or wildcard pattern
            if pattern.pattern_value:
                if "*" in pattern.pattern_value:
                    # Wildcard pattern
                    if path_prefix:
                        # Check if file is under path and matches pattern
                        if self._is_under_path(filepath, path_prefix):
                            filename = Path(filepath).name
                            if fnmatch.fnmatch(filename, pattern.pattern_value):
                                match_info["matches"] = True
                    else:
                        # No path restriction, just match filename
                        filename = Path(filepath).name
                        if fnmatch.fnmatch(filename, pattern.pattern_value):
                            match_info["matches"] = True
                else:
                    # Exact file match
                    if path_prefix:
                        full_pattern = f"{path_prefix}/{pattern.pattern_value}"
                        if filepath == full_pattern:
                            match_info["matches"] = True
                    else:
                        # Match just the filename
                        if (
                            filepath == pattern.pattern_value
                            or Path(filepath).name == pattern.pattern_value
                        ):
                            match_info["matches"] = True

        elif pattern.pattern_type == "files":
            # Check file extension
            if pattern.pattern_value and filepath.endswith(pattern.pattern_value):
                match_info["matches"] = True

        elif pattern.pattern_type == "endsWith":
            # Check if filename ends with pattern
            filename = Path(filepath).name
            if pattern.pattern_value and filename.endswith(pattern.pattern_value):
                match_info["matches"] = True

        elif pattern.pattern_type == "includes":
            # Case-insensitive substring match
            if (
                pattern.pattern_value
                and pattern.pattern_value.lower() in filepath.lower()
            ):
                match_info["matches"] = True

        elif pattern.pattern_type == "path":
            # Direct path pattern
            if pattern.pattern_value:
                full_pattern = f"{path_prefix}/{pattern.pattern_value}"
                if fnmatch.fnmatch(filepath, full_pattern):
                    match_info["matches"] = True

        return match_info

    def _is_under_path(self, filepath: str, path_prefix: str) -> bool:
        """Check if filepath is under the given path prefix."""
        # Normalize paths for comparison
        filepath = filepath.strip("/")
        path_prefix = path_prefix.strip("/")

        if not path_prefix:
            return True

        # Handle exact match or subpath
        if filepath == path_prefix or filepath.startswith(path_prefix + "/"):
            return True

        # For single-component paths like "modules", check if file starts with it
        if "/" not in path_prefix and filepath.startswith(path_prefix + "/"):
            return True

        return False

    def extract_module_info(
        self, filepath: str, pattern: YAMLPattern
    ) -> dict[str, Any]:
        """Extract module-specific information from a matched file."""
        module_info = {"module_type": None, "module_name": None}

        # Determine module type from pattern path
        if "modules" in pattern.path_components:
            # This is a module file
            idx = pattern.path_components.index("modules")
            if idx + 1 < len(pattern.path_components):
                module_info["module_type"] = pattern.path_components[idx + 1]

            # Extract module name from filename
            if pattern.pattern_type == "endsWith" and pattern.pattern_value:
                filename = Path(filepath).stem
                if filename.endswith(pattern.pattern_value):
                    module_info["module_name"] = filename[: -len(pattern.pattern_value)]
            else:
                module_info["module_name"] = Path(filepath).stem

        return module_info

    def determine_impact_level(
        self, filepath: str, matches: list[tuple[YAMLPattern, dict]], file_status: str
    ) -> str:
        """Determine impact level based on file path and matches."""
        # Priority order for impact levels
        impact_priority = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "minimal": 1,
        }

        # Collect all impact levels from various sources
        impact_levels = []

        # Get impact from pattern matches (from YAML definitions)
        for pattern, _match_info in matches:
            if hasattr(pattern, "impact") and pattern.impact:
                impact_levels.append(pattern.impact)

        # Default impact levels based on path components
        if any(pattern.path_components[0] == "build" for pattern, _ in matches):
            impact_levels.append("high")
        elif any(pattern.path_components[0] == "source" for pattern, _ in matches):
            if any("core" in pattern.path_components for pattern, _ in matches):
                impact_levels.append("high")
            else:
                impact_levels.append("medium")
        elif any(pattern.path_components[0] == "testing" for pattern, _ in matches):
            impact_levels.append("low")
        elif any(pattern.path_components[0] == "docs" for pattern, _ in matches):
            impact_levels.append("minimal")

        # Check for new additions to critical paths
        if file_status == "added":
            for pattern, match_info in matches:
                if match_info.get("is_new_addition") and pattern.path_components[0] in [
                    "source",
                    "build",
                ]:
                    impact_levels.append("high")

        # Return the highest priority impact level
        if impact_levels:
            # Sort by priority and return the highest
            sorted_impacts = sorted(
                impact_levels, key=lambda x: impact_priority.get(x, 0), reverse=True
            )
            return sorted_impacts[0]

        return "medium"  # Default
