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
