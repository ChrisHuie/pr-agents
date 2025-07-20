"""Developer summary agent using Google ADK."""

from google.adk import Agent
from google.adk.tools import BaseTool

from ..base import BaseSummaryAgent
from ..tools import CodeAnalyzerTool, PatternDetectorTool


class DeveloperSummaryAgent(BaseSummaryAgent):
    """Agent specialized in generating developer-focused technical summaries."""

    def get_instructions(self) -> str:
        """Get developer-specific instructions."""
        return """You are a technical summary specialist analyzing code changes for software engineers.

OUTPUT REQUIREMENT:
Provide a comprehensive technical summary (6-10 sentences, more for complex changes) that accurately describes the code changes and their integration with the repository.

FOCUS:
- Specific code changes: functions modified, logic altered, data structures changed
- How changes integrate with existing codebase architecture
- Technical patterns and approaches used
- Impact on system behavior and compatibility
- Test coverage and validation
- Dependencies or configuration changes

For Prebid.js specifically:
- Adapter changes: focus on buildRequests, interpretResponse, getUserSyncs methods
- Core changes: auction logic, bidding pipeline, event handling
- Module patterns: how new code fits into the plugin architecture
- Integration points with Prebid core

Be precise and technical. Reference actual function names, variables, and patterns from the code diffs.

End with:

Modified files:
- path/to/file1.js
- path/to/file2.js"""

    def get_tools(self) -> list[BaseTool]:
        """Get tools for technical analysis."""
        return [CodeAnalyzerTool(), PatternDetectorTool()]

    def create_agent(self) -> Agent:
        """Create the developer summary agent."""
        return Agent(
            name="developer_summary_agent",
            model=self.model,
            instruction=self.get_instructions(),
            description="Generates detailed technical summaries for developers",
            tools=self.get_tools(),
        )

    def _prepare_input(self, code_changes: dict, repo_context: dict) -> str:
        """Prepare developer-focused input with technical details."""
        # Use the base implementation to get the full prompt with patches
        base_prompt = super()._prepare_input(code_changes, repo_context)

        # Add developer-specific focus at the end
        developer_suffix = "\n\nProvide a technical developer summary focusing on implementation details, code patterns, and technical implications."

        return base_prompt + developer_suffix

    def _old_prepare_input(self, code_changes: dict, repo_context: dict) -> str:
        """Old implementation - kept for reference."""
        tech_context = repo_context.get("technical_context", {})
        if tech_context:
            prompt_parts.append("\nTechnical Context:")
            if "architecture" in tech_context:
                prompt_parts.append(f"- Architecture: {tech_context['architecture']}")
            if "key_apis" in tech_context:
                prompt_parts.append(
                    f"- Key APIs: {', '.join(tech_context['key_apis'])}"
                )

        # Detailed code statistics
        prompt_parts.extend(
            [
                "\nCode Change Metrics:",
                f"- Total Files: {code_changes.get('changed_files', 0)}",
                f"- Lines Added: {code_changes.get('total_additions', 0)}",
                f"- Lines Deleted: {code_changes.get('total_deletions', 0)}",
                f"- Net Change: {code_changes.get('total_additions', 0) - code_changes.get('total_deletions', 0)}",
            ]
        )

        # Analyze file patterns
        file_diffs = code_changes.get("file_diffs", [])

        # Categorize files by type
        js_files = [d for d in file_diffs if d.get("filename", "").endswith(".js")]
        test_files = [d for d in file_diffs if "test" in d.get("filename", "").lower()]
        config_files = [
            d
            for d in file_diffs
            if any(ext in d.get("filename", "") for ext in [".json", ".yaml", ".yml"])
        ]
        doc_files = [
            d for d in file_diffs if d.get("filename", "").endswith((".md", ".rst"))
        ]

        prompt_parts.append("\nFile Categories:")
        if js_files:
            prompt_parts.append(f"- JavaScript files: {len(js_files)}")
        if test_files:
            prompt_parts.append(f"- Test files: {len(test_files)}")
        if config_files:
            prompt_parts.append(f"- Configuration files: {len(config_files)}")
        if doc_files:
            prompt_parts.append(f"- Documentation files: {len(doc_files)}")

        # Detailed file changes
        prompt_parts.append("\nDetailed File Changes:")

        # Group by directory
        by_directory = {}
        for diff in file_diffs:
            filepath = diff.get("filename", "")
            directory = (
                "/".join(filepath.split("/")[:-1]) if "/" in filepath else "root"
            )

            if directory not in by_directory:
                by_directory[directory] = []
            by_directory[directory].append(diff)

        # Show top directories with changes
        for directory, diffs in sorted(by_directory.items())[:5]:
            total_changes = sum(
                d.get("additions", 0) + d.get("deletions", 0) for d in diffs
            )
            prompt_parts.append(f"\n{directory}/:")
            for diff in diffs[:3]:  # First 3 files per directory
                prompt_parts.append(
                    f"  - {diff['filename'].split('/')[-1]} "
                    f"(+{diff.get('additions', 0)}, -{diff.get('deletions', 0)})"
                )
            if len(diffs) > 3:
                prompt_parts.append(f"  - ... and {len(diffs) - 3} more files")

        # Add detected patterns from context
        if "file_analysis" in repo_context:
            analysis = repo_context["file_analysis"]
            if analysis.get("detected_modules"):
                prompt_parts.append(
                    f"\nDetected Module Types: {', '.join(analysis['detected_modules'])}"
                )
            if analysis.get("has_tests"):
                prompt_parts.append("- Test coverage included")

        # Code complexity indicators
        total_changes = code_changes.get("total_additions", 0) + code_changes.get(
            "total_deletions", 0
        )
        if total_changes > 500:
            prompt_parts.append("\n⚠️ Large changeset - consider architectural impact")
        elif total_changes < 50:
            prompt_parts.append("\n✓ Small, focused changeset")

        prompt_parts.append(
            "\nProvide a detailed technical summary including implementation approach, patterns used, and modified files."
        )

        return "\n".join(prompt_parts)
