"""
Single PR analysis coordinator.
"""

import time
from typing import Any
from urllib.parse import urlparse

from github import Github
from github.PullRequest import PullRequest
from loguru import logger

from ...logging_config import log_data_flow
from ..models import PRData, ProcessingResult
from .base import BaseCoordinator
from .component_manager import ComponentManager


class SinglePRCoordinator(BaseCoordinator):
    """
    Coordinates the analysis of a single PR.

    Manages the extraction and processing pipeline for individual PRs.
    """

    def __init__(
        self, github_client: Github, component_manager: ComponentManager
    ) -> None:
        """
        Initialize single PR coordinator.

        Args:
            github_client: Authenticated GitHub client
            component_manager: Component registry manager
        """
        super().__init__(github_client)
        self.component_manager = component_manager

    def coordinate(
        self,
        pr_url: str,
        extract_components: set[str] | None = None,
        run_processors: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze a single PR.

        Args:
            pr_url: GitHub PR URL
            extract_components: Components to extract (None for all)
            run_processors: Processors to run (None for all)

        Returns:
            Analysis results dictionary
        """
        # Extract components
        pr_data = self.extract_pr_components(pr_url, extract_components)

        # Process components
        processing_results = self.process_components(pr_data, run_processors)

        # Generate summary
        summary = self._generate_summary(pr_data, processing_results)

        return {
            "pr_url": pr_url,
            "extracted_data": pr_data.model_dump(exclude_none=True),
            "processing_results": [
                result.model_dump() for result in processing_results
            ],
            "summary": summary,
        }

    def extract_pr_components(
        self, pr_url: str, components: set[str] | None = None
    ) -> PRData:
        """
        Extract specified components from a PR.

        Args:
            pr_url: GitHub PR URL
            components: Components to extract (None for all)

        Returns:
            PRData with extracted components
        """
        logger.info(f"📥 Extracting PR components from: {pr_url}")

        pr_obj = self._get_pr_from_url(pr_url)
        if not pr_obj:
            logger.error(f"❌ Failed to retrieve PR from URL: {pr_url}")
            raise ValueError(f"Could not retrieve PR from URL: {pr_url}")

        # Determine which extractors to use
        if components is None:
            extractors = self.component_manager.get_extractors()
        else:
            extractors = self.component_manager.get_extractors(components)

        pr_data = PRData()

        # Extract components in isolation
        for name, extractor in extractors.items():
            try:
                logger.info(f"Running {name} extractor")
                start_time = time.time()

                # Extract component data
                component_data = extractor.extract(pr_obj)

                # Log performance
                extraction_time = int((time.time() - start_time) * 1000)
                log_data_flow(
                    f"{name} extracted",
                    {"keys": list(component_data.keys()) if component_data else []},
                )

                # Map to PRData fields
                if name == "metadata" and component_data:
                    pr_data.metadata = component_data
                elif name == "code_changes" and component_data:
                    pr_data.code_changes = component_data
                elif name == "repository" and component_data:
                    pr_data.repository_info = component_data
                elif name == "reviews" and component_data:
                    pr_data.review_data = component_data

                logger.success(f"✅ {name} extraction complete ({extraction_time}ms)")

            except Exception as e:
                logger.error(f"❌ Error in {name} extractor: {e}")

        return pr_data

    def process_components(
        self, pr_data: PRData, processors: list[str] | None = None
    ) -> list[ProcessingResult]:
        """
        Process extracted components.

        Args:
            pr_data: Extracted PR data
            processors: List of processors to run (None for all)

        Returns:
            List of processing results
        """
        logger.info("🔄 Processing extracted components")

        # Determine which processors to use
        if processors is None:
            processor_map = self.component_manager.get_processors()
        else:
            processor_map = self.component_manager.get_processors(processors)

        results = []

        for processor_name, processor in processor_map.items():
            # Get component data for this processor
            component_data = self.component_manager.get_component_data(
                pr_data, processor_name
            )

            if component_data is None:
                logger.debug(f"No data available for {processor_name} processor")
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

            elif (
                result.component == "repository" and "health_assessment" in result.data
            ):
                health = result.data["health_assessment"]
                insights["repo_health"] = health.get("health_level")

        if insights:
            summary["insights"] = insights

        return summary
