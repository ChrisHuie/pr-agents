"""
Release-based PR fetcher implementation.
"""

from datetime import datetime
from typing import Any

from github.Repository import Repository
from loguru import logger

from ...logging_config import log_api_call, log_processing_step
from .base import BasePRFetcher


class ReleasePRFetcher(BasePRFetcher):
    """
    Fetches PRs based on release tags and versions.

    Handles:
    - PRs in a specific release
    - PRs between two releases
    - Unreleased PRs since last release
    """

    def fetch(self, **kwargs) -> list[dict[str, Any]]:
        """
        Fetch PRs based on release criteria.

        Supported kwargs:
        - repo_name: Repository name (required)
        - release_tag: Specific release tag
        - from_tag: Starting release tag (with to_tag)
        - to_tag: Ending release tag (with from_tag)
        - unreleased: Boolean flag for unreleased PRs
        - base_branch: Base branch for unreleased PRs (default: "main")

        Returns:
            List of PR data dictionaries
        """
        repo_name = kwargs.get("repo_name")
        if not repo_name:
            raise ValueError("repo_name is required")

        if kwargs.get("release_tag"):
            return self.get_prs_by_release(repo_name, kwargs["release_tag"])
        elif kwargs.get("from_tag") and kwargs.get("to_tag"):
            return self.get_prs_between_releases(
                repo_name, kwargs["from_tag"], kwargs["to_tag"]
            )
        elif kwargs.get("unreleased"):
            base_branch = kwargs.get("base_branch", "main")
            return self.get_unreleased_prs(repo_name, base_branch)
        else:
            raise ValueError(
                "Must specify either release_tag, from_tag/to_tag, or unreleased=True"
            )

    def get_prs_by_release(
        self, repo_name: str, release_tag: str
    ) -> list[dict[str, Any]]:
        """
        Get all PRs included in a specific release.

        Args:
            repo_name: Repository name (e.g., "owner/repo")
            release_tag: Release tag name (e.g., "v1.2.3")

        Returns:
            List of PR data dictionaries
        """
        try:
            log_processing_step(
                f"Fetching PRs for release {release_tag} in {repo_name}"
            )
            repo = self.github_client.get_repo(repo_name)

            # Get the release by tag
            log_api_call("get_release_by_tag", {"repo": repo_name, "tag": release_tag})
            release = repo.get_release(release_tag)
            release_date = release.created_at

            # Get previous release to establish date range
            previous_release_date = self._get_previous_release_date(repo, release_date)

            # Get all merged PRs between previous release and this release
            prs = self._get_merged_prs_between_dates(
                repo, previous_release_date, release_date
            )

            logger.info(
                f"Found {len(prs)} PRs in release {release_tag} for {repo_name}"
            )
            return prs

        except Exception as e:
            logger.error(f"Error fetching PRs for release {release_tag}: {e}")
            raise

    def get_prs_between_releases(
        self, repo_name: str, from_tag: str, to_tag: str
    ) -> list[dict[str, Any]]:
        """
        Get all PRs merged between two release tags.

        Args:
            repo_name: Repository name (e.g., "owner/repo")
            from_tag: Starting release tag (exclusive)
            to_tag: Ending release tag (inclusive)

        Returns:
            List of PR data dictionaries
        """
        try:
            log_processing_step(
                f"Fetching PRs between {from_tag} and {to_tag} in {repo_name}"
            )
            repo = self.github_client.get_repo(repo_name)

            # Get both releases
            log_api_call(
                "get_releases", {"repo": repo_name, "from": from_tag, "to": to_tag}
            )
            from_release = repo.get_release(from_tag)
            to_release = repo.get_release(to_tag)

            # Get merged PRs between the two release dates
            prs = self._get_merged_prs_between_dates(
                repo, from_release.created_at, to_release.created_at
            )

            logger.info(
                f"Found {len(prs)} PRs between {from_tag} and {to_tag} for {repo_name}"
            )
            return prs

        except Exception as e:
            logger.error(f"Error fetching PRs between {from_tag} and {to_tag}: {e}")
            raise

    def get_unreleased_prs(
        self, repo_name: str, base_branch: str = "main"
    ) -> list[dict[str, Any]]:
        """
        Get all merged PRs that haven't been included in a release yet.

        Args:
            repo_name: Repository name (e.g., "owner/repo")
            base_branch: Base branch to check (default: "main")

        Returns:
            List of PR data dictionaries
        """
        try:
            log_processing_step(f"Fetching unreleased PRs from {base_branch}")
            repo = self.github_client.get_repo(repo_name)

            # Get the latest release date
            latest_release_date = self._get_latest_release_date(repo)

            if latest_release_date:
                # Get all merged PRs after the latest release
                log_api_call(
                    "search_issues",
                    {
                        "repo": repo_name,
                        "type": "pr",
                        "state": "closed",
                        "base": base_branch,
                        "merged": ">=" + latest_release_date.isoformat(),
                    },
                )

                # Search for merged PRs after latest release
                query = (
                    f"repo:{repo_name} "
                    f"type:pr "
                    f"is:merged "
                    f"base:{base_branch} "
                    f"merged:>={latest_release_date.isoformat()}"
                )

                prs = []
                for pr in self.github_client.search_issues(query=query):
                    prs.append(self._build_pr_data(pr))
            else:
                # No releases yet, get all merged PRs
                logger.warning(
                    f"No releases found for {repo_name}, fetching all merged PRs"
                )
                prs = self._get_all_merged_prs(repo, base_branch)

            logger.info(f"Found {len(prs)} unreleased PRs in {repo_name}")
            return prs

        except Exception as e:
            logger.error(f"Error fetching unreleased PRs: {e}")
            raise

    def _get_previous_release_date(
        self, repo: Repository, current_release_date: datetime
    ) -> datetime:
        """Get the date of the release before the given date."""
        try:
            releases = list(repo.get_releases())

            # Sort releases by date descending
            releases.sort(key=lambda r: r.created_at, reverse=True)

            # Find the release just before our target date
            for i, release in enumerate(releases):
                if release.created_at < current_release_date and i > 0:
                    return release.created_at

            # If no previous release, use repo creation date
            return repo.created_at

        except Exception:
            # Fallback to repo creation date
            return repo.created_at

    def _get_latest_release_date(self, repo: Repository) -> datetime | None:
        """Get the date of the latest release."""
        try:
            latest_release = repo.get_latest_release()
            return latest_release.created_at
        except Exception:
            # No releases found
            return None

    def _get_merged_prs_between_dates(
        self, repo: Repository, start_date: datetime, end_date: datetime
    ) -> list[dict[str, Any]]:
        """Get all merged PRs between two dates."""
        log_api_call(
            "search_merged_prs",
            {
                "repo": repo.full_name,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        )

        # Use GitHub search API for better performance
        query = (
            f"repo:{repo.full_name} "
            f"type:pr "
            f"is:merged "
            f"merged:{start_date.isoformat()}..{end_date.isoformat()}"
        )

        prs = []
        for pr in self.github_client.search_issues(query=query):
            prs.append(self._build_pr_data(pr))

        return prs

    def _get_all_merged_prs(
        self, repo: Repository, base_branch: str
    ) -> list[dict[str, Any]]:
        """Get all merged PRs for a repository."""
        query = (
            f"repo:{repo.full_name} " f"type:pr " f"is:merged " f"base:{base_branch}"
        )

        log_api_call("search_all_merged_prs", {"repo": repo.full_name})

        prs = []
        for pr in self.github_client.search_issues(query=query):
            prs.append(self._build_pr_data(pr))

        return prs
