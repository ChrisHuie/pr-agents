"""Executive summary agent using Google ADK."""

from google.adk import Agent
from google.adk.tools import BaseTool

from ..base import BaseSummaryAgent
from ..tools import CodeAnalyzerTool, PatternDetectorTool


class ExecutiveSummaryAgent(BaseSummaryAgent):
    """Agent specialized in generating executive-level summaries."""

    def get_instructions(self) -> str:
        """Get executive-specific instructions."""
        return """You are creating a concise summary of code changes.

STRICT OUTPUT REQUIREMENT:
Your response MUST be exactly 1-2 sentences. No more.

FOCUS:
- What was changed in the code
- The main purpose of the change
- No business jargon or revenue speculation
- No statistics or percentages
- Just describe what the code change does

Write ONLY 1-2 sentences total describing the actual code changes."""

    def get_tools(self) -> list[BaseTool]:
        """Get tools for executive analysis."""
        return [CodeAnalyzerTool(), PatternDetectorTool()]

    def create_agent(self) -> Agent:
        """Create the executive summary agent."""
        return Agent(
            name="executive_summary_agent",
            model=self.model,
            instruction=self.get_instructions(),
            description="Generates concise summaries of code changes",
            tools=self.get_tools(),
        )

    def _prepare_input(self, code_changes: dict, repo_context: dict) -> str:
        """Prepare executive-focused input."""
        # Use the base implementation to get the full prompt with patches
        base_prompt = super()._prepare_input(code_changes, repo_context)

        # Add executive-specific focus at the end
        executive_suffix = "\n\nProvide a concise 1-2 sentence summary of what was changed in the code."

        return base_prompt + executive_suffix
