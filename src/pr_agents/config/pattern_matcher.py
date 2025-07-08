"""
Pattern matching utilities for file categorization.
"""

import fnmatch
import re
from functools import lru_cache

from .exceptions import InvalidPatternError
from .models import ModulePattern


# Cached functions to avoid memory leaks with lru_cache on methods
@lru_cache(maxsize=256)
def _match_suffix_cached(filepath: str, pattern: str) -> bool:
    """Match files with suffix pattern."""
    if pattern.startswith("*"):
        suffix = pattern[1:]
        return filepath.endswith(suffix)
    else:
        raise InvalidPatternError(f"Suffix pattern should start with '*': {pattern}")


@lru_cache(maxsize=256)
def _match_prefix_cached(filepath: str, pattern: str) -> bool:
    """Match files with prefix pattern."""
    if pattern.endswith("*"):
        prefix = pattern[:-1]
        filename = filepath.split("/")[-1]
        return filename.startswith(prefix)
    else:
        raise InvalidPatternError(f"Prefix pattern should end with '*': {pattern}")


@lru_cache(maxsize=256)
def _match_directory_cached(filepath: str, pattern: str) -> bool:
    """Match directory patterns."""
    if pattern.endswith("/*"):
        directory = pattern[:-2]
        return filepath.startswith(directory + "/")
    elif pattern.endswith("/**/*"):
        directory = pattern[:-5]
        return filepath.startswith(directory + "/")
    else:
        # Exact directory match
        parts = filepath.split("/")
        return pattern in parts[:-1]  # Exclude filename


@lru_cache(maxsize=256)
def _match_glob_cached(filepath: str, pattern: str) -> bool:
    """Match using glob pattern."""
    return fnmatch.fnmatch(filepath, pattern)


class PatternMatcher:
    """Handles pattern matching for file categorization."""

    def __init__(self):
        self._compiled_patterns: dict[str, re.Pattern] = {}

    def match_pattern(self, filepath: str, pattern: ModulePattern) -> bool:
        """
        Check if a filepath matches a pattern.

        Args:
            filepath: Path to match
            pattern: Pattern specification

        Returns:
            True if pattern matches
        """
        # Check exclusions first
        if self._is_excluded(filepath, pattern.exclude_patterns):
            return False

        # Match based on pattern type
        pattern_type = pattern.pattern_type.lower()

        if pattern_type == "suffix":
            return self._match_suffix(filepath, pattern.pattern)
        elif pattern_type == "prefix":
            return self._match_prefix(filepath, pattern.pattern)
        elif pattern_type == "regex":
            return self._match_regex(filepath, pattern.pattern)
        elif pattern_type == "directory":
            return self._match_directory(filepath, pattern.pattern)
        else:
            # Default to glob
            return self._match_glob(filepath, pattern.pattern)

    def extract_name(self, filepath: str, pattern: ModulePattern) -> str | None:
        """
        Extract module name from filepath based on pattern.

        Args:
            filepath: File path
            pattern: Pattern with extraction rules

        Returns:
            Extracted name or None
        """
        if not pattern.name_extraction:
            return None

        # Get filename without path
        filename = filepath.split("/")[-1]

        # Handle different extraction methods
        if pattern.name_extraction.startswith("remove_suffix:"):
            suffix = pattern.name_extraction.split(":", 1)[1]
            if filename.endswith(suffix + ".js"):
                return filename[: -len(suffix + ".js")]
            elif filename.endswith(suffix):
                return filename[: -len(suffix)]

        elif pattern.name_extraction.startswith("remove_prefix:"):
            prefix = pattern.name_extraction.split(":", 1)[1]
            if filename.startswith(prefix):
                return filename[len(prefix) :]

        elif pattern.name_extraction == "filename":
            # Return filename without extension
            return filename.rsplit(".", 1)[0]

        elif pattern.name_extraction == "directory":
            # Return parent directory name
            parts = filepath.split("/")
            return parts[-2] if len(parts) > 1 else None

        return None

    def _match_suffix(self, filepath: str, pattern: str) -> bool:
        """Match files with suffix pattern."""
        return _match_suffix_cached(filepath, pattern)

    def _match_prefix(self, filepath: str, pattern: str) -> bool:
        """Match files with prefix pattern."""
        return _match_prefix_cached(filepath, pattern)

    def _match_regex(self, filepath: str, pattern: str) -> bool:
        """Match using regular expression."""
        if pattern not in self._compiled_patterns:
            try:
                self._compiled_patterns[pattern] = re.compile(pattern)
            except re.error as e:
                raise InvalidPatternError(f"Invalid regex pattern: {pattern}") from e

        regex = self._compiled_patterns[pattern]
        return bool(regex.search(filepath))

    def _match_directory(self, filepath: str, pattern: str) -> bool:
        """Match directory patterns."""
        return _match_directory_cached(filepath, pattern)

    def _match_glob(self, filepath: str, pattern: str) -> bool:
        """Match using glob pattern."""
        return _match_glob_cached(filepath, pattern)

    def _is_excluded(self, filepath: str, exclude_patterns: list[str]) -> bool:
        """Check if filepath matches any exclusion pattern."""
        for exclude in exclude_patterns:
            if fnmatch.fnmatch(filepath, exclude):
                return True
        return False

    def find_best_match(
        self, filepath: str, patterns: list[ModulePattern]
    ) -> tuple[ModulePattern | None, float]:
        """
        Find the best matching pattern for a filepath.

        Args:
            filepath: Path to match
            patterns: List of patterns to try

        Returns:
            Tuple of (best_pattern, confidence_score)
        """
        matches = []

        for pattern in patterns:
            if self.match_pattern(filepath, pattern):
                # Calculate match score based on specificity
                score = self._calculate_match_score(filepath, pattern)
                matches.append((pattern, score))

        if not matches:
            return None, 0.0

        # Return highest scoring match
        return max(matches, key=lambda x: x[1])

    def _calculate_match_score(self, filepath: str, pattern: ModulePattern) -> float:
        """Calculate match score based on pattern specificity."""
        score = 0.5  # Base score for any match

        # More specific patterns get higher scores
        if pattern.pattern_type == "regex":
            score += 0.3
        elif pattern.pattern_type in ("suffix", "prefix"):
            score += 0.2

        # Patterns with name extraction are more specific
        if pattern.name_extraction:
            score += 0.1

        # Patterns with exclusions are more specific
        if pattern.exclude_patterns:
            score += 0.1

        return min(score, 1.0)
