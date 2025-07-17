"""Tests for the Rate Limit Manager."""

import time
from datetime import UTC, datetime
from unittest.mock import Mock, patch

from github import RateLimitExceededException

from src.pr_agents.utilities.rate_limit_manager import RateLimitManager


class TestRateLimitManager:
    """Test cases for RateLimitManager."""

    def setup_method(self):
        """Reset singleton before each test."""
        RateLimitManager._instance = None
        RateLimitManager._github_client = None

    def test_singleton_pattern(self):
        """Test that RateLimitManager is a singleton."""
        manager1 = RateLimitManager()
        manager2 = RateLimitManager()
        assert manager1 is manager2

    def test_set_github_client(self):
        """Test setting the GitHub client."""
        manager = RateLimitManager()
        mock_client = Mock()
        manager.set_github_client(mock_client)
        assert manager._github_client == mock_client

    def test_check_rate_limit_no_client(self):
        """Test checking rate limit without a client."""
        manager = RateLimitManager()
        result = manager.check_rate_limit()

        assert result["limit"] == 5000
        assert result["remaining"] == 5000
        assert result["reset"] == 0

    def test_check_rate_limit_with_client(self):
        """Test checking rate limit with a client."""
        manager = RateLimitManager()
        mock_client = Mock()

        # Mock rate limit response
        mock_rate_limit = Mock()
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.remaining = 4500
        mock_rate_limit.core.reset.timestamp.return_value = 1234567890
        mock_rate_limit.search.limit = 30
        mock_rate_limit.search.remaining = 25
        mock_rate_limit.search.reset.timestamp.return_value = 1234567900

        mock_client.get_rate_limit.return_value = mock_rate_limit
        manager.set_github_client(mock_client)

        # Check core rate limit
        result = manager.check_rate_limit("core")
        assert result["limit"] == 5000
        assert result["remaining"] == 4500
        assert result["reset"] == 1234567890

        # Check search rate limit
        result = manager.check_rate_limit("search")
        assert result["limit"] == 30
        assert result["remaining"] == 25
        assert result["reset"] == 1234567900

    def test_rate_limit_caching(self):
        """Test that rate limit data is cached."""
        manager = RateLimitManager()
        mock_client = Mock()

        mock_rate_limit = Mock()
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.remaining = 4500
        mock_rate_limit.core.reset.timestamp.return_value = 1234567890

        mock_client.get_rate_limit.return_value = mock_rate_limit
        manager.set_github_client(mock_client)

        # First call should hit the API
        manager.check_rate_limit()
        assert mock_client.get_rate_limit.call_count == 1

        # Second call within interval should use cache
        manager.check_rate_limit()
        assert mock_client.get_rate_limit.call_count == 1

    @patch("time.sleep")
    def test_wait_if_needed_sufficient_remaining(self, mock_sleep):
        """Test wait_if_needed when sufficient requests remain."""
        manager = RateLimitManager()
        manager._rate_limit_data = {
            "core": {"limit": 5000, "remaining": 1000, "reset": 0}
        }

        manager.wait_if_needed(min_remaining=100)
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_if_needed_approaching_limit(self, mock_time, mock_sleep):
        """Test wait_if_needed when approaching rate limit."""
        manager = RateLimitManager()
        mock_client = Mock()
        manager.set_github_client(mock_client)

        current_time = 1234567890
        reset_time = current_time + 300  # 5 minutes in future

        mock_time.return_value = current_time
        # Set cached data and update last check time to avoid API call
        manager._rate_limit_data = {
            "core": {"limit": 5000, "remaining": 50, "reset": reset_time}
        }
        manager._last_check = current_time  # Prevent API call

        manager.wait_if_needed(min_remaining=100, safety_margin=1.0)

        # Should wait for reset time + safety margin
        expected_wait = 301.0
        mock_sleep.assert_called_once_with(expected_wait)

    def test_track_request(self):
        """Test tracking requests."""
        manager = RateLimitManager()
        manager._rate_limit_data = {
            "core": {"limit": 5000, "remaining": 1000, "reset": 0}
        }

        manager.track_request("core")
        assert manager._rate_limit_data["core"]["remaining"] == 999

        manager.track_request("core")
        assert manager._rate_limit_data["core"]["remaining"] == 998

    @patch("time.sleep")
    def test_handle_rate_limit_exception(self, mock_sleep):
        """Test handling rate limit exceeded exception."""
        manager = RateLimitManager()

        # Create mock exception
        future_time = datetime.now(tz=UTC).timestamp() + 300
        mock_exception = Mock(spec=RateLimitExceededException)
        mock_exception.reset_time = future_time

        manager.handle_rate_limit_exception(mock_exception)

        # Should sleep until reset + 1 second
        assert mock_sleep.called
        sleep_time = mock_sleep.call_args[0][0]
        assert 299 < sleep_time < 302  # Allow some variance

    def test_get_reset_time(self):
        """Test getting reset time."""
        manager = RateLimitManager()
        mock_client = Mock()
        manager.set_github_client(mock_client)
        reset_timestamp = 1234567890

        # Set cached data and update last check time to avoid API call
        manager._rate_limit_data = {
            "core": {"limit": 5000, "remaining": 1000, "reset": reset_timestamp}
        }
        manager._last_check = time.time()  # Prevent API call

        reset_time = manager.get_reset_time("core")
        assert isinstance(reset_time, datetime)
        assert reset_time.timestamp() == reset_timestamp

    def test_get_reset_time_no_data(self):
        """Test getting reset time with no data."""
        manager = RateLimitManager()
        reset_time = manager.get_reset_time("core")
        assert reset_time is None
