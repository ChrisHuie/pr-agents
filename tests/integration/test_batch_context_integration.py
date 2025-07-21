"""Integration tests for batch context processing with PR analysis."""

from unittest.mock import Mock, patch

import pytest

from pr_agents.pr_processing.coordinator import PRCoordinator


class TestBatchContextIntegration:
    """Test batch context integration with PR analysis pipeline."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return Mock()

    @pytest.fixture
    def coordinator(self, mock_github_client):
        """Create a PRCoordinator with mocked dependencies."""
        with patch("pr_agents.pr_processing.coordinator.Github") as mock_github:
            with patch("pr_agents.pr_processing.coordinator.PRFetcher"):
                mock_github.return_value = mock_github_client
                coord = PRCoordinator("fake-token", ai_enabled=True)
                coord.github_client = mock_github_client
                return coord

    def test_batch_analysis_with_ai_same_repo(self, coordinator):
        """Test batch analysis with AI summaries for PRs from same repository."""
        # Setup PR URLs from same repo
        pr_urls = [
            "https://github.com/prebid/Prebid.js/pull/1001",
            "https://github.com/prebid/Prebid.js/pull/1002",
            "https://github.com/prebid/Prebid.js/pull/1003",
        ]

        # Mock AI processor with batch methods
        mock_ai_processor = Mock()
        mock_ai_service = Mock()
        mock_ai_processor.ai_service = mock_ai_service
        mock_ai_service.start_batch = Mock()
        mock_ai_service.end_batch = Mock()

        # Mock component manager
        coordinator.component_manager.get_processor = Mock(
            return_value=mock_ai_processor
        )

        # Mock single PR analysis results
        def mock_analyze_pr(pr_url, extract_components=None, run_processors=None):
            return {
                "pr_url": pr_url,
                "success": True,
                "processing_results": [
                    {
                        "component": "ai_summaries",
                        "success": True,
                        "data": {
                            "executive_summary": f"Executive summary for {pr_url}",
                            "product_summary": f"Product summary for {pr_url}",
                            "developer_summary": f"Developer summary for {pr_url}",
                        },
                    }
                ],
            }

        coordinator.batch_coordinator.single_pr_coordinator.coordinate = Mock(
            side_effect=mock_analyze_pr
        )

        # Run batch analysis with AI
        results = coordinator.analyze_prs_batch(
            pr_urls, run_processors=["ai_summaries"]
        )

        # Verify batch context was started and ended
        mock_ai_service.start_batch.assert_called_once_with(
            "https://github.com/prebid/Prebid.js"
        )
        mock_ai_service.end_batch.assert_called_once()

        # Verify all PRs analyzed
        assert len(results["pr_results"]) == 3
        assert results["batch_summary"]["total_prs"] == 3
        assert results["batch_summary"]["successful_analyses"] == 3

    def test_batch_analysis_with_ai_mixed_repos(self, coordinator):
        """Test batch analysis with AI summaries for PRs from different repositories."""
        # Setup PR URLs from different repos
        pr_urls = [
            "https://github.com/prebid/Prebid.js/pull/1001",
            "https://github.com/prebid/prebid-server/pull/500",  # Different repo
            "https://github.com/prebid/Prebid.js/pull/1003",
        ]

        # Mock AI processor
        mock_ai_processor = Mock()
        mock_ai_service = Mock()
        mock_ai_processor.ai_service = mock_ai_service
        mock_ai_service.start_batch = Mock()
        mock_ai_service.end_batch = Mock()

        coordinator.component_manager.get_processor = Mock(
            return_value=mock_ai_processor
        )

        # Mock single PR analysis
        coordinator.batch_coordinator.single_pr_coordinator.coordinate = Mock(
            return_value={"success": True, "processing_results": []}
        )

        # Run batch analysis
        results = coordinator.analyze_prs_batch(
            pr_urls, run_processors=["ai_summaries"]
        )

        # Verify batch context NOT started (mixed repos)
        mock_ai_service.start_batch.assert_not_called()
        mock_ai_service.end_batch.assert_not_called()

        # Verify all PRs still analyzed
        assert len(results["pr_results"]) == 3

    def test_batch_analysis_without_ai(self, coordinator):
        """Test batch analysis without AI summaries doesn't use batch context."""
        pr_urls = [
            "https://github.com/prebid/Prebid.js/pull/1001",
            "https://github.com/prebid/Prebid.js/pull/1002",
        ]

        # Mock component manager
        mock_processor = Mock()
        coordinator.component_manager.get_processor = Mock(return_value=mock_processor)

        # Mock single PR analysis
        coordinator.batch_coordinator.single_pr_coordinator.coordinate = Mock(
            return_value={"success": True, "processing_results": []}
        )

        # Run batch analysis without AI
        results = coordinator.analyze_prs_batch(
            pr_urls, run_processors=["code_changes", "metadata"]  # No ai_summaries
        )

        # Verify get_processor not called for AI
        coordinator.component_manager.get_processor.assert_not_called()

        # Verify PRs analyzed
        assert len(results["pr_results"]) == 2

    def test_release_batch_analysis_with_context(self, coordinator):
        """Test release PR analysis with batch context."""
        repo_name = "prebid/Prebid.js"
        release_tag = "v8.0.0"

        # Mock PR fetcher to return PRs
        mock_prs = [
            {"url": "https://github.com/prebid/Prebid.js/pull/2001"},
            {"url": "https://github.com/prebid/Prebid.js/pull/2002"},
            {"url": "https://github.com/prebid/Prebid.js/pull/2003"},
        ]
        coordinator.batch_coordinator.pr_fetcher.get_prs_by_release = Mock(
            return_value=mock_prs
        )

        # Mock AI processor
        mock_ai_processor = Mock()
        mock_ai_service = Mock()
        mock_ai_processor.ai_service = mock_ai_service
        mock_ai_service.start_batch = Mock()
        mock_ai_service.end_batch = Mock()

        coordinator.component_manager.get_processor = Mock(
            return_value=mock_ai_processor
        )

        # Mock single PR analysis
        coordinator.batch_coordinator.single_pr_coordinator.coordinate = Mock(
            return_value={"success": True, "processing_results": []}
        )

        # Run release analysis with AI
        results = coordinator.analyze_release_prs(
            repo_name, release_tag, run_processors=["ai_summaries"]
        )

        # Verify batch context used
        mock_ai_service.start_batch.assert_called_once_with(
            "https://github.com/prebid/Prebid.js"
        )
        mock_ai_service.end_batch.assert_called_once()

        # Verify results
        assert results["repository"] == repo_name
        assert results["release_tag"] == release_tag
        assert results["batch_summary"]["total_prs"] == 3

    def test_batch_context_error_handling(self, coordinator):
        """Test batch context error propagation."""
        pr_urls = ["https://github.com/prebid/Prebid.js/pull/3001"]

        # Mock AI processor that raises on start_batch
        mock_ai_processor = Mock()
        mock_ai_service = Mock()
        mock_ai_processor.ai_service = mock_ai_service
        mock_ai_service.start_batch = Mock(side_effect=Exception("Context load error"))
        mock_ai_service.end_batch = Mock()

        coordinator.component_manager.get_processor = Mock(
            return_value=mock_ai_processor
        )

        # Mock single PR analysis to succeed
        coordinator.batch_coordinator.single_pr_coordinator.coordinate = Mock(
            return_value={"success": True, "processing_results": []}
        )

        # Run batch analysis - currently raises exception
        with pytest.raises(Exception, match="Context load error"):
            coordinator.analyze_prs_batch(pr_urls, run_processors=["ai_summaries"])
