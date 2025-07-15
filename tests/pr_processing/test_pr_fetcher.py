"""
Tests for PR Fetcher - batch PR retrieval functionality.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.pr_agents.pr_processing.pr_fetcher import PRFetcher


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    return MagicMock()


@pytest.fixture
def pr_fetcher(mock_github_client):
    """Create a PRFetcher instance with mocked GitHub client."""
    with patch("src.pr_agents.pr_processing.pr_fetcher.Github") as mock_github:
        mock_github.return_value = mock_github_client
        fetcher = PRFetcher("fake-token")
        fetcher.github_client = mock_github_client
        return fetcher


class TestPRFetcher:
    """Test PR fetcher functionality."""

    def test_get_prs_by_release(self, pr_fetcher, mock_github_client):
        """Test fetching PRs by release tag."""
        # Setup mock repository
        mock_repo = MagicMock()
        mock_github_client.get_repo.return_value = mock_repo

        # Mock release
        mock_release = MagicMock()
        mock_release.created_at = datetime.now()
        mock_repo.get_release.return_value = mock_release

        # Mock previous release for date range
        mock_repo.created_at = datetime.now() - timedelta(days=365)
        mock_releases = [mock_release]
        mock_repo.get_releases.return_value = mock_releases

        # Mock search results
        mock_pr1 = MagicMock()
        mock_pr1.html_url = "https://github.com/owner/repo/pull/123"
        mock_pr1.number = 123
        mock_pr1.title = "Fix bug"
        mock_pr1.user.login = "author1"
        mock_pr1.labels = []
        mock_pr1.pull_request.merged_at = datetime.now()

        mock_github_client.search_issues.return_value = [mock_pr1]

        # Test
        result = pr_fetcher.get_prs_by_release("owner/repo", "v1.0.0")

        assert len(result) == 1
        assert result[0]["url"] == "https://github.com/owner/repo/pull/123"
        assert result[0]["number"] == 123
        assert result[0]["title"] == "Fix bug"
        assert result[0]["author"] == "author1"

    def test_get_unreleased_prs(self, pr_fetcher, mock_github_client):
        """Test fetching unreleased PRs."""
        # Setup mock repository
        mock_repo = MagicMock()
        mock_github_client.get_repo.return_value = mock_repo

        # Mock latest release
        mock_release = MagicMock()
        mock_release.created_at = datetime.now() - timedelta(days=7)
        mock_repo.get_latest_release.return_value = mock_release

        # Mock unreleased PRs
        mock_pr1 = MagicMock()
        mock_pr1.html_url = "https://github.com/owner/repo/pull/124"
        mock_pr1.number = 124
        mock_pr1.title = "New feature"
        mock_pr1.user.login = "author2"
        mock_pr1.labels = []
        mock_pr1.pull_request.merged_at = datetime.now()

        mock_github_client.search_issues.return_value = [mock_pr1]

        # Test
        result = pr_fetcher.get_unreleased_prs("owner/repo", "main")

        assert len(result) == 1
        assert result[0]["url"] == "https://github.com/owner/repo/pull/124"
        assert result[0]["title"] == "New feature"

    def test_get_unreleased_prs_no_releases(self, pr_fetcher, mock_github_client):
        """Test fetching unreleased PRs when no releases exist."""
        # Setup mock repository
        mock_repo = MagicMock()
        mock_github_client.get_repo.return_value = mock_repo

        # Mock no releases
        mock_repo.get_latest_release.side_effect = Exception("No releases")

        # Mock all PRs
        mock_pr1 = MagicMock()
        mock_pr1.html_url = "https://github.com/owner/repo/pull/1"
        mock_pr1.number = 1
        mock_pr1.title = "Initial commit"
        mock_pr1.user.login = "author1"
        mock_pr1.labels = []
        mock_pr1.pull_request.merged_at = datetime.now()

        mock_github_client.search_issues.return_value = [mock_pr1]

        # Test
        result = pr_fetcher.get_unreleased_prs("owner/repo", "main")

        assert len(result) == 1
        assert result[0]["number"] == 1

    def test_get_prs_between_releases(self, pr_fetcher, mock_github_client):
        """Test fetching PRs between two releases."""
        # Setup mock repository
        mock_repo = MagicMock()
        mock_github_client.get_repo.return_value = mock_repo

        # Mock releases
        mock_from_release = MagicMock()
        mock_from_release.created_at = datetime.now() - timedelta(days=30)

        mock_to_release = MagicMock()
        mock_to_release.created_at = datetime.now() - timedelta(days=7)

        def get_release_side_effect(tag):
            if tag == "v1.0.0":
                return mock_from_release
            elif tag == "v1.1.0":
                return mock_to_release

        mock_repo.get_release.side_effect = get_release_side_effect

        # Mock PRs between releases
        mock_pr1 = MagicMock()
        mock_pr1.html_url = "https://github.com/owner/repo/pull/125"
        mock_pr1.number = 125
        mock_pr1.title = "Feature between releases"
        mock_pr1.user.login = "author3"
        mock_pr1.labels = []
        mock_pr1.pull_request.merged_at = datetime.now() - timedelta(days=14)

        mock_github_client.search_issues.return_value = [mock_pr1]

        # Test
        result = pr_fetcher.get_prs_between_releases("owner/repo", "v1.0.0", "v1.1.0")

        assert len(result) == 1
        assert result[0]["number"] == 125
        assert result[0]["title"] == "Feature between releases"

    def test_get_prs_by_label(self, pr_fetcher, mock_github_client):
        """Test fetching PRs by label."""
        # Mock labeled PRs
        mock_label = MagicMock()
        mock_label.name = "bug"

        mock_pr1 = MagicMock()
        mock_pr1.html_url = "https://github.com/owner/repo/pull/126"
        mock_pr1.number = 126
        mock_pr1.title = "Bug fix"
        mock_pr1.state = "closed"
        mock_pr1.user.login = "author4"
        mock_pr1.labels = [mock_label]
        mock_pr1.created_at = datetime.now()

        mock_github_client.search_issues.return_value = [mock_pr1]

        # Test
        result = pr_fetcher.get_prs_by_label("owner/repo", "bug", "closed")

        assert len(result) == 1
        assert result[0]["number"] == 126
        assert result[0]["labels"] == ["bug"]

    def test_error_handling(self, pr_fetcher, mock_github_client):
        """Test error handling in PR fetcher."""
        # Setup mock to raise exception
        mock_github_client.get_repo.side_effect = Exception("API Error")

        # Test that exception is raised
        with pytest.raises(Exception) as exc_info:
            pr_fetcher.get_prs_by_release("owner/repo", "v1.0.0")

        assert "API Error" in str(exc_info.value)
