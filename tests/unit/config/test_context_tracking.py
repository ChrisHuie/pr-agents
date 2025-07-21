"""Unit tests for context tracking functionality."""

from src.pr_agents.config.context_tracker import (
    ContextSource,
    ContextTracker,
    ContextUsage,
    PRContextTracking,
)


class TestContextTracker:
    """Test context tracking functionality."""

    def test_singleton_pattern(self):
        """Test that ContextTracker follows singleton pattern."""
        tracker1 = ContextTracker()
        tracker2 = ContextTracker()
        assert tracker1 is tracker2

    def test_start_pr_tracking(self):
        """Test starting PR tracking."""
        tracker = ContextTracker()
        pr_url = "https://github.com/prebid/Prebid.js/pull/123"
        repo_name = "prebid/Prebid.js"

        tracking = tracker.start_pr_tracking(pr_url, repo_name)

        assert tracking.pr_url == pr_url
        assert tracking.repo_name == repo_name
        assert len(tracking.contexts) == 0

    def test_record_context_usage(self):
        """Test recording context usage."""
        tracker = ContextTracker()
        pr_url = "https://github.com/prebid/Prebid.js/pull/123"
        repo_name = "prebid/Prebid.js"

        # Start tracking
        tracker.start_pr_tracking(pr_url, repo_name)

        # Record successful load
        tracker.record_context_usage(
            pr_url=pr_url,
            context_name="repository_structure",
            source=ContextSource.JSON_CONFIG,
            loaded=True,
            is_default=False,
            file_path="/config/repositories.json",
            size_bytes=1024,
            load_time_ms=50.5,
            metadata={"repo_type": "prebid-js"},
        )

        # Record default context
        tracker.record_context_usage(
            pr_url=pr_url,
            context_name="agent_context",
            source=ContextSource.DEFAULT,
            loaded=True,
            is_default=True,
            size_bytes=512,
            load_time_ms=10.0,
        )

        # Record failed load
        tracker.record_context_usage(
            pr_url=pr_url,
            context_name="markdown_context",
            source=ContextSource.MARKDOWN,
            loaded=False,
            error="File not found",
            load_time_ms=5.0,
        )

        # Get tracking data
        tracking = tracker.get_pr_tracking(pr_url)
        assert tracking is not None
        assert len(tracking.contexts) == 3

        # Verify structure context
        struct_ctx = tracking.contexts["repository_structure"]
        assert struct_ctx.source == ContextSource.JSON_CONFIG
        assert struct_ctx.loaded is True
        assert struct_ctx.is_default is False
        assert struct_ctx.file_path == "/config/repositories.json"
        assert struct_ctx.size_bytes == 1024
        assert struct_ctx.load_time_ms == 50.5
        assert struct_ctx.metadata["repo_type"] == "prebid-js"

        # Verify default context
        agent_ctx = tracking.contexts["agent_context"]
        assert agent_ctx.source == ContextSource.DEFAULT
        assert agent_ctx.loaded is True
        assert agent_ctx.is_default is True

        # Verify failed context
        md_ctx = tracking.contexts["markdown_context"]
        assert md_ctx.source == ContextSource.MARKDOWN
        assert md_ctx.loaded is False
        assert md_ctx.error == "File not found"

    def test_get_summary(self):
        """Test getting context usage summary."""
        tracker = ContextTracker()
        pr_url = "https://github.com/prebid/Prebid.js/pull/456"
        repo_name = "prebid/Prebid.js"

        # Start tracking and add contexts
        tracker.start_pr_tracking(pr_url, repo_name)

        # Add various contexts
        tracker.record_context_usage(
            pr_url=pr_url,
            context_name="repository_structure",
            source=ContextSource.JSON_CONFIG,
            loaded=True,
            size_bytes=1024,
            load_time_ms=50.0,
        )

        tracker.record_context_usage(
            pr_url=pr_url,
            context_name="agent_context",
            source=ContextSource.DEFAULT,
            loaded=True,
            is_default=True,
            size_bytes=512,
            load_time_ms=10.0,
        )

        tracker.record_context_usage(
            pr_url=pr_url,
            context_name="markdown_context",
            source=ContextSource.MARKDOWN,
            loaded=False,
            error="Not found",
            load_time_ms=5.0,
        )

        # Get summary
        summary = tracker.get_summary(pr_url)
        assert summary is not None
        assert summary["pr_url"] == pr_url
        assert summary["repo_name"] == repo_name

        # Check summary stats
        stats = summary["summary"]
        assert stats["total_contexts"] == 3
        assert stats["loaded_count"] == 2
        assert stats["default_count"] == 1
        assert stats["error_count"] == 1
        assert stats["total_size_bytes"] == 1536  # 1024 + 512
        assert stats["total_load_time_ms"] == 65.0  # 50 + 10 + 5

        # Check individual contexts
        contexts = summary["contexts_loaded"]
        assert len(contexts) == 3
        assert "repository_structure" in contexts
        assert "agent_context" in contexts
        assert "markdown_context" in contexts

    def test_clear_tracking(self):
        """Test clearing tracking data."""
        tracker = ContextTracker()
        pr_url1 = "https://github.com/prebid/Prebid.js/pull/789"
        pr_url2 = "https://github.com/prebid/Prebid.js/pull/790"

        # Add tracking for two PRs
        tracker.start_pr_tracking(pr_url1, "prebid/Prebid.js")
        tracker.start_pr_tracking(pr_url2, "prebid/Prebid.js")

        # Clear specific PR
        tracker.clear_tracking(pr_url1)
        assert tracker.get_pr_tracking(pr_url1) is None
        assert tracker.get_pr_tracking(pr_url2) is not None

        # Clear all
        tracker.clear_tracking()
        assert tracker.get_pr_tracking(pr_url2) is None

    def test_context_usage_dataclass(self):
        """Test ContextUsage dataclass."""
        usage = ContextUsage(
            source=ContextSource.JSON_CONFIG,
            loaded=True,
            is_default=False,
            file_path="/config/test.json",
            size_bytes=2048,
            load_time_ms=100.5,
            error=None,
            metadata={"test": "value"},
        )

        assert usage.source == ContextSource.JSON_CONFIG
        assert usage.loaded is True
        assert usage.is_default is False
        assert usage.file_path == "/config/test.json"
        assert usage.size_bytes == 2048
        assert usage.load_time_ms == 100.5
        assert usage.error is None
        assert usage.metadata["test"] == "value"

    def test_pr_context_tracking_dataclass(self):
        """Test PRContextTracking dataclass."""
        tracking = PRContextTracking(
            pr_url="https://github.com/prebid/Prebid.js/pull/999",
            repo_name="prebid/Prebid.js",
        )

        # Add context
        usage = ContextUsage(
            source=ContextSource.CACHED,
            loaded=True,
            is_default=False,
        )
        tracking.add_context("test_context", usage)

        assert len(tracking.contexts) == 1
        assert "test_context" in tracking.contexts
        assert tracking.contexts["test_context"] == usage

    def test_cached_context_tracking(self):
        """Test tracking cached context usage."""
        tracker = ContextTracker()
        pr_url = "https://github.com/prebid/Prebid.js/pull/111"

        tracker.start_pr_tracking(pr_url, "prebid/Prebid.js")

        # Record cached context
        tracker.record_context_usage(
            pr_url=pr_url,
            context_name="unified_context",
            source=ContextSource.CACHED,
            loaded=True,
            is_default=False,
            metadata={"repo_url": "https://github.com/prebid/Prebid.js"},
        )

        tracking = tracker.get_pr_tracking(pr_url)
        cached_ctx = tracking.contexts["unified_context"]
        assert cached_ctx.source == ContextSource.CACHED
        assert cached_ctx.loaded is True
        assert cached_ctx.metadata["repo_url"] == "https://github.com/prebid/Prebid.js"
