"""
PR Enricher - Adds computed metadata to fetched PRs.
"""

from datetime import datetime
from typing import Any

from github import Github
from github.Repository import Repository
from loguru import logger

from ...logging_config import log_api_call, log_processing_step


class PREnricher:
    """
    Enriches PR data with additional metadata.

    Following the single responsibility principle, this component
    only adds metadata to existing PR data without fetching new PRs.
    """

    def __init__(self, github_token: str) -> None:
        """
        Initialize enricher with GitHub client.

        Args:
            github_token: GitHub API token for authentication
        """
        self.github_client = Github(github_token)
        self._release_cache = {}  # Cache releases per repo
        logger.info("🔧 Initialized PR Enricher")

    def enrich(
        self,
        prs: list[dict[str, Any]],
        add_release_status: bool = True,
        add_time_metrics: bool = True,
        add_repo_context: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Enrich a list of PRs with additional metadata.

        Args:
            prs: List of PR data dictionaries
            add_release_status: Whether to add release information
            add_time_metrics: Whether to add time-based metrics
            add_repo_context: Whether to add repository context

        Returns:
            Enriched list of PR data dictionaries
        """
        if not prs:
            return prs

        log_processing_step(f"Enriching {len(prs)} PRs with metadata")

        # Group PRs by repository for efficient processing
        prs_by_repo = self._group_prs_by_repo(prs)

        enriched_prs = []
        for repo_name, repo_prs in prs_by_repo.items():
            try:
                repo = self.github_client.get_repo(repo_name)

                if add_release_status:
                    repo_prs = self._add_release_status(repo, repo_prs)

                if add_time_metrics:
                    repo_prs = self._add_time_metrics(repo_prs)

                if add_repo_context:
                    repo_prs = self._add_repo_context(repo, repo_prs)

                enriched_prs.extend(repo_prs)

            except Exception as e:
                logger.error(f"Error enriching PRs for {repo_name}: {e}")
                # Return PRs without enrichment if error occurs
                enriched_prs.extend(repo_prs)

        logger.info(f"Successfully enriched {len(enriched_prs)} PRs")
        return enriched_prs

    def add_release_status(
        self, repo_name: str, prs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Add release status information to PRs.

        Args:
            repo_name: Repository name
            prs: List of PR data dictionaries

        Returns:
            PRs with added release status
        """
        try:
            repo = self.github_client.get_repo(repo_name)
            return self._add_release_status(repo, prs)
        except Exception as e:
            logger.error(f"Error adding release status: {e}")
            return prs

    def _add_release_status(
        self, repo: Repository, prs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Add release status information to each PR."""
        try:
            # Get cached releases or fetch them
            repo_name = repo.full_name
            if repo_name not in self._release_cache:
                log_api_call("get_releases", {"repo": repo_name})
                releases = list(repo.get_releases())
                # Sort by date descending
                releases.sort(key=lambda r: r.created_at, reverse=True)
                self._release_cache[repo_name] = releases
            else:
                releases = self._release_cache[repo_name]

            # Add release info to each PR
            for pr in prs:
                pr["is_released"] = False
                pr["release_tag"] = None
                pr["release_date"] = None
                pr["releases_since_merge"] = []

                if pr.get("merged_at"):
                    merge_date = self._parse_date(pr["merged_at"])

                    if merge_date:
                        # Find all releases after this PR was merged
                        releases_after = [
                            r for r in releases if r.created_at > merge_date
                        ]

                        if releases_after:
                            # PR is released - get the first release
                            first_release = releases_after[-1]  # Last in reversed list
                            pr["is_released"] = True
                            pr["release_tag"] = first_release.tag_name
                            pr["release_date"] = first_release.created_at.isoformat()

                            # List all releases that include this PR
                            pr["releases_since_merge"] = [
                                {
                                    "tag": r.tag_name,
                                    "date": r.created_at.isoformat(),
                                    "name": r.name or r.tag_name,
                                }
                                for r in releases_after
                            ]

        except Exception as e:
            logger.warning(f"Could not determine release status: {e}")

        return prs

    def _add_time_metrics(self, prs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Add time-based metrics to PRs."""
        now = datetime.now()

        for pr in prs:
            try:
                # Add age metrics
                if pr.get("created_at"):
                    created_date = self._parse_date(pr["created_at"])
                    if created_date:
                        age_days = (now - created_date).days
                        pr["age_days"] = age_days
                        pr["age_category"] = self._categorize_age(age_days)

                # Add merge time metrics
                if pr.get("merged_at") and pr.get("created_at"):
                    merged_date = self._parse_date(pr["merged_at"])
                    created_date = self._parse_date(pr["created_at"])

                    if merged_date and created_date:
                        merge_time_hours = (
                            merged_date - created_date
                        ).total_seconds() / 3600
                        pr["merge_time_hours"] = round(merge_time_hours, 2)
                        pr["merge_time_category"] = self._categorize_merge_time(
                            merge_time_hours
                        )

                # Add time since release
                if pr.get("release_date") and pr.get("merged_at"):
                    release_date = self._parse_date(pr["release_date"])
                    merged_date = self._parse_date(pr["merged_at"])

                    if release_date and merged_date:
                        time_to_release_days = (release_date - merged_date).days
                        pr["time_to_release_days"] = time_to_release_days

            except Exception as e:
                logger.warning(f"Error adding time metrics to PR: {e}")

        return prs

    def _add_repo_context(
        self, repo: Repository, prs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Add repository context to PRs."""
        try:
            # Get repo metadata once
            repo_data = {
                "repo_full_name": repo.full_name,
                "repo_name": repo.name,
                "repo_owner": repo.owner.login,
                "repo_default_branch": repo.default_branch,
                "repo_language": repo.language,
                "repo_is_fork": repo.fork,
                "repo_stars": repo.stargazers_count,
            }

            # Add to each PR
            for pr in prs:
                pr.update(repo_data)

        except Exception as e:
            logger.warning(f"Could not add repo context: {e}")

        return prs

    def _group_prs_by_repo(
        self, prs: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Group PRs by repository for efficient processing."""
        prs_by_repo = {}

        for pr in prs:
            # Try to extract repo from URL or repository field
            repo_name = pr.get("repository")

            if not repo_name and pr.get("url"):
                # Extract from URL: https://github.com/owner/repo/pull/123
                parts = pr["url"].split("/")
                if len(parts) >= 5 and parts[2] == "github.com":
                    repo_name = f"{parts[3]}/{parts[4]}"

            if repo_name:
                if repo_name not in prs_by_repo:
                    prs_by_repo[repo_name] = []
                prs_by_repo[repo_name].append(pr)
            else:
                logger.warning(
                    f"Could not determine repository for PR: {pr.get('url')}"
                )

        return prs_by_repo

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date string to datetime object."""
        try:
            # Handle ISO format with Z suffix
            if date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"
            return datetime.fromisoformat(date_str)
        except Exception:
            try:
                # Fallback to basic ISO parsing
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except Exception:
                return None

    def _categorize_age(self, days: int) -> str:
        """Categorize PR age."""
        if days <= 1:
            return "fresh"
        elif days <= 7:
            return "recent"
        elif days <= 30:
            return "moderate"
        elif days <= 90:
            return "old"
        else:
            return "ancient"

    def _categorize_merge_time(self, hours: float) -> str:
        """Categorize merge time."""
        if hours <= 4:
            return "rapid"
        elif hours <= 24:
            return "quick"
        elif hours <= 72:
            return "normal"
        elif hours <= 168:  # 1 week
            return "slow"
        else:
            return "delayed"
