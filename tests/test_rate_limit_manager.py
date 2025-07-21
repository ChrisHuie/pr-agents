"""Tests for the Rate Limit Manager"""

import time
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from github import Github, GithubException, RateLimitExceededException

from src.pr_agents.utilities.rate_limit_manager import (
    RateLimitInfo,
    RateLimitManager,
    RequestPriority,
    RequestStats,
)


class TestRateLimitManager:
    """Test cases for RateLimitManager"""

    def setup_method(self):
        """Reset singleton before each test"""
        RateLimitManager._instance = None
        RateLimitManager._github_client = None

    def test_singleton_pattern(self):
        """Test that RateLimitManager is a singleton"""
        manager1 = RateLimitManager()
        manager2 = RateLimitManager()
        assert manager1 is manager2

    def test_set_github_client(self):
        """Test setting the GitHub client"""
        manager = RateLimitManager()
        mock_client = Mock(spec=Github)
        manager.set_github_client(mock_client)
        assert manager._github_client == mock_client

    def test_check_rate_limit_no_client(self):
        """Test checking rate limit without a client"""
        manager = RateLimitManager()
        result = manager.check_rate_limit()

        assert isinstance(result, RateLimitInfo)
        assert result.limit == 5000
        assert result.remaining == 5000
        assert result.reset > 0

    def test_check_rate_limit_with_client(self):
        """Test checking rate limit with a client"""
        manager = RateLimitManager()
        mock_client = Mock(spec=Github)

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
        assert isinstance(result, RateLimitInfo)
        assert result.limit == 5000
        assert result.remaining == 4500
        assert result.reset == 1234567890

        # Test usage calculation
        assert result.usage_percentage == 10.0  # 500/5000 * 100

        # Check search rate limit
        result = manager.check_rate_limit("search")
        assert result.limit == 30
        assert result.remaining == 25
        assert result.reset == 1234567900

    def test_rate_limit_info_properties(self):
        """Test RateLimitInfo properties"""
        current_time = time.time()
        info = RateLimitInfo(limit=5000, remaining=1000, reset=current_time + 3600)

        assert info.used == 4000
        assert info.usage_percentage == 80.0
        assert 3590 <= info.time_until_reset <= 3610
        assert not info.is_critical

        # Test critical status
        critical_info = RateLimitInfo(
            limit=5000, remaining=50, reset=current_time + 3600
        )
        assert critical_info.is_critical

    def test_rate_limit_caching(self):
        """Test that rate limit data is cached"""
        manager = RateLimitManager()
        mock_client = Mock(spec=Github)

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

    def test_calculate_intelligent_delay(self):
        """Test intelligent delay calculation"""
        manager = RateLimitManager()

        # Test with plenty of requests remaining
        high_capacity = RateLimitInfo(
            limit=5000, remaining=2000, reset=time.time() + 3600
        )
        delay = manager._calculate_intelligent_delay(
            high_capacity, RequestPriority.NORMAL
        )
        assert delay == 0.0

        # Test with critical remaining
        critical = RateLimitInfo(limit=5000, remaining=50, reset=time.time() + 3600)
        delay = manager._calculate_intelligent_delay(critical, RequestPriority.NORMAL)
        assert delay >= 10.0  # Should be aggressive throttling

        # Test priority differences
        high_prio_delay = manager._calculate_intelligent_delay(
            critical, RequestPriority.CRITICAL
        )
        normal_prio_delay = manager._calculate_intelligent_delay(
            critical, RequestPriority.NORMAL
        )
        low_prio_delay = manager._calculate_intelligent_delay(
            critical, RequestPriority.LOW
        )

        # With critical status and final calculations, the delays should be different
        # unless they're both clamped at the maximum
        if high_prio_delay < 30.0 and low_prio_delay < 30.0:
            assert high_prio_delay < normal_prio_delay < low_prio_delay

        # Verify minimum values - all should be at least aggressive throttling
        assert high_prio_delay >= 10.0  # Base aggressive throttling
        assert normal_prio_delay >= 10.0  # Should be at least aggressive
        assert low_prio_delay >= 10.0  # All critical requests get aggressive throttling

    @patch("time.sleep")
    def test_wait_if_needed(self, mock_sleep):
        """Test wait_if_needed functionality"""
        manager = RateLimitManager()
        mock_client = Mock(spec=Github)
        manager.set_github_client(mock_client)

        # Mock rate limit with plenty remaining
        high_capacity = RateLimitInfo(
            limit=5000, remaining=2000, reset=time.time() + 3600
        )
        manager._rate_limit_cache["core"] = high_capacity
        manager._last_check = time.time()  # Prevent API call

        wait_time = manager.wait_if_needed("core", RequestPriority.NORMAL)
        assert wait_time == 0.0
        mock_sleep.assert_not_called()

        # Mock rate limit with low remaining
        low_capacity = RateLimitInfo(limit=5000, remaining=50, reset=time.time() + 3600)
        manager._rate_limit_cache["core"] = low_capacity

        wait_time = manager.wait_if_needed("core", RequestPriority.NORMAL)
        assert wait_time > 0
        mock_sleep.assert_called()

    def test_track_request(self):
        """Test request tracking"""
        manager = RateLimitManager()

        # Set up cached rate limit info
        rate_info = RateLimitInfo(limit=5000, remaining=1000, reset=time.time() + 3600)
        manager._rate_limit_cache["core"] = rate_info

        # Track successful request
        initial_total = manager._stats.total_requests
        initial_successful = manager._stats.successful_requests

        manager.track_request("core", success=True)

        assert manager._stats.total_requests == initial_total + 1
        assert manager._stats.successful_requests == initial_successful + 1
        assert manager._rate_limit_cache["core"].remaining == 999

    def test_get_optimal_batch_size(self):
        """Test optimal batch size calculation"""
        manager = RateLimitManager()
        # Don't set a client to avoid any fallback issues during check_rate_limit calls

        # High capacity
        high_capacity = RateLimitInfo(
            limit=5000, remaining=2000, reset=time.time() + 3600
        )
        manager._rate_limit_cache["core"] = high_capacity
        manager._last_check = time.time()

        batch_size = manager.get_optimal_batch_size("core")
        assert batch_size == 100

        # Low capacity (but not critical)
        low_capacity = RateLimitInfo(
            limit=5000, remaining=600, reset=time.time() + 3600
        )
        manager._rate_limit_cache["core"] = low_capacity
        manager._last_check = time.time()  # Ensure cache is used

        batch_size = manager.get_optimal_batch_size("core")
        # 600 remaining: used=4400, 4400/5000=88% < 90%, so not critical
        # 600 > 500, so should return 50
        assert batch_size == 50

        # Critical capacity
        critical = RateLimitInfo(limit=5000, remaining=50, reset=time.time() + 3600)
        manager._rate_limit_cache["core"] = critical

        batch_size = manager.get_optimal_batch_size("core")
        assert batch_size == 5

    @patch("time.sleep")
    def test_execute_with_retry_success(self, mock_sleep):
        """Test successful execution with retry wrapper"""
        manager = RateLimitManager()
        mock_client = Mock(spec=Github)
        manager.set_github_client(mock_client)

        # Set up rate limit info to avoid throttling
        rate_info = RateLimitInfo(limit=5000, remaining=2000, reset=time.time() + 3600)
        manager._rate_limit_cache["core"] = rate_info
        manager._last_check = time.time()

        # Mock function that succeeds
        mock_func = Mock(return_value="success")

        result = manager.execute_with_retry(mock_func, "arg1", "arg2", kwarg="test")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", "arg2", kwarg="test")
        mock_sleep.assert_not_called()  # No throttling needed

    @patch("time.sleep")
    @patch("random.uniform")
    def test_execute_with_retry_rate_limit_exception(self, mock_random, mock_sleep):
        """Test retry on rate limit exception"""
        manager = RateLimitManager()
        mock_client = Mock(spec=Github)
        manager.set_github_client(mock_client)

        # Mock random for jitter
        mock_random.return_value = 0.5

        # Set up rate limit
        rate_info = RateLimitInfo(limit=5000, remaining=2000, reset=time.time() + 3600)
        manager._rate_limit_cache["core"] = rate_info
        manager._last_check = time.time()

        # Mock function that fails once then succeeds
        mock_func = Mock()
        mock_exception = RateLimitExceededException(
            status=403, data={"message": "rate limit"}
        )
        mock_exception.reset_time = time.time() + 1  # Add reset_time property
        mock_func.side_effect = [mock_exception, "success"]

        result = manager.execute_with_retry(mock_func, resource="core")

        assert result == "success"
        assert manager._stats.retried_requests == 1

    def test_extract_rate_limit_from_headers(self):
        """Test extracting rate limit info from headers"""
        manager = RateLimitManager()

        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4500",
            "X-RateLimit-Reset": "1234567890",
        }

        rate_info = manager.extract_rate_limit_from_headers(headers)

        assert rate_info is not None
        assert rate_info.limit == 5000
        assert rate_info.remaining == 4500
        assert rate_info.reset == 1234567890.0

    def test_extract_rate_limit_invalid_headers(self):
        """Test extracting rate limit from invalid headers"""
        manager = RateLimitManager()

        # Missing headers
        rate_info = manager.extract_rate_limit_from_headers({})
        assert rate_info is None

        # Invalid values
        rate_info = manager.extract_rate_limit_from_headers(
            {
                "X-RateLimit-Limit": "invalid",
                "X-RateLimit-Remaining": "4500",
                "X-RateLimit-Reset": "1234567890",
            }
        )
        assert rate_info is None

    def test_update_from_response(self):
        """Test updating rate limit from API response"""
        manager = RateLimitManager()

        # Mock response with headers
        mock_response = Mock()
        mock_response.headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4500",
            "X-RateLimit-Reset": "1234567890",
        }

        manager.update_from_response(mock_response, "core")

        assert "core" in manager._rate_limit_cache
        rate_info = manager._rate_limit_cache["core"]
        assert rate_info.limit == 5000
        assert rate_info.remaining == 4500

    def test_get_stats(self):
        """Test getting statistics"""
        manager = RateLimitManager()

        stats = manager.get_stats()
        assert isinstance(stats, RequestStats)
        assert stats.total_requests == 0
        assert stats.successful_requests == 0

    def test_reset_stats(self):
        """Test resetting statistics"""
        manager = RateLimitManager()

        # Modify stats
        manager._stats.total_requests = 10
        manager._stats.successful_requests = 8

        manager.reset_stats()

        assert manager._stats.total_requests == 0
        assert manager._stats.successful_requests == 0

    def test_request_priority_enum(self):
        """Test RequestPriority enum values"""
        assert RequestPriority.CRITICAL.value == 1
        assert RequestPriority.HIGH.value == 2
        assert RequestPriority.NORMAL.value == 3
        assert RequestPriority.LOW.value == 4

    @patch("time.sleep")
    def test_handle_rate_limit_exception(self, mock_sleep):
        """Test handling rate limit exceeded exception"""
        manager = RateLimitManager()

        future_time = datetime.now(tz=UTC).timestamp() + 300
        mock_exception = Mock(spec=RateLimitExceededException)
        mock_exception.reset_time = future_time

        initial_count = manager._stats.rate_limited_requests
        manager.handle_rate_limit_exception(mock_exception)

        # Should increment counter and sleep
        assert manager._stats.rate_limited_requests == initial_count + 1
        assert mock_sleep.called
        sleep_time = mock_sleep.call_args[0][0]
        assert 299 < sleep_time < 302  # Allow some variance

    @patch("time.sleep")
    def test_github_exception_retry_logic(self, mock_sleep):
        """Test retry logic for GitHub exceptions with 403/429"""
        manager = RateLimitManager()
        mock_client = Mock(spec=Github)
        manager.set_github_client(mock_client)

        # Set up rate limit to avoid throttling
        rate_info = RateLimitInfo(limit=5000, remaining=2000, reset=time.time() + 3600)
        manager._rate_limit_cache["core"] = rate_info
        manager._last_check = time.time()

        # Mock function that fails with 403 then succeeds
        mock_func = Mock()
        github_exception = GithubException(status=403, data={"message": "Forbidden"})
        mock_func.side_effect = [github_exception, "success"]

        with patch("random.uniform", return_value=0.5):
            result = manager.execute_with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2
        assert mock_sleep.called

    def test_execute_with_retry_non_rate_limit_exception(self):
        """Test that non-rate-limit exceptions are propagated"""
        manager = RateLimitManager()
        mock_client = Mock(spec=Github)
        manager.set_github_client(mock_client)

        rate_info = RateLimitInfo(limit=5000, remaining=2000, reset=time.time() + 3600)
        manager._rate_limit_cache["core"] = rate_info
        manager._last_check = time.time()

        # Mock function that raises a non-rate-limit error
        mock_func = Mock()
        mock_func.side_effect = ValueError("Test error")

        with pytest.raises(ValueError):
            manager.execute_with_retry(mock_func)

        # Should track as failed request
        assert manager._stats.total_requests == 1
        assert manager._stats.successful_requests == 0

    def test_all_retries_exhausted(self):
        """Test behavior when all retries are exhausted"""
        manager = RateLimitManager()
        mock_client = Mock(spec=Github)
        manager.set_github_client(mock_client)

        rate_info = RateLimitInfo(limit=5000, remaining=2000, reset=time.time() + 3600)
        manager._rate_limit_cache["core"] = rate_info
        manager._last_check = time.time()

        # Mock function that always fails with rate limit
        mock_func = Mock()
        github_exception = GithubException(
            status=429, data={"message": "Too Many Requests"}
        )
        mock_func.side_effect = github_exception

        with pytest.raises(GithubException):
            manager.execute_with_retry(mock_func)

        # Should have tried max_retries + 1 times
        assert mock_func.call_count == manager._max_retries + 1
