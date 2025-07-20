"""Code Review persona agent for detailed code analysis."""

from google.adk import Agent

from ..base import BaseSummaryAgent


class ReviewerSummaryAgent(BaseSummaryAgent):
    """Agent that provides code review insights and recommendations."""

    def create_agent(self) -> Agent:
        """Create the code reviewer ADK agent."""
        return Agent(
            name="Code Reviewer Agent",
            instructions=self.get_instructions(),
            model=self.model,
            tools=self.get_tools(),
        )

    def get_instructions(self) -> str:
        """Get code review specific instructions."""
        return """You are an experienced code reviewer analyzing pull request changes.

FOCUS ON:
1. Potential Issues and Bugs
2. Security Concerns
3. Performance Implications
4. Code Quality and Maintainability
5. Test Coverage Assessment
6. Adherence to Best Practices

STRICT OUTPUT REQUIREMENTS:
- Provide 3-5 concise review points
- Each point should be actionable
- Focus on the most important issues
- Be constructive and specific
- Reference specific files or patterns when relevant

OUTPUT FORMAT:
Start with the most critical issues first. Use clear, direct language.
Example: "The error handling in api.js could miss null responses. Consider adding validation for response.data before accessing nested properties."

DO NOT:
- Summarize what the code does (that's for other personas)
- Include praise unless addressing a specific security or performance improvement
- Be vague or generic
- Exceed 5 review points

Remember: You are reviewing the actual code changes, not summarizing them."""

    def get_tools(self) -> list:
        """Get tools for the code reviewer agent."""
        # Code reviewer doesn't need special tools
        return []
