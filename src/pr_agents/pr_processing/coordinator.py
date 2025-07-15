"""
PR Processing Coordinator - orchestrates extraction and processing with strict boundaries.

This is the main facade that delegates to specialized sub-coordinators.
"""

from pathlib import Path
from typing import Any

from github import Github
from loguru import logger

from ..logging_config import log_processing_step
from ..output import OutputManager
from .analysis import ResultFormatter, SummaryBuilder
from .coordinators import BatchCoordinator, ComponentManager, SinglePRCoordinator
from .pr_fetcher import PRFetcher


class PRCoordinator:
    """
    Main coordinator facade for PR processing.

    Delegates to specialized sub-coordinators while maintaining backward compatibility.
    """

    def __init__(self, github_token: str) -> None:
        """
        Initialize PR Coordinator with sub-coordinators.

        Args:
            github_token: GitHub authentication token
        """
        logger.info("🔧 Initializing PR Coordinator")
        self.github_client = Github(github_token)
        self.github_token = github_token
        log_processing_step("GitHub client initialized")

        # Initialize component manager
        self.component_manager = ComponentManager(self.github_client)
        log_processing_step("Component manager initialized")

        # Initialize sub-coordinators
        self.single_pr_coordinator = SinglePRCoordinator(
            self.github_client, self.component_manager
        )
        self.batch_coordinator = BatchCoordinator(
            self.github_client,
            github_token,
            self.component_manager,
            self.single_pr_coordinator,
        )
        log_processing_step("Sub-coordinators initialized")

        # Initialize output manager
        self.output_manager = OutputManager()
        log_processing_step("Output Manager initialized")

        # Initialize legacy PR fetcher for backward compatibility
        self.pr_fetcher = PRFetcher(github_token)
        log_processing_step("PR Fetcher initialized")

    # ===================
    # Single PR Analysis
    # ===================

    def extract_pr_components(
        self, pr_url: str, components: set[str] | None = None
    ) -> Any:
        """
        Extract specified components from a PR.

        Args:
            pr_url: GitHub PR URL
            components: Components to extract (None for all)

        Returns:
            PRData with extracted components
        """
        return self.single_pr_coordinator.extract_pr_components(pr_url, components)

    def process_components(
        self, pr_data: Any, processors: list[str] | None = None
    ) -> list[Any]:
        """
        Process extracted components.

        Args:
            pr_data: Extracted PR data
            processors: List of processors to run (None for all)

        Returns:
            List of processing results
        """
        return self.single_pr_coordinator.process_components(pr_data, processors)

    def analyze_pr(
        self,
        pr_url: str,
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Complete PR analysis pipeline with component isolation.

        Args:
            pr_url: GitHub PR URL
            extract_components: Components to extract
            run_processors: Processors to run

        Returns:
            Dictionary with extracted data and processing results
        """
        # Bind PR URL context for the entire analysis pipeline
        bound_logger = logger.bind(pr_url=pr_url)
        bound_logger.info("🔬 Starting complete PR analysis")

        results = self.single_pr_coordinator.coordinate(
            pr_url, extract_components, run_processors
        )

        bound_logger.success("🏁 PR analysis pipeline complete")
        return results

    # ===================
    # Output Integration
    # ===================

    def analyze_pr_and_save(
        self,
        pr_url: str,
        output_path: str | Path,
        output_format: str = "markdown",
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
    ) -> tuple[dict[str, Any], Path]:
        """
        Analyze PR and save results to file.

        Args:
            pr_url: GitHub PR URL
            output_path: Path to save the output file
            output_format: Output format (markdown, json, text)
            extract_components: Components to extract
            run_processors: Processors to run

        Returns:
            Tuple of (analysis results, saved file path)
        """
        # Run analysis
        results = self.analyze_pr(pr_url, extract_components, run_processors)

        # Format results for output
        formatted_results = ResultFormatter.format_for_output(results)

        # Save to file
        saved_path = self.output_manager.save(
            formatted_results, output_path, output_format
        )

        return results, saved_path

    # ===================
    # Batch Operations
    # ===================

    def analyze_prs_batch(
        self,
        pr_urls: list[str],
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze multiple PRs in batch.

        Args:
            pr_urls: List of PR URLs to analyze
            extract_components: Components to extract
            run_processors: Processors to run

        Returns:
            Batch analysis results
        """
        return self.batch_coordinator.coordinate(
            pr_urls, extract_components, run_processors
        )

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
        return self.batch_coordinator.analyze_release_prs(
            repo_name, release_tag, extract_components, run_processors
        )

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
        return self.batch_coordinator.analyze_unreleased_prs(
            repo_name, base_branch, extract_components, run_processors
        )

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
        return self.batch_coordinator.analyze_prs_between_releases(
            repo_name, from_tag, to_tag, extract_components, run_processors
        )

    # ===================
    # Internal Helpers
    # ===================

    def _get_pr_from_url(self, pr_url: str) -> Any:
        """
        Extract PR from GitHub URL.

        Delegates to SinglePRCoordinator for consistency.
        """
        return self.single_pr_coordinator._get_pr_from_url(pr_url)

    def _get_component_data(self, pr_data: Any, component_name: str) -> Any:
        """
        Get component data for processing.

        Delegates to ComponentManager.
        """
        return self.component_manager.get_component_data(pr_data, component_name)

    def _generate_summary(
        self, pr_data: Any, processing_results: list[Any]
    ) -> dict[str, Any]:
        """
        Generate high-level summary of PR analysis.

        Delegates to SummaryBuilder.
        """
        return SummaryBuilder.build_single_pr_summary(pr_data, processing_results)

    def _generate_batch_summary(self, pr_results: dict[str, Any]) -> dict[str, Any]:
        """
        Generate summary for batch results.

        Delegates to SummaryBuilder.
        """
        return SummaryBuilder.build_batch_summary(pr_results)

    def _format_results_for_output(self, results: dict[str, Any]) -> dict[str, Any]:
        """
        Format results for output.

        Delegates to ResultFormatter.
        """
        return ResultFormatter.format_for_output(results)

    # These methods provide backward compatibility
    def _parse_pr_url(self, pr_url: str) -> dict[str, Any]:
        """Parse PR URL (backward compatibility)."""
        return ResultFormatter._parse_pr_url(pr_url)

    def _format_metadata_output(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format metadata output (backward compatibility)."""
        return ResultFormatter._format_metadata(data)

    def _format_code_output(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format code output (backward compatibility)."""
        return ResultFormatter._format_code_changes(data)

    def _format_repo_output(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format repo output (backward compatibility)."""
        return ResultFormatter._format_repository(data)

    def _format_reviews_output(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format reviews output (backward compatibility)."""
        return ResultFormatter._format_reviews(data)

    def _format_processing_metrics(self, results: dict[str, Any]) -> dict[str, Any]:
        """Format processing metrics (backward compatibility)."""
        return ResultFormatter._format_metrics(results)
