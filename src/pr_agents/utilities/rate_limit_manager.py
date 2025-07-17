"""Rate limit management for GitHub API calls."""

import time
from datetime import UTC, datetime
from typing import Any, Optional

from github import Github, RateLimitExceededException
from loguru import logger

from src.pr_agents.logging_config import log_api_call, log_error_with_context


class RateLimitManager:
    """Manages GitHub API rate limits across all components.

    This is a singleton class that tracks API usage and prevents
    rate limit exceeded errors by implementing smart waiting strategies.
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
        self._check_interval: float = 60.0  # Check every 60 seconds
        self._rate_limit_data: dict[str, Any] = {}

    def set_github_client(self, github_client: Github) -> None:
        """Set the GitHub client to use for rate limit checks.

        Args:
            github_client: Authenticated GitHub client
        """
        self._github_client = github_client

    def check_rate_limit(self, resource: str = "core") -> dict[str, Any]:
        """Check current rate limit status.

        Args:
            resource: The API resource to check (core, search, graphql)

        Returns:
            Dict containing limit, remaining, reset time
        """
        if not self._github_client:
            logger.warning("No GitHub client set for rate limit manager")
            return {"limit": 5000, "remaining": 5000, "reset": 0}

        current_time = time.time()

        # Use cached data if checked recently
        if current_time - self._last_check < self._check_interval:
            return self._rate_limit_data.get(
                resource, {"limit": 5000, "remaining": 5000, "reset": 0}
            )

        try:
            log_api_call("GET", "/rate_limit", {})
            rate_limit = self._github_client.get_rate_limit()

            # Update cache
            self._last_check = current_time
            self._rate_limit_data = {
                "core": {
                    "limit": rate_limit.core.limit,
                    "remaining": rate_limit.core.remaining,
                    "reset": rate_limit.core.reset.timestamp(),
                },
                "search": {
                    "limit": rate_limit.search.limit,
                    "remaining": rate_limit.search.remaining,
                    "reset": rate_limit.search.reset.timestamp(),
                },
            }

            logger.debug(
                f"Rate limit for {resource}: {self._rate_limit_data.get(resource)}"
            )
            return self._rate_limit_data.get(resource, {})

        except Exception as e:
            log_error_with_context(
                e, {"operation": "check_rate_limit", "resource": resource}
            )
            return {"limit": 5000, "remaining": 5000, "reset": 0}

    def wait_if_needed(
        self,
        resource: str = "core",
        min_remaining: int = 100,
        safety_margin: float = 1.0,
    ) -> None:
        """Wait if approaching rate limit.

        Args:
            resource: The API resource being used
            min_remaining: Minimum requests to keep in reserve
            safety_margin: Extra seconds to wait after reset
        """
        # Skip if no client is set
        if not self._github_client:
            return

        rate_info = self.check_rate_limit(resource)
        remaining = rate_info.get("remaining", 5000)

        if remaining <= min_remaining:
            reset_time = rate_info.get("reset", 0)
            current_time = time.time()

            if reset_time > current_time:
                wait_time = reset_time - current_time + safety_margin
                logger.warning(
                    f"Approaching rate limit for {resource}. "
                    f"Waiting {wait_time:.1f} seconds until reset."
                )
                time.sleep(wait_time)

                # Clear cache to force refresh after waiting
                self._last_check = 0

    def handle_rate_limit_exception(
        self, exception: RateLimitExceededException, resource: str = "core"
    ) -> None:
        """Handle a rate limit exceeded exception.

        Args:
            exception: The rate limit exception
            resource: The API resource that was limited
        """
        reset_time = exception.reset_time
        current_time = datetime.now(UTC).timestamp()

        if reset_time > current_time:
            wait_time = reset_time - current_time + 1.0
            logger.error(
                f"Rate limit exceeded for {resource}. "
                f"Waiting {wait_time:.1f} seconds until reset."
            )
            time.sleep(wait_time)

            # Clear cache
            self._last_check = 0

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

    def track_request(self, resource: str = "core") -> None:
        """Track that a request was made.

        This decrements the cached remaining count to avoid
        needing to check the API constantly.

        Args:
            resource: The API resource used
        """
        if resource in self._rate_limit_data:
            self._rate_limit_data[resource]["remaining"] -= 1
            logger.debug(
                f"Request tracked for {resource}. "
                f"Remaining: {self._rate_limit_data[resource]['remaining']}"
            )
