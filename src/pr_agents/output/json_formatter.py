"""
Modular JSON formatter for PR analysis output.
"""

import json
from typing import Any

from .base import BaseFormatter
from .formatters.base import FormatterConfig
from .formatters.json_transformers import TRANSFORMER_REGISTRY


class JSONFormatter(BaseFormatter):
    """Formats PR analysis results as JSON with modular transformers."""

    def __init__(
        self,
        config: FormatterConfig | None = None,
        indent: int = 2,
        sort_keys: bool = True,
    ):
        """
        Initialize JSON formatter with optional configuration.

        Args:
            config: Formatter configuration for customizing output
            indent: Number of spaces for indentation
            sort_keys: Whether to sort dictionary keys
        """
        self.config = config or FormatterConfig.default()
        self.indent = indent
        self.sort_keys = sort_keys

    def format(self, data: dict[str, Any]) -> str:
        """
        Format PR analysis data as JSON.

        Args:
            data: PR analysis results dictionary

        Returns:
            JSON formatted string
        """
        # Check if this is batch results
        if "pr_results" in data and "batch_summary" in data:
            if self._is_release_data(data) and self.config.grouped_by_tag:
                output_data = self._format_grouped_release_json(data)
            else:
                output_data = self._format_batch_json(data)
        else:
            # Single PR analysis
            output_data = self._format_single_pr_json(data)

        # Clean and serialize
        cleaned_data = self._clean_data(output_data)
        return json.dumps(
            cleaned_data,
            indent=self.indent,
            sort_keys=self.sort_keys,
            ensure_ascii=False,
            default=str,
        )

    def _format_single_pr_json(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format single PR data using transformers."""
        # Check if this is PR analysis data or simple data
        has_analysis_sections = any(
            key in data
            for key in [
                "metadata",
                "code_changes",
                "ai_summaries",
                "modules",
                "reviews",
                "repository_info",
                "processing_metrics",
            ]
        )

        # If no analysis sections found, return data as-is (for simple/test data)
        if not has_analysis_sections:
            return data

        # Otherwise, use transformers for PR analysis data
        output = {}

        # Add basic info
        if "pr_url" in data:
            output["pr_url"] = data["pr_url"]
        if "pr_number" in data:
            output["pr_number"] = data["pr_number"]
        if "repository" in data:
            repo_info = data["repository"]
            if isinstance(repo_info, dict):
                output["repository"] = repo_info.get("full_name", "Unknown")
            else:
                output["repository"] = repo_info
        if "release_version" in data:
            output["release_version"] = data["release_version"]

        # Apply transformers based on configuration
        options = {
            "compact": self.config.compact,
            "personas": self.config.personas,
            "include_metrics": self.config.include_metrics,
        }

        for section_name, transformer in TRANSFORMER_REGISTRY.items():
            # Check if section is enabled
            if self.config.sections and section_name not in self.config.sections:
                continue

            # Apply transformer if data is available
            if transformer.applies_to(data):
                transformed_data = transformer.transform(data, options)
                if transformed_data:
                    output[transformer.get_field_name()] = transformed_data

        return output

    def _format_batch_json(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format batch PR data."""
        output = {
            "type": "batch_analysis",
            "repository": data.get("repository", "Unknown"),
        }

        # Add release info if available
        if "release_tag" in data:
            output["release_tag"] = data["release_tag"]
        elif "from_tag" in data and "to_tag" in data:
            output["from_tag"] = data["from_tag"]
            output["to_tag"] = data["to_tag"]

        # Add batch summary
        if "batch_summary" in data:
            output["batch_summary"] = data["batch_summary"]

        # Add individual PR results
        if "pr_results" in data:
            output["pr_results"] = {}
            for pr_url, pr_result in data["pr_results"].items():
                if pr_result.get("error"):
                    output["pr_results"][pr_url] = {"error": pr_result["error"]}
                else:
                    # Process through ResultFormatter
                    from ..pr_processing.analysis import ResultFormatter

                    formatted_pr = ResultFormatter.format_for_output(pr_result)
                    output["pr_results"][pr_url] = self._format_single_pr_json(
                        formatted_pr
                    )

        return output

    def _format_grouped_release_json(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format release data with PR grouping."""
        output = {
            "type": "release_summary",
            "repository": data.get("repository", "Unknown"),
            "release": data.get("release_tag", data.get("release_version", "Unknown")),
        }

        # Add summary statistics
        if "batch_summary" in data:
            output["statistics"] = {
                "total_prs": data["batch_summary"].get("total_prs", 0),
                "successful_analyses": data["batch_summary"].get(
                    "successful_analyses", 0
                ),
                "failed_analyses": data["batch_summary"].get("failed_analyses", 0),
                "total_additions": data["batch_summary"].get("total_additions", 0),
                "total_deletions": data["batch_summary"].get("total_deletions", 0),
            }

        # Group PRs by tag
        pr_groups = self._group_prs_by_tag_json(data.get("pr_results", {}))
        output["pr_groups"] = pr_groups

        # Category breakdown
        total_prs = output["statistics"]["total_prs"]
        output["category_breakdown"] = {}
        for tag in ["Feature", "Bug Fix", "Maintenance"]:
            count = len(pr_groups.get(tag, []))
            percentage = (count / total_prs * 100) if total_prs > 0 else 0
            output["category_breakdown"][tag] = {
                "count": count,
                "percentage": round(percentage, 1),
            }

        return output

    def _group_prs_by_tag_json(self, pr_results: dict[str, Any]) -> dict[str, list]:
        """Group PRs by their tags for JSON output."""
        groups = {"Feature": [], "Bug Fix": [], "Maintenance": []}

        for pr_url, pr_result in pr_results.items():
            if pr_result.get("error"):
                continue

            # Process the PR result
            from ..pr_processing.analysis import ResultFormatter

            formatted_pr = ResultFormatter.format_for_output(pr_result)

            # Extract key info
            pr_number = formatted_pr.get("pr_number", "unknown")
            metadata = formatted_pr.get("metadata", {})
            title = metadata.get("label_analysis", {}).get("title", "No title")

            # Determine tag
            tag = self._determine_pr_tag(metadata)

            # Create PR summary
            pr_info = {
                "number": pr_number,
                "title": title,
                "url": pr_url,
            }

            # Add AI summaries if available
            if "ai_summaries" in formatted_pr:
                pr_info["ai_summaries"] = {}
                ai_data = formatted_pr["ai_summaries"]
                for persona in [
                    "executive_summary",
                    "product_summary",
                    "developer_summary",
                    "reviewer_summary",
                    "technical_writer_summary",
                ]:
                    if persona in ai_data and ai_data[persona].get("summary"):
                        pr_info["ai_summaries"][persona] = ai_data[persona]["summary"]

            # Add metrics
            if "code_changes" in formatted_pr:
                code_data = formatted_pr["code_changes"]
                if "change_stats" in code_data:
                    stats = code_data["change_stats"]
                    pr_info["metrics"] = {
                        "additions": stats.get("total_additions", 0),
                        "deletions": stats.get("total_deletions", 0),
                        "files_changed": stats.get("changed_files", 0),
                    }
                if "risk_assessment" in code_data:
                    pr_info["risk_level"] = code_data["risk_assessment"].get(
                        "risk_level", "Unknown"
                    )

            groups[tag].append(pr_info)

        # Sort PRs in each group
        for tag in groups:
            groups[tag].sort(
                key=lambda x: int(x["number"]) if str(x["number"]).isdigit() else 0
            )

        return groups

    def _determine_pr_tag(self, metadata: dict[str, Any]) -> str:
        """Determine PR tag based on labels."""
        label_analysis = metadata.get("label_analysis", {})
        all_labels = []

        # Collect all labels
        categorized = label_analysis.get("categorized", {})
        for category_labels in categorized.values():
            all_labels.extend(category_labels)

        uncategorized = label_analysis.get("uncategorized", [])
        all_labels.extend(uncategorized)

        # Convert to lowercase for matching
        label_names = [label.lower() for label in all_labels]

        # Check for feature-related labels
        feature_labels = ["feature", "enhancement", "adapter"]
        for label in label_names:
            for feature_label in feature_labels:
                if feature_label in label:
                    return "Feature"

        # Check for bug-related labels
        bug_labels = ["bug", "fix", "security"]
        for label in label_names:
            for bug_label in bug_labels:
                if bug_label in label:
                    return "Bug Fix"

        # Default to maintenance
        return "Maintenance"

    def _is_release_data(self, data: dict[str, Any]) -> bool:
        """Check if data is from release analysis."""
        return (
            "release_tag" in data
            or "release_version" in data
            or (
                ("batch_summary" in data and "pr_results" in data)
                and data.get("batch_summary", {}).get("total_prs", 0) > 1
            )
        )

    def _clean_data(self, obj: Any) -> Any:
        """
        Recursively clean data to ensure JSON serializability.

        Args:
            obj: Object to clean

        Returns:
            Cleaned object
        """
        if isinstance(obj, dict):
            return {k: self._clean_data(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [self._clean_data(item) for item in obj if item is not None]
        elif isinstance(obj, str | int | float | bool) or obj is None:
            return obj
        else:
            # Convert other types to string
            return str(obj)

    def get_file_extension(self) -> str:
        """Return JSON file extension."""
        return ".json"

    def validate_data(self, data: dict[str, Any]) -> bool:
        """
        Validate that the data can be serialized to JSON.

        Args:
            data: PR analysis results dictionary

        Returns:
            True if data can be serialized, False otherwise
        """
        try:
            json.dumps(data, default=str)
            return True
        except (TypeError, ValueError):
            return False
