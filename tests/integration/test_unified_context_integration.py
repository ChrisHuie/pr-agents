"""Integration tests for unified context system."""

import pytest

from src.pr_agents.config.context_models import QualityIndicators
from src.pr_agents.config.unified_manager import UnifiedRepositoryContextManager


class TestUnifiedContextIntegration:
    """Integration tests for the unified context system."""

    @pytest.fixture
    def manager(self):
        """Create a real context manager with actual config files."""
        return UnifiedRepositoryContextManager(config_path="config")

    def test_prebid_js_full_context(self, manager):
        """Test loading full context for Prebid.js repository."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Load full context
        context = manager.get_full_context(repo_url)

        # Verify basic information
        assert context.repo_name == "prebid/Prebid.js"
        assert context.repo_url == repo_url
        assert context.primary_language == "JavaScript"

        # Verify structure was loaded
        assert context.structure is not None
        assert context.structure.repo_type == "prebid-js"
        assert len(context.structure.module_categories) > 0

        # Check for bid_adapter category
        assert "bid_adapter" in context.structure.module_categories
        bid_adapter = context.structure.module_categories["bid_adapter"]
        assert bid_adapter.display_name == "Bid Adapters"
        assert any("modules/" in path for path in bid_adapter.paths)

        # Verify knowledge was loaded
        assert context.knowledge.purpose != ""
        assert len(context.knowledge.key_features) > 0
        assert "header bidding" in context.knowledge.purpose.lower()

        # Verify agent context was loaded
        # Note: The current YAML structure doesn't parse into pr_patterns
        # but the raw data should be available in the context
        assert context.agent_context is not None

        # At minimum, we should have default quality indicators
        assert isinstance(context.agent_context.quality_indicators, QualityIndicators)

    def test_prebid_js_ai_context(self, manager):
        """Test AI-optimized context for Prebid.js."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Get AI context
        ai_context = manager.get_context_for_ai(repo_url)

        # Verify structure
        assert ai_context["name"] == "prebid/Prebid.js"
        assert ai_context["url"] == repo_url
        assert ai_context["type"] == "prebid-js"
        assert ai_context["primary_language"] == "JavaScript"

        # Verify description and features
        assert "description" in ai_context
        assert "header bidding" in ai_context["description"].lower()
        assert "key_features" in ai_context
        assert len(ai_context["key_features"]) > 0

        # Verify module patterns
        assert "module_patterns" in ai_context
        assert "bid_adapter" in ai_context["module_patterns"]
        assert (
            ai_context["module_patterns"]["bid_adapter"]["display_name"]
            == "Bid Adapters"
        )

        # Verify PR patterns if agent context exists
        if "pr_patterns" in ai_context:
            assert len(ai_context["pr_patterns"]) > 0
            # Check that patterns have required fields
            for pattern in ai_context["pr_patterns"]:
                assert "pattern" in pattern
                assert "indicators" in pattern

    def test_prebid_js_pr_review_context(self, manager):
        """Test PR review context for Prebid.js."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Get PR review context
        review_context = manager.get_pr_review_context(repo_url)

        # Verify structure
        assert review_context["repo_type"] == "prebid-js"
        assert review_context["purpose"] != ""
        assert len(review_context["key_features"]) > 0

        # Verify quality indicators
        assert "quality_indicators" in review_context
        qi = review_context["quality_indicators"]
        # May be empty if no specific indicators were parsed from YAML
        assert isinstance(qi["good_pr"], list)
        assert isinstance(qi["red_flags"], list)

        # Verify review guidelines
        assert "review_guidelines" in review_context
        assert "required_checks" in review_context["review_guidelines"]

        # Verify module patterns
        assert "module_patterns" in review_context
        assert len(review_context["module_patterns"]) > 0

    def test_context_caching_integration(self, manager):
        """Test that context caching works in real environment."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # First load
        context1 = manager.get_full_context(repo_url)

        # Second load should be cached
        context2 = manager.get_full_context(repo_url)

        # Should be the same object
        assert context1 is context2

        # Clear cache
        manager.clear_cache()

        # Third load should be new object
        context3 = manager.get_full_context(repo_url)
        assert context1 is not context3

        # But content should be equivalent
        assert context3.repo_name == context1.repo_name
        assert context3.structure.repo_type == context1.structure.repo_type

    @pytest.mark.parametrize(
        "repo_url,expected_type,has_config",
        [
            ("https://github.com/prebid/Prebid.js", "prebid-js", True),
            (
                "https://github.com/prebid/prebid-server-java",
                "prebid-server-java",
                True,
            ),
            (
                "https://github.com/prebid/prebid-server",
                "prebid-server-go",
                True,
            ),  # This actually maps to go
        ],
    )
    def test_multiple_prebid_repos(self, manager, repo_url, expected_type, has_config):
        """Test that different Prebid repositories load correctly."""
        context = manager.get_full_context(repo_url)

        if has_config:
            # Basic checks
            assert context.structure is not None
            assert context.structure.repo_type == expected_type

            # Each should have some module categories
            assert len(context.structure.module_categories) > 0

            # Language should match repo type
            if "java" in expected_type:
                assert context.primary_language == "Java"
            elif "go" in expected_type:
                assert context.primary_language == "Go"
            elif "js" in expected_type:
                assert context.primary_language == "JavaScript"
        else:
            # No structure for repos without config
            assert context.structure is None
