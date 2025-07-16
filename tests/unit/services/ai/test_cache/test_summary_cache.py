"""Unit tests for summary cache."""

import time
from datetime import datetime

import pytest

from src.pr_agents.pr_processing.analysis_models import AISummaries, PersonaSummary
from src.pr_agents.pr_processing.models import CodeChanges, FileDiff
from src.pr_agents.services.ai.cache import SummaryCache


class TestSummaryCache:
    """Test cases for SummaryCache."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance with short TTL for testing."""
        return SummaryCache(ttl_seconds=2)  # 2 seconds for testing

    @pytest.fixture
    def sample_code_changes(self):
        """Create sample code changes."""
        return CodeChanges(
            file_diffs=[
                FileDiff(
                    filename="modules/exampleBidAdapter.js",
                    status="added",
                    additions=100,
                    deletions=0,
                    changes=100,
                    patch="+ code",
                ),
                FileDiff(
                    filename="test/spec/modules/exampleBidAdapter_spec.js",
                    status="added",
                    additions=50,
                    deletions=0,
                    changes=50,
                    patch="+ test",
                ),
            ],
            total_additions=150,
            total_deletions=0,
            total_changes=150,
            changed_files=2,
            base_sha="abc123",
            head_sha="def456",
        )

    @pytest.fixture
    def sample_summaries(self):
        """Create sample AI summaries."""
        return AISummaries(
            executive_summary=PersonaSummary(
                persona="executive",
                summary="Example adapter added",
                confidence=0.95,
            ),
            product_summary=PersonaSummary(
                persona="product",
                summary="Example adapter with banner support",
                confidence=0.90,
            ),
            developer_summary=PersonaSummary(
                persona="developer",
                summary="Example adapter implementation details",
                confidence=0.85,
            ),
            model_used="test-model",
            generation_timestamp=datetime.now(),
            cached=False,
        )

    def test_get_key_generation(self, cache, sample_code_changes):
        """Test cache key generation."""
        # Act
        key1 = cache.get_key(sample_code_changes, "prebid/Prebid.js", "prebid-js")
        key2 = cache.get_key(sample_code_changes, "prebid/Prebid.js", "prebid-js")
        key3 = cache.get_key(sample_code_changes, "other/repo", "other-type")

        # Assert
        assert key1 == key2  # Same inputs produce same key
        assert key1 != key3  # Different repo produces different key
        assert len(key1) == 16  # Key is truncated to 16 chars

    def test_set_and_get(self, cache, sample_summaries):
        """Test setting and getting cached summaries."""
        # Arrange
        key = "test-key"

        # Act
        cache.set(key, sample_summaries)
        result = cache.get(key)

        # Assert
        assert result is not None
        assert (
            result.executive_summary.summary
            == sample_summaries.executive_summary.summary
        )

    def test_get_expired(self, cache, sample_summaries):
        """Test getting expired cache entry."""
        # Arrange
        key = "test-key"
        cache.set(key, sample_summaries)

        # Act
        time.sleep(3)  # Wait for expiration
        result = cache.get(key)

        # Assert
        assert result is None

    def test_clear(self, cache, sample_summaries):
        """Test clearing cache."""
        # Arrange
        cache.set("key1", sample_summaries)
        cache.set("key2", sample_summaries)

        # Act
        cache.clear()

        # Assert
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cleanup_expired(self, cache, sample_summaries):
        """Test cleaning up expired entries."""
        # Arrange
        cache.set("key1", sample_summaries)
        time.sleep(1)
        cache.set("key2", sample_summaries)
        time.sleep(1.5)  # key1 is expired (2.5s old), key2 is not (1.5s old)

        # Act
        removed = cache.cleanup_expired()

        # Assert
        assert removed == 1
        assert cache.get("key1") is None
        assert cache.get("key2") is not None

    def test_change_magnitude_categorization(self, cache):
        """Test change magnitude categorization."""
        # Test small changes
        small_changes = CodeChanges(
            file_diffs=[],
            total_additions=20,
            total_deletions=10,
            total_changes=30,
            changed_files=1,
            base_sha="abc123",
            head_sha="def456",
        )
        assert cache._get_change_magnitude(small_changes) == "small"

        # Test medium changes
        medium_changes = CodeChanges(
            file_diffs=[],
            total_additions=200,
            total_deletions=100,
            total_changes=300,
            changed_files=5,
            base_sha="abc123",
            head_sha="def456",
        )
        assert cache._get_change_magnitude(medium_changes) == "medium"

        # Test large changes
        large_changes = CodeChanges(
            file_diffs=[],
            total_additions=600,
            total_deletions=400,
            total_changes=1000,
            changed_files=10,
            base_sha="abc123",
            head_sha="def456",
        )
        assert cache._get_change_magnitude(large_changes) == "large"

    def test_file_patterns_extraction(self, cache, sample_code_changes):
        """Test file pattern extraction."""
        # Act
        patterns = cache._get_file_patterns(sample_code_changes)

        # Assert
        assert "bid-adapter" in patterns
        assert "test" in patterns

    def test_file_patterns_various_types(self, cache):
        """Test pattern extraction for various file types."""
        # Arrange
        code_changes = CodeChanges(
            file_diffs=[
                FileDiff(
                    filename="modules/exampleBidAdapter.js",
                    status="added",
                    additions=100,
                    deletions=0,
                    changes=100,
                    patch="",
                ),
                FileDiff(
                    filename="modules/exampleAnalyticsAdapter.js",
                    status="added",
                    additions=50,
                    deletions=0,
                    changes=50,
                    patch="",
                ),
                FileDiff(
                    filename="src/core.js",
                    status="modified",
                    additions=20,
                    deletions=10,
                    changes=30,
                    patch="",
                ),
                FileDiff(
                    filename="package.json",
                    status="modified",
                    additions=5,
                    deletions=2,
                    changes=7,
                    patch="",
                ),
                FileDiff(
                    filename="README.md",
                    status="modified",
                    additions=10,
                    deletions=5,
                    changes=15,
                    patch="",
                ),
            ],
            total_additions=185,
            total_deletions=17,
            total_changes=202,
            changed_files=5,
            base_sha="abc123",
            head_sha="def456",
        )

        # Act
        patterns = cache._get_file_patterns(code_changes)

        # Assert
        expected_patterns = {
            "analytics-adapter",
            "bid-adapter",
            "config",
            "core",
            "docs",
        }
        assert set(patterns.split(",")) == expected_patterns

    def test_primary_directories(self, cache, sample_code_changes):
        """Test primary directory extraction."""
        # Act
        dirs = cache._get_primary_directories(sample_code_changes)

        # Assert
        assert "modules" in dirs
        assert "test" in dirs

    def test_find_similar_no_cache(self, cache, sample_code_changes):
        """Test finding similar entries when cache is empty."""
        # Act
        result = cache.find_similar(
            sample_code_changes, "prebid/Prebid.js", "prebid-js"
        )

        # Assert
        assert result is None

    def test_find_similar_exact_match(
        self, cache, sample_code_changes, sample_summaries
    ):
        """Test finding exact match in cache."""
        # Arrange
        key = cache.get_key(sample_code_changes, "prebid/Prebid.js", "prebid-js")
        cache.set(key, sample_summaries)

        # Act
        result = cache.find_similar(
            sample_code_changes, "prebid/Prebid.js", "prebid-js"
        )

        # Assert
        assert result is not None
        assert (
            result.executive_summary.summary
            == sample_summaries.executive_summary.summary
        )
