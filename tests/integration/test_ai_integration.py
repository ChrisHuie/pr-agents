"""Integration tests for AI-powered PR analysis."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.pr_agents.pr_processing.coordinator import PRCoordinator
from src.pr_agents.services.ai.providers.base import LLMResponse


class TestAIIntegration:
    """Integration tests for AI features."""

    @pytest.fixture
    def mock_github_pr(self):
        """Create a mock GitHub PR."""
        pr = Mock()
        pr.url = "https://github.com/prebid/Prebid.js/pull/13529"
        pr.html_url = "https://github.com/prebid/Prebid.js/pull/13529"
        pr.number = 13529
        pr.title = "Add Sevio Bid Adapter"
        pr.body = "This PR adds a new bid adapter for Sevio DSP with banner and native support."
        pr.state = "open"
        pr.base.ref = "master"
        pr.base.sha = "abc123"
        pr.head.ref = "feature/sevio-adapter"
        pr.head.sha = "def456"
        pr.created_at = datetime.now()
        pr.updated_at = datetime.now()
        pr.merged_at = None
        pr.merge_commit_sha = "xyz789"
        pr.labels = []
        pr.milestone = None
        pr.assignees = []
        pr.user = Mock()
        pr.user.login = "test-user"
        pr.get_labels.return_value = []

        # Mock repository
        pr.base.repo.name = "Prebid.js"
        pr.base.repo.full_name = "prebid/Prebid.js"
        pr.base.repo.description = "Header bidding library"
        pr.base.repo.private = False
        pr.base.repo.fork = False
        pr.base.repo.parent = None
        pr.base.repo.default_branch = "master"
        pr.base.repo.language = "JavaScript"
        pr.base.repo.owner = Mock()
        pr.base.repo.owner.login = "prebid"
        pr.base.repo.get_topics.return_value = [
            "advertising",
            "header-bidding",
            "prebid",
        ]
        pr.base.repo.get_languages.return_value = {
            "JavaScript": 95,
            "HTML": 3,
            "CSS": 2,
        }

        # Mock files
        file1 = Mock()
        file1.filename = "modules/sevioBidAdapter.js"
        file1.status = "added"
        file1.additions = 350
        file1.deletions = 0
        file1.changes = 350
        file1.previous_filename = None
        file1.patch = """
@@ -0,0 +1,350 @@
+import { registerBidder } from '../src/adapters/bidderFactory.js';
+import { BANNER, NATIVE } from '../src/mediaTypes.js';
+
+const BIDDER_CODE = 'sevio';
+
+export const spec = {
+  code: BIDDER_CODE,
+  supportedMediaTypes: [BANNER, NATIVE],
+
+  isBidRequestValid: function(bid) {
+    return !!(bid.params && bid.params.placementId);
+  },
+
+  buildRequests: function(validBidRequests, bidderRequest) {
+    // Implementation details...
+  },
+
+  interpretResponse: function(serverResponse, request) {
+    // Implementation details...
+  },
+
+  getUserSyncs: function(syncOptions, serverResponses) {
+    // User sync implementation...
+  },
+
+  onBidWon: function(bid) {
+    // Bid won tracking...
+  }
+};
+
+registerBidder(spec);
"""

        file2 = Mock()
        file2.filename = "test/spec/modules/sevioBidAdapter_spec.js"
        file2.status = "added"
        file2.additions = 200
        file2.deletions = 0
        file2.changes = 200
        file2.previous_filename = None
        file2.patch = """
