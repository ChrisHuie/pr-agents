"""Integration tests for context loading with prebid repositories."""

from pathlib import Path

import pytest

from src.pr_agents.config.unified_manager import UnifiedRepositoryContextManager


class TestContextLoadingIntegration:
    """Test context loading for prebid repositories."""

    @pytest.fixture
    def context_manager(self):
        """Create context manager instance."""
        config_path = Path(__file__).parent.parent.parent / "config"
        return UnifiedRepositoryContextManager(
            config_path=str(config_path), enable_hot_reload=False, cache_contexts=True
        )

    def test_prebid_js_context_loading(self, context_manager):
        """Test loading context for Prebid.js repository."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Get full context
        context = context_manager.get_full_context(repo_url)

        # Verify basic information
        assert context.repo_name == "prebid/Prebid.js"
        assert context.repo_url == repo_url
        assert context.primary_language == "JavaScript"

        # Verify structure is loaded
        assert context.structure is not None
        assert context.structure.repo_type == "prebid-js"

        # Verify knowledge is parsed from JSON config
        assert context.knowledge is not None
        assert context.knowledge.purpose == "Prebid.js - Header Bidding Library"
        assert len(context.knowledge.key_features) > 0

        # Verify markdown context is loaded
        assert context.markdown_context is not None
        assert "Prebid.js" in context.markdown_context

        # Verify agent context provides defaults
        assert context.agent_context is not None
        assert len(context.agent_context.quality_indicators.good_pr) > 0

    def test_prebid_server_go_context_loading(self, context_manager):
        """Test loading context for Prebid Server Go repository."""
        repo_url = "https://github.com/prebid/prebid-server-go"

        context = context_manager.get_full_context(repo_url)

        assert context.repo_name == "prebid/prebid-server-go"
        # Primary language might be empty if structure is not loaded
        if context.structure:
            assert context.primary_language == "Go"

        # Verify markdown context
        assert context.markdown_context is not None
        assert "Prebid Server" in context.markdown_context

    def test_ai_context_generation(self, context_manager):
        """Test AI-optimized context generation."""
        repo_url = "https://github.com/prebid/Prebid.js"

        ai_context = context_manager.get_context_for_ai(repo_url)

        # Verify AI context structure
        assert ai_context["name"] == "prebid/Prebid.js"
        assert ai_context["type"] == "prebid-js"
        assert ai_context["primary_language"] == "JavaScript"
        assert ai_context["description"] == "Prebid.js - Header Bidding Library"

        # Verify module patterns are included
        assert "module_patterns" in ai_context
        assert "bid_adapter" in ai_context["module_patterns"]

        # Verify markdown context is included
        assert "markdown_context" in ai_context
        assert ai_context["markdown_context"] is not None

    def test_context_caching(self, context_manager):
        """Test that context is cached properly."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # First call should load context
        context1 = context_manager.get_full_context(repo_url)

        # Second call should return cached context
        context2 = context_manager.get_full_context(repo_url)

        # They should be the same object (cached)
        assert context1 is context2

        # Clear cache
        context_manager.clear_cache()

        # Third call should load fresh context
        context3 = context_manager.get_full_context(repo_url)
        assert context3 is not context1

    def test_batch_context_preloading(self, context_manager):
        """Test batch processing context optimization."""
        from src.pr_agents.services.ai import AIService

        ai_service = AIService()
        # Inject context manager
        ai_service.context_manager = context_manager

        repo_url = "https://github.com/prebid/Prebid.js"

        # Start batch - should preload context
        ai_service.start_batch(repo_url)

        # Verify context is cached
        assert repo_url in context_manager._context_cache

        # End batch
        ai_service.end_batch()

        # Context should still be cached
        assert repo_url in context_manager._context_cache

    @pytest.mark.parametrize(
        "repo_url,expected_type,expected_language",
        [
            ("https://github.com/prebid/Prebid.js", "prebid-js", "JavaScript"),
            (
                "https://github.com/prebid/prebid-server-java",
                "prebid-server-java",
                "Java",
            ),
            ("https://github.com/prebid/prebid-server-go", "prebid-server-go", "Go"),
            (
                "https://github.com/prebid/prebid-mobile-ios",
                "prebid-mobile-ios",
                "Swift",
            ),
            (
                "https://github.com/prebid/prebid-mobile-android",
                "prebid-mobile-android",
                "Kotlin",
            ),
        ],
    )
    def test_multiple_prebid_repos(
        self, context_manager, repo_url, expected_type, expected_language
    ):
        """Test context loading for various prebid repositories."""
        context = context_manager.get_full_context(repo_url)

        # Basic checks
        assert context.repo_url == repo_url

        if context.structure:
            assert context.structure.repo_type == expected_type
            assert context.primary_language == expected_language
        else:
            # If no structure, we might still have detected language from type
            if expected_language and context.primary_language:
                assert context.primary_language == expected_language
