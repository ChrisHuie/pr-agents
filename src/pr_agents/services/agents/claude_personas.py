"""Claude-powered persona agents for PR summarization."""

from typing import Any

from src.pr_agents.services.agents.claude_base import ClaudeAgent


class ClaudeExecutiveAgent(ClaudeAgent):
    """Claude agent for executive-level summaries."""

    @property
    def persona(self) -> str:
        """Get the persona name."""
        return "executive"

    @property
    def max_tokens(self) -> int:
        """Maximum tokens for executive summary."""
        return 150

    def build_prompt(self, context: dict[str, Any]) -> str:
        """Build executive-focused prompt.

        Args:
            context: PR and repository context

        Returns:
            Formatted prompt for executive summary
        """
        repo_context = self.get_repo_context_prompt(context)

        prompt = f"""You are summarizing code changes for an executive audience.
{repo_context}

PR Title: {context.get('pr_title', 'Unknown')}
Files Changed: {context.get('files_changed', 0)}
Lines Added: {context.get('additions', 0)}
Lines Deleted: {context.get('deletions', 0)}

Change Categories:
{self._format_change_categories(context.get('change_categories', {}))}

Provide a 1-2 sentence executive summary focusing on:
- Business impact and value
- Revenue or strategic implications
- High-level scope of changes

Keep it under {self.max_tokens} tokens. Be concise and business-focused."""

        return prompt

    def _format_change_categories(self, categories: dict[str, list[str]]) -> str:
        """Format change categories for the prompt."""
        if not categories:
            return "- No specific categories identified"

        lines = []
        for category, files in categories.items():
            lines.append(f"- {category}: {len(files)} files")
        return "\n".join(lines)


class ClaudeProductAgent(ClaudeAgent):
    """Claude agent for product manager summaries."""

    @property
    def persona(self) -> str:
        """Get the persona name."""
        return "product"

    @property
    def max_tokens(self) -> int:
        """Maximum tokens for product summary."""
        return 300

    def build_prompt(self, context: dict[str, Any]) -> str:
        """Build product-focused prompt.

        Args:
            context: PR and repository context

        Returns:
            Formatted prompt for product summary
        """
        repo_context = self.get_repo_context_prompt(context)

        prompt = f"""You are summarizing code changes for a product manager audience.
{repo_context}

PR Title: {context.get('pr_title', 'Unknown')}
PR Description: {context.get('pr_description', 'No description provided')[:500]}
Files Changed: {context.get('files_changed', 0)}
Lines Added: {context.get('additions', 0)}
Lines Deleted: {context.get('deletions', 0)}

Change Categories:
{self._format_change_categories_detailed(context.get('change_categories', {}))}

Has Tests: {context.get('has_tests', False)}

Provide a 2-4 sentence product summary focusing on:
- Features and capabilities added or modified
- User-facing impacts and benefits
- Integration points and compatibility
- Configuration or setup requirements

Keep it under {self.max_tokens} tokens. Be specific about features and user value."""

        return prompt

    def _format_change_categories_detailed(
        self, categories: dict[str, list[str]]
    ) -> str:
        """Format change categories with more detail for product view."""
        if not categories:
            return "- No specific categories identified"

        lines = []
        for category, files in categories.items():
            # Show first few files as examples
            examples = files[:3]
            examples_str = ", ".join(examples)
            if len(files) > 3:
                examples_str += f" (+{len(files) - 3} more)"
            lines.append(f"- {category}: {examples_str}")
        return "\n".join(lines)


class ClaudeDeveloperAgent(ClaudeAgent):
    """Claude agent for developer-focused summaries."""

    @property
    def persona(self) -> str:
        """Get the persona name."""
        return "developer"

    @property
    def max_tokens(self) -> int:
        """Maximum tokens for developer summary."""
        return 500

    def build_prompt(self, context: dict[str, Any]) -> str:
        """Build developer-focused prompt.

        Args:
            context: PR and repository context

        Returns:
            Formatted prompt for developer summary
        """
        repo_context = self.get_repo_context_prompt(context)

        prompt = f"""You are summarizing code changes for a developer audience.
{repo_context}

PR Title: {context.get('pr_title', 'Unknown')}
PR Description: {context.get('pr_description', 'No description provided')[:1000]}
Files Changed: {context.get('files_changed', 0)}
Lines Added: {context.get('additions', 0)}
Lines Deleted: {context.get('deletions', 0)}
Primary Language: {context.get('primary_language', 'Unknown')}

Change Categories:
{self._format_change_categories_full(context.get('change_categories', {}))}

Has Tests: {context.get('has_tests', False)}

Module Patterns (if applicable):
{self._format_module_patterns(context.get('module_patterns', {}))}

Provide a 4-6 sentence developer summary focusing on:
- Technical implementation details and architecture
- New classes, functions, or modules added
- Dependencies or libraries introduced
- API changes or interface modifications
- Testing approach and coverage
- Performance implications or optimizations
- Security considerations if applicable

Keep it under {self.max_tokens} tokens. Be technically precise and include relevant implementation details."""

        return prompt

    def _format_change_categories_full(self, categories: dict[str, list[str]]) -> str:
        """Format all change categories for developer view."""
        if not categories:
            return "- No specific categories identified"

        lines = []
        for category, files in categories.items():
            lines.append(f"\n{category} ({len(files)} files):")
            for file in files[:10]:  # Show up to 10 files per category
                lines.append(f"  - {file}")
            if len(files) > 10:
                lines.append(f"  ... and {len(files) - 10} more files")
        return "\n".join(lines)

    def _format_module_patterns(self, patterns: dict[str, Any]) -> str:
        """Format module patterns if available."""
        if not patterns:
            return "- No specific module patterns configured"

        lines = []
        for pattern_type, pattern_info in patterns.items():
            if isinstance(pattern_info, dict) and "paths" in pattern_info:
                paths = ", ".join(pattern_info["paths"][:3])
                lines.append(f"- {pattern_type}: {paths}")
        return "\n".join(lines) if lines else "- No module patterns identified"
