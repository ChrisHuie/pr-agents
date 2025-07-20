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
        # Check if this is batch results
        if "pr_results" in data and "batch_summary" in data:
            return self._format_batch_results(data)

        # Single PR analysis
        lines = []

        # Always add header
        lines.append("# PR Analysis Report")

        # Add PR URL if available
        if "pr_url" in data:
            lines.append(f"\n**Pull Request:** {data['pr_url']}")

        if "pr_number" in data:
            lines.append(f"**PR Number:** #{data['pr_number']}")

        # Repository info
        if "repository" in data:
            repo_info = data["repository"]
            if isinstance(repo_info, dict):
                lines.append(f"**Repository:** {repo_info.get('full_name', 'Unknown')}")
            else:
                lines.append(f"**Repository:** {repo_info}")

        # Release info (if available)
        if "release_version" in data:
            lines.append(f"**Release:** {data['release_version']}")
        else:
            lines.append("**Release:** Unreleased")

        lines.append("")  # Empty line

        # Modules Section
        if "modules" in data:
            lines.extend(self._format_modules(data["modules"]))

        # Files Changed and Statistics
        if "code_changes" in data:
            lines.extend(self._format_simplified_code_changes(data["code_changes"]))

        # Labels
        if "metadata" in data:
            lines.extend(self._format_labels_only(data["metadata"]))

        # AI Summaries Section (All Personas)
        if "ai_summaries" in data:
            lines.extend(self._format_ai_summaries(data["ai_summaries"]))

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

    def _format_modules(self, modules_data: dict[str, Any]) -> list[str]:
        """Format modules section."""
        lines = ["## 📦 Modules Analysis", ""]

        # Handle the case where modules_data might be the processed result
        if "modules" in modules_data:
            modules = modules_data["modules"]
            if isinstance(modules, list) and modules:
                lines.append(f"### Modules Found ({len(modules)})")
                for module in modules:
                    if isinstance(module, dict):
                        name = module.get("name", "Unknown")
                        mod_type = module.get("type", "unknown")
                        action = module.get("action", "")

                        # Format based on available info
                        if action and action != "modified":
                            lines.append(f"- **{name}** ({mod_type}) - {action}")
                        else:
                            lines.append(f"- **{name}** ({mod_type})")
                    else:
                        lines.append(f"- {module}")
                lines.append("")

        # Show total modules if available
        if "total_modules" in modules_data:
            lines.append(f"**Total Modules:** {modules_data['total_modules']}")

        # Show repository type if available
        if "repository_type" in modules_data:
            lines.append(f"**Repository Type:** {modules_data['repository_type']}")

        # Show primary module type
        if "primary_type" in modules_data:
            lines.append(f"**Primary Module Type:** {modules_data['primary_type']}")

        # Show changes summary if available
        if "changes_summary" in modules_data:
            lines.append(f"**Summary:** {modules_data['changes_summary']}")

        # Show adapter changes for JS repos
        if "adapter_changes" in modules_data:
            lines.append("")
            lines.append("### Adapter Changes")
            for adapter_type, count in modules_data["adapter_changes"].items():
                lines.append(f"- {adapter_type.replace('_', ' ').title()}: {count}")

        # Show new adapters if any
        if "new_adapters" in modules_data:
            lines.append("")
            lines.append("### New Adapters")
            for adapter in modules_data["new_adapters"]:
                lines.append(f"- **{adapter['name']}** ({adapter['type']})")

        # Show important modules if any
        if "important_modules" in modules_data:
            lines.append("")
            lines.append("### Important Module Changes")
            for module in modules_data["important_modules"]:
                lines.append(f"- {module}")

        # Show bidder changes for server repos
        if "bidder_changes" in modules_data:
            lines.append("")
            lines.append("### Bidder Changes")
            for bidder in modules_data["bidder_changes"]:
                lines.append(f"- **{bidder['name']}** - {bidder['action']}")

        # Show component changes for mobile repos
        if "component_changes" in modules_data:
            lines.append("")
            lines.append("### Component Changes")
            for component, count in modules_data["component_changes"].items():
                if count > 0:
                    lines.append(f"- {component.title()}: {count}")

        lines.append("")
        return lines

    def _format_ai_summaries(self, ai_summaries: dict[str, Any]) -> list[str]:
        """Format AI-generated summaries section."""
        lines = ["## 🤖 AI-Generated Summaries", ""]

        # Executive Summary
        if "executive_summary" in ai_summaries:
            exec_summary = ai_summaries["executive_summary"]
            summary_text = exec_summary.get("summary", "No summary available")
            if summary_text != "[Not requested]":
                lines.append("### Executive Summary")
                lines.append(f"{summary_text}")
                lines.append("")

        # Product Manager Summary
        if "product_summary" in ai_summaries:
            product_summary = ai_summaries["product_summary"]
            summary_text = product_summary.get("summary", "No summary available")
            if summary_text != "[Not requested]":
                lines.append("### Product Manager Summary")
                lines.append(f"{summary_text}")
                lines.append("")

        # Developer Summary
        if "developer_summary" in ai_summaries:
            dev_summary = ai_summaries["developer_summary"]
            summary_text = dev_summary.get("summary", "No summary available")
            if summary_text != "[Not requested]":
                lines.append("### Technical Developer Summary")
                lines.append(f"{summary_text}")
                lines.append("")

        # Code Review
        if "reviewer_summary" in ai_summaries:
            reviewer_summary = ai_summaries["reviewer_summary"]
            summary_text = reviewer_summary.get("summary", "No summary available")
            if summary_text != "[Not requested]":
                lines.append("### Code Review")
                lines.append(f"{summary_text}")
                lines.append("")

        # Summary Metadata
        lines.append("### Summary Generation Details")
        lines.append(f"- **Model Used:** {ai_summaries.get('model_used', 'Unknown')}")
        lines.append(
            f"- **Generated At:** {ai_summaries.get('generation_timestamp', 'Unknown')}"
        )
        lines.append(
            f"- **From Cache:** {'Yes' if ai_summaries.get('cached', False) else 'No'}"
        )

        if "total_tokens" in ai_summaries and ai_summaries["total_tokens"] > 0:
            lines.append(f"- **Total Tokens:** {ai_summaries['total_tokens']}")

        if "generation_time_ms" in ai_summaries:
            lines.append(
                f"- **Generation Time:** {ai_summaries['generation_time_ms']}ms"
            )

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

    def _format_simplified_code_changes(
        self, code_changes: dict[str, Any]
    ) -> list[str]:
        """Format simplified code changes section with only files and statistics."""
        lines = ["## 💻 Files Changed", ""]

        # Get file count and stats
        stats = code_changes.get("change_stats", {})
        file_count = stats.get("changed_files", 0)

        # Change Statistics
        if stats:
            lines.append("### Change Statistics")
            lines.append(f"- **Total Changes:** {stats.get('total_changes', 0)} lines")
            lines.append(f"- **Additions:** +{stats.get('total_additions', 0)}")
            lines.append(f"- **Deletions:** -{stats.get('total_deletions', 0)}")
            lines.append(f"- **Files Changed:** {file_count}")
            lines.append("")

        # List of files changed
        if "file_analysis" in code_changes:
            file_analysis = code_changes["file_analysis"]

            # Show actual files if available
            if "changed_files" in file_analysis and file_analysis["changed_files"]:
                lines.append("### Files")
                for file_path in file_analysis["changed_files"]:
                    lines.append(f"- `{file_path}`")
                lines.append("")

            # File Type Breakdown
            if "file_types" in file_analysis and file_analysis["file_types"]:
                lines.append("### File Types")
                for file_type, count in file_analysis["file_types"].items():
                    lines.append(
                        f"- **{file_type}:** {count} file{'s' if count > 1 else ''}"
                    )
                lines.append("")

        return lines

    def _format_labels_only(self, metadata: dict[str, Any]) -> list[str]:
        """Format labels section without quality metrics."""
        lines = []

        # Label Analysis
        if "label_analysis" in metadata:
            labels = metadata["label_analysis"]
            lines.append(f"## 🏷️ Labels ({labels.get('total_count', 0)})")

            if categorized := labels.get("categorized", {}):
                for category, label_list in categorized.items():
                    if label_list:
                        lines.append(f"- **{category}:** {', '.join(label_list)}")

            if uncategorized := labels.get("uncategorized", []):
                lines.append(f"- **Other:** {', '.join(uncategorized)}")

            lines.append("")

        return lines

    def get_file_extension(self) -> str:
        """Return markdown file extension."""
        return ".md"

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

                # Extract key information
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
                f"**Title Quality:** {quality.get('quality_level', 'Unknown')} ({quality.get('score', 0)}/100)"
            )

        if "description_quality" in metadata:
            quality = metadata["description_quality"]
            lines.append(
                f"**Description Quality:** {quality.get('quality_level', 'Unknown')} ({quality.get('score', 0)}/100)"
            )

        return lines

    def _format_pr_summary_code(self, code_changes: dict[str, Any]) -> list[str]:
        """Format PR code changes summary for batch report."""
        lines = []

        if "change_stats" in code_changes:
            stats = code_changes["change_stats"]
            lines.append(
                f"**Changes:** {stats.get('changed_files', 0)} files, +{stats.get('total_additions', 0)}/-{stats.get('total_deletions', 0)}"
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
