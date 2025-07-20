"""
Result formatter for preparing analysis results for output.
"""

from typing import Any
from urllib.parse import urlparse


class ResultFormatter:
    """
    Formats PR analysis results for output systems.

    Transforms internal analysis data into output-ready format.
    """

    @staticmethod
    def format_for_output(results: dict[str, Any]) -> dict[str, Any]:
        """
        Format analysis results for output formatters.

        Args:
            results: Raw analysis results from coordinators

        Returns:
            Formatted results dictionary ready for output
        """
        # Extract PR metadata
        pr_url = results.get("pr_url", "")
        processing_results = results.get("processing_results", [])
        extracted_data = results.get("extracted_data", {})

        # Parse PR info from URL
        pr_info = ResultFormatter._parse_pr_url(pr_url)

        # Build formatted output
        output = {
            "pr_url": pr_url,
            "pr_number": pr_info.get("pr_number"),
            "repository": (
                {"full_name": pr_info.get("repository")}
                if pr_info.get("repository")
                else None
            ),
        }

        # Add processed component data
        for result in processing_results:
            if result.get("success"):
                component = result.get("component")
                data = result.get("data", {})

                if component == "metadata":
                    output["metadata"] = ResultFormatter._format_metadata(data)
                    # Also store the raw title for filename generation
                    if "title" in data:
                        output["pr_title"] = data["title"]
                elif component == "code_changes":
                    output["code_changes"] = ResultFormatter._format_code_changes(data)
                elif component == "repository":
                    output["repository_info"] = ResultFormatter._format_repository(data)
                    # Also update the repository field with full_name if available
                    if "full_name" in data:
                        output["repository"] = {"full_name": data["full_name"]}
                elif component == "reviews":
                    output["reviews"] = ResultFormatter._format_reviews(data)
                elif component == "modules":
                    output["modules"] = (
                        data  # Keep raw module data for filename generation
                    )
                elif component == "ai_summaries":
                    output["ai_summaries"] = data

        # Add extracted data that doesn't have processors (like modules)
        if extracted_data and isinstance(extracted_data, dict):
            # Check for modules data in extracted components
            if "modules" in extracted_data and "modules" not in output:
                output["modules"] = extracted_data["modules"]

        # Add processing metrics
        output["processing_metrics"] = ResultFormatter._format_metrics(results)

        return output

    @staticmethod
    def _parse_pr_url(pr_url: str) -> dict[str, Any]:
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

    @staticmethod
    def _format_metadata(data: dict[str, Any]) -> dict[str, Any]:
        """Format metadata component data for output."""
        return {
            "title_quality": data.get("title_quality", {}),
            "description_quality": data.get("description_quality", {}),
            "label_analysis": data.get("label_analysis", {}),
        }

    @staticmethod
    def _format_code_changes(data: dict[str, Any]) -> dict[str, Any]:
        """Format code changes component data for output."""
        return {
            "change_stats": data.get("change_stats", {}),
            "risk_assessment": data.get("risk_assessment", {}),
            "pattern_analysis": data.get("pattern_analysis", {}),
            "file_analysis": data.get("file_analysis", {}),
        }

    @staticmethod
    def _format_repository(data: dict[str, Any]) -> dict[str, Any]:
        """Format repository component data for output."""
        return {
            "health_assessment": data.get("health_assessment", {}),
            "language_analysis": data.get("language_analysis", {}),
            "branch_analysis": data.get("branch_analysis", {}),
        }

    @staticmethod
    def _format_reviews(data: dict[str, Any]) -> dict[str, Any]:
        """Format reviews component data for output."""
        return {
            "review_summary": data.get("review_summary", {}),
            "review_timeline": data.get("review_timeline", {}),
            "comment_analysis": data.get("comment_analysis", {}),
        }

    @staticmethod
    def _format_metrics(results: dict[str, Any]) -> dict[str, Any]:
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
