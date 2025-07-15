"""
Multi-repository PR fetcher implementation.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from loguru import logger

from ...logging_config import log_processing_step
from .base import BasePRFetcher
from .date_range import DateRangePRFetcher
from .label import LabelPRFetcher
from .release import ReleasePRFetcher


class MultiRepoPRFetcher(BasePRFetcher):
    """
    Coordinates PR fetching across multiple repositories.

    This fetcher delegates to other specialized fetchers but handles
    multi-repo coordination, parallelization, and result aggregation.
    """

    def __init__(self, github_token: str) -> None:
        """Initialize with specialized fetchers."""
        super().__init__(github_token)

        # Initialize specialized fetchers
        self.release_fetcher = ReleasePRFetcher(github_token)
        self.date_fetcher = DateRangePRFetcher(github_token)
        self.label_fetcher = LabelPRFetcher(github_token)

    def fetch(self, **kwargs) -> list[dict[str, Any]]:
        """
        Fetch PRs from multiple repositories.

        Supported kwargs:
        - repo_names: List of repository names (required)
        - fetch_type: Type of fetch operation (date, release, label)
        - grouped: Return results grouped by repo (default: False)
        - parallel: Fetch from repos in parallel (default: True)
        - max_workers: Max parallel workers (default: 5)
        - Plus all kwargs supported by the specific fetcher type

        Returns:
            List of PR data dictionaries (or dict if grouped=True)
        """
        repo_names = kwargs.get("repo_names")
        if not repo_names:
            raise ValueError("repo_names is required")

        fetch_type = kwargs.get("fetch_type", "date")
        grouped = kwargs.get("grouped", False)
        parallel = kwargs.get("parallel", True)
        max_workers = kwargs.get("max_workers", 5)

        # Determine which fetcher to use
        fetcher = self._get_fetcher_for_type(fetch_type)

        if parallel and len(repo_names) > 1:
            results = self._fetch_parallel(repo_names, fetcher, kwargs, max_workers)
        else:
            results = self._fetch_sequential(repo_names, fetcher, kwargs)

        if grouped:
            return results
        else:
            # Flatten results into a single list
            all_prs = []
            for repo_prs in results.values():
                if isinstance(repo_prs, list):
                    all_prs.extend(repo_prs)
            return all_prs

    def get_multi_repo_summary(
        self, repo_names: list[str], fetch_type: str = "date", **kwargs
    ) -> dict[str, Any]:
        """
        Get a summary of PRs across multiple repositories.

        Args:
            repo_names: List of repository names
            fetch_type: Type of fetch operation
            **kwargs: Arguments for the specific fetcher

        Returns:
            Summary statistics across all repositories
        """
        log_processing_step(
            f"Generating multi-repo summary for {len(repo_names)} repos"
        )

        # Fetch PRs grouped by repo
        kwargs["repo_names"] = repo_names
        kwargs["fetch_type"] = fetch_type
        kwargs["grouped"] = True

        repo_results = self.fetch(**kwargs)

        # Generate summary
        summary = {
            "total_repos": len(repo_names),
            "total_prs": 0,
            "successful_repos": 0,
            "failed_repos": 0,
            "by_repository": {},
            "aggregated_stats": {
                "authors": set(),
                "labels": {},
                "pr_states": {},
            },
        }

        for repo_name, prs in repo_results.items():
            if isinstance(prs, list):
                summary["successful_repos"] += 1
                summary["total_prs"] += len(prs)

                # Repository-specific summary
                repo_summary = {
                    "pr_count": len(prs),
                    "authors": list({pr["author"] for pr in prs}),
                    "unique_labels": list(
                        {label for pr in prs for label in pr.get("labels", [])}
                    ),
                }
                summary["by_repository"][repo_name] = repo_summary

                # Update aggregated stats
                for pr in prs:
                    summary["aggregated_stats"]["authors"].add(pr["author"])

                    for label in pr.get("labels", []):
                        summary["aggregated_stats"]["labels"][label] = (
                            summary["aggregated_stats"]["labels"].get(label, 0) + 1
                        )

                    state = pr.get("state", "unknown")
                    summary["aggregated_stats"]["pr_states"][state] = (
                        summary["aggregated_stats"]["pr_states"].get(state, 0) + 1
                    )
            else:
                # Error case
                summary["failed_repos"] += 1
                summary["by_repository"][repo_name] = {"error": str(prs)}

        # Convert sets to lists for JSON serialization
        summary["aggregated_stats"]["authors"] = list(
            summary["aggregated_stats"]["authors"]
        )

        logger.info(
            f"Multi-repo summary: {summary['total_prs']} PRs from "
            f"{summary['successful_repos']}/{summary['total_repos']} repos"
        )

        return summary

    def _get_fetcher_for_type(self, fetch_type: str) -> BasePRFetcher:
        """Get the appropriate fetcher for the given type."""
        fetchers = {
            "date": self.date_fetcher,
            "release": self.release_fetcher,
            "label": self.label_fetcher,
        }

        if fetch_type not in fetchers:
            raise ValueError(f"Invalid fetch_type: {fetch_type}")

        return fetchers[fetch_type]

    def _fetch_sequential(
        self, repo_names: list[str], fetcher: BasePRFetcher, kwargs: dict[str, Any]
    ) -> dict[str, list[dict[str, Any]] | str]:
        """Fetch PRs sequentially from multiple repositories."""
        results = {}

        for repo_name in repo_names:
            try:
                # Create repo-specific kwargs
                repo_kwargs = kwargs.copy()
                repo_kwargs["repo_name"] = repo_name
                # Remove multi-repo specific kwargs
                for key in [
                    "repo_names",
                    "fetch_type",
                    "grouped",
                    "parallel",
                    "max_workers",
                ]:
                    repo_kwargs.pop(key, None)

                prs = fetcher.fetch(**repo_kwargs)
                results[repo_name] = prs

            except Exception as e:
                logger.error(f"Failed to fetch PRs for {repo_name}: {e}")
                results[repo_name] = str(e)

        return results

    def _fetch_parallel(
        self,
        repo_names: list[str],
        fetcher: BasePRFetcher,
        kwargs: dict[str, Any],
        max_workers: int,
    ) -> dict[str, list[dict[str, Any]] | str]:
        """Fetch PRs in parallel from multiple repositories."""
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all fetch tasks
            future_to_repo = {}

            for repo_name in repo_names:
                # Create repo-specific kwargs
                repo_kwargs = kwargs.copy()
                repo_kwargs["repo_name"] = repo_name
                # Remove multi-repo specific kwargs
                for key in [
                    "repo_names",
                    "fetch_type",
                    "grouped",
                    "parallel",
                    "max_workers",
                ]:
                    repo_kwargs.pop(key, None)

                future = executor.submit(fetcher.fetch, **repo_kwargs)
                future_to_repo[future] = repo_name

            # Collect results as they complete
            for future in as_completed(future_to_repo):
                repo_name = future_to_repo[future]
                try:
                    prs = future.result()
                    results[repo_name] = prs
                except Exception as e:
                    logger.error(f"Failed to fetch PRs for {repo_name}: {e}")
                    results[repo_name] = str(e)

        return results
