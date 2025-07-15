"""
Markdown formatter for PR analysis output.
"""

from typing import Any

from .base import BaseFormatter


class MarkdownFormatter(BaseFormatter):
    """Formats PR analysis results as Markdown."""

    def format(self, data: dict[str, Any]) -> str:
        """
        Format PR analysis data as Markdown.

        Args:
            data: PR analysis results dictionary

        Returns:
            Markdown formatted string
        """
        lines = []

        # Always add header
        lines.append("# PR Analysis Report")

        # Add PR URL if available
        if "pr_url" in data:
            lines.append(f"\n**Pull Request:** {data['pr_url']}")

        if "pr_number" in data:
            lines.append(f"**PR Number:** #{data['pr_number']}")

        if "repository" in data:
            lines.append(f"**Repository:** {data['repository']}")

        lines.append("")  # Empty line

        # Metadata Section
        if "metadata" in data:
            lines.extend(self._format_metadata(data["metadata"]))

        # Code Changes Section
        if "code_changes" in data:
            lines.extend(self._format_code_changes(data["code_changes"]))

        # Repository Info Section
        if "repository_info" in data:
            lines.extend(self._format_repository_info(data["repository_info"]))

        # Reviews Section
        if "reviews" in data:
            lines.extend(self._format_reviews(data["reviews"]))

        # Processing Metrics
        if "processing_metrics" in data:
            lines.extend(self._format_processing_metrics(data["processing_metrics"]))

        return "\n".join(lines)

    def _format_metadata(self, metadata: dict[str, Any]) -> list[str]:
        """Format metadata section."""
        lines = ["## 📋 Metadata Analysis", ""]

        # Title and Description Quality
        if "title_quality" in metadata:
            quality = metadata["title_quality"]
            lines.append(
                f"### Title Quality: {quality.get('quality_level', 'Unknown')} ({quality.get('score', 0)}/100)"
            )
            if issues := quality.get("issues", []):
                lines.append("**Issues:**")
                for issue in issues:
                    lines.append(f"- {issue}")
            lines.append("")

        if "description_quality" in metadata:
            quality = metadata["description_quality"]
            lines.append(
                f"### Description Quality: {quality.get('quality_level', 'Unknown')} ({quality.get('score', 0)}/100)"
            )
            if issues := quality.get("issues", []):
                lines.append("**Issues:**")
                for issue in issues:
                    lines.append(f"- {issue}")
            lines.append("")

        # Label Analysis
        if "label_analysis" in metadata:
            labels = metadata["label_analysis"]
            lines.append(f"### Labels ({labels.get('total_count', 0)})")

            if categorized := labels.get("categorized", {}):
                for category, label_list in categorized.items():
                    if label_list:
                        lines.append(f"- **{category}:** {', '.join(label_list)}")

            if uncategorized := labels.get("uncategorized", []):
                lines.append(f"- **Other:** {', '.join(uncategorized)}")

            lines.append("")

        return lines

    def _format_code_changes(self, code_changes: dict[str, Any]) -> list[str]:
        """Format code changes section."""
        lines = ["## 💻 Code Changes Analysis", ""]

        # Change Statistics
        if "change_stats" in code_changes:
            stats = code_changes["change_stats"]
            lines.append("### Change Statistics")
            lines.append(f"- **Total Changes:** {stats.get('total_changes', 0)} lines")
            lines.append(f"- **Additions:** +{stats.get('total_additions', 0)}")
            lines.append(f"- **Deletions:** -{stats.get('total_deletions', 0)}")
            lines.append(f"- **Files Changed:** {stats.get('changed_files', 0)}")
            lines.append("")

        # Risk Assessment
        if "risk_assessment" in code_changes:
            risk = code_changes["risk_assessment"]
            lines.append(f"### Risk Level: {risk.get('risk_level', 'Unknown')}")
            lines.append(f"**Risk Score:** {risk.get('risk_score', 0)} points")

            if factors := risk.get("risk_factors", []):
                lines.append("**Risk Factors:**")
                for factor in factors:
                    lines.append(f"- {factor}")
            lines.append("")

        # Pattern Analysis
        if "pattern_analysis" in code_changes:
            patterns = code_changes["pattern_analysis"]
            if detected := patterns.get("detected_patterns", []):
                lines.append("### Detected Patterns")
                for pattern in detected:
                    lines.append(f"- {pattern}")
                lines.append("")

        return lines

    def _format_repository_info(self, repo_info: dict[str, Any]) -> list[str]:
        """Format repository information section."""
        lines = ["## 🏗️ Repository Analysis", ""]

        # Repository Health
        if "health_assessment" in repo_info:
            health = repo_info["health_assessment"]
            lines.append(
                f"### Repository Health: {health.get('health_level', 'Unknown')} ({health.get('health_score', 0)}/70)"
            )

            if components := health.get("health_components", {}):
                lines.append("**Health Components:**")
                for component, score in components.items():
                    lines.append(
                        f"- {component.replace('_', ' ').title()}: {score} points"
                    )
            lines.append("")

        # Language Analysis
        if "language_analysis" in repo_info:
            languages = repo_info["language_analysis"]
            if primary := languages.get("primary_language"):
                lines.append(f"### Primary Language: {primary}")

            if all_langs := languages.get("languages", {}):
                lines.append("**All Languages:**")
                for lang, percentage in sorted(
                    all_langs.items(), key=lambda x: x[1], reverse=True
                ):
                    lines.append(f"- {lang}: {percentage:.1f}%")
                lines.append("")

        return lines

    def _format_reviews(self, reviews: dict[str, Any]) -> list[str]:
        """Format reviews section."""
        lines = ["## 👥 Review Analysis", ""]

        # Review Summary
        if "review_summary" in reviews:
            summary = reviews["review_summary"]
            lines.append("### Review Summary")
            lines.append(f"- **Total Reviews:** {summary.get('total_reviews', 0)}")
            lines.append(
                f"- **Unique Reviewers:** {summary.get('unique_reviewers', 0)}"
            )
            lines.append(f"- **Total Comments:** {summary.get('total_comments', 0)}")

            if approval := summary.get("approval_status"):
                lines.append(f"- **Approval Status:** {approval}")
            lines.append("")

        # Review Timeline
        if "review_timeline" in reviews:
            timeline = reviews["review_timeline"]
            if avg_time := timeline.get("average_response_time"):
                lines.append(f"### Average Response Time: {avg_time}")

            if first_review := timeline.get("first_review_time"):
                lines.append(f"- **First Review:** {first_review}")

            lines.append("")

        return lines

    def _format_processing_metrics(self, metrics: dict[str, Any]) -> list[str]:
        """Format processing metrics section."""
        lines = ["## ⚡ Processing Metrics", ""]

        if "total_duration" in metrics:
            lines.append(f"**Total Processing Time:** {metrics['total_duration']:.2f}s")

        if "component_durations" in metrics:
            lines.append("**Component Processing Times:**")
            for component, duration in metrics["component_durations"].items():
                lines.append(f"- {component}: {duration:.3f}s")

        lines.append("")
        return lines

    def get_file_extension(self) -> str:
        """Return markdown file extension."""
        return ".md"
