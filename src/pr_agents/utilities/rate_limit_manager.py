"""Rate limit management for GitHub API calls."""

import random
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from github import Github, GithubException, RateLimitExceededException
from loguru import logger

from src.pr_agents.logging_config import log_api_call, log_error_with_context


class RequestPriority(Enum):
    """Priority levels for API requests."""

    CRITICAL = 1  # Must complete (e.g., fetching PR metadata)
    HIGH = 2  # Important but can be delayed (e.g., reviews)
    NORMAL = 3  # Standard priority (e.g., file contents)
    LOW = 4  # Nice to have (e.g., additional context)


@dataclass
class RateLimitInfo:
    """Container for rate limit information."""

    limit: int
    remaining: int
    reset: float
    used: int = field(init=False)

    def __post_init__(self):
        if isinstance(self.limit, int) and isinstance(self.remaining, int):
            self.used = self.limit - self.remaining
        else:
            self.used = 0

    @property
    def usage_percentage(self) -> float:
        """Calculate percentage of rate limit used."""
        if self.limit == 0:
            return 0.0
        return (self.used / self.limit) * 100

    @property
    def time_until_reset(self) -> float:
        """Calculate seconds until rate limit resets."""
        return max(self.reset - time.time(), 0)

    @property
    def is_critical(self) -> bool:
        """Check if rate limit is critically low."""
        return self.remaining < 100 or self.usage_percentage > 90


@dataclass
class RequestStats:
    """Statistics for rate limit management."""

    total_requests: int = 0
    successful_requests: int = 0
    rate_limited_requests: int = 0
    retried_requests: int = 0
    wait_time_total: float = 0.0
    last_request_time: float = field(default_factory=time.time)


