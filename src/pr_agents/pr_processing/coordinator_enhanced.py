"""
Enhanced PR Processing Coordinator - integrates modular fetchers and enrichers.
"""

from datetime import datetime
from typing import Any

from loguru import logger

from ..logging_config import log_processing_step
from .coordinator import PRCoordinator
from .enrichers import PREnricher
from .fetchers import (
    DateRangePRFetcher,
    LabelPRFetcher,
    MultiRepoPRFetcher,
    ReleasePRFetcher,
)


class EnhancedPRCoordinator(PRCoordinator):
    """
    Enhanced coordinator with modular fetching and enrichment capabilities.

    Extends the base coordinator to support:
    - Date-based PR fetching
    - Multi-repository analysis
    - PR enrichment with release status
    - Advanced filtering and aggregation
    """

    def __init__(self, github_token: str) -> None:
        """Initialize enhanced coordinator with additional components."""
        super().__init__(github_token)

        # Initialize modular fetchers
        self.release_fetcher = ReleasePRFetcher(github_token)
        self.date_fetcher = DateRangePRFetcher(github_token)
        self.label_fetcher = LabelPRFetcher(github_token)
        self.multi_repo_fetcher = MultiRepoPRFetcher(github_token)

        # Initialize enricher
        self.enricher = PREnricher(github_token)

        logger.info("🚀 Enhanced PR Coordinator initialized with modular fetchers")

    def fetch_and_analyze_by_date(
        self,
        repo_name: str,
        start_date: datetime,
        end_date: datetime | None = None,
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
        enrich: bool = True,
    ) -> dict[str, Any]:
        """
        Fetch and analyze PRs within a date range.

        Args:
            repo_name: Repository name
            start_date: Start date for PR search
            end_date: End date (optional, defaults to now)
            extract_components: Components to extract for each PR
            run_processors: Processors to run on each PR
            enrich: Whether to enrich PRs with metadata

        Returns:
            Analysis results with enriched PR data
        """
        log_processing_step(f"Fetching PRs by date range for {repo_name}")

        # Fetch PRs
        prs = self.date_fetcher.fetch(
            repo_name=repo_name,
            start_date=start_date,
            end_date=end_date,
            state="merged",
        )

        # Enrich if requested
        if enrich:
            prs = self.enricher.enrich(prs)

        # Analyze each PR
        results = {
            "repository": repo_name,
            "date_range": {
                "start": start_date.isoformat(),
                "end": (end_date or datetime.now()).isoformat(),
            },
            "total_prs": len(prs),
            "prs": prs,
            "analysis": {},
        }

        # Run analysis on each PR if components specified
        if extract_components or run_processors:
            analyzed_prs = []
            for pr in prs:
                try:
                    pr_analysis = self.analyze_pr(
                        pr["url"], extract_components, run_processors
                    )
                    # Merge enriched data with analysis
                    pr_analysis["enriched_data"] = pr
                    analyzed_prs.append(pr_analysis)
                except Exception as e:
                    logger.error(f"Failed to analyze PR {pr['url']}: {e}")
                    analyzed_prs.append({"url": pr["url"], "error": str(e)})

            results["analysis"] = analyzed_prs

        return results

    def fetch_and_analyze_multi_repo(
        self,
        repo_names: list[str],
        fetch_type: str = "date",
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
        enrich: bool = True,
        **fetch_kwargs,
    ) -> dict[str, Any]:
        """
        Fetch and analyze PRs from multiple repositories.

        Args:
            repo_names: List of repository names
            fetch_type: Type of fetch (date, release, label)
            extract_components: Components to extract
            run_processors: Processors to run
            enrich: Whether to enrich PRs
            **fetch_kwargs: Additional arguments for fetcher

        Returns:
            Multi-repo analysis results
        """
        log_processing_step(f"Fetching PRs from {len(repo_names)} repositories")

        # Use multi-repo fetcher
        fetch_kwargs["repo_names"] = repo_names
        fetch_kwargs["fetch_type"] = fetch_type
        fetch_kwargs["grouped"] = True

        repo_results = self.multi_repo_fetcher.fetch(**fetch_kwargs)

        # Process results for each repo
        final_results = {
            "total_repos": len(repo_names),
            "fetch_type": fetch_type,
            "by_repository": {},
            "aggregated_stats": {
                "total_prs": 0,
                "released_prs": 0,
                "unreleased_prs": 0,
            },
        }

        for repo_name, prs in repo_results.items():
            if isinstance(prs, list):
                # Enrich if requested
                if enrich:
                    prs = self.enricher.enrich(prs)

                # Calculate stats
                released = len([pr for pr in prs if pr.get("is_released", False)])
                unreleased = len(prs) - released

                repo_result = {
                    "pr_count": len(prs),
                    "released": released,
                    "unreleased": unreleased,
                    "prs": prs,
                }

                # Run analysis if requested
                if extract_components or run_processors:
                    analyzed_prs = []
                    for pr in prs[:5]:  # Limit to 5 PRs per repo to avoid overload
                        try:
                            pr_analysis = self.analyze_pr(
                                pr["url"], extract_components, run_processors
                            )
                            analyzed_prs.append(pr_analysis)
                        except Exception as e:
                            logger.error(f"Failed to analyze PR {pr['url']}: {e}")

                    repo_result["sample_analysis"] = analyzed_prs

                final_results["by_repository"][repo_name] = repo_result
                final_results["aggregated_stats"]["total_prs"] += len(prs)
                final_results["aggregated_stats"]["released_prs"] += released
                final_results["aggregated_stats"]["unreleased_prs"] += unreleased
            else:
                # Error case
                final_results["by_repository"][repo_name] = {"error": str(prs)}

        return final_results

    def get_release_comparison(
        self,
        repo_name: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Compare released vs unreleased PRs over a time period.

        Args:
            repo_name: Repository name
            days: Number of days to analyze

        Returns:
            Comparison of released vs unreleased PRs
        """
        log_processing_step(f"Generating release comparison for {repo_name}")

        # Fetch PRs from last N days
        prs = self.date_fetcher.fetch(
            repo_name=repo_name, last_n_days=days, state="merged"
        )

        # Enrich with release status
        enriched_prs = self.enricher.enrich(prs, add_release_status=True)

        # Categorize PRs
        released_prs = []
        unreleased_prs = []

        for pr in enriched_prs:
            if pr.get("is_released", False):
                released_prs.append(pr)
            else:
                unreleased_prs.append(pr)

        # Generate comparison
        comparison = {
            "repository": repo_name,
            "time_period_days": days,
            "total_prs": len(enriched_prs),
            "released": {
                "count": len(released_prs),
                "percentage": (
                    round(len(released_prs) / len(enriched_prs) * 100, 2)
                    if enriched_prs
                    else 0
                ),
                "prs": released_prs,
            },
            "unreleased": {
                "count": len(unreleased_prs),
                "percentage": (
                    round(len(unreleased_prs) / len(enriched_prs) * 100, 2)
                    if enriched_prs
                    else 0
                ),
                "prs": unreleased_prs,
            },
        }

        # Add release timeline
        if released_prs:
            releases = {}
            for pr in released_prs:
                tag = pr.get("release_tag")
                if tag:
                    if tag not in releases:
                        releases[tag] = {
                            "tag": tag,
                            "date": pr.get("release_date"),
                            "pr_count": 0,
                            "prs": [],
                        }
                    releases[tag]["pr_count"] += 1
                    releases[tag]["prs"].append(
                        {
                            "url": pr["url"],
                            "title": pr["title"],
                            "merged_at": pr["merged_at"],
                        }
                    )

            comparison["releases"] = list(releases.values())

        return comparison

    def analyze_pr_velocity(
        self,
        repo_names: list[str],
        days: int = 90,
    ) -> dict[str, Any]:
        """
        Analyze PR velocity metrics across repositories.

        Args:
            repo_names: List of repository names
            days: Number of days to analyze

        Returns:
            Velocity metrics and trends
        """
        log_processing_step(f"Analyzing PR velocity for {len(repo_names)} repos")

        # Fetch PRs from all repos
        all_prs = self.multi_repo_fetcher.fetch(
            repo_names=repo_names,
            fetch_type="date",
            last_n_days=days,
            grouped=False,
        )

        # Enrich with time metrics
        enriched_prs = self.enricher.enrich(
            all_prs, add_time_metrics=True, add_release_status=True
        )

        # Calculate velocity metrics
        velocity = {
            "time_period_days": days,
            "total_prs": len(enriched_prs),
            "average_prs_per_day": round(len(enriched_prs) / days, 2),
            "merge_time_stats": self._calculate_merge_time_stats(enriched_prs),
            "release_velocity": self._calculate_release_velocity(enriched_prs),
            "by_repository": {},
        }

        # Break down by repository
        for repo_name in repo_names:
            repo_prs = [pr for pr in enriched_prs if pr.get("repository") == repo_name]
            if repo_prs:
                velocity["by_repository"][repo_name] = {
                    "pr_count": len(repo_prs),
                    "average_prs_per_day": round(len(repo_prs) / days, 2),
                    "merge_time_stats": self._calculate_merge_time_stats(repo_prs),
                }

        return velocity

    def _calculate_merge_time_stats(self, prs: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate merge time statistics."""
        merge_times = [
            pr["merge_time_hours"]
            for pr in prs
            if pr.get("merge_time_hours") is not None
        ]

        if not merge_times:
            return {}

        merge_times.sort()

        return {
            "average_hours": round(sum(merge_times) / len(merge_times), 2),
            "median_hours": round(merge_times[len(merge_times) // 2], 2),
            "min_hours": round(min(merge_times), 2),
            "max_hours": round(max(merge_times), 2),
            "categories": {
                "rapid": len([t for t in merge_times if t <= 4]),
                "quick": len([t for t in merge_times if 4 < t <= 24]),
                "normal": len([t for t in merge_times if 24 < t <= 72]),
                "slow": len([t for t in merge_times if 72 < t <= 168]),
                "delayed": len([t for t in merge_times if t > 168]),
            },
        }

    def _calculate_release_velocity(self, prs: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate release velocity metrics."""
        released_prs = [pr for pr in prs if pr.get("is_released", False)]

        if not released_prs:
            return {"released_percentage": 0}

        time_to_release = [
            pr["time_to_release_days"]
            for pr in released_prs
            if pr.get("time_to_release_days") is not None
        ]

        if not time_to_release:
            return {"released_percentage": round(len(released_prs) / len(prs) * 100, 2)}

        time_to_release.sort()

        return {
            "released_percentage": round(len(released_prs) / len(prs) * 100, 2),
            "average_days_to_release": round(
                sum(time_to_release) / len(time_to_release), 2
            ),
            "median_days_to_release": time_to_release[len(time_to_release) // 2],
            "min_days_to_release": min(time_to_release),
            "max_days_to_release": max(time_to_release),
        }
