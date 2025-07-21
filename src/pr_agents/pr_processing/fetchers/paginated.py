"""
Paginated PR fetcher with rate limit handling.

Handles large numbers of PRs by using proper pagination and rate limiting.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from github import Github
from github.PaginatedList import PaginatedList
from loguru import logger

from ...utilities.rate_limit_manager import RateLimitManager
from .base import BasePRFetcher


class PaginatedPRFetcher(BasePRFetcher):
    """
    PR fetcher with pagination and rate limit handling.

    Features:
    - Automatic pagination for large result sets
    - Rate limit aware with adaptive delays
    - Progress tracking with checkpoint support
    - Resilient to interruptions
    """

    def __init__(
        self,
        github_token: str,
        per_page: int = 30,
        checkpoint_dir: Path | None = None,
    ):
        """
        Initialize paginated PR fetcher.

        Args:
            github_token: GitHub authentication token
            per_page: Results per page (max 100)
            checkpoint_dir: Directory for checkpoint files
        """
        self.github_client = Github(github_token, per_page=min(per_page, 100))
        self.rate_limit_manager = RateLimitManager()
        self.rate_limit_manager.set_github_client(self.github_client)
        self.per_page = min(per_page, 100)
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None

        if self.checkpoint_dir:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, **kwargs) -> list[dict[str, Any]]:
        """
        Fetch PRs based on provided criteria.

        Supports:
        - repo_name + release_tag: PRs in a release
        - repo_name + from_date + to_date: PRs in date range
        - repo_name + labels: PRs with specific labels
        - pr_urls: List of specific PR URLs
        """
        if "pr_urls" in kwargs:
            return self._fetch_specific_prs(kwargs["pr_urls"])
        elif "release_tag" in kwargs:
            return self.fetch_release_prs(
                kwargs["repo_name"],
                kwargs["release_tag"],
                kwargs.get("checkpoint_file"),
            )
        elif "from_date" in kwargs and "to_date" in kwargs:
            return self.fetch_date_range_prs(
                kwargs["repo_name"],
                kwargs["from_date"],
                kwargs["to_date"],
                kwargs.get("checkpoint_file"),
            )
        elif "labels" in kwargs:
            return self.fetch_labeled_prs(
                kwargs["repo_name"],
                kwargs["labels"],
                kwargs.get("state", "all"),
                kwargs.get("checkpoint_file"),
            )
        else:
            raise ValueError("Invalid fetch parameters")

    def fetch_release_prs(
        self,
        repo_name: str,
        release_tag: str,
        checkpoint_file: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch all PRs included in a release with pagination support.

        Args:
            repo_name: Repository name (owner/repo)
            release_tag: Release tag
            checkpoint_file: Name for checkpoint file

        Returns:
            List of PR data dictionaries
        """
        checkpoint_path = self._get_checkpoint_path(checkpoint_file)
        checkpoint_data = self._load_checkpoint(checkpoint_path)

        # Check if we're resuming
        if checkpoint_data and checkpoint_data.get("release_tag") == release_tag:
            logger.info(
                f"Resuming from checkpoint: {len(checkpoint_data.get('prs', []))} PRs already processed"
            )
            existing_prs = checkpoint_data.get("prs", [])
            existing_numbers = {pr["number"] for pr in existing_prs}
        else:
            existing_prs = []
            existing_numbers = set()

        try:
            # Check rate limit before starting
            self.rate_limit_manager.wait_if_needed(resource="core", min_remaining=50)

            repo = self.github_client.get_repo(repo_name)

            # Get release
            logger.info(f"Fetching release {release_tag}")
            release = repo.get_release(release_tag)
            release_date = release.created_at

            # Get previous release date
            previous_date = self._get_previous_release_date(repo, release_date)

            # Build search query
            query = (
                f"repo:{repo_name} "
                f"type:pr "
                f"is:merged "
                f"merged:{previous_date.isoformat()}..{release_date.isoformat()}"
            )

            logger.info(f"Searching PRs with query: {query}")

            # Fetch PRs with pagination
            prs = self._paginated_search(
                query,
                existing_numbers,
                checkpoint_path,
                {
                    "repo_name": repo_name,
                    "release_tag": release_tag,
                    "prs": existing_prs,
                },
            )

            logger.success(f"Fetched {len(prs)} PRs for release {release_tag}")

            # Clean up checkpoint on success
            if checkpoint_path and checkpoint_path.exists():
                checkpoint_path.unlink()

            return prs

        except Exception as e:
            logger.error(f"Error fetching release PRs: {e}")
            # Return what we have so far
            return existing_prs

    def fetch_date_range_prs(
        self,
        repo_name: str,
        from_date: datetime,
        to_date: datetime,
        checkpoint_file: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch PRs merged within a date range.

        Args:
            repo_name: Repository name
            from_date: Start date
            to_date: End date
            checkpoint_file: Checkpoint file name

        Returns:
            List of PR data
        """
        checkpoint_path = self._get_checkpoint_path(checkpoint_file)
        checkpoint_data = self._load_checkpoint(checkpoint_path)

        # Check if resuming
        if checkpoint_data:
            existing_prs = checkpoint_data.get("prs", [])
            existing_numbers = {pr["number"] for pr in existing_prs}
        else:
            existing_prs = []
            existing_numbers = set()

        # Build query
        query = (
            f"repo:{repo_name} "
            f"type:pr "
            f"is:merged "
            f"merged:{from_date.isoformat()}..{to_date.isoformat()}"
        )

        # Fetch with pagination
        prs = self._paginated_search(
            query,
            existing_numbers,
            checkpoint_path,
            {
                "repo_name": repo_name,
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "prs": existing_prs,
            },
        )

        # Clean up checkpoint
        if checkpoint_path and checkpoint_path.exists():
            checkpoint_path.unlink()

        return prs

    def _paginated_search(
        self,
        query: str,
        existing_numbers: set[int],
        checkpoint_path: Path | None,
        checkpoint_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Execute paginated search with rate limit handling.

        Args:
            query: GitHub search query
            existing_numbers: PR numbers already processed
            checkpoint_path: Path to checkpoint file
            checkpoint_data: Data to save in checkpoint

        Returns:
            List of PR data
        """
        prs = checkpoint_data.get("prs", []).copy()
        total_processed = len(prs)

        try:
            # Get paginated results
            search_results = self.github_client.search_issues(query=query)

            # Get total count
            total_count = search_results.totalCount
            logger.info(f"Found {total_count} PRs to process")

            # Process pages
            for page_num, pr in enumerate(search_results):
                # Skip if already processed
                if pr.number in existing_numbers:
                    continue

                # Check rate limit periodically
                if page_num % 10 == 0:
                    self.rate_limit_manager.wait_if_needed(
                        resource="search", min_remaining=30
                    )

                # Extract PR data
                pr_data = {
                    "url": pr.html_url,
                    "number": pr.number,
                    "title": pr.title,
                    "author": pr.user.login,
                    "labels": [label.name for label in pr.labels],
                    "created_at": pr.created_at.isoformat(),
                    "merged_at": (
                        pr.pull_request.merged_at.isoformat()
                        if pr.pull_request and pr.pull_request.merged_at
                        else None
                    ),
                }

                prs.append(pr_data)
                total_processed += 1

                # Save checkpoint periodically
                if checkpoint_path and total_processed % 20 == 0:
                    checkpoint_data["prs"] = prs
                    checkpoint_data["last_processed"] = pr.number
                    checkpoint_data["total_processed"] = total_processed
                    self._save_checkpoint(checkpoint_path, checkpoint_data)
                    logger.info(
                        f"Progress: {total_processed}/{total_count} PRs processed"
                    )

                # Apply adaptive delay
                delay = self._calculate_delay(search_results)
                if delay > 0:
                    time.sleep(delay)

        except Exception as e:
            logger.error(f"Error during paginated search: {e}")
            # Save checkpoint on error
            if checkpoint_path:
                checkpoint_data["prs"] = prs
                checkpoint_data["error"] = str(e)
                self._save_checkpoint(checkpoint_path, checkpoint_data)

        return prs

    def _calculate_delay(self, paginated_list: PaginatedList) -> float:
        """Calculate adaptive delay based on rate limit status."""
        rate_info = self.rate_limit_manager.check_rate_limit("search")
        remaining = rate_info.get("remaining", 30)

        if remaining > 20:
            return 0.1  # Minimal delay when we have plenty
        elif remaining > 10:
            return 0.5  # Half second delay
        else:
            return 1.0  # Full second when running low

    def _get_previous_release_date(
        self, repo: Any, current_release_date: datetime
    ) -> datetime:
        """Get the date of the previous release."""
        try:
            releases = list(repo.get_releases())
            releases.sort(key=lambda r: r.created_at, reverse=True)

            for release in releases:
                if release.created_at < current_release_date:
                    return release.created_at

            # No previous release, use repo creation
            return repo.created_at
        except Exception:
            return repo.created_at

    def _get_checkpoint_path(self, checkpoint_file: str | None) -> Path | None:
        """Get checkpoint file path."""
        if not checkpoint_file or not self.checkpoint_dir:
            return None
        return self.checkpoint_dir / checkpoint_file

    def _load_checkpoint(self, checkpoint_path: Path | None) -> dict[str, Any]:
        """Load checkpoint data."""
        if not checkpoint_path or not checkpoint_path.exists():
            return {}

        try:
            with open(checkpoint_path) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return {}

    def _save_checkpoint(self, checkpoint_path: Path, data: dict[str, Any]) -> None:
        """Save checkpoint data."""
        try:
            data["timestamp"] = datetime.now().isoformat()
            with open(checkpoint_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _fetch_specific_prs(self, pr_urls: list[str]) -> list[dict[str, Any]]:
        """Fetch specific PRs by URL."""
        prs = []

        for url in pr_urls:
            try:
                # Check rate limit
                self.rate_limit_manager.wait_if_needed(
                    resource="core", min_remaining=50
                )

                # Extract owner, repo, number from URL
                parts = url.strip("/").split("/")
                if len(parts) >= 7 and parts[-2] == "pull":
                    owner = parts[-4]
                    repo = parts[-3]
                    number = int(parts[-1])

                    pr = self.github_client.get_repo(f"{owner}/{repo}").get_pull(number)

                    pr_data = {
                        "url": url,
                        "number": number,
                        "title": pr.title,
                        "author": pr.user.login,
                        "labels": [label.name for label in pr.labels],
                        "created_at": pr.created_at.isoformat(),
                        "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                    }

                    prs.append(pr_data)

            except Exception as e:
                logger.error(f"Error fetching PR {url}: {e}")

        return prs
