"""
Batch PR analysis coordinator.
"""

import time
from typing import Any

from github import Github
from loguru import logger

from ..pr_fetcher import PRFetcher
from .base import BaseCoordinator
from .component_manager import ComponentManager
from .single_pr import SinglePRCoordinator


class BatchCoordinator(BaseCoordinator):
    """
    Coordinates batch analysis of multiple PRs.

    Handles release-based, date-based, and custom batch PR analysis.
    """

    def __init__(
        self,
        github_client: Github,
        github_token: str,
        component_manager: ComponentManager,
        single_pr_coordinator: SinglePRCoordinator,
    ) -> None:
        """
        Initialize batch coordinator.

        Args:
            github_client: Authenticated GitHub client
            github_token: GitHub authentication token
            component_manager: Component registry manager
            single_pr_coordinator: Single PR analysis coordinator
        """
        super().__init__(github_client)
        self.github_token = github_token
        self.component_manager = component_manager
        self.single_pr_coordinator = single_pr_coordinator
        self.pr_fetcher = PRFetcher(github_token)

    def coordinate(
        self,
        pr_urls: list[str],
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze a batch of PRs.

        Args:
            pr_urls: List of PR URLs to analyze
            extract_components: Components to extract
            run_processors: Processors to run

        Returns:
            Batch analysis results
        """
        logger.info(f"📊 Starting batch analysis of {len(pr_urls)} PRs")

        results = {}
        total_start = time.time()

        # Analyze each PR
        for pr_url in pr_urls:
            try:
                logger.info(f"Analyzing: {pr_url}")
                pr_results = self.single_pr_coordinator.coordinate(
                    pr_url, extract_components, run_processors
                )
                results[pr_url] = pr_results

            except Exception as e:
                logger.error(f"Error analyzing {pr_url}: {e}")
                results[pr_url] = {
                    "error": str(e),
                    "success": False,
                }

        # Calculate batch processing time
        total_time = time.time() - total_start

        # Generate batch summary
        batch_summary = self._generate_batch_summary(results)
        batch_summary["total_processing_time"] = total_time

        logger.success(
            f"🏁 Batch analysis complete: {len(results)} PRs in {total_time:.2f}s"
        )

        return {
            "pr_results": results,
            "batch_summary": batch_summary,
        }

    def analyze_release_prs(
        self,
        repo_name: str,
        release_tag: str,
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze all PRs in a specific release.

        Args:
            repo_name: Repository name (owner/name format)
            release_tag: Release tag to analyze
            extract_components: Components to extract
            run_processors: Processors to run

        Returns:
            Release PR analysis results
        """
        logger.info(f"🏷️ Analyzing PRs for release {release_tag} in {repo_name}")

        # Fetch PRs for the release
        prs = self.pr_fetcher.fetch_release_prs(repo_name, release_tag)

        if not prs:
            logger.warning(f"No PRs found for release {release_tag}")
            return {
                "release_tag": release_tag,
                "pr_results": {},
                "batch_summary": {"total_prs": 0},
            }

        # Extract PR URLs
        pr_urls = [pr["url"] for pr in prs if "url" in pr]

        # Run batch analysis
        results = self.coordinate(pr_urls, extract_components, run_processors)

        # Add release metadata
        results["release_tag"] = release_tag
        results["repository"] = repo_name

        return results

    def analyze_unreleased_prs(
        self,
        repo_name: str,
        base_branch: str = "main",
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze PRs merged but not yet released.

        Args:
            repo_name: Repository name (owner/name format)
            base_branch: Base branch to check
            extract_components: Components to extract
            run_processors: Processors to run

        Returns:
            Unreleased PR analysis results
        """
        logger.info(f"📦 Analyzing unreleased PRs in {repo_name}")

        # Fetch unreleased PRs
        prs = self.pr_fetcher.fetch_unreleased_prs(repo_name, base_branch)

        if not prs:
            logger.info("No unreleased PRs found")
            return {
                "base_branch": base_branch,
                "pr_results": {},
                "batch_summary": {"total_prs": 0},
            }

        # Extract PR URLs
        pr_urls = [pr["url"] for pr in prs if "url" in pr]

        # Run batch analysis
        results = self.coordinate(pr_urls, extract_components, run_processors)

        # Add metadata
        results["repository"] = repo_name
        results["base_branch"] = base_branch
        results["status"] = "unreleased"

        return results

    def analyze_prs_between_releases(
        self,
        repo_name: str,
        from_tag: str,
        to_tag: str,
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze PRs between two releases.

        Args:
            repo_name: Repository name (owner/name format)
            from_tag: Starting release tag
            to_tag: Ending release tag
            extract_components: Components to extract
            run_processors: Processors to run

        Returns:
            PR analysis results between releases
        """
        logger.info(f"🔄 Analyzing PRs between {from_tag} and {to_tag} in {repo_name}")

        # Fetch PRs between releases
        prs = self.pr_fetcher.fetch_prs_between_releases(repo_name, from_tag, to_tag)

        if not prs:
            logger.warning(f"No PRs found between {from_tag} and {to_tag}")
            return {
                "from_tag": from_tag,
                "to_tag": to_tag,
                "pr_results": {},
                "batch_summary": {"total_prs": 0},
            }

        # Extract PR URLs
        pr_urls = [pr["url"] for pr in prs if "url" in pr]

        # Run batch analysis
        results = self.coordinate(pr_urls, extract_components, run_processors)

        # Add metadata
        results["repository"] = repo_name
        results["from_tag"] = from_tag
        results["to_tag"] = to_tag

        return results

    def _generate_batch_summary(self, pr_results: dict[str, Any]) -> dict[str, Any]:
        """Generate summary statistics for batch results."""
        summary = {
            "total_prs": len(pr_results),
            "successful_analyses": 0,
            "failed_analyses": 0,
            "by_risk_level": {
                "minimal": 0,
                "low": 0,
                "medium": 0,
                "high": 0,
            },
            "by_title_quality": {
                "poor": 0,
                "fair": 0,
                "good": 0,
                "excellent": 0,
            },
            "by_description_quality": {
                "poor": 0,
                "fair": 0,
                "good": 0,
                "excellent": 0,
            },
            "total_additions": 0,
            "total_deletions": 0,
            "average_files_changed": 0,
        }

        files_changed_list = []

        for _pr_url, pr_result in pr_results.items():
            if pr_result.get("error"):
                summary["failed_analyses"] += 1
                continue

            summary["successful_analyses"] += 1

            # Extract insights from processing results
            if "processing_results" in pr_result:
                for result in pr_result["processing_results"]:
                    if not result.get("success"):
                        continue

                    component = result.get("component")
                    data = result.get("data", {})

                    # Code change statistics
                    if component == "code_changes" and "risk_assessment" in data:
                        risk_level = data["risk_assessment"].get(
                            "risk_level", "minimal"
                        )
                        summary["by_risk_level"][risk_level] += 1

                        # Code statistics
                        if "change_stats" in data:
                            stats = data["change_stats"]
                            summary["total_additions"] += stats.get(
                                "total_additions", 0
                            )
                            summary["total_deletions"] += stats.get(
                                "total_deletions", 0
                            )
                            files_changed_list.append(stats.get("changed_files", 0))

                    # Metadata quality
                    elif component == "metadata":
                        if "title_quality" in data:
                            title_level = data["title_quality"].get(
                                "quality_level", "poor"
                            )
                            summary["by_title_quality"][title_level] += 1

                        if "description_quality" in data:
                            desc_level = data["description_quality"].get(
                                "quality_level", "poor"
                            )
                            summary["by_description_quality"][desc_level] += 1

        # Calculate averages
        if files_changed_list:
            summary["average_files_changed"] = sum(files_changed_list) / len(
                files_changed_list
            )

        return summary


