"""Prompt builder for constructing context-aware prompts."""

from typing import Any

from src.pr_agents.pr_processing.models import CodeChanges
from src.pr_agents.services.ai.prompts.templates import (
    DEVELOPER_TEMPLATE,
    EXECUTIVE_TEMPLATE,
    PRODUCT_TEMPLATE,
    REVIEWER_TEMPLATE,
)


class PromptBuilder:
    """Builds prompts with repository context and code changes."""

    def __init__(self):
        """Initialize the prompt builder."""
        self.templates = {
            "executive": EXECUTIVE_TEMPLATE,
            "product": PRODUCT_TEMPLATE,
            "developer": DEVELOPER_TEMPLATE,
            "reviewer": REVIEWER_TEMPLATE,
        }

    def build_prompt(
        self,
        persona: str,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
        agent_context: str | None = None,
    ) -> str:
        """Build a prompt for the specified persona.

        Args:
            persona: Target persona (executive, product, developer)
            code_changes: Extracted code change data
            repo_context: Repository-specific context
            pr_metadata: PR metadata including title and description
            agent_context: Optional agent-specific context

        Returns:
            Formatted prompt string

        Raises:
            ValueError: If persona is not recognized
        """
        if persona not in self.templates:
            raise ValueError(f"Unknown persona: {persona}")

        template = self.templates[persona]

        # Extract data for template variables
        template_vars = self._extract_template_variables(
            persona, code_changes, repo_context, pr_metadata
        )

        # Add agent context if provided
        if agent_context:
            # Prepend agent context to the prompt
            prompt = f"{agent_context}\n\n---\n\n{template.format(**template_vars)}"
        else:
            prompt = template.format(**template_vars)

        return prompt

    def _extract_template_variables(
        self,
        persona: str,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract variables needed for prompt templates.

        Args:
            persona: Target persona
            code_changes: Code change data
            repo_context: Repository context
            pr_metadata: PR metadata

        Returns:
            Dictionary of template variables
        """
        # Basic PR information
        vars_dict = {
            "repo_name": repo_context.get("name", "Unknown"),
            "repo_type": repo_context.get("type", "Unknown"),
            "pr_title": pr_metadata.get("title", "No title"),
            "pr_description_preview": self._get_description_preview(pr_metadata),
            "base_branch": pr_metadata.get("base_branch", "main"),
            "head_branch": pr_metadata.get("head_branch", "feature"),
        }

        # Code change statistics
        vars_dict.update(
            {
                "file_count": len(code_changes.file_diffs),
                "additions": code_changes.total_additions,
                "deletions": code_changes.total_deletions,
                "file_types": self._get_file_types(code_changes),
                "primary_language": repo_context.get("primary_language", "Unknown"),
                "modified_paths": self._get_modified_paths(code_changes),
            }
        )

        # Repository context
        vars_dict["repo_context"] = self._format_repo_context(repo_context)

        # Persona-specific content
        if persona == "executive":
            vars_dict["changes_summary"] = self._build_executive_summary(code_changes)
        elif persona == "product":
            vars_dict["detailed_changes"] = self._build_product_changes(code_changes)
        elif persona in ["developer", "reviewer"]:
            vars_dict["code_patterns"] = self._detect_code_patterns(code_changes)
            vars_dict["full_diff_analysis"] = self._build_developer_diff_analysis(
                code_changes
            )

        return vars_dict

    def _get_description_preview(self, pr_metadata: dict[str, Any]) -> str:
        """Get a preview of the PR description."""
        description = pr_metadata.get("description", "")
        if not description:
            return "No description provided"

        # First 200 characters
        preview = description[:200]
        if len(description) > 200:
            preview += "..."
        return preview

    def _get_file_types(self, code_changes: CodeChanges) -> str:
        """Get a summary of file types changed."""
        extensions = {}
        for diff in code_changes.file_diffs:
            ext = diff.filename.split(".")[-1] if "." in diff.filename else "no-ext"
            extensions[ext] = extensions.get(ext, 0) + 1

        return ", ".join(f"{ext}({count})" for ext, count in extensions.items())

    def _get_modified_paths(self, code_changes: CodeChanges) -> str:
        """Get a summary of modified paths."""
        paths = set()
        for diff in code_changes.file_diffs:
            parts = diff.filename.split("/")
            if len(parts) > 1:
                paths.add(parts[0])

        return ", ".join(sorted(paths)) if paths else "root"

    def _format_repo_context(self, repo_context: dict[str, Any]) -> str:
        """Format repository context for the prompt."""
        lines = []

        if "description" in repo_context:
            lines.append(f"Description: {repo_context['description']}")

        if "module_patterns" in repo_context:
            lines.append("Module Types:")
            for module_type, patterns in repo_context["module_patterns"].items():
                lines.append(f"  - {module_type}: {', '.join(patterns)}")

        if "structure" in repo_context:
            lines.append("Repository Structure:")
            for key, value in repo_context["structure"].items():
                lines.append(f"  - {key}: {value}")

        return "\n".join(lines) if lines else "No specific repository context available"

    def _build_executive_summary(self, code_changes: CodeChanges) -> str:
        """Build a high-level summary for executives."""
        summary_parts = []

        # File change summary
        summary_parts.append(
            f"{len(code_changes.file_diffs)} files modified with "
            f"{code_changes.total_additions} additions and {code_changes.total_deletions} deletions"
        )

        # Key file types
        key_files = [
            diff.filename
            for diff in code_changes.file_diffs
            if any(
                keyword in diff.filename.lower()
                for keyword in ["adapter", "module", "core", "lib"]
            )
        ]
        if key_files:
            summary_parts.append(f"Key files: {', '.join(key_files[:3])}")

        return "\n".join(summary_parts)

    def _build_product_changes(self, code_changes: CodeChanges) -> str:
        """Build detailed changes summary for product managers."""
        changes = []

        for diff in code_changes.file_diffs[:10]:  # First 10 files
            change_type = "Added" if diff.status == "added" else "Modified"
            changes.append(
                f"- {change_type} {diff.filename} "
                f"(+{diff.additions}, -{diff.deletions})"
            )

        if len(code_changes.file_diffs) > 10:
            changes.append(f"- ... and {len(code_changes.file_diffs) - 10} more files")

        return "\n".join(changes)

    def _detect_code_patterns(self, code_changes: CodeChanges) -> str:
        """Detect code patterns for developer summary."""
        patterns = []

        # Check for test files
        test_files = [
            diff.filename
            for diff in code_changes.file_diffs
            if "test" in diff.filename.lower() or "spec" in diff.filename.lower()
        ]
        if test_files:
            patterns.append(f"Test files: {len(test_files)}")

        # Check for configuration files
        config_files = [
            diff.filename
            for diff in code_changes.file_diffs
            if any(
                ext in diff.filename for ext in [".json", ".yaml", ".yml", ".config"]
            )
        ]
        if config_files:
            patterns.append(f"Configuration files: {len(config_files)}")

        # Check for documentation
        doc_files = [
            diff.filename
            for diff in code_changes.file_diffs
            if any(ext in diff.filename for ext in [".md", ".rst", ".txt"])
        ]
        if doc_files:
            patterns.append(f"Documentation files: {len(doc_files)}")

        return "\n".join(patterns) if patterns else "No specific patterns detected"

    def _build_developer_diff_analysis(self, code_changes: CodeChanges) -> str:
        """Build detailed diff analysis for developers."""
        analysis = []

        # Group files by directory
        by_directory = {}
        for diff in code_changes.file_diffs:
            dir_name = "/".join(diff.filename.split("/")[:-1]) or "root"
            if dir_name not in by_directory:
                by_directory[dir_name] = []
            by_directory[dir_name].append(diff)

        # Summarize by directory
        for directory, diffs in sorted(by_directory.items())[:5]:  # Top 5 directories
            total_changes = sum(d.additions + d.deletions for d in diffs)
            analysis.append(
                f"{directory}/: {len(diffs)} files, {total_changes} total changes"
            )

        if len(by_directory) > 5:
            analysis.append(f"... and {len(by_directory) - 5} more directories")

        return "\n".join(analysis)
