"""
Date-based PR fetcher implementation.
"""

from datetime import datetime, timedelta
from typing import Any

from loguru import logger

from ...logging_config import log_api_call, log_processing_step
from .base import BasePRFetcher


class DateRangePRFetcher(BasePRFetcher):
    """
    Fetches PRs based on date ranges.

    Handles:
    - PRs within a specific date range
    - PRs from the last N days
    - PRs from the last calendar month
    - PRs from specific time periods
    """

    def fetch(self, **kwargs) -> list[dict[str, Any]]:
        """
        Fetch PRs based on date criteria.

        Supported kwargs:
        - repo_name: Repository name (required)
        - start_date: Start date for range
        - end_date: End date for range (optional, defaults to now)
        - last_n_days: Number of days to look back
        - last_month: Boolean flag for last calendar month
        - state: PR state filter (open, closed, merged, all)

        Returns:
            List of PR data dictionaries
        """
        repo_name = kwargs.get("repo_name")
        if not repo_name:
            raise ValueError("repo_name is required")

        if kwargs.get("last_n_days"):
            return self.get_prs_last_n_days(
                repo_name, kwargs["last_n_days"], kwargs.get("state", "merged")
            )
        elif kwargs.get("last_month"):
            return self.get_prs_last_month(repo_name, kwargs.get("state", "merged"))
        elif kwargs.get("start_date"):
            return self.get_prs_by_date_range(
                repo_name,
                kwargs["start_date"],
                kwargs.get("end_date"),
                kwargs.get("state", "merged"),
            )
        else:
            raise ValueError(
                "Must specify either start_date, last_n_days, or last_month=True"
            )

    def get_prs_by_date_range(
        self,
        repo_name: str,
        start_date: datetime,
        end_date: datetime | None = None,
        state: str = "merged",
    ) -> list[dict[str, Any]]:
        """
        Get all PRs within a specific date range.

        Args:
            repo_name: Repository name (e.g., "owner/repo")
            start_date: Start date for PR search
            end_date: End date for PR search (defaults to now)
            state: PR state filter (open, closed, merged, all)

        Returns:
            List of PR data dictionaries
        """
        try:
            if end_date is None:
                end_date = datetime.now()

            log_processing_step(
                f"Fetching {state} PRs from {start_date.date()} to {end_date.date()}"
            )

            # Build query based on state
            query = f"repo:{repo_name} type:pr"

            if state == "merged":
                query += f" is:merged merged:{start_date.isoformat()}..{end_date.isoformat()}"
            elif state == "closed":
                query += f" is:closed closed:{start_date.isoformat()}..{end_date.isoformat()}"
            elif state == "open":
                query += (
                    f" is:open created:{start_date.isoformat()}..{end_date.isoformat()}"
                )
            elif state == "all":
                # For all PRs, use created date
                query += f" created:{start_date.isoformat()}..{end_date.isoformat()}"
            else:
                raise ValueError(f"Invalid state: {state}")

            log_api_call("search_issues", {"query": query})

            prs = []
            for pr in self.github_client.search_issues(query=query):
                pr_data = self._build_pr_data(pr)
                # Add repo context
                pr_data["repository"] = repo_name
                prs.append(pr_data)

            logger.info(
                f"Found {len(prs)} {state} PRs between {start_date.date()} and {end_date.date()}"
            )
            return prs

        except Exception as e:
            logger.error(f"Error fetching PRs by date range: {e}")
            raise

    def get_prs_last_n_days(
        self, repo_name: str, days: int = 30, state: str = "merged"
    ) -> list[dict[str, Any]]:
        """
        Get all PRs from the last N days.

        Args:
            repo_name: Repository name
            days: Number of days to look back (default: 30)
            state: PR state filter (open, closed, merged, all)

        Returns:
            List of PR data dictionaries
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        log_processing_step(f"Fetching {state} PRs from last {days} days")

        return self.get_prs_by_date_range(repo_name, start_date, end_date, state)

    def get_prs_last_month(
        self, repo_name: str, state: str = "merged"
    ) -> list[dict[str, Any]]:
        """
        Get all PRs from the last calendar month.

        Args:
            repo_name: Repository name
            state: PR state filter (open, closed, merged, all)

        Returns:
            List of PR data dictionaries
        """
        today = datetime.now()

        # Calculate first day of current month
        first_of_current = today.replace(day=1)

        # Calculate last day of previous month
        last_of_previous = first_of_current - timedelta(days=1)

        # Calculate first day of previous month
        first_of_previous = last_of_previous.replace(day=1)

        log_processing_step(
            f"Fetching {state} PRs from last month "
            f"({first_of_previous.date()} to {last_of_previous.date()})"
        )

        return self.get_prs_by_date_range(
            repo_name, first_of_previous, last_of_previous, state
        )

    def get_prs_by_quarter(
        self, repo_name: str, year: int, quarter: int, state: str = "merged"
    ) -> list[dict[str, Any]]:
        """
        Get all PRs from a specific quarter.

        Args:
            repo_name: Repository name
            year: Year (e.g., 2024)
            quarter: Quarter number (1-4)
            state: PR state filter

        Returns:
            List of PR data dictionaries
        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Quarter must be 1, 2, 3, or 4")

        # Calculate quarter boundaries
        quarter_starts = {
            1: datetime(year, 1, 1),
            2: datetime(year, 4, 1),
            3: datetime(year, 7, 1),
            4: datetime(year, 10, 1),
        }

        start_date = quarter_starts[quarter]

        # Calculate end date (start of next quarter or year)
        if quarter == 4:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = quarter_starts[quarter + 1] - timedelta(days=1)

        log_processing_step(f"Fetching {state} PRs from Q{quarter} {year}")

        return self.get_prs_by_date_range(repo_name, start_date, end_date, state)
