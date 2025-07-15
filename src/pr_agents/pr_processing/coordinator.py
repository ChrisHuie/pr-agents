"""
PR Processing Coordinator - orchestrates extraction and processing with strict boundaries.
"""

import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from github import Github
from github.PullRequest import PullRequest
from loguru import logger

from ..logging_config import (
    log_data_flow,
    log_processing_step,
)
from ..output import OutputManager
from .extractors import (
    BaseExtractor,
    CodeChangesExtractor,
    MetadataExtractor,
    RepositoryExtractor,
    ReviewsExtractor,
)
from .models import PRData, ProcessingResult
from .pr_fetcher import PRFetcher
from .processors import BaseProcessor, CodeProcessor, MetadataProcessor, RepoProcessor


class PRCoordinator:
    """
    Coordinates PR processing with strict component isolation.

    Ensures no context bleeding between different PR components
    (metadata, code changes, repository info, reviews).
    """

    def __init__(self, github_token: str) -> None:
        logger.info("🔧 Initializing PR Coordinator")
        self.github_client = Github(github_token)
        self.github_token = github_token
        log_processing_step("GitHub client initialized")

        # Initialize PR fetcher
        self.pr_fetcher = PRFetcher(github_token)
        log_processing_step("PR Fetcher initialized")

        # Initialize output manager
        self.output_manager = OutputManager()
        log_processing_step("Output Manager initialized")

        # Initialize extractors
        self._extractors: dict[str, BaseExtractor] = {
            "metadata": MetadataExtractor(self.github_client),
            "code_changes": CodeChangesExtractor(self.github_client),
            "repository": RepositoryExtractor(self.github_client),
            "reviews": ReviewsExtractor(self.github_client),
        }
        log_processing_step(
            "Extractors initialized", f"Available: {list(self._extractors.keys())}"
        )

        # Initialize processors
        self._processors: dict[str, BaseProcessor] = {
            "metadata": MetadataProcessor(),
            "code_changes": CodeProcessor(),
            "repository": RepoProcessor(),
        }
        log_processing_step(
            "Processors initialized", f"Available: {list(self._processors.keys())}"
        )
        logger.success("✅ PR Coordinator ready")

    def extract_pr_components(
        self, pr_url: str, components: set[str] | None = None
    ) -> PRData:
        """
        Extract PR components with strict isolation.

        Args:
            pr_url: GitHub PR URL
            components: Set of components to extract. If None, extracts all.
                       Valid: {'metadata', 'code_changes', 'repository', 'reviews'}

        Returns:
            PRData with requested components populated
        """
        # Bind PR URL to logger context for all operations in this scope
        bound_logger = logger.bind(pr_url=pr_url)
        bound_logger.info("📥 Starting component extraction")

        if components is None:
            components = {"metadata", "code_changes", "repository", "reviews"}

        log_data_flow("Requested components", components, "extraction input")

        # Validate components
        valid_components = set(self._extractors.keys())
        invalid_components = components - valid_components
        if invalid_components:
            error_msg = f"Invalid components: {invalid_components}"
            bound_logger.error(f"💥 {error_msg}")
            raise ValueError(error_msg)

        # Parse PR URL and get PR object
        log_processing_step("Parsing PR URL")
        pr = self._get_pr_from_url(pr_url)
        if not pr:
            error_msg = f"Could not retrieve PR from URL: {pr_url}"
            bound_logger.error(f"💥 {error_msg}")
            raise ValueError(error_msg)

        bound_logger.info(f"✅ Retrieved PR #{pr.number}: {pr.title}")

        # Extract components in isolation
        pr_data = PRData()
        extracted_count = 0

        if "metadata" in components:
            log_processing_step("Extracting metadata")
            metadata_data = self._extractors["metadata"].extract(pr)
            if metadata_data:
                pr_data.metadata = metadata_data
                extracted_count += 1
                log_data_flow(
                    "Metadata extracted", f"{len(metadata_data)} fields", "metadata"
                )

        if "code_changes" in components:
            log_processing_step("Extracting code changes")
            code_data = self._extractors["code_changes"].extract(pr)
            if code_data:
                pr_data.code_changes = code_data
                extracted_count += 1
                log_data_flow(
                    "Code changes extracted",
                    f"{code_data.get('changed_files', 0)} files",
                    "code_changes",
                )

        if "repository" in components:
            log_processing_step("Extracting repository info")
            repo_data = self._extractors["repository"].extract(pr)
            if repo_data:
                pr_data.repository_info = repo_data
                extracted_count += 1
                log_data_flow(
                    "Repository info extracted",
                    repo_data.get("name", "unknown"),
                    "repository",
                )

        if "reviews" in components:
            log_processing_step("Extracting reviews")
            review_data = self._extractors["reviews"].extract(pr)
            if review_data:
                pr_data.review_data = review_data
                extracted_count += 1
                log_data_flow(
                    "Reviews extracted",
                    f"{len(review_data.get('reviews', []))} reviews",
                    "reviews",
                )

        bound_logger.success(
            f"🎯 Extraction complete: {extracted_count}/{len(components)} components"
        )
        return pr_data

    def process_components(
        self, pr_data: PRData, processors: list[str] | None = None
    ) -> list[ProcessingResult]:
        """
        Process extracted components in isolation.

        Args:
            pr_data: PRData with extracted components
            processors: List of processors to run. If None, runs all available.
                       Valid: ['metadata', 'code_changes', 'repository']

        Returns:
            List of ProcessingResult objects
        """
        if processors is None:
            processors = list(self._processors.keys())

        # Validate processors
        valid_processors = set(self._processors.keys())
        invalid_processors = set(processors) - valid_processors
        if invalid_processors:
            raise ValueError(f"Invalid processors: {invalid_processors}")

        results = []

        for processor_name in processors:
            processor = self._processors[processor_name]

            # Get component data based on processor type
            component_data = self._get_component_data(pr_data, processor_name)

            if component_data is None:
                results.append(
                    ProcessingResult(
                        component=processor_name,
                        success=False,
                        errors=[f"No data available for component: {processor_name}"],
                    )
                )
                continue

            # Process component in isolation
            start_time = time.time()
            result = processor.process(component_data)
            processing_time = int((time.time() - start_time) * 1000)

            # Add timing information
            result.processing_time_ms = processing_time
            results.append(result)

        return results

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

        # Extract components
        pr_data = self.extract_pr_components(pr_url, extract_components)

        # Process components
        processing_results = self.process_components(pr_data, run_processors)

        bound_logger.success("🏁 PR analysis pipeline complete")

        return {
            "pr_url": pr_url,
            "extracted_data": pr_data.model_dump(exclude_none=True),
            "processing_results": [
                result.model_dump() for result in processing_results
            ],
            "summary": self._generate_summary(pr_data, processing_results),
        }

    def _get_pr_from_url(self, pr_url: str) -> PullRequest | None:
        """Extract PR from GitHub URL."""
        try:
            # Parse URL: https://github.com/owner/repo/pull/123
            parsed = urlparse(pr_url)
            path_parts = parsed.path.strip("/").split("/")

            if len(path_parts) < 4 or path_parts[2] != "pull":
                logger.debug(f"Invalid PR URL format: {pr_url}")
                return None

            owner = path_parts[0]
            repo_name = path_parts[1]
            pr_number = int(path_parts[3])

            repo = self.github_client.get_repo(f"{owner}/{repo_name}")
            return repo.get_pull(pr_number)

        except ValueError as e:
            logger.debug(f"Failed to parse PR number from URL {pr_url}: {e}")
            return None
        except Exception as e:
            logger.debug(
                f"Failed to retrieve PR from {pr_url}: {type(e).__name__}: {e}"
            )
            return None

    def _get_component_data(
        self, pr_data: PRData, component_name: str
    ) -> dict[str, Any] | None:
        """Get component data for processing."""
        component_map = {
            "metadata": pr_data.metadata,
            "code_changes": pr_data.code_changes,
            "repository": pr_data.repository_info,
            "reviews": pr_data.review_data,
        }

        data = component_map.get(component_name)
        return data if data is not None else None

    def _generate_summary(
        self, pr_data: PRData, processing_results: list[ProcessingResult]
    ) -> dict[str, Any]:
        """Generate high-level summary of PR analysis."""
        successful_results = [r for r in processing_results if r.success]
        failed_results = [r for r in processing_results if not r.success]

        summary = {
            "components_extracted": [],
            "components_processed": len(successful_results),
            "processing_failures": len(failed_results),
            "total_processing_time_ms": sum(
                r.processing_time_ms or 0 for r in processing_results
            ),
        }

        # Track what was extracted
        if pr_data.metadata:
            summary["components_extracted"].append("metadata")
        if pr_data.code_changes:
            summary["components_extracted"].append("code_changes")
        if pr_data.repository_info:
            summary["components_extracted"].append("repository")
        if pr_data.review_data:
            summary["components_extracted"].append("reviews")

        # Add quick insights if available
        insights = {}

        for result in successful_results:
            if result.component == "metadata" and "metadata_quality" in result.data:
                quality = result.data["metadata_quality"]
                insights["metadata_quality"] = quality.get("quality_level")

            elif (
                result.component == "code_changes" and "risk_assessment" in result.data
            ):
                risk = result.data["risk_assessment"]
                insights["code_risk_level"] = risk.get("risk_level")

            elif result.component == "repository" and "repo_health" in result.data:
                health = result.data["repo_health"]
                insights["repo_health_level"] = health.get("health_level")

        summary["insights"] = insights
        return summary

    def analyze_prs_batch(
        self,
        pr_urls: list[str],
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
        parallel: bool = False,
    ) -> dict[str, Any]:
        """
        Analyze multiple PRs in batch.

        Args:
            pr_urls: List of GitHub PR URLs
            extract_components: Components to extract
            run_processors: Processors to run
            parallel: Whether to process PRs in parallel (future enhancement)

        Returns:
            Dictionary with results for each PR
        """
        logger.info(f"🔄 Starting batch analysis of {len(pr_urls)} PRs")

        results = {
            "total_prs": len(pr_urls),
            "successful": 0,
            "failed": 0,
            "pr_results": {},
            "summary": {},
        }

        for pr_url in pr_urls:
            try:
                pr_result = self.analyze_pr(pr_url, extract_components, run_processors)
                results["pr_results"][pr_url] = pr_result
                results["successful"] += 1
            except Exception as e:
                logger.error(f"Failed to analyze PR {pr_url}: {e}")
                results["pr_results"][pr_url] = {
                    "error": str(e),
                    "success": False,
                }
                results["failed"] += 1

        # Generate batch summary
        results["summary"] = self._generate_batch_summary(results["pr_results"])

        logger.success(
            f"✅ Batch analysis complete: {results['successful']}/{results['total_prs']} successful"
        )
        return results

    def analyze_release_prs(
        self,
        repo_name: str,
        release_tag: str,
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze all PRs included in a specific release.

        Args:
            repo_name: Repository name (e.g., "owner/repo")
            release_tag: Release tag name (e.g., "v1.2.3")
            extract_components: Components to extract
            run_processors: Processors to run

        Returns:
            Dictionary with analysis results for the release
        """
        logger.info(f"📦 Analyzing PRs for release {release_tag} in {repo_name}")

        # Fetch PRs for the release
        prs = self.pr_fetcher.get_prs_by_release(repo_name, release_tag)
        pr_urls = [pr["url"] for pr in prs]

        # Analyze all PRs
        results = self.analyze_prs_batch(pr_urls, extract_components, run_processors)

        # Add release metadata
        results["release_info"] = {
            "repository": repo_name,
            "release_tag": release_tag,
            "total_prs": len(prs),
        }

        return results

    def analyze_unreleased_prs(
        self,
        repo_name: str,
        base_branch: str = "main",
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze all merged PRs that haven't been released yet.

        Args:
            repo_name: Repository name (e.g., "owner/repo")
            base_branch: Base branch to check (default: "main")
            extract_components: Components to extract
            run_processors: Processors to run

        Returns:
            Dictionary with analysis results for unreleased PRs
        """
        logger.info(f"🚀 Analyzing unreleased PRs in {repo_name}")

        # Fetch unreleased PRs
        prs = self.pr_fetcher.get_unreleased_prs(repo_name, base_branch)
        pr_urls = [pr["url"] for pr in prs]

        # Analyze all PRs
        results = self.analyze_prs_batch(pr_urls, extract_components, run_processors)

        # Add unreleased metadata
        results["unreleased_info"] = {
            "repository": repo_name,
            "base_branch": base_branch,
            "total_unreleased_prs": len(prs),
        }

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
        Analyze PRs between two release tags.

        Args:
            repo_name: Repository name
            from_tag: Starting release tag (exclusive)
            to_tag: Ending release tag (inclusive)
            extract_components: Components to extract
            run_processors: Processors to run

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"🔍 Analyzing PRs between {from_tag} and {to_tag} in {repo_name}")

        # Fetch PRs between releases
        prs = self.pr_fetcher.get_prs_between_releases(repo_name, from_tag, to_tag)
        pr_urls = [pr["url"] for pr in prs]

        # Analyze all PRs
        results = self.analyze_prs_batch(pr_urls, extract_components, run_processors)

        # Add version range metadata
        results["version_range_info"] = {
            "repository": repo_name,
            "from_tag": from_tag,
            "to_tag": to_tag,
            "total_prs": len(prs),
        }

        return results

    def _generate_batch_summary(self, pr_results: dict[str, Any]) -> dict[str, Any]:
        """Generate summary statistics for batch PR analysis."""
        summary = {
            "total_analyzed": len(pr_results),
            "by_risk_level": {"minimal": 0, "low": 0, "medium": 0, "high": 0},
            "by_title_quality": {"poor": 0, "fair": 0, "good": 0, "excellent": 0},
            "by_description_quality": {"poor": 0, "fair": 0, "good": 0, "excellent": 0},
            "average_files_changed": 0,
            "total_additions": 0,
            "total_deletions": 0,
        }

        successful_prs = [
            result
            for result in pr_results.values()
            if result.get("success", True) and "processing_results" in result
        ]

        files_changed_list = []

        for pr_result in successful_prs:
            # Process each component result
            for proc_result in pr_result.get("processing_results", []):
                if proc_result["success"]:
                    component = proc_result["component"]
                    data = proc_result["data"]

                    # Code risk levels
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
        formatted_results = self._format_results_for_output(results)

        # Save to file
        saved_path = self.output_manager.save(
            formatted_results, output_path, output_format
        )

        return results, saved_path

    def _format_results_for_output(self, results: dict[str, Any]) -> dict[str, Any]:
        """
        Format analysis results for output formatters.

        Args:
            results: Raw analysis results

        Returns:
            Formatted results dictionary
        """
        # Extract PR metadata
        pr_url = results.get("pr_url", "")
        processing_results = results.get("processing_results", [])

        # Parse PR info from URL
        pr_info = self._parse_pr_url(pr_url)

        # Build formatted output
        output = {
            "pr_url": pr_url,
            "pr_number": pr_info.get("pr_number"),
            "repository": pr_info.get("repository"),
        }

        # Add processed component data
        for result in processing_results:
            if result.get("success"):
                component = result.get("component")
                data = result.get("data", {})

                if component == "metadata":
                    output["metadata"] = self._format_metadata_output(data)
                elif component == "code_changes":
                    output["code_changes"] = self._format_code_output(data)
                elif component == "repository":
                    output["repository_info"] = self._format_repo_output(data)
                elif component == "reviews":
                    output["reviews"] = self._format_reviews_output(data)

        # Add processing metrics
        output["processing_metrics"] = self._format_processing_metrics(results)

        return output

    def _parse_pr_url(self, pr_url: str) -> dict[str, Any]:
        """Parse PR URL to extract repository and PR number."""
        try:
            parsed = urlparse(pr_url)
            path_parts = parsed.path.strip("/").split("/")

            if len(path_parts) >= 4 and path_parts[2] == "pull":
                return {
                    "repository": f"{path_parts[0]}/{path_parts[1]}",
                    "pr_number": int(path_parts[3]),
                }
        except Exception:
            pass

        return {}

    def _format_metadata_output(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format metadata component data for output."""
        return {
            "title_quality": data.get("title_quality", {}),
            "description_quality": data.get("description_quality", {}),
            "label_analysis": data.get("label_analysis", {}),
        }

    def _format_code_output(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format code changes component data for output."""
        return {
            "change_stats": data.get("change_stats", {}),
            "risk_assessment": data.get("risk_assessment", {}),
            "pattern_analysis": data.get("pattern_analysis", {}),
            "file_analysis": data.get("file_analysis", {}),
        }

    def _format_repo_output(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format repository component data for output."""
        return {
            "health_assessment": data.get("health_assessment", {}),
            "language_analysis": data.get("language_analysis", {}),
            "branch_analysis": data.get("branch_analysis", {}),
        }

    def _format_reviews_output(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format reviews component data for output."""
        return {
            "review_summary": data.get("review_summary", {}),
            "review_timeline": data.get("review_timeline", {}),
            "comment_analysis": data.get("comment_analysis", {}),
        }

    def _format_processing_metrics(self, results: dict[str, Any]) -> dict[str, Any]:
        """Format processing metrics for output."""
        processing_results = results.get("processing_results", [])
        summary = results.get("summary", {})

        # Calculate component durations
        component_durations = {}
        for result in processing_results:
            component = result.get("component")
            duration = (result.get("processing_time_ms", 0) or 0) / 1000.0
            if component:
                component_durations[component] = duration

        return {
            "total_duration": summary.get("total_processing_time_ms", 0) / 1000.0,
            "component_durations": component_durations,
            "components_processed": summary.get("components_processed", 0),
            "processing_failures": summary.get("processing_failures", 0),
        }
