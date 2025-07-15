"""
Tests for DateRangePRFetcher.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.pr_agents.pr_processing.fetchers.date_range import DateRangePRFetcher
from tests.fixtures.mock_github import MockLabel


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    return MagicMock()


@pytest.fixture
def date_fetcher(mock_github_client):
    """Create a DateRangePRFetcher with mocked GitHub client."""
    with patch("src.pr_agents.pr_processing.fetchers.base.Github") as mock_github:
        mock_github.return_value = mock_github_client
        fetcher = DateRangePRFetcher("fake-token")
        fetcher.github_client = mock_github_client
        return fetcher


class TestDateRangePRFetcher:
    """Test date-based PR fetching functionality."""

    def test_fetch_by_date_range(self, date_fetcher, mock_github_client):
        """Test fetching PRs within a specific date range."""
        # Setup
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        mock_prs = [
            MagicMock(
                html_url="https://github.com/owner/repo/pull/1",
                number=1,
                title="Test PR 1",
                user=MagicMock(login="user1"),
                labels=[MockLabel(name="bug")],
                created_at=datetime(2024, 1, 15),
                updated_at=datetime(2024, 1, 16),
                state="closed",
                pull_request=MagicMock(merged_at=datetime(2024, 1, 16)),
            ),
            MagicMock(
                html_url="https://github.com/owner/repo/pull/2",
                number=2,
                title="Test PR 2",
                user=MagicMock(login="user2"),
                labels=[MockLabel(name="feature")],
                created_at=datetime(2024, 1, 20),
                updated_at=datetime(2024, 1, 22),
                state="closed",
                pull_request=MagicMock(merged_at=datetime(2024, 1, 22)),
            ),
        ]

        mock_github_client.search_issues.return_value = mock_prs

        # Execute
        result = date_fetcher.fetch(
            repo_name="owner/repo", start_date=start_date, end_date=end_date
        )

        # Assert
        assert len(result) == 2
        assert result[0]["url"] == "https://github.com/owner/repo/pull/1"
        assert result[0]["repository"] == "owner/repo"
        assert result[1]["title"] == "Test PR 2"
        assert result[0]["labels"] == ["bug"]

        # Verify search query
        mock_github_client.search_issues.assert_called_once()
        call_args = mock_github_client.search_issues.call_args[1]["query"]
        assert "repo:owner/repo" in call_args
        assert "type:pr" in call_args
        assert "is:merged" in call_args
        assert f"merged:{start_date.isoformat()}..{end_date.isoformat()}" in call_args

    def test_fetch_last_n_days(self, date_fetcher, mock_github_client):
        """Test fetching PRs from the last N days."""
        # Setup
        mock_prs = [
            MagicMock(
                html_url="https://github.com/owner/repo/pull/3",
                number=3,
                title="Recent PR",
                user=MagicMock(login="user3"),
                labels=[],
                created_at=datetime.now() - timedelta(days=5),
                updated_at=datetime.now() - timedelta(days=4),
                state="closed",
                pull_request=MagicMock(merged_at=datetime.now() - timedelta(days=4)),
            ),
        ]

        mock_github_client.search_issues.return_value = mock_prs

        # Execute
        result = date_fetcher.fetch(repo_name="owner/repo", last_n_days=7)

        # Assert
        assert len(result) == 1
        assert result[0]["number"] == 3

        # Verify the query includes proper date range
        call_args = mock_github_client.search_issues.call_args[1]["query"]
        assert "merged:" in call_args

    def test_fetch_last_month(self, date_fetcher, mock_github_client):
        """Test fetching PRs from the last calendar month."""
        # Setup
        mock_prs = []
        mock_github_client.search_issues.return_value = mock_prs

        # Execute
        result = date_fetcher.fetch(repo_name="owner/repo", last_month=True)

        # Assert
        assert result == []

        # Verify query was made
        mock_github_client.search_issues.assert_called_once()

    def test_fetch_by_quarter(self, date_fetcher, mock_github_client):
        """Test fetching PRs from a specific quarter."""
        # Setup
        mock_prs = [
            MagicMock(
                html_url="https://github.com/owner/repo/pull/4",
                number=4,
                title="Q1 PR",
                user=MagicMock(login="user4"),
                labels=[],
                created_at=datetime(2024, 2, 15),
                updated_at=datetime(2024, 2, 16),
                state="closed",
                pull_request=MagicMock(merged_at=datetime(2024, 2, 16)),
            ),
        ]

        mock_github_client.search_issues.return_value = mock_prs

        # Execute
        result = date_fetcher.get_prs_by_quarter("owner/repo", year=2024, quarter=1)

        # Assert
        assert len(result) == 1
        assert result[0]["number"] == 4

        # Verify date range in query
        call_args = mock_github_client.search_issues.call_args[1]["query"]
        assert "2024-01-01" in call_args
        assert "2024-03-31" in call_args

    def test_fetch_with_different_states(self, date_fetcher, mock_github_client):
        """Test fetching PRs with different state filters."""
        # Setup
        mock_prs = [
            MagicMock(
                html_url="https://github.com/owner/repo/pull/5",
                number=5,
                title="Open PR",
                user=MagicMock(login="user5"),
                labels=[],
                created_at=datetime.now() - timedelta(days=2),
                updated_at=datetime.now() - timedelta(days=1),
                state="open",
                pull_request=None,
            ),
        ]

        mock_github_client.search_issues.return_value = mock_prs

        # Execute
        result = date_fetcher.fetch(repo_name="owner/repo", last_n_days=7, state="open")

        # Assert
        assert len(result) == 1
        assert result[0]["state"] == "open"

        # Verify query includes open state
        call_args = mock_github_client.search_issues.call_args[1]["query"]
        assert "is:open" in call_args

    def test_invalid_fetch_params(self, date_fetcher):
        """Test error handling for invalid parameters."""
        # Missing repo_name
        with pytest.raises(ValueError, match="repo_name is required"):
            date_fetcher.fetch()

        # Missing date criteria
        with pytest.raises(ValueError, match="Must specify either"):
            date_fetcher.fetch(repo_name="owner/repo")

    def test_invalid_quarter(self, date_fetcher):
        """Test error handling for invalid quarter."""
        with pytest.raises(ValueError, match="Quarter must be"):
            date_fetcher.get_prs_by_quarter("owner/repo", 2024, 5)
