"""
Tests for PRCoordinator batch processing functionality.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.pr_agents.pr_processing.coordinator import PRCoordinator


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    return MagicMock()


@pytest.fixture
def coordinator(mock_github_client):
    """Create a PRCoordinator instance with mocked dependencies."""
    with patch("src.pr_agents.pr_processing.coordinator.Github") as mock_github:
        with patch("src.pr_agents.pr_processing.coordinator.PRFetcher"):
            mock_github.return_value = mock_github_client
            coord = PRCoordinator("fake-token")
            coord.github_client = mock_github_client
            return coord


class TestPRCoordinatorBatch:
    """Test batch processing functionality in PRCoordinator."""

    def test_analyze_prs_batch_success(self, coordinator):
        """Test successful batch PR analysis."""
        pr_urls = [
            "https://github.com/owner/repo/pull/1",
            "https://github.com/owner/repo/pull/2",
        ]

        # Mock analyze_pr to return successful results
        mock_results = []
        for _, url in enumerate(pr_urls):
            mock_results.append(
                {
                    "pr_url": url,
                    "success": True,
                    "processing_results": [
                        {
                            "component": "metadata",
                            "success": True,
                            "data": {
                                "title_quality": {"score": 80, "quality_level": "good"},
                                "description_quality": {
                                    "score": 70,
                                    "quality_level": "good",
                                },
                            },
                        },
                        {
                            "component": "code_changes",
                            "success": True,
                            "data": {
                                "risk_assessment": {"risk_level": "low"},
                                "change_stats": {
                                    "total_additions": 100,
                                    "total_deletions": 50,
                                    "changed_files": 5,
                                },
                            },
                        },
                    ],
                }
            )

        coordinator.batch_coordinator.single_pr_coordinator.coordinate = Mock(
            side_effect=mock_results
        )

        # Test batch analysis
        results = coordinator.analyze_prs_batch(pr_urls)

        assert "pr_results" in results
        assert "batch_summary" in results
        assert results["batch_summary"]["total_prs"] == 2
        assert results["batch_summary"]["successful_analyses"] == 2
        assert results["batch_summary"]["failed_analyses"] == 0
        assert len(results["pr_results"]) == 2

        # Check summary statistics
        summary = results["batch_summary"]
        assert summary["by_risk_level"]["low"] == 2
        assert summary["by_title_quality"]["good"] == 2
        assert summary["total_additions"] == 200
        assert summary["total_deletions"] == 100
        assert summary["average_files_changed"] == 5.0

    def test_analyze_prs_batch_with_failures(self, coordinator):
        """Test batch PR analysis with some failures."""
        pr_urls = [
            "https://github.com/owner/repo/pull/1",
            "https://github.com/owner/repo/pull/2",
            "https://github.com/owner/repo/pull/3",
        ]

        # Mock analyze_pr to return mixed results
        def coordinate_side_effect(url, *args, **kwargs):
            if url == pr_urls[1]:
                raise Exception("PR not found")
            return {
                "pr_url": url,
                "success": True,
                "processing_results": [
                    {
                        "component": "metadata",
                        "success": True,
                        "data": {
                            "title_quality": {
                                "score": 85,
                                "quality_level": "excellent",
                            },
                            "description_quality": {
                                "score": 60,
                                "quality_level": "good",
                            },
                        },
                    },
                ],
            }

        coordinator.batch_coordinator.single_pr_coordinator.coordinate = Mock(
            side_effect=coordinate_side_effect
        )

        # Test batch analysis
        results = coordinator.analyze_prs_batch(pr_urls)

        assert results["batch_summary"]["total_prs"] == 3
        assert results["batch_summary"]["successful_analyses"] == 2
        assert results["batch_summary"]["failed_analyses"] == 1
        assert pr_urls[1] in results["pr_results"]
        assert results["pr_results"][pr_urls[1]]["success"] is False
        assert "error" in results["pr_results"][pr_urls[1]]

    def test_analyze_release_prs(self, coordinator):
        """Test analyzing PRs in a release."""
        # Mock PR fetcher
        mock_prs = [
            {"url": "https://github.com/owner/repo/pull/10"},
            {"url": "https://github.com/owner/repo/pull/11"},
        ]
        coordinator.batch_coordinator.pr_fetcher.get_prs_by_release = Mock(
            return_value=mock_prs
        )

        # Mock single PR coordinator
        mock_pr_result = {
            "pr_url": "test_url",
            "success": True,
            "processing_results": [],
        }
        coordinator.batch_coordinator.single_pr_coordinator.coordinate = Mock(
            return_value=mock_pr_result
        )

        # Test
        results = coordinator.analyze_release_prs("owner/repo", "v1.0.0")

        assert "repository" in results
        assert results["repository"] == "owner/repo"
        assert "release_tag" in results
        assert results["release_tag"] == "v1.0.0"
        assert results["batch_summary"]["total_prs"] == 2

        # Verify calls
        coordinator.batch_coordinator.pr_fetcher.get_prs_by_release.assert_called_once_with(
            "owner/repo", "v1.0.0"
        )
        # Verify single PR coordinator was called for each PR
        assert (
            coordinator.batch_coordinator.single_pr_coordinator.coordinate.call_count
            == 2
        )

    def test_analyze_unreleased_prs(self, coordinator):
        """Test analyzing unreleased PRs."""
        # Mock PR fetcher
        mock_prs = [
            {"url": "https://github.com/owner/repo/pull/20"},
            {"url": "https://github.com/owner/repo/pull/21"},
            {"url": "https://github.com/owner/repo/pull/22"},
        ]
        coordinator.batch_coordinator.pr_fetcher.get_unreleased_prs = Mock(
            return_value=mock_prs
        )

        # Mock batch analysis
        mock_batch_result = {
            "pr_results": {},
            "batch_summary": {
                "total_prs": 3,
                "successful_analyses": 3,
                "failed_analyses": 0,
            },
        }
        coordinator.analyze_prs_batch = Mock(return_value=mock_batch_result)

        # Test
        results = coordinator.analyze_unreleased_prs("owner/repo", "main")

        assert "repository" in results
        assert results["repository"] == "owner/repo"
        assert "base_branch" in results
        assert results["base_branch"] == "main"
        assert results["batch_summary"]["total_prs"] == 3

        # Verify calls
        coordinator.batch_coordinator.pr_fetcher.get_unreleased_prs.assert_called_once_with(
            "owner/repo", "main"
        )

    def test_analyze_prs_between_releases(self, coordinator):
        """Test analyzing PRs between releases."""
        # Mock PR fetcher
        mock_prs = [
            {"url": "https://github.com/owner/repo/pull/30"},
            {"url": "https://github.com/owner/repo/pull/31"},
            {"url": "https://github.com/owner/repo/pull/32"},
            {"url": "https://github.com/owner/repo/pull/33"},
        ]
        coordinator.batch_coordinator.pr_fetcher.get_prs_between_releases = Mock(
            return_value=mock_prs
        )

        # Mock batch analysis
        mock_batch_result = {
            "pr_results": {},
            "batch_summary": {
                "total_prs": 4,
                "successful_analyses": 4,
                "failed_analyses": 0,
            },
        }
        coordinator.analyze_prs_batch = Mock(return_value=mock_batch_result)

        # Test
        results = coordinator.analyze_prs_between_releases(
            "owner/repo", "v1.0.0", "v1.1.0"
        )

        assert "repository" in results
        assert results["repository"] == "owner/repo"
        assert "from_tag" in results
        assert results["from_tag"] == "v1.0.0"
        assert "to_tag" in results
        assert results["to_tag"] == "v1.1.0"
        assert results["batch_summary"]["total_prs"] == 4

        # Verify calls
        coordinator.batch_coordinator.pr_fetcher.get_prs_between_releases.assert_called_once_with(
            "owner/repo", "v1.0.0", "v1.1.0"
        )

    def test_generate_batch_summary(self, coordinator):
        """Test batch summary generation."""
        pr_results = {
            "url1": {
                "success": True,
                "processing_results": [
                    {
                        "success": True,
                        "component": "metadata",
                        "data": {
                            "title_quality": {
                                "score": 90,
                                "quality_level": "excellent",
                            },
                            "description_quality": {
                                "score": 40,
                                "quality_level": "poor",
                            },
                        },
                    },
                    {
                        "success": True,
                        "component": "code_changes",
                        "data": {
                            "risk_assessment": {"risk_level": "high"},
                            "change_stats": {
                                "total_additions": 1000,
                                "total_deletions": 500,
                                "changed_files": 20,
                            },
                        },
                    },
                ],
            },
            "url2": {
                "success": True,
                "processing_results": [
                    {
                        "success": True,
                        "component": "metadata",
                        "data": {
                            "title_quality": {"score": 70, "quality_level": "good"},
                            "description_quality": {
                                "score": 85,
                                "quality_level": "excellent",
                            },
                        },
                    },
                    {
                        "success": True,
                        "component": "code_changes",
                        "data": {
                            "risk_assessment": {"risk_level": "low"},
                            "change_stats": {
                                "total_additions": 50,
                                "total_deletions": 30,
                                "changed_files": 3,
                            },
                        },
                    },
                ],
            },
            "url3": {
                "success": False,
                "error": "Failed to fetch PR",
            },
        }

        summary = coordinator._generate_batch_stats(pr_results)

        assert summary["total_prs"] == 3
        assert summary["by_risk_level"]["high"] == 1
        assert summary["by_risk_level"]["low"] == 1
        assert summary["by_title_quality"]["excellent"] == 1
        assert summary["by_title_quality"]["good"] == 1
        assert summary["by_description_quality"]["poor"] == 1
        assert summary["by_description_quality"]["excellent"] == 1
        assert summary["total_additions"] == 1050
        assert summary["total_deletions"] == 530
        assert summary["average_files_changed"] == 11.5