class RateLimitManager:
    """Manages GitHub API rate limits across all components.

    This is a singleton class that tracks API usage and prevents
    rate limit exceeded errors by implementing smart waiting strategies.
    Features:
    - Intelligent request batching and throttling
    - Exponential backoff with jitter
    - Cross-fetcher rate limit awareness
    - Request prioritization
    - Comprehensive metrics tracking
    """

    _instance: Optional["RateLimitManager"] = None
    _github_client: Github | None = None

    def __new__(cls) -> "RateLimitManager":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the rate limit manager."""
        if self._initialized:
            return

        self._initialized = True
        self._last_check: float = 0
        self._check_interval: float = 30.0  # Check every 30 seconds
        self._rate_limit_cache: dict[str, RateLimitInfo] = {}
        self._request_queue: deque[tuple[RequestPriority, Callable, dict]] = deque()
        self._stats = RequestStats()

        # Configuration
        self._safety_buffer = 100  # Keep this many requests in reserve
        self._critical_threshold = 0.1  # 10% remaining is critical
        self._aggressive_threshold = (
            0.25  # 25% remaining triggers aggressive throttling
        )
        self._max_retries = 3
        self._base_retry_delay = 1.0
        self._max_retry_delay = 60.0

    def set_github_client(self, github_client: Github) -> None:
        """Set the GitHub client to use for rate limit checks.

        Args:
            github_client: Authenticated GitHub client
        """
        RateLimitManager._github_client = github_client

    def check_rate_limit(
        self, resource: str = "core", force_check: bool = False
    ) -> RateLimitInfo:
        """Check current rate limit status.

        Args:
            resource: The API resource to check (core, search, graphql)
            force_check: Force an API call even if cached data exists

        Returns:
            RateLimitInfo object with current status
        """
        current_time = time.time()

        # Use cached data if available and recent
        if not force_check and resource in self._rate_limit_cache:
            cached_info = self._rate_limit_cache[resource]
            if current_time - self._last_check < self._check_interval:
                return cached_info

        if not self._github_client:
            logger.warning("No GitHub client set for rate limit manager")
            return RateLimitInfo(limit=5000, remaining=5000, reset=time.time() + 3600)

        try:
            log_api_call("GET", "/rate_limit", {})
            rate_limit = self._github_client.get_rate_limit()
            self._last_check = current_time

            # Update cache for all resources
            resource_map = {
                "core": rate_limit.core,
                "search": rate_limit.search,
                "graphql": getattr(rate_limit, "graphql", None),
            }

            for res_name, res_limit in resource_map.items():
                if res_limit:
                    self._rate_limit_cache[res_name] = RateLimitInfo(
                        limit=res_limit.limit,
                        remaining=res_limit.remaining,
                        reset=res_limit.reset.timestamp(),
                    )

            rate_info = self._rate_limit_cache.get(resource)
            if rate_info:
                logger.debug(
                    f"Rate limit for {resource}: {rate_info.remaining}/{rate_info.limit} "
                    f"(used {rate_info.usage_percentage:.1f}%) - "
                    f"resets in {rate_info.time_until_reset:.0f}s"
                )
                return rate_info
            else:
                # Fallback for unknown resource
                return RateLimitInfo(
                    limit=5000, remaining=5000, reset=time.time() + 3600
                )

        except Exception as e:
            log_error_with_context(
                e, {"operation": "check_rate_limit", "resource": resource}
            )
            # Return conservative defaults on error
            return RateLimitInfo(limit=5000, remaining=1000, reset=time.time() + 3600)

    def wait_if_needed(
        self,
        resource: str = "core",
        priority: RequestPriority = RequestPriority.NORMAL,
    ) -> float:
        """Wait if needed based on rate limit status and request priority.

        Args:
            resource: The API resource being used
            priority: Priority level of the request

        Returns:
            Actual wait time in seconds
        """
        if not self._github_client:
            return 0.0

        rate_info = self.check_rate_limit(resource)

        # Calculate delay based on current state
        delay = self._calculate_intelligent_delay(rate_info, priority)

        if delay > 0:
            # Add jitter to prevent thundering herd
            jittered_delay = delay * (0.9 + random.random() * 0.2)

            logger.info(
                f"Rate limit throttling for {resource}: waiting {jittered_delay:.1f}s "
                f"({rate_info.remaining}/{rate_info.limit} remaining, "
                f"{rate_info.usage_percentage:.1f}% used)"
            )

            time.sleep(jittered_delay)
            self._stats.wait_time_total += jittered_delay

            # Force cache refresh after significant wait
            if jittered_delay > 10:
                self._last_check = 0

            return jittered_delay

        return 0.0

    def _calculate_intelligent_delay(
        self, rate_info: RateLimitInfo, priority: RequestPriority
    ) -> float:
        """Calculate intelligent delay based on rate limit status and priority.

        Args:
            rate_info: Current rate limit information
            priority: Request priority level

        Returns:
            Delay in seconds
        """
        # No delay if we have plenty of requests
        if rate_info.remaining > 1000:
            return 0.0

        # Priority multipliers (lower = less delay)
        priority_multipliers = {
            RequestPriority.CRITICAL: 0.1,
            RequestPriority.HIGH: 0.3,
            RequestPriority.NORMAL: 1.0,
            RequestPriority.LOW: 2.0,
        }

        multiplier = priority_multipliers.get(priority, 1.0)

        # Calculate base delay based on usage
        if rate_info.is_critical:
            # Critical: aggressive throttling
            base_delay = 10.0
        elif rate_info.usage_percentage > 75:
            # High usage: moderate throttling
            base_delay = 5.0
        elif rate_info.usage_percentage > 50:
            # Medium usage: light throttling
            base_delay = 2.0
        else:
            # Low usage: minimal throttling
            base_delay = 0.5

        # Adjust based on time until reset
        time_factor = min(rate_info.time_until_reset / 3600, 1.0)  # Cap at 1 hour

        # Calculate sustainable rate
        if rate_info.remaining > 0 and rate_info.time_until_reset > 0:
            # Leave safety buffer
            effective_remaining = max(rate_info.remaining - self._safety_buffer, 1)
            sustainable_rate = effective_remaining / rate_info.time_until_reset

            if sustainable_rate > 0:
                sustainable_delay = 1.0 / sustainable_rate
                # Use the more conservative delay
                base_delay = max(base_delay, sustainable_delay)

        # Apply priority multiplier and time factor
        final_delay = base_delay * multiplier * (1.0 + time_factor)

        # Clamp to reasonable range
        clamped_delay = min(max(final_delay, 0.1), 30.0)

        # Ensure different priorities have different delays for critical states
        if rate_info.is_critical and final_delay >= 10.0:
            # Add a small additional delay for lower priorities
            priority_adjustment = {
                RequestPriority.CRITICAL: 0.0,
                RequestPriority.HIGH: 2.0,
                RequestPriority.NORMAL: 5.0,
                RequestPriority.LOW: 10.0,
            }.get(priority, 0.0)
            clamped_delay = min(clamped_delay + priority_adjustment, 30.0)

        return clamped_delay

    def handle_rate_limit_exception(
        self, exception: RateLimitExceededException, resource: str = "core"
    ) -> None:
        """Handle a rate limit exceeded exception.

        Args:
            exception: The rate limit exception
            resource: The API resource that was limited
        """
        self._stats.rate_limited_requests += 1

        # Extract reset time from exception
        reset_time = getattr(exception, "reset_time", None)
        if reset_time is None:
            # Fallback: wait for 5 minutes if no reset time available
            reset_time = datetime.now(UTC).timestamp() + 300
        elif hasattr(reset_time, "timestamp"):
            reset_time = reset_time.timestamp()

        current_time = datetime.now(UTC).timestamp()

        if reset_time > current_time:
            wait_time = reset_time - current_time + 1.0
            logger.error(
                f"Rate limit exceeded for {resource}. "
                f"Waiting {wait_time:.1f} seconds until reset."
            )
            time.sleep(wait_time)
            self._stats.wait_time_total += wait_time

            # Force cache refresh
            self._last_check = 0
            if resource in self._rate_limit_cache:
                del self._rate_limit_cache[resource]

    def get_reset_time(self, resource: str = "core") -> datetime | None:
        """Get the reset time for a resource.

        Args:
            resource: The API resource

        Returns:
            DateTime when the rate limit resets, or None
        """
        # Return None if no client
        if not self._github_client:
            return None

        rate_info = self.check_rate_limit(resource)
        reset_timestamp = rate_info.get("reset")

        if reset_timestamp:
            return datetime.fromtimestamp(reset_timestamp, tz=UTC)
        return None

    def track_request(self, resource: str = "core", success: bool = True) -> None:
        """Track that a request was made.

        This decrements the cached remaining count to avoid
        needing to check the API constantly.

        Args:
            resource: The API resource used
            success: Whether the request was successful
        """
        self._stats.total_requests += 1
        self._stats.last_request_time = time.time()

        if success:
            self._stats.successful_requests += 1

            # Decrement cached count
            if resource in self._rate_limit_cache and hasattr(
                self._rate_limit_cache[resource], "remaining"
            ):
                if isinstance(self._rate_limit_cache[resource].remaining, int):
                    self._rate_limit_cache[resource].remaining = max(
                        self._rate_limit_cache[resource].remaining - 1, 0
                    )

                logger.debug(
                    f"Request tracked for {resource}. "
                    f"Remaining: {self._rate_limit_cache[resource].remaining}"
                )

    def get_adaptive_delay(
        self, resource: str = "core", priority: RequestPriority = RequestPriority.NORMAL
    ) -> float:
        """Calculate adaptive delay between requests based on rate limit.

        Args:
            resource: API resource to check
            priority: Request priority level

        Returns:
            Delay in seconds to maintain sustainable request rate
        """
        rate_info = self.check_rate_limit(resource)
        return self._calculate_intelligent_delay(rate_info, priority)

    def get_optimal_batch_size(self, resource: str = "core") -> int:
        """Calculate optimal batch size based on current rate limit.

        Args:
            resource: API resource to check

        Returns:
            Recommended batch size for current conditions
        """
        rate_info = self.check_rate_limit(resource)

        # If rate limit is critical, use small batches
        if rate_info.is_critical:
            return 5

        # Calculate based on remaining capacity
        if rate_info.remaining > 1000:
            return 100  # Large batches when plenty of capacity
        elif rate_info.remaining > 500:
            return 50  # Medium batches
        elif rate_info.remaining > 200:
            return 20  # Small batches
        else:
            return 10  # Minimal batches when low on requests

    def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        resource: str = "core",
        priority: RequestPriority = RequestPriority.NORMAL,
        **kwargs,
    ) -> Any:
        """Execute a function with automatic retry and rate limit handling.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            resource: API resource being used
            priority: Request priority
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            Exception: If all retries are exhausted
        """
        last_exception = None
        retry_count = 0

        while retry_count <= self._max_retries:
            try:
                # Wait if needed before making request
                self.wait_if_needed(resource, priority)

                # Execute the function
                result = func(*args, **kwargs)

                # Track successful request
                self.track_request(resource, success=True)

                if retry_count > 0:
                    self._stats.retried_requests += 1
                    logger.info(f"Request succeeded after {retry_count} retries")

                return result

            except RateLimitExceededException as e:
                last_exception = e
                self.handle_rate_limit_exception(e, resource)
                retry_count += 1

            except GithubException as e:
                # Check if it's a rate limit error (403 or 429)
                if e.status in [403, 429]:
                    last_exception = e
                    logger.warning(f"GitHub API error {e.status}: {e.data}")

                    # Exponential backoff with jitter
                    wait_time = min(
                        self._base_retry_delay * (2**retry_count)
                        + random.uniform(0, 1),
                        self._max_retry_delay,
                    )

                    logger.info(
                        f"Retry {retry_count}/{self._max_retries} after {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)
                    retry_count += 1
                else:
                    # Non-rate-limit error, propagate
                    self.track_request(resource, success=False)
                    raise

            except Exception:
                # Unexpected error, propagate
                self.track_request(resource, success=False)
                raise

        # All retries exhausted
        logger.error(f"All {self._max_retries} retries exhausted for {resource}")
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError(f"Failed after {self._max_retries} retries")

    def extract_rate_limit_from_headers(
        self, headers: dict[str, str]
    ) -> RateLimitInfo | None:
        """Extract rate limit information from response headers.

        Args:
            headers: HTTP response headers

        Returns:
            RateLimitInfo if headers contain rate limit data, None otherwise
        """
        try:
            # GitHub rate limit headers
            limit = int(headers.get("X-RateLimit-Limit", 0))
            remaining = int(headers.get("X-RateLimit-Remaining", 0))
            reset = int(headers.get("X-RateLimit-Reset", 0))

            if limit > 0 and reset > 0:
                return RateLimitInfo(
                    limit=limit, remaining=remaining, reset=float(reset)
                )
        except (ValueError, TypeError):
            pass

        return None

    def update_from_response(self, response: Any, resource: str = "core") -> None:
        """Update rate limit information from API response.

        Args:
            response: GitHub API response object
            resource: API resource used
        """
        # Try to extract headers from response
        headers = {}
        if hasattr(response, "headers"):
            headers = response.headers
        elif hasattr(response, "raw_headers"):
            headers = dict(response.raw_headers)

        if headers:
            rate_info = self.extract_rate_limit_from_headers(headers)
            if rate_info:
                self._rate_limit_cache[resource] = rate_info
                logger.debug(
                    f"Updated {resource} rate limit from headers: "
                    f"{rate_info.remaining}/{rate_info.limit}"
                )

    def get_stats(self) -> RequestStats:
        """Get request statistics.

        Returns:
            Current request statistics
        """
        return self._stats

    def reset_stats(self) -> None:
        """Reset request statistics."""
        self._stats = RequestStats()
