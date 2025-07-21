"""
Batch PR analysis coordinator.
"""

import time
from typing import Any

from github import Github
from loguru import logger

from ...utilities.rate_limit_manager import RateLimitManager
from ..fetchers.paginated import PaginatedPRFetcher
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

        # Initialize paginated fetcher for large batches
        self.paginated_fetcher = PaginatedPRFetcher(
            github_token,
            per_page=50,
            checkpoint_dir=".pr_agents_checkpoints",
        )

        # Initialize rate limit manager
        self.rate_limit_manager = RateLimitManager()
        self.rate_limit_manager.set_github_client(github_client)

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

        # Check if AI summaries are requested and all PRs are from same repo
        has_ai_processor = run_processors and "ai_summaries" in run_processors
        repo_url = None
        same_repo = True

        if has_ai_processor and pr_urls:
            # Extract repository URL from first PR
            first_pr = pr_urls[0]
            if "github.com" in first_pr:
                parts = first_pr.split("/")
                if len(parts) >= 5:
                    repo_url = f"https://github.com/{parts[3]}/{parts[4]}"

            # Check if all PRs are from same repo
            for pr_url in pr_urls[1:]:
                if repo_url and repo_url not in pr_url:
                    same_repo = False
                    break

        # Start batch context if applicable
        if has_ai_processor and same_repo and repo_url:
            logger.info(f"Detected batch from same repository: {repo_url}")
            # Notify AI processor about batch start
            ai_processor = self.component_manager.get_processor("ai_summaries")
            if hasattr(ai_processor, "ai_service") and hasattr(
                ai_processor.ai_service, "start_batch"
            ):
                ai_processor.ai_service.start_batch(repo_url)
                logger.info("Started batch context for AI processing")

        # Analyze each PR
        for i, pr_url in enumerate(pr_urls):
            try:
                # Check rate limit before each PR
                self.rate_limit_manager.wait_if_needed(
                    resource="core", min_remaining=50
                )

                logger.info(f"Analyzing ({i+1}/{len(pr_urls)}): {pr_url}")
                pr_results = self.single_pr_coordinator.coordinate(
                    pr_url, extract_components, run_processors
                )
                results[pr_url] = pr_results

                # Track the request
                self.rate_limit_manager.track_request("core")

                # Apply adaptive delay between PRs
                if i < len(pr_urls) - 1 and (i + 1) % 10 == 0:
                    delay = 2.0  # Pause between every 10 PRs
                    logger.debug(f"Pausing {delay}s between batches")
                    time.sleep(delay)

            except Exception as e:
                logger.error(f"Error analyzing {pr_url}: {e}")
                results[pr_url] = {
                    "error": str(e),
                    "success": False,
                }

        # End batch context if it was started
        if has_ai_processor and same_repo and repo_url:
            ai_processor = self.component_manager.get_processor("ai_summaries")
            if hasattr(ai_processor, "ai_service") and hasattr(
                ai_processor.ai_service, "end_batch"
            ):
                ai_processor.ai_service.end_batch()
                logger.info("Ended batch context for AI processing")

        # Calculate batch processing time
        total_time = time.time() - total_start

        # Generate batch statistics
        batch_stats = self._generate_batch_stats(results)
        batch_stats["total_processing_time"] = total_time

        logger.success(
            f"🏁 Batch analysis complete: {len(results)} PRs in {total_time:.2f}s"
        )

        return {
            "pr_results": results,
            "batch_summary": batch_stats,
        }

    def analyze_release_prs(
        self,
        repo_name: str,
        release_tag: str,
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze all PRs in a specific release with AI summaries.

        Args:
            repo_name: Repository name (owner/name format)
            release_tag: Release tag to analyze
            extract_components: Components to extract
            run_processors: Processors to run

        Returns:
            Release PR analysis results
        """
        logger.info(f"🏷️ Analyzing PRs for release {release_tag} in {repo_name}")

        # Use paginated fetcher for proper GitHub API handling
        checkpoint_file = f"{repo_name.replace('/', '_')}_{release_tag}.json"

        # Fetch PRs with pagination
        prs = self.paginated_fetcher.fetch_release_prs(
            repo_name,
            release_tag,
            checkpoint_file,
        )

        if not prs:
            logger.warning(f"No PRs found for release {release_tag}")
            return {
                "release_tag": release_tag,
                "repository": repo_name,
                "pr_results": {},
                "batch_summary": {"total_prs": 0},
            }

        logger.info(f"Found {len(prs)} PRs in release {release_tag}")

        # Extract PR URLs
        pr_urls = [pr["url"] for pr in prs if "url" in pr]

        # Process in batches to avoid timeout
        batch_size = 15  # Smaller batches for AI processing
        all_results = {}

        for i in range(0, len(pr_urls), batch_size):
            batch_urls = pr_urls[i : i + batch_size]
            logger.info(
                f"Processing batch {i//batch_size + 1}/{(len(pr_urls) + batch_size - 1) // batch_size}"
            )

            # Analyze batch
            batch_results = self.coordinate(
                batch_urls, extract_components, run_processors
            )
            all_results.update(batch_results.get("pr_results", {}))

            # Brief pause between batches
            if i + batch_size < len(pr_urls):
                time.sleep(3)

        # Simple summary
        batch_summary = {
            "total_prs": len(all_results),
            "successful_analyses": sum(
                1 for r in all_results.values() if not r.get("error")
            ),
            "failed_analyses": sum(1 for r in all_results.values() if r.get("error")),
        }

        return {
            "release_tag": release_tag,
            "repository": repo_name,
            "pr_results": all_results,
            "batch_summary": batch_summary,
        }

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
        prs = self.pr_fetcher.get_unreleased_prs(repo_name, base_branch)

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
        prs = self.pr_fetcher.get_prs_between_releases(repo_name, from_tag, to_tag)

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

    def _generate_batch_stats(self, pr_results: dict[str, Any]) -> dict[str, Any]:
        """Generate statistics for batch results."""
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
