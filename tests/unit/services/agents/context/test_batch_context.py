"""Tests for batch context provider functionality."""

from unittest.mock import Mock

import pytest

from src.pr_agents.services.agents.context.batch_context import BatchContextProvider


class TestBatchContextProvider:
    """Test batch context provider functionality."""

    @pytest.fixture
    def mock_base_provider(self):
        """Create a mock enhanced repository context provider."""
        return Mock()

    @pytest.fixture
    def provider(self, mock_base_provider):
        """Create a batch context provider with mocked base provider."""
        provider = BatchContextProvider()
        provider._base_provider = mock_base_provider
        return provider

    def test_initialization(self, provider):
        """Test provider initializes correctly."""
        assert provider._repo_context_cache == {}
        assert provider._current_batch_repo is None
        assert provider._batch_context is None
        assert provider._base_provider is not None

    def test_start_batch_loads_context(self, provider, mock_base_provider):
        """Test starting a batch loads repository context."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Setup mocks
        mock_base_provider._determine_repo_type.return_value = "prebid-js"
        mock_base_provider._load_knowledge_base.return_value = {
            "repository": "prebid/Prebid.js",
            "description": "Header bidding library",
            "primary_language": "JavaScript",
            "ecosystem": "web-advertising",
            "module_patterns": {
                "bid_adapter": {
                    "path_pattern": "modules/*BidAdapter.js",
                    "description": "Bid adapter modules",
                }
            },
        }

        # Start batch
        provider.start_batch(repo_url)

        # Verify context loaded
        assert provider._current_batch_repo == repo_url
        assert provider._batch_context is not None
        assert provider._batch_context["repo_url"] == repo_url
        assert provider._batch_context["repo_type"] == "prebid-js"
        assert provider._batch_context["repository"] == "prebid/Prebid.js"
        assert provider._batch_context["primary_language"] == "JavaScript"

        # Verify methods called
        mock_base_provider._determine_repo_type.assert_called_once_with(repo_url)
        mock_base_provider._load_knowledge_base.assert_called_once_with("prebid-js")

    def test_start_batch_different_repo_clears_context(
        self, provider, mock_base_provider
    ):
        """Test starting batch for different repo clears previous context."""
        repo1 = "https://github.com/prebid/Prebid.js"
        repo2 = "https://github.com/prebid/prebid-server"

        # Setup mock
        mock_base_provider._determine_repo_type.return_value = "prebid-server"
        mock_base_provider._load_knowledge_base.return_value = {
            "repository": "prebid/prebid-server"
        }

        # Set initial batch
        provider._current_batch_repo = repo1
        provider._batch_context = {"old": "context"}

        # Start new batch
        provider.start_batch(repo2)

        # Verify context cleared and new one loaded
        assert provider._current_batch_repo == repo2
        assert provider._batch_context is not None
        assert "old" not in provider._batch_context  # Old context was cleared
        assert provider._batch_context["repository"] == "prebid/prebid-server"

    def test_start_batch_no_knowledge_base(self, provider, mock_base_provider):
        """Test starting batch when no knowledge base exists."""
        repo_url = "https://github.com/unknown/repo"

        # Setup mocks
        mock_base_provider._determine_repo_type.return_value = "unknown"
        mock_base_provider._load_knowledge_base.return_value = None

        # Start batch
        provider.start_batch(repo_url)

        # Verify no context loaded
        assert provider._current_batch_repo == repo_url
        assert provider._batch_context is None

    def test_get_context_for_pr_with_batch(self, provider, mock_base_provider):
        """Test getting context for PR when batch is active."""
        repo_url = "https://github.com/prebid/Prebid.js"
        files_changed = [
            "modules/exampleBidAdapter.js",
            "test/spec/modules/exampleBidAdapter_spec.js",
        ]

        # Setup batch context
        provider._current_batch_repo = repo_url
        provider._batch_context = {
            "repository": "prebid/Prebid.js",
            "repo_type": "prebid-js",
            "description": "Header bidding library",
            "primary_language": "JavaScript",
            "ecosystem": "web-advertising",
            "knowledge": {
                "module_patterns": {
                    "bid_adapter": {"path_pattern": "modules/*BidAdapter.js"}
                },
                "code_examples": {"adapter": "example code"},
                "patterns": {"naming": "camelCase"},
                "quality_checklist": ["item1", "item2"],
                "common_issues": ["issue1"],
                "file_guidance": {"modules/": "Module files"},
            },
        }

        # Setup mock methods
        mock_base_provider._get_relevant_examples.return_value = ["example1"]
        mock_base_provider._get_relevant_patterns.return_value = {"pattern": "value"}
        mock_base_provider._get_quality_checklist.return_value = ["check1", "check2"]
        mock_base_provider._get_common_issues.return_value = ["issue1"]
        mock_base_provider._get_file_guidance.return_value = {"file": "guidance"}

        # Get context
        context = provider.get_context_for_pr(repo_url, files_changed)

        # Verify base context included
        assert context["repository"] == "prebid/Prebid.js"
        assert context["type"] == "prebid-js"
        assert context["primary_language"] == "JavaScript"

        # Verify file-specific context generated
        assert context["relevant_examples"] == ["example1"]
        assert context["patterns"] == {"pattern": "value"}
        assert context["quality_checklist"] == ["check1", "check2"]
        assert context["common_issues"] == ["issue1"]
        assert context["file_guidance"] == {"file": "guidance"}

        # Verify methods called with correct arguments
        knowledge = provider._batch_context["knowledge"]
        mock_base_provider._get_relevant_examples.assert_called_once_with(
            knowledge, files_changed
        )
        mock_base_provider._get_relevant_patterns.assert_called_once_with(
            knowledge, files_changed
        )

    def test_get_context_for_pr_without_batch(self, provider, mock_base_provider):
        """Test getting context for PR when no batch is active."""
        repo_url = "https://github.com/prebid/Prebid.js"
        files_changed = ["modules/exampleBidAdapter.js"]

        # No batch context
        provider._current_batch_repo = None
        provider._batch_context = None

        # Setup mock
        mock_base_provider.get_context.return_value = {
            "repository": "prebid/Prebid.js",
            "fallback": True,
        }

        # Get context
        context = provider.get_context_for_pr(repo_url, files_changed)

        # Verify fallback to regular context
        assert context["fallback"] is True
        mock_base_provider.get_context.assert_called_once_with(repo_url, files_changed)

    def test_get_context_for_pr_different_repo(self, provider, mock_base_provider):
        """Test getting context for PR from different repo than batch."""
        batch_repo = "https://github.com/prebid/Prebid.js"
        pr_repo = "https://github.com/prebid/prebid-server"
        files_changed = ["src/main.go"]

        # Setup batch for different repo
        provider._current_batch_repo = batch_repo
        provider._batch_context = {"repository": "prebid/Prebid.js"}

        # Setup mock
        mock_base_provider.get_context.return_value = {
            "repository": "prebid/prebid-server",
            "fallback": True,
        }

        # Get context for different repo
        context = provider.get_context_for_pr(pr_repo, files_changed)

        # Verify fallback used
        assert context["fallback"] is True
        mock_base_provider.get_context.assert_called_once_with(pr_repo, files_changed)

    def test_end_batch(self, provider):
        """Test ending batch clears context."""
        # Setup batch context
        provider._current_batch_repo = "https://github.com/prebid/Prebid.js"
        provider._batch_context = {"some": "context"}

        # End batch
        provider.end_batch()

        # Verify cleared
        assert provider._current_batch_repo is None
        assert provider._batch_context is None

    def test_get_batch_statistics_no_batch(self, provider):
        """Test getting statistics when no batch is active."""
        stats = provider.get_batch_statistics()

        assert stats == {"active": False}

    def test_get_batch_statistics_with_batch(self, provider):
        """Test getting statistics with active batch."""
        # Setup batch context
        provider._current_batch_repo = "https://github.com/prebid/Prebid.js"
        provider._batch_context = {
            "repo_type": "prebid-js",
            "knowledge": {
                "code_examples": {"example1": "code", "example2": "code"},
                "patterns": {
                    "pattern1": "desc",
                    "pattern2": "desc",
                    "pattern3": "desc",
                },
            },
        }

        stats = provider.get_batch_statistics()

        assert stats["active"] is True
        assert stats["repository"] == "https://github.com/prebid/Prebid.js"
        assert stats["repo_type"] == "prebid-js"
        assert stats["has_knowledge_base"] is True
        assert stats["available_examples"] == 2
        assert stats["available_patterns"] == 3

    def test_batch_context_reuse_same_repo(self, provider, mock_base_provider):
        """Test batch context behavior for same repository."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Setup mocks
        mock_base_provider._determine_repo_type.return_value = "prebid-js"
        mock_base_provider._load_knowledge_base.return_value = {
            "repository": "prebid/Prebid.js"
        }

        # Start batch - this will set current repo and load context
        provider.start_batch(repo_url)
        assert provider._current_batch_repo == repo_url
        assert provider._batch_context is not None

        # Start batch again for same repo
        # Current implementation reloads the context each time
        provider.start_batch(repo_url)

        # Verify repo is still set correctly
        assert provider._current_batch_repo == repo_url
        assert provider._batch_context is not None

        # In current implementation, methods are called twice
        assert mock_base_provider._determine_repo_type.call_count == 2
        assert mock_base_provider._load_knowledge_base.call_count == 2
