"""
Summary builder for PR analysis results.
"""

from typing import Any

from ..models import PRData, ProcessingResult


class SummaryBuilder:
    """
    Builds summaries and analytics from PR analysis results.

    Pure functions for generating insights and statistics.
    """

    @staticmethod
    def build_single_pr_summary(
        pr_data: PRData, processing_results: list[ProcessingResult]
    ) -> dict[str, Any]:
        """
        Generate high-level summary for a single PR analysis.

        Args:
            pr_data: Extracted PR data
            processing_results: List of processing results

        Returns:
            Summary dictionary with insights
        """
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
        insights = SummaryBuilder._extract_insights(successful_results)
        if insights:
            summary["insights"] = insights

        return summary

    @staticmethod
    def build_batch_summary(pr_results: dict[str, Any]) -> dict[str, Any]:
        """
        Generate summary statistics for batch PR results.

        Args:
            pr_results: Dictionary of PR analysis results

        Returns:
            Batch summary with aggregated statistics
        """
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
                SummaryBuilder._aggregate_pr_statistics(
                    pr_result["processing_results"], summary, files_changed_list
                )

        # Calculate averages
        if files_changed_list:
            summary["average_files_changed"] = sum(files_changed_list) / len(
                files_changed_list
            )

        return summary

    @staticmethod
    def _extract_insights(successful_results: list[ProcessingResult]) -> dict[str, Any]:
        """Extract key insights from processing results."""
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

        return insights

    @staticmethod
    def _aggregate_pr_statistics(
        processing_results: list[dict],
        summary: dict[str, Any],
        files_changed_list: list[int],
    ) -> None:
        """Aggregate statistics from individual PR results."""
        for result in processing_results:
            if not result.get("success"):
                continue

            component = result.get("component")
            data = result.get("data", {})

            # Code change statistics
            if component == "code_changes" and "risk_assessment" in data:
                risk_level = data["risk_assessment"].get("risk_level", "minimal")
                summary["by_risk_level"][risk_level] += 1

                # Code statistics
                if "change_stats" in data:
                    stats = data["change_stats"]
                    summary["total_additions"] += stats.get("total_additions", 0)
                    summary["total_deletions"] += stats.get("total_deletions", 0)
                    files_changed_list.append(stats.get("changed_files", 0))

            # Metadata quality
            elif component == "metadata":
                if "title_quality" in data:
                    title_level = data["title_quality"].get("quality_level", "poor")
                    summary["by_title_quality"][title_level] += 1

                if "description_quality" in data:
                    desc_level = data["description_quality"].get(
                        "quality_level", "poor"
                    )
                    summary["by_description_quality"][desc_level] += 1
