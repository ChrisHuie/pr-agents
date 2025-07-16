"""Cache implementation for AI summaries to ensure consistency."""

import hashlib
import time
from dataclasses import replace
from typing import Any

from src.pr_agents.pr_processing.analysis_models import AISummaries
from src.pr_agents.pr_processing.models import CodeChanges


class SummaryCache:
    """In-memory cache for AI-generated summaries.

    Ensures consistent summaries for similar code changes.
    """

    def __init__(self, ttl_seconds: int = 86400):
        """Initialize the cache.

        Args:
            ttl_seconds: Time to live for cache entries (default: 24 hours)
        """
        self.cache: dict[str, tuple[AISummaries, float]] = {}
        self.ttl_seconds = ttl_seconds

    def get_key(
        self,
        code_changes: CodeChanges,
        repo_name: str,
        repo_type: str,
    ) -> str:
        """Generate a cache key from code changes and repository info.

        The key is based on:
        - Repository name and type
        - File patterns (e.g., "*BidAdapter.js")
        - Change magnitude (small/medium/large)
        - Primary directories affected

        Args:
            code_changes: The code changes to cache
            repo_name: Repository name
            repo_type: Repository type (e.g., "prebid-js")

        Returns:
            Cache key string
        """
        key_parts = [
            repo_name,
            repo_type,
            self._get_change_magnitude(code_changes),
            self._get_file_patterns(code_changes),
            self._get_primary_directories(code_changes),
        ]

        # Create hash of key parts
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def get(self, key: str) -> AISummaries | None:
        """Retrieve cached summaries if available and not expired.

        Args:
            key: Cache key

        Returns:
            Cached AISummaries or None if not found/expired
        """
        if key in self.cache:
            summaries, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                # Return a copy to avoid modifying the cached instance
                return replace(
                    summaries,
                    executive_summary=replace(summaries.executive_summary),
                    product_summary=replace(summaries.product_summary),
                    developer_summary=replace(summaries.developer_summary),
                )
            else:
                # Expired, remove from cache
                del self.cache[key]
        return None

    def set(self, key: str, summaries: AISummaries) -> None:
        """Store summaries in cache.

        Args:
            key: Cache key
            summaries: AI summaries to cache
        """
        self.cache[key] = (summaries, time.time())

    def find_similar(
        self,
        code_changes: CodeChanges,
        repo_name: str,
        repo_type: str,
        similarity_threshold: float = 0.8,
    ) -> AISummaries | None:
        """Find cached summaries for similar code changes.

        Args:
            code_changes: Current code changes
            repo_name: Repository name
            repo_type: Repository type
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            Similar cached summaries or None
        """
        current_key = self.get_key(code_changes, repo_name, repo_type)

        # First try exact match
        exact_match = self.get(current_key)
        if exact_match:
            return exact_match

        # Then try similarity matching
        current_signature = self._get_change_signature(code_changes)

        for key, (summaries, timestamp) in list(self.cache.items()):
            # Skip expired entries
            if time.time() - timestamp >= self.ttl_seconds:
                del self.cache[key]
                continue

            # Check if repository matches
            if not key.startswith(repo_name[:8]):  # Rough check
                continue

            # For now, we'll use a simple pattern matching
            # In the future, this could use more sophisticated similarity metrics
            if (
                self._calculate_similarity(current_signature, key)
                >= similarity_threshold
            ):
                return summaries

        return None

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= self.ttl_seconds
        ]

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)

    def _get_change_magnitude(self, code_changes: CodeChanges) -> str:
        """Categorize change magnitude."""
        total_changes = code_changes.total_additions + code_changes.total_deletions

        if total_changes < 50:
            return "small"
        elif total_changes < 500:
            return "medium"
        else:
            return "large"

    def _get_file_patterns(self, code_changes: CodeChanges) -> str:
        """Extract file patterns from changed files."""
        patterns = []
        
        # Pattern rules: (pattern_name, check_function)
        pattern_rules = [
            # Adapter patterns
            ("bid-adapter", lambda f: f.endswith("BidAdapter.js")),
            ("analytics-adapter", lambda f: f.endswith("AnalyticsAdapter.js")),
            ("rtd-module", lambda f: f.endswith("RtdProvider.js")),
            ("user-module", lambda f: f.endswith("IdSystem.js")),
            ("adapter", lambda f: "adapter" in f.lower() and not any(
                f.endswith(x) for x in ["BidAdapter.js", "AnalyticsAdapter.js"]
            )),
            
            # Test patterns
            ("unit-test", lambda f: "test/spec/" in f or "_spec.js" in f),
            ("integration-test", lambda f: "test/integration/" in f),
            ("test", lambda f: ("test" in f.lower() or "spec" in f.lower()) and not any(
                x in f for x in ["test/spec/", "test/integration/", "_spec.js"]
            )),
            
            # Configuration patterns
            ("package-json", lambda f: f == "package.json"),
            ("webpack-config", lambda f: "webpack" in f and f.endswith(".js")),
            ("babel-config", lambda f: f.startswith(".babel") or f == "babel.config.js"),
            ("config", lambda f: f.endswith((".json", ".yaml", ".yml", ".toml")) and not any(
                x in f for x in ["package.json", "webpack", "babel"]
            )),
            
            # Documentation patterns
            ("readme", lambda f: f.lower() in ["readme.md", "readme.rst", "readme.txt"]),
            ("api-docs", lambda f: "docs/api/" in f or "api.md" in f),
            ("docs", lambda f: f.endswith((".md", ".rst", ".txt")) and not any(
                x in f for x in ["readme", "api", "changelog", "license"]
            )),
            
            # Core/Library patterns
            ("core-src", lambda f: "src/core/" in f or "src/prebid.js" == f),
            ("core", lambda f: ("src/" in f or "/core/" in f) and "src/core/" not in f),
            ("library", lambda f: "/lib/" in f or "/library/" in f or "libraries/" in f),
            
            # Build/CI patterns
            ("github-actions", lambda f: ".github/workflows/" in f),
            ("ci-config", lambda f: any(x in f for x in [".travis", ".circleci", "jenkins"])),
            ("build", lambda f: "gulpfile" in f or "Makefile" in f or "/build/" in f),
        ]

        for diff in code_changes.file_diffs:
            filename = diff.filename.lower()
            
            # Apply pattern rules
            for pattern_name, check_func in pattern_rules:
                if check_func(filename):
                    patterns.append(pattern_name)

        return ",".join(sorted(set(patterns)))

    def _get_primary_directories(self, code_changes: CodeChanges) -> str:
        """Get primary directories affected."""
        directories = set()

        for diff in code_changes.file_diffs:
            parts = diff.filename.split("/")
            if len(parts) > 1:
                directories.add(parts[0])

        # Return top 3 directories
        return ",".join(sorted(directories)[:3])

    def _get_change_signature(self, code_changes: CodeChanges) -> dict[str, Any]:
        """Create a signature of the changes for similarity comparison."""
        return {
            "magnitude": self._get_change_magnitude(code_changes),
            "patterns": self._get_file_patterns(code_changes),
            "directories": self._get_primary_directories(code_changes),
            "file_count": len(code_changes.file_diffs),
        }

    def _calculate_similarity(
        self,
        signature: dict[str, Any],
        cache_key: str,
    ) -> float:
        """Calculate similarity between current changes and cached entry.

        This is a simplified similarity calculation.
        In production, this could use more sophisticated metrics.
        """
        # For now, return 0 as we're using exact key matching
        # This method is a placeholder for future enhancement
        return 0.0
