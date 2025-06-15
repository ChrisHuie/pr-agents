"""
PR Processing Coordinator - orchestrates extraction and processing with strict boundaries.
"""

import time
from typing import Any
from urllib.parse import urlparse

from github import Github
from github.PullRequest import PullRequest

from .extractors import (
    BaseExtractor,
    CodeChangesExtractor,
    MetadataExtractor,
    RepositoryExtractor,
    ReviewsExtractor,
)
from .models import PRData, ProcessingResult
from .processors import BaseProcessor, CodeProcessor, MetadataProcessor, RepoProcessor


class PRCoordinator:
    """
    Coordinates PR processing with strict component isolation.

    Ensures no context bleeding between different PR components
    (metadata, code changes, repository info, reviews).
    """

    def __init__(self, github_token: str) -> None:
        self.github_client = Github(github_token)

        # Initialize extractors
        self._extractors: dict[str, BaseExtractor] = {
            "metadata": MetadataExtractor(self.github_client),
            "code_changes": CodeChangesExtractor(self.github_client),
            "repository": RepositoryExtractor(self.github_client),
            "reviews": ReviewsExtractor(self.github_client),
        }

        # Initialize processors
        self._processors: dict[str, BaseProcessor] = {
            "metadata": MetadataProcessor(),
            "code_changes": CodeProcessor(),
            "repository": RepoProcessor(),
        }

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
        if components is None:
            components = {"metadata", "code_changes", "repository", "reviews"}

        # Validate components
        valid_components = set(self._extractors.keys())
        invalid_components = components - valid_components
        if invalid_components:
            raise ValueError(f"Invalid components: {invalid_components}")

        # Parse PR URL and get PR object
        pr = self._get_pr_from_url(pr_url)
        if not pr:
            raise ValueError(f"Could not retrieve PR from URL: {pr_url}")

        # Extract components in isolation
        pr_data = PRData()

        if "metadata" in components:
            metadata_data = self._extractors["metadata"].extract(pr)
            if metadata_data:
                pr_data.metadata = metadata_data

        if "code_changes" in components:
            code_data = self._extractors["code_changes"].extract(pr)
            if code_data:
                pr_data.code_changes = code_data

        if "repository" in components:
            repo_data = self._extractors["repository"].extract(pr)
            if repo_data:
                pr_data.repository_info = repo_data

        if "reviews" in components:
            review_data = self._extractors["reviews"].extract(pr)
            if review_data:
                pr_data.review_data = review_data

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
        # Extract components
        pr_data = self.extract_pr_components(pr_url, extract_components)

        # Process components
        processing_results = self.process_components(pr_data, run_processors)

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
                return None

            owner = path_parts[0]
            repo_name = path_parts[1]
            pr_number = int(path_parts[3])

            repo = self.github_client.get_repo(f"{owner}/{repo_name}")
            return repo.get_pull(pr_number)

        except Exception:
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
