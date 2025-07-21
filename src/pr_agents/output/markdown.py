"""
Modular markdown formatter for PR analysis output.
"""

from typing import Any

from .base import BaseFormatter
from .formatters.base import FormatterConfig
from .formatters.sections import (
    AISection,
    CodeChangesSection,
    HeaderSection,
    LabelsSection,
    MetadataSection,
    MetricsSection,
    ModulesSection,
    RepositorySection,
    ReviewsSection,
)


class MarkdownFormatter(BaseFormatter):
    """Formats PR analysis results as Markdown with modular sections."""

    def __init__(self, config: FormatterConfig | None = None):
        """
        Initialize formatter with optional configuration.

        Args:
            config: Formatter configuration for customizing output
        """
        self.config = config or FormatterConfig.default()

    def format(self, data: dict[str, Any]) -> str:
        """
        Format PR analysis data as Markdown.

        Args:
            data: PR analysis results dictionary

        Returns:
            Markdown formatted string
        """
        # Check if this is batch results
        if "pr_results" in data and "batch_summary" in data:
            # Check if we should use grouped format
            if self._is_release_data(data) and self._should_use_grouped_format(data):
                return self._format_grouped_release_results(data)
            return self._format_batch_results(data)

        # Single PR analysis - use modular sections
        lines = []

        # Get formatting options
        options = {
            "compact": self.config.compact,
            "personas": self.config.personas,
            "include_metrics": self.config.include_metrics,
        }

        # Define all available sections in priority order
        sections = [
            HeaderSection(),
            ModulesSection(),
            CodeChangesSection(),
            LabelsSection(),
            MetadataSection(),
            AISection(),
            ReviewsSection(),
            RepositorySection(),
            MetricsSection(),
        ]

        # Sort by priority
        sections.sort(key=lambda s: s.get_priority())

        # Apply each section if it has data and is enabled
        for section in sections:
            # Check if section is enabled in config
            section_name = section.__class__.__name__.replace("Section", "").lower()
            if self.config.sections and section_name not in self.config.sections:
                continue

            # Apply section if it has data
            if section.applies_to(data):
                section_lines = section.format(data, options)
                if section_lines:
                    lines.extend(section_lines)

        return "\n".join(lines)

    def _format_batch_results(self, data: dict[str, Any]) -> str:
        """Format batch PR analysis results."""
        lines = []

        # Header
        lines.append("# Batch PR Analysis Report")
        lines.append("")

        # Repository info if available
        if "repository" in data:
            lines.append(f"**Repository:** {data['repository']}")

        # Tag info for release analysis
        if "release_tag" in data:
            lines.append(f"**Release:** {data['release_tag']}")
        elif "from_tag" in data and "to_tag" in data:
            lines.append(f"**From Release:** {data['from_tag']}")
            lines.append(f"**To Release:** {data['to_tag']}")

        lines.append("")

        # Batch Summary
        if "batch_summary" in data:
            lines.extend(self._format_batch_summary(data["batch_summary"]))

        # Individual PR Results
        if "pr_results" in data:
            lines.append("## 📋 Individual PR Analyses")
            lines.append("")

            for pr_url, pr_result in data["pr_results"].items():
                lines.append(f"### 🔗 {pr_url}")
                lines.append("")

                # Check for errors
                if pr_result.get("error"):
                    lines.append(f"**Error:** {pr_result['error']}")
                    lines.append("")
                    continue

                # Process the PR result through ResultFormatter
                from ..pr_processing.analysis import ResultFormatter

                formatted_pr = ResultFormatter.format_for_output(pr_result)

                # Extract key information using summary format
                if "metadata" in formatted_pr:
                    lines.extend(
                        self._format_pr_summary_metadata(formatted_pr["metadata"])
                    )

                if "code_changes" in formatted_pr:
                    lines.extend(
                        self._format_pr_summary_code(formatted_pr["code_changes"])
                    )

                if "ai_summaries" in formatted_pr:
                    lines.extend(
                        self._format_pr_summary_ai(formatted_pr["ai_summaries"])
                    )

                lines.append("")  # Space between PRs

        return "\n".join(lines)

    def _format_batch_summary(self, summary: dict[str, Any]) -> list[str]:
        """Format batch summary statistics."""
        lines = ["## 📊 Batch Summary", ""]

        # Overall stats
        lines.append("### Overall Statistics")
        lines.append(f"- **Total PRs:** {summary.get('total_prs', 0)}")
        lines.append(
            f"- **Successful Analyses:** {summary.get('successful_analyses', 0)}"
        )
        lines.append(f"- **Failed Analyses:** {summary.get('failed_analyses', 0)}")

        if "total_processing_time" in summary:
            lines.append(
                f"- **Total Processing Time:** {summary['total_processing_time']:.2f}s"
            )

        lines.append("")

        # Code statistics
        if "total_additions" in summary or "total_deletions" in summary:
            lines.append("### Code Change Statistics")
            lines.append(f"- **Total Additions:** +{summary.get('total_additions', 0)}")
            lines.append(f"- **Total Deletions:** -{summary.get('total_deletions', 0)}")
            lines.append(
                f"- **Average Files Changed:** {summary.get('average_files_changed', 0):.1f}"
            )
            lines.append("")

        # Risk distribution
        if "by_risk_level" in summary:
            lines.append("### Risk Level Distribution")
            for level, count in summary["by_risk_level"].items():
                lines.append(f"- **{level.title()}:** {count}")
            lines.append("")

        # Quality distribution
        if "by_title_quality" in summary:
            lines.append("### Title Quality Distribution")
            for quality, count in summary["by_title_quality"].items():
                lines.append(f"- **{quality.title()}:** {count}")
            lines.append("")

        if "by_description_quality" in summary:
            lines.append("### Description Quality Distribution")
            for quality, count in summary["by_description_quality"].items():
                lines.append(f"- **{quality.title()}:** {count}")
            lines.append("")

        return lines

    def _format_pr_summary_metadata(self, metadata: dict[str, Any]) -> list[str]:
        """Format PR metadata summary for batch report."""
        lines = []

        if "title_quality" in metadata:
            quality = metadata["title_quality"]
            lines.append(
                f"**Title Quality:** {quality.get('quality_level', 'Unknown')} "
                f"({quality.get('score', 0)}/100)"
            )

        if "description_quality" in metadata:
            quality = metadata["description_quality"]
            lines.append(
                f"**Description Quality:** {quality.get('quality_level', 'Unknown')} "
                f"({quality.get('score', 0)}/100)"
            )

        return lines

    def _format_pr_summary_code(self, code_changes: dict[str, Any]) -> list[str]:
        """Format PR code changes summary for batch report."""
        lines = []

        if "change_stats" in code_changes:
            stats = code_changes["change_stats"]
            lines.append(
                f"**Changes:** {stats.get('changed_files', 0)} files, "
                f"+{stats.get('total_additions', 0)}/-{stats.get('total_deletions', 0)}"
            )

        if "risk_assessment" in code_changes:
            risk = code_changes["risk_assessment"]
            lines.append(f"**Risk Level:** {risk.get('risk_level', 'Unknown')}")

        return lines

    def _format_pr_summary_ai(self, ai_summaries: dict[str, Any]) -> list[str]:
        """Format PR AI summaries for batch report."""
        lines = ["", "#### AI Summaries"]

        if "executive_summary" in ai_summaries:
            exec_summary = ai_summaries["executive_summary"]
            lines.append(f"**Executive:** {exec_summary.get('summary', 'N/A')}")

        if "product_summary" in ai_summaries:
            product_summary = ai_summaries["product_summary"]
            lines.append(f"**Product:** {product_summary.get('summary', 'N/A')}")

        if "developer_summary" in ai_summaries:
            dev_summary = ai_summaries["developer_summary"]
            # Truncate long developer summaries in batch view
            dev_text = dev_summary.get("summary", "N/A")
            if len(dev_text) > 200:
                dev_text = dev_text[:200] + "..."
            lines.append(f"**Developer:** {dev_text}")

        return lines

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

    def _should_use_grouped_format(self, data: dict[str, Any]) -> bool:
        """Determine if grouped format should be used."""
        # Use grouped format for release data with multiple PRs
        if self._is_release_data(data):
            pr_results = data.get("pr_results", {})
            return len(pr_results) > 1
        return False

    def _format_grouped_release_results(self, data: dict[str, Any]) -> str:
        """Format release results with PR grouping by tags."""
        lines = []

        # Header
        release_tag = data.get("release_tag", data.get("release_version", "Unknown"))
        lines.append(f"# Release {release_tag} Summary")
        lines.append("")

        # Repository info
        if "repository" in data:
            lines.append(f"**Repository:** {data['repository']}")

        # PR count
        batch_summary = data.get("batch_summary", {})
        lines.append(f"**Total PRs:** {batch_summary.get('total_prs', 0)}")
        lines.append("")

        # Group PRs by tag
        pr_groups = self._group_prs_by_tag(data.get("pr_results", {}))

        # Display PRs by category
        for tag in ["Feature", "Bug Fix", "Maintenance"]:
            prs = pr_groups.get(tag, [])
            if prs:
                lines.append(f"## {tag}")
                lines.append("")

                for pr in prs:
                    # Include PR number, title, and AI summaries
                    lines.append(f"### PR #{pr['number']}: {pr['title']}")
                    lines.append(f"**URL:** {pr['url']}")
                    lines.append("")

                    # Add AI summaries if available
                    if pr.get("ai_summaries"):
                        lines.append("#### AI Summaries")
                        for persona, summary in pr["ai_summaries"].items():
                            if summary and summary != "[Not requested]":
                                persona_name = (
                                    persona.replace("_summary", "")
                                    .replace("_", " ")
                                    .title()
                                )
                                lines.append(f"**{persona_name}:** {summary}")
                        lines.append("")

                    # Add basic metrics
                    if pr.get("metrics"):
                        lines.append(
                            f"**Changes:** +{pr['metrics'].get('additions', 0)}/"
                            f"-{pr['metrics'].get('deletions', 0)} in "
                            f"{pr['metrics'].get('files_changed', 0)} files"
                        )
                        lines.append(
                            f"**Risk Level:** {pr['metrics'].get('risk_level', 'Unknown')}"
                        )
                        lines.append("")

                lines.append("")

        # Summary statistics
        lines.append("## Summary Statistics")
        lines.append("")
        lines.append(f"- **Total PRs:** {batch_summary.get('total_prs', 0)}")
        lines.append(
            f"- **Successful Analyses:** {batch_summary.get('successful_analyses', 0)}"
        )
        lines.append(
            f"- **Failed Analyses:** {batch_summary.get('failed_analyses', 0)}"
        )

        # Category breakdown
        lines.append("")
        lines.append("### Breakdown by Category")
        total_prs = batch_summary.get("total_prs", 0)
        for tag in ["Feature", "Bug Fix", "Maintenance"]:
            count = len(pr_groups.get(tag, []))
            percentage = (count / total_prs * 100) if total_prs > 0 else 0
            lines.append(f"- **{tag}:** {count} PRs ({percentage:.1f}%)")

        return "\n".join(lines)

    def _group_prs_by_tag(self, pr_results: dict[str, Any]) -> dict[str, list]:
        """Group PRs by their tags (Feature, Bug Fix, Maintenance)."""
        groups = {"Feature": [], "Bug Fix": [], "Maintenance": []}

        for pr_url, pr_result in pr_results.items():
            if pr_result.get("error"):
                continue

            # Process the PR result through ResultFormatter
            from ..pr_processing.analysis import ResultFormatter

            formatted_pr = ResultFormatter.format_for_output(pr_result)

            # Extract PR metadata
            pr_number = formatted_pr.get("pr_number", "unknown")
            metadata = formatted_pr.get("metadata", {})

            # Determine tag based on labels
            tag = self._determine_pr_tag(metadata)

            # Extract AI summaries
            ai_summaries = {}
            if "ai_summaries" in formatted_pr:
                ai_data = formatted_pr["ai_summaries"]
                if "executive_summary" in ai_data:
                    ai_summaries["executive_summary"] = ai_data[
                        "executive_summary"
                    ].get("summary")
                if "product_summary" in ai_data:
                    ai_summaries["product_summary"] = ai_data["product_summary"].get(
                        "summary"
                    )
                if "developer_summary" in ai_data:
                    ai_summaries["developer_summary"] = ai_data[
                        "developer_summary"
                    ].get("summary")
                if "reviewer_summary" in ai_data:
                    ai_summaries["reviewer_summary"] = ai_data["reviewer_summary"].get(
                        "summary"
                    )
                if "technical_writer_summary" in ai_data:
                    ai_summaries["technical_writer_summary"] = ai_data[
                        "technical_writer_summary"
                    ].get("summary")

            # Extract metrics
            metrics = {}
            if "code_changes" in formatted_pr:
                code_data = formatted_pr["code_changes"]
                if "change_stats" in code_data:
                    stats = code_data["change_stats"]
                    metrics["additions"] = stats.get("total_additions", 0)
                    metrics["deletions"] = stats.get("total_deletions", 0)
                    metrics["files_changed"] = stats.get("changed_files", 0)
                if "risk_assessment" in code_data:
                    metrics["risk_level"] = code_data["risk_assessment"].get(
                        "risk_level", "Unknown"
                    )

            pr_info = {
                "number": pr_number,
                "title": metadata.get("label_analysis", {}).get("title", "No title"),
                "url": pr_url,
                "ai_summaries": ai_summaries,
                "metrics": metrics,
            }

            groups[tag].append(pr_info)

        # Sort PRs in each group by number
        for tag in groups:
            groups[tag].sort(
                key=lambda x: int(x["number"]) if str(x["number"]).isdigit() else 0
            )

        return groups

    def _determine_pr_tag(self, metadata: dict[str, Any]) -> str:
        """Determine PR tag based on labels."""
        label_analysis = metadata.get("label_analysis", {})
        all_labels = []

        # Collect all labels from categorized and uncategorized
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

    def get_file_extension(self) -> str:
        """Return markdown file extension."""
        return ".md"

    def validate_data(self, data: dict[str, Any]) -> bool:
        """
        Validate that the data can be formatted.

        Args:
            data: PR analysis results dictionary

        Returns:
            True if data is valid for formatting
        """
        # Basic validation - ensure it's a dictionary
        return isinstance(data, dict)