@@ -0,0 +1,200 @@
+import { expect } from 'chai';
+import { spec } from 'modules/sevioBidAdapter.js';
+
+describe('SevioBidAdapter', function() {
+  // Test implementation...
+});
"""

        pr.get_files.return_value = [file1, file2]

        # Mock reviews
        pr.get_reviews.return_value = []
        pr.get_review_comments.return_value = []
        pr.get_issue_comments.return_value = []

        return pr

    @pytest.fixture
    def mock_llm_responses(self):
        """Create mock LLM responses for different personas."""
        return {
            "executive": LLMResponse(
                content="Sevio Bid Adapter added to Prebid.js and supports banner and native media types.",
                model="mock-model",
                tokens_used=30,
                response_time_ms=200,
            ),
            "product": LLMResponse(
                content="Sevio Bid Adapter added to Prebid.js with comprehensive support for banner and native ad formats. Implements standard adapter callbacks including onBidWon for conversion tracking, getUserSyncs for cookie syncing, and includes full test coverage with 200 lines of unit tests.",
                model="mock-model",
                tokens_used=60,
                response_time_ms=300,
            ),
            "developer": LLMResponse(
                content="Sevio Bid Adapter (modules/sevioBidAdapter.js) implemented following Prebid.js adapter patterns. The adapter extends the bidderFactory base class and implements required methods: isBidRequestValid() for parameter validation, buildRequests() for bid request construction, and interpretResponse() for bid response parsing. Supports BANNER and NATIVE media types with placement ID as required parameter. Includes comprehensive test suite (test/spec/modules/sevioBidAdapter_spec.js) with 200 lines covering core functionality. Implements optional features including getUserSyncs() for cookie synchronization and onBidWon() callback for conversion tracking.",
                model="mock-model",
                tokens_used=120,
                response_time_ms=500,
            ),
        }

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_ai_pipeline(self, mock_github_pr, mock_llm_responses):
        """Test complete AI summarization pipeline."""
        # Patch at the module level where Github is used
        with patch(
            "src.pr_agents.pr_processing.coordinator.Github"
        ) as mock_github_class:
            # Setup GitHub mock
            mock_github = Mock()
            mock_repo = Mock()

            # Configure the mock chain
            mock_github_class.return_value = mock_github
            mock_github.get_repo.return_value = mock_repo
            mock_repo.get_pull.return_value = mock_github_pr

            # Mock LLM provider
            with patch(
                "src.pr_agents.services.ai.providers.gemini.GeminiProvider"
            ) as mock_provider_class:
                mock_provider = Mock()
                mock_provider.name = "gemini"

                # Setup different responses for different prompts
                async def mock_generate(prompt, **kwargs):
                    if "executive audience" in prompt:
                        return mock_llm_responses["executive"]
                    elif "product manager" in prompt:
                        return mock_llm_responses["product"]
                    elif "software engineer" in prompt:
                        return mock_llm_responses["developer"]
                    return mock_llm_responses["executive"]

                mock_provider.generate = AsyncMock(side_effect=mock_generate)
                mock_provider_class.return_value = mock_provider

                # Create coordinator with AI enabled
                with patch.dict(
                    "os.environ",
                    {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"},
                ):
                    coordinator = PRCoordinator(
                        github_token="test-token", ai_enabled=True
                    )

                    # Run analysis
                    results = coordinator.analyze_pr_with_ai(
                        "https://github.com/prebid/Prebid.js/pull/13529"
                    )

                    # Verify results structure
                    assert "extracted_data" in results
                    assert "processing_results" in results
                    assert "ai_summaries" in results

                    # Verify AI summaries
                    ai_summaries = results["ai_summaries"]
                    assert "executive_summary" in ai_summaries
                    assert "product_summary" in ai_summaries
                    assert "developer_summary" in ai_summaries

                    # Verify summary content
                    assert (
                        "Sevio Bid Adapter"
                        in ai_summaries["executive_summary"]["summary"]
                    )
                    assert (
                        "banner and native"
                        in ai_summaries["executive_summary"]["summary"]
                    )

                    assert "onBidWon" in ai_summaries["product_summary"]["summary"]
                    assert "getUserSyncs" in ai_summaries["product_summary"]["summary"]

                    assert (
                        "bidderFactory" in ai_summaries["developer_summary"]["summary"]
                    )
                    assert (
                        "isBidRequestValid"
                        in ai_summaries["developer_summary"]["summary"]
                    )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ai_pipeline_with_cache(self, mock_github_pr, mock_llm_responses):
        """Test AI pipeline with caching enabled."""
        # Patch at the module level where Github is used
        with patch(
            "src.pr_agents.pr_processing.coordinator.Github"
        ) as mock_github_class:
            # Setup GitHub mock
            mock_github = Mock()
            mock_repo = Mock()

            # Configure the mock chain
            mock_github_class.return_value = mock_github
            mock_github.get_repo.return_value = mock_repo
            mock_repo.get_pull.return_value = mock_github_pr

            # Mock LLM provider
            with patch(
                "src.pr_agents.services.ai.providers.gemini.GeminiProvider"
            ) as mock_provider_class:
                mock_provider = Mock()
                mock_provider.name = "gemini"

                # Track call count
                call_count = 0

                async def mock_generate(prompt, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if "executive audience" in prompt:
                        return mock_llm_responses["executive"]
                    elif "product manager" in prompt:
                        return mock_llm_responses["product"]
                    elif "software engineer" in prompt:
                        return mock_llm_responses["developer"]
                    return mock_llm_responses["executive"]

                mock_provider.generate = AsyncMock(side_effect=mock_generate)
                mock_provider_class.return_value = mock_provider

                # Create coordinator with AI enabled
                with patch.dict(
                    "os.environ",
                    {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"},
                ):
                    coordinator = PRCoordinator(
                        github_token="test-token", ai_enabled=True
                    )

                    # First analysis
                    results1 = coordinator.analyze_pr_with_ai(
                        "https://github.com/prebid/Prebid.js/pull/13529"
                    )

                    # Second analysis (should use cache)
                    results2 = coordinator.analyze_pr_with_ai(
                        "https://github.com/prebid/Prebid.js/pull/13529"
                    )

                    # Verify caching
                    assert not results1["ai_summaries"]["cached"]
                    assert results2["ai_summaries"]["cached"]

                    # Provider should only be called 3 times total (not 6)
                    assert call_count == 3

    @pytest.mark.integration
    def test_ai_disabled_error(self):
        """Test error when AI is not enabled."""
        with patch("src.pr_agents.pr_processing.coordinator.Github"):
            coordinator = PRCoordinator(github_token="test-token", ai_enabled=False)

            with pytest.raises(ValueError, match="AI is not enabled"):
                coordinator.analyze_pr_with_ai(
                    "https://github.com/prebid/Prebid.js/pull/13529"
                )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ai_with_output_formatting(self, mock_github_pr, mock_llm_responses):
        """Test AI summaries in different output formats."""
        # Patch at the module level where Github is used
        with patch(
            "src.pr_agents.pr_processing.coordinator.Github"
        ) as mock_github_class:
            # Setup GitHub mock
            mock_github = Mock()
            mock_repo = Mock()

            # Configure the mock chain
            mock_github_class.return_value = mock_github
            mock_github.get_repo.return_value = mock_repo
            mock_repo.get_pull.return_value = mock_github_pr

            # Mock LLM provider
            with patch(
                "src.pr_agents.services.ai.providers.gemini.GeminiProvider"
            ) as mock_provider_class:
                mock_provider = Mock()
                mock_provider.name = "gemini"
                mock_provider.generate = AsyncMock(
                    return_value=mock_llm_responses["executive"]
                )
                mock_provider_class.return_value = mock_provider

                # Create coordinator
                with patch.dict(
                    "os.environ",
                    {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"},
                ):
                    coordinator = PRCoordinator(
                        github_token="test-token", ai_enabled=True
                    )

                    # Test markdown output
                    results, path = coordinator.analyze_pr_and_save(
                        "https://github.com/prebid/Prebid.js/pull/13529",
                        output_path="test_output",
                        output_format="markdown",
                        extract_components={"metadata", "code_changes"},
                        run_processors=["ai_summaries"],
                    )

                    # Read the output file
                    with open(path) as f:
                        content = f.read()

                    # Verify AI summaries are in the output
                    assert "## 🤖 AI-Generated Summaries" in content
                    assert "### Executive Summary" in content
                    assert "### Product Manager Summary" in content
                    assert "### Technical Developer Summary" in content

                    # Clean up
                    import os

                    os.remove(path)
