"""Individual section formatters for modular output."""

from typing import Any

from .base import SectionFormatter


class HeaderSection(SectionFormatter):
    """Formats the header section of a PR analysis."""

    def format(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> list[str]:
        """Format header section."""
        lines = []

        # Determine header based on data type
        if "pr_results" in data and "batch_summary" in data:
            if data.get("release_tag") or data.get("release_version"):
                release_tag = data.get(
                    "release_tag", data.get("release_version", "Unknown")
                )
                lines.append(f"# Release {release_tag} Summary")
            else:
                lines.append("# Batch PR Analysis Report")
        else:
            lines.append("# PR Analysis Report")

        lines.append("")

        # Add basic info
        if "pr_url" in data:
            lines.append(f"**Pull Request:** {data['pr_url']}")

        if "pr_number" in data:
            lines.append(f"**PR Number:** #{data['pr_number']}")

        if "repository" in data:
            repo_info = data["repository"]
            if isinstance(repo_info, dict):
                lines.append(f"**Repository:** {repo_info.get('full_name', 'Unknown')}")
            else:
                lines.append(f"**Repository:** {repo_info}")

        if "release_version" in data:
            lines.append(f"**Release:** {data['release_version']}")
        elif "release_tag" in data:
            lines.append(f"**Release:** {data['release_tag']}")
        else:
            lines.append("**Release:** Unreleased")

        lines.append("")
        return lines

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Always show header."""
        return True

    def get_priority(self) -> int:
        """Header always comes first."""
        return 0


class AISection(SectionFormatter):
    """Formats AI-generated summaries."""

    def format(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> list[str]:
        """Format AI summaries section."""
        options = options or {}
        personas_filter = options.get("personas")

        if "ai_summaries" not in data:
            return []

        lines = ["## 🤖 AI-Generated Summaries", ""]
        ai_summaries = data["ai_summaries"]

        personas = [
            ("executive_summary", "Executive Summary"),
            ("product_summary", "Product Manager Summary"),
            ("developer_summary", "Technical Developer Summary"),
            ("reviewer_summary", "Code Review"),
            ("technical_writer_summary", "Technical Writer Summary"),
        ]

        for persona_key, persona_title in personas:
            # Skip if filtering personas
            if (
                personas_filter
                and persona_key.replace("_summary", "") not in personas_filter
            ):
                continue

            if persona_key in ai_summaries:
                summary_data = ai_summaries[persona_key]
                if summary_data is None:
                    summary_text = "Error generating summary"
                else:
                    summary_text = summary_data.get("summary", "No summary available")

                if summary_text != "[Not requested]":
                    lines.append(f"### {persona_title}")
                    lines.append(summary_text)
                    lines.append("")

        # Add metadata if not in compact mode
        if not options.get("compact", False):
            lines.append("### Summary Generation Details")
            lines.append(
                f"- **Model Used:** {ai_summaries.get('model_used', 'Unknown')}"
            )
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

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if AI summaries are present."""
        return "ai_summaries" in data

    def get_priority(self) -> int:
        """AI summaries come early."""
        return 10


class ModulesSection(SectionFormatter):
    """Formats modules analysis section."""

    def format(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> list[str]:
        """Format modules section."""
        if "modules" not in data:
            return []

        lines = ["## 📦 Modules Analysis", ""]
        modules_data = data["modules"]

        # Handle modules list
        if "modules" in modules_data:
            modules = modules_data["modules"]
            if isinstance(modules, list) and modules:
                lines.append(f"### Modules Found ({len(modules)})")
                for module in modules:
                    if isinstance(module, dict):
                        name = module.get("name", "Unknown")
                        mod_type = module.get("type", "unknown")
                        action = module.get("action", "")

                        if action and action != "modified":
                            lines.append(f"- **{name}** ({mod_type}) - {action}")
                        else:
                            lines.append(f"- **{name}** ({mod_type})")
                    else:
                        lines.append(f"- {module}")
                lines.append("")

        # Show summary info
        if "total_modules" in modules_data:
            lines.append(f"**Total Modules:** {modules_data['total_modules']}")

        if "repository_type" in modules_data:
            lines.append(f"**Repository Type:** {modules_data['repository_type']}")

        if "primary_type" in modules_data:
            lines.append(f"**Primary Module Type:** {modules_data['primary_type']}")

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

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if modules data is present."""
        return "modules" in data

    def get_priority(self) -> int:
        """Modules come after header."""
        return 20


class CodeChangesSection(SectionFormatter):
    """Formats code changes section."""

    def format(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> list[str]:
        """Format code changes section."""
        if "code_changes" not in data:
            return []

        options = options or {}
        compact = options.get("compact", False)

        lines = ["## 💻 Files Changed", ""]
        code_changes = data["code_changes"]

        # Change Statistics
        if "change_stats" in code_changes:
            stats = code_changes["change_stats"]
            lines.append("### Change Statistics")
            lines.append(f"- **Total Changes:** {stats.get('total_changes', 0)} lines")
            lines.append(f"- **Additions:** +{stats.get('total_additions', 0)}")
            lines.append(f"- **Deletions:** -{stats.get('total_deletions', 0)}")
            lines.append(f"- **Files Changed:** {stats.get('changed_files', 0)}")
            lines.append("")

        # Risk Assessment (if not compact)
        if not compact and "risk_assessment" in code_changes:
            risk = code_changes["risk_assessment"]
            lines.append(f"### Risk Level: {risk.get('risk_level', 'Unknown')}")
            lines.append(f"**Risk Score:** {risk.get('risk_score', 0)} points")

            if factors := risk.get("risk_factors", []):
                lines.append("**Risk Factors:**")
                for factor in factors:
                    lines.append(f"- {factor}")
            lines.append("")

        # File list (if not compact)
        if not compact and "file_analysis" in code_changes:
            file_analysis = code_changes["file_analysis"]

            if "changed_files" in file_analysis and file_analysis["changed_files"]:
                lines.append("### Files")
                for file_path in file_analysis["changed_files"]:
                    lines.append(f"- `{file_path}`")
                lines.append("")

            if "file_types" in file_analysis and file_analysis["file_types"]:
                lines.append("### File Types")
                for file_type, count in file_analysis["file_types"].items():
                    lines.append(
                        f"- **{file_type}:** {count} file{'s' if count > 1 else ''}"
                    )
                lines.append("")

        return lines

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if code changes data is present."""
        return "code_changes" in data

    def get_priority(self) -> int:
        """Code changes come after modules."""
        return 30


class LabelsSection(SectionFormatter):
    """Formats labels section."""

    def format(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> list[str]:
        """Format labels section."""
        if "metadata" not in data or "label_analysis" not in data["metadata"]:
            return []

        lines = []
        labels = data["metadata"]["label_analysis"]

        lines.append(f"## 🏷️ Labels ({labels.get('total_count', 0)})")

        if categorized := labels.get("categorized", {}):
            for category, label_list in categorized.items():
                if label_list:
                    lines.append(f"- **{category}:** {', '.join(label_list)}")

        if uncategorized := labels.get("uncategorized", []):
            lines.append(f"- **Other:** {', '.join(uncategorized)}")

        lines.append("")
        return lines

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if label data is present."""
        return "metadata" in data and "label_analysis" in data.get("metadata", {})

    def get_priority(self) -> int:
        """Labels come after code changes."""
        return 40


class MetadataSection(SectionFormatter):
    """Formats metadata quality section."""

    def format(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> list[str]:
        """Format metadata section."""
        if "metadata" not in data:
            return []

        options = options or {}
        if options.get("compact", False):
            return []  # Skip in compact mode

        lines = ["## 📋 Metadata Analysis", ""]
        metadata = data["metadata"]

        # Title Quality
        if "title_quality" in metadata:
            quality = metadata["title_quality"]
            lines.append(
                f"### Title Quality: {quality.get('quality_level', 'Unknown')} "
                f"({quality.get('score', 0)}/100)"
            )
            if issues := quality.get("issues", []):
                lines.append("**Issues:**")
                for issue in issues:
                    lines.append(f"- {issue}")
            lines.append("")

        # Description Quality
        if "description_quality" in metadata:
            quality = metadata["description_quality"]
            lines.append(
                f"### Description Quality: {quality.get('quality_level', 'Unknown')} "
                f"({quality.get('score', 0)}/100)"
            )
            if issues := quality.get("issues", []):
                lines.append("**Issues:**")
                for issue in issues:
                    lines.append(f"- {issue}")
            lines.append("")

        return lines

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if metadata quality data is present."""
        metadata = data.get("metadata", {})
        return "title_quality" in metadata or "description_quality" in metadata

    def get_priority(self) -> int:
        """Metadata analysis comes later."""
        return 50


class ReviewsSection(SectionFormatter):
    """Formats reviews section."""

    def format(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> list[str]:
        """Format reviews section."""
        if "reviews" not in data:
            return []

        lines = ["## 👥 Review Analysis", ""]
        reviews = data["reviews"]

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

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if reviews data is present."""
        return "reviews" in data

    def get_priority(self) -> int:
        """Reviews come after metadata."""
        return 60


class RepositorySection(SectionFormatter):
    """Formats repository information section."""

    def format(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> list[str]:
        """Format repository section."""
        if "repository_info" not in data:
            return []

        lines = ["## 🏗️ Repository Analysis", ""]
        repo_info = data["repository_info"]

        # Repository Health
        if "health_assessment" in repo_info:
            health = repo_info["health_assessment"]
            lines.append(
                f"### Repository Health: {health.get('health_level', 'Unknown')} "
                f"({health.get('health_score', 0)}/70)"
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

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if repository info is present."""
        return "repository_info" in data

    def get_priority(self) -> int:
        """Repository info comes later."""
        return 70


class MetricsSection(SectionFormatter):
    """Formats processing metrics section."""

    def format(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> list[str]:
        """Format metrics section."""
        if "processing_metrics" not in data:
            return []

        options = options or {}
        if not options.get("include_metrics", True):
            return []

        lines = ["## ⚡ Processing Metrics", ""]
        metrics = data["processing_metrics"]

        if "total_duration" in metrics:
            lines.append(f"**Total Processing Time:** {metrics['total_duration']:.2f}s")

        if "component_durations" in metrics:
            lines.append("**Component Processing Times:**")
            for component, duration in metrics["component_durations"].items():
                lines.append(f"- {component}: {duration:.3f}s")

        lines.append("")
        return lines

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if metrics are present."""
        return "processing_metrics" in data

    def get_priority(self) -> int:
        """Metrics come last."""
        return 100
