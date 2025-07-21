"""
Enhanced markdown formatter for grouped release output.
"""

from pathlib import Path
from typing import Any

from .markdown import MarkdownFormatter


class GroupedReleaseFormatter(MarkdownFormatter):
    """
    Formats release analysis results with PR grouping by tags.

    Creates a main summary file and individual PR files with enhanced structure.
    """

    def __init__(self, output_dir: Path | str | None = None):
        """
        Initialize formatter with output directory.

        Args:
            output_dir: Directory to save individual PR files
        """
        super().__init__()
        self.output_dir = Path(output_dir) if output_dir else None

    def format(self, data: dict[str, Any]) -> str:
        """
        Format release data with grouped structure.

        Args:
            data: Release analysis results

        Returns:
            Main release summary content
        """
        # Check if this is release data
        if not self._is_release_data(data):
            # Fall back to parent formatter for non-release data
            return super().format(data)

        # Create output directory if specified
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

        # Group PRs by tag
        pr_groups = self._group_prs_by_tag(data.get("pr_results", []))

        # Create individual PR files if output_dir is set
        if self.output_dir:
            self._create_individual_pr_files(data.get("pr_results", []))

        # Create main summary
        return self._create_release_summary(data, pr_groups)

    def _is_release_data(self, data: dict[str, Any]) -> bool:
        """Check if data is from release analysis."""
        return (
            "release_tag" in data
            or "release_version" in data
            or ("batch_summary" in data and "pr_results" in data)
        )

    def _get_pr_tag(self, pr_data: dict[str, Any]) -> str:
        """
        Determine PR tag based on labels.

        Returns one of: Feature, Bug Fix, or Maintenance
        """
        labels = pr_data.get("labels", [])
        if not labels:
            return "Maintenance"

        label_names = [label["name"].lower() for label in labels]

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

        return "Maintenance"

    def _group_prs_by_tag(self, pr_results: list[dict]) -> dict[str, list]:
        """Group PRs by their tags."""
        groups = {"Feature": [], "Bug Fix": [], "Maintenance": []}

        for pr_result in pr_results:
            if pr_result.get("success"):
                pr_data = pr_result.get("pr_data", {})
                tag = self._get_pr_tag(pr_data)

                pr_info = {
                    "number": pr_data.get("number", "unknown"),
                    "title": pr_data.get("title", "No title"),
                    "url": pr_data.get("url", ""),
                    "file": (
                        f"pr_{pr_data.get('number', 'unknown')}.md"
                        if self.output_dir
                        else None
                    ),
                }

                groups[tag].append(pr_info)

        return groups

    def _create_individual_pr_files(self, pr_results: list[dict]) -> None:
        """Create individual markdown files for each PR."""
        if not self.output_dir:
            return

        for pr_result in pr_results:
            if pr_result.get("success"):
                pr_data = pr_result.get("pr_data", {})
                pr_number = pr_data.get("number", "unknown")

                content = self._format_individual_pr(pr_result)

                pr_file = self.output_dir / f"pr_{pr_number}.md"
                pr_file.write_text(content)

    def _format_individual_pr(self, pr_result: dict) -> str:
        """Format individual PR with all personas and details."""
        pr_data = pr_result.get("pr_data", {})
        lines = []

        # Header
        lines.append(
            f"# PR #{pr_data.get('number', 'unknown')}: {pr_data.get('title', 'No title')}"
        )
        lines.append("")

        # Basic info
        lines.append(f"**URL**: {pr_data.get('url', 'N/A')}")
        lines.append(f"**Author**: {pr_data.get('author', 'Unknown')}")
        lines.append(f"**Created**: {pr_data.get('created_at', 'Unknown')}")
        lines.append(f"**Merged**: {pr_data.get('merged_at', 'Not merged')}")
        lines.append(f"**State**: {pr_data.get('state', 'Unknown')}")
        lines.append("")

        # AI Summaries with all 4 personas
        lines.append("## AI Summaries")
        lines.append("")

        ai_summaries = self._extract_ai_summaries(pr_result)

        personas = [
            ("Executive", "executive_summary"),
            ("Product Manager", "product_summary"),
            ("Developer", "developer_summary"),
            ("Technical Writer", "technical_writer_summary"),
        ]

        for persona_name, persona_key in personas:
            lines.append(f"### {persona_name} Summary")

            if ai_summaries and persona_key in ai_summaries:
                lines.append(ai_summaries[persona_key])
            else:
                if persona_key == "technical_writer_summary":
                    lines.append(
                        "*Technical documentation summary not available - this persona may need to be configured*"
                    )
                else:
                    lines.append("*No summary available*")
            lines.append("")

        # Tool Metrics
        lines.append("## Tool Metrics")
        lines.append("")

        metrics = pr_result.get("metrics", {})
        if metrics:
            lines.append(
                f"- **Extraction Time**: {metrics.get('extraction_time', 'N/A')}s"
            )
            lines.append(
                f"- **Processing Time**: {metrics.get('processing_time', 'N/A')}s"
            )
            lines.append(f"- **Total Time**: {metrics.get('total_time', 'N/A')}s")
            lines.append(
                f"- **Components Extracted**: {metrics.get('components_extracted', 'N/A')}"
            )
            lines.append(
                f"- **Processors Run**: {metrics.get('processors_run', 'N/A')}"
            )
        else:
            lines.append("*No metrics available*")
        lines.append("")

        # PR Details section
        lines.append("## PR Details")
        lines.append("")

        # Extract and format other components
        processing_results = pr_result.get("processing_results", [])

        # Metadata
        for result in processing_results:
            if result.get("component") == "metadata" and result.get("success"):
                lines.extend(self._format_pr_metadata(result.get("data", {})))
                break

        # Code changes
        for result in processing_results:
            if result.get("component") == "code_changes" and result.get("success"):
                lines.extend(self._format_pr_code_changes(result.get("data", {})))
                break

        # Reviews
        for result in processing_results:
            if result.get("component") == "reviews" and result.get("success"):
                lines.extend(self._format_pr_reviews(result.get("data", {})))
                break

        # Labels
        if pr_data.get("labels"):
            lines.append("### Labels")
            for label in pr_data["labels"]:
                lines.append(f"- {label['name']}")
            lines.append("")

        return "\n".join(lines)

    def _extract_ai_summaries(self, pr_result: dict) -> dict[str, str] | None:
        """Extract AI summaries from processing results."""
        for result in pr_result.get("processing_results", []):
            if result.get("component") == "ai_summaries" and result.get("success"):
                return result.get("data", {})
        return None

    def _format_pr_metadata(self, metadata: dict) -> list[str]:
        """Format PR metadata section."""
        lines = ["### Metadata"]
        lines.append(f"- **Title Quality**: {metadata.get('title_quality', 'N/A')}")
        lines.append(
            f"- **Description Quality**: {metadata.get('description_quality', 'N/A')}"
        )
        lines.append(f"- **Has Tests**: {metadata.get('has_tests', 'Unknown')}")
        lines.append(
            f"- **Has Documentation**: {metadata.get('has_documentation', 'Unknown')}"
        )
        lines.append("")
        return lines

    def _format_pr_code_changes(self, code_data: dict) -> list[str]:
        """Format PR code changes section."""
        lines = ["### Code Changes"]
        lines.append(f"- **Files Changed**: {code_data.get('files_changed', 0)}")
        lines.append(f"- **Lines Added**: {code_data.get('additions', 0)}")
        lines.append(f"- **Lines Deleted**: {code_data.get('deletions', 0)}")
        lines.append(f"- **Risk Level**: {code_data.get('risk_level', 'Unknown')}")

        file_types = code_data.get("file_types", {})
        if file_types:
            lines.append(f"- **File Types**: {', '.join(file_types.keys())}")

        lines.append("")
        return lines

    def _format_pr_reviews(self, review_data: dict) -> list[str]:
        """Format PR reviews section."""
        lines = ["### Reviews"]
        lines.append(f"- **Total Reviews**: {review_data.get('review_count', 0)}")
        lines.append(f"- **Approved**: {review_data.get('approved_count', 0)}")
        lines.append(
            f"- **Changes Requested**: {review_data.get('changes_requested_count', 0)}"
        )
        lines.append(f"- **Comments**: {review_data.get('comment_count', 0)}")
        lines.append("")
        return lines

    def _create_release_summary(self, data: dict, pr_groups: dict) -> str:
        """Create main release summary content."""
        lines = []

        # Header
        release_tag = data.get("release_tag", data.get("release_version", "Unknown"))
        lines.append(f"# Release {release_tag} Summary")
        lines.append("")

        # Basic info
        lines.append(f"**Repository**: {data.get('repository', 'Unknown')}")

        # Extract release date if available
        if "release_date" in data:
            lines.append(f"**Release Date**: {data['release_date']}")

        # PR count
        batch_summary = data.get("batch_summary", {})
        lines.append(f"**Total PRs**: {batch_summary.get('total_prs', 0)}")
        lines.append("")

        # PRs grouped by tag
        for tag in ["Feature", "Bug Fix", "Maintenance"]:
            prs = pr_groups.get(tag, [])
            if prs:
                lines.append(f"## {tag}")
                lines.append("")

                # Sort PRs by number
                sorted_prs = sorted(
                    prs,
                    key=lambda x: int(x["number"]) if str(x["number"]).isdigit() else 0,
                )

                for pr in sorted_prs:
                    if pr.get("file") and self.output_dir:
                        # Link to individual file
                        lines.append(
                            f"- [#{pr['number']}]({pr['file']}): {pr['title']}"
                        )
                    else:
                        # Just show PR info
                        lines.append(f"- #{pr['number']}: {pr['title']}")

                lines.append("")

        # Summary statistics
        lines.append("## Summary Statistics")
        lines.append("")
        lines.append(f"- **Total PRs Analyzed**: {batch_summary.get('total_prs', 0)}")
        lines.append(
            f"- **Successful Analyses**: {batch_summary.get('successful_analyses', 0)}"
        )
        lines.append(
            f"- **Failed Analyses**: {batch_summary.get('failed_analyses', 0)}"
        )
        lines.append("")

        # Breakdown by category
        lines.append("### Breakdown by Category")
        total_prs = batch_summary.get("total_prs", 0)
        for tag in ["Feature", "Bug Fix", "Maintenance"]:
            count = len(pr_groups.get(tag, []))
            percentage = (count / total_prs * 100) if total_prs > 0 else 0
            lines.append(f"- **{tag}**: {count} PRs ({percentage:.1f}%)")

        lines.append("")

        # Failed analyses if any
        if batch_summary.get("failed_analyses", 0) > 0:
            lines.append("### Failed PR Analysis")

            for pr_result in data.get("pr_results", []):
                if not pr_result.get("success"):
                    pr_data = pr_result.get("pr_data", {})
                    pr_num = pr_data.get("number", "unknown")
                    error = pr_result.get("error", "Unknown error")
                    lines.append(f"- PR #{pr_num}: {error}")

            lines.append("")

        return "\n".join(lines)
