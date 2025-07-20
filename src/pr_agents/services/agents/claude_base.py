"""Base class for Claude-powered agents."""

from abc import ABC, abstractmethod
from typing import Any

from anthropic import Anthropic
from loguru import logger

from src.pr_agents.logging_config import (
    log_function_entry,
    log_function_exit,
    log_processing_step,
)
from src.pr_agents.pr_processing.analysis_models import PersonaSummary


class ClaudeAgent(ABC):
    """Base class for Claude-powered persona agents."""

    def __init__(self, api_key: str | None = None):
        """Initialize Claude agent.

        Args:
            api_key: Anthropic API key (uses env var if not provided)
        """
        log_function_entry(self.__class__.__name__)
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.model = "claude-3-opus-20240229"
        log_function_exit(self.__class__.__name__)

    @property
    @abstractmethod
    def persona(self) -> str:
        """Get the persona name for this agent."""
        pass

    @property
    @abstractmethod
    def max_tokens(self) -> int:
        """Get the maximum tokens for this persona's summary."""
        pass

    @abstractmethod
    def build_prompt(self, context: dict[str, Any]) -> str:
        """Build the prompt for this persona.

        Args:
            context: PR and repository context

        Returns:
            Formatted prompt string
        """
        pass

    async def generate_summary(self, context: dict[str, Any]) -> PersonaSummary:
        """Generate a summary for this persona.

        Args:
            context: PR and repository context

        Returns:
            PersonaSummary with the generated summary
        """
        log_function_entry(
            f"{self.persona}_generate_summary",
            pr_title=context.get("pr_title"),
            total_changes=context.get("total_changes"),
        )

        try:
            # Build persona-specific prompt
            prompt = self.build_prompt(context)

            # Call Claude API
            log_processing_step(f"Calling Claude API for {self.persona} summary")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.3,  # Lower temperature for consistent summaries
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            summary_text = response.content[0].text.strip()

            # Calculate confidence based on response quality
            confidence = self._calculate_confidence(summary_text, context)

            result = PersonaSummary(
                persona=self.persona,
                summary=summary_text,
                confidence=confidence,
            )

            log_function_exit(
                f"{self.persona}_generate_summary",
                confidence=confidence,
                summary_length=len(summary_text),
            )

            return result

        except Exception as e:
            logger.error(f"Error generating {self.persona} summary: {str(e)}")
            return PersonaSummary(
                persona=self.persona,
                summary=f"Error generating {self.persona} summary: {str(e)}",
                confidence=0.0,
            )

    def _calculate_confidence(self, summary: str, context: dict[str, Any]) -> float:
        """Calculate confidence score for the generated summary.

        Args:
            summary: Generated summary text
            context: PR context

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence
        confidence = 0.7

        # Adjust based on summary quality indicators
        if len(summary) < 20:
            confidence -= 0.3
        elif len(summary) > self.max_tokens * 4:  # Approximate chars
            confidence -= 0.1

        # Boost confidence if summary mentions key elements
        if context.get("pr_title", "").lower() in summary.lower():
            confidence += 0.1

        if any(file in summary for file in context.get("change_categories", {}).keys()):
            confidence += 0.1

        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))

    def get_repo_context_prompt(self, context: dict[str, Any]) -> str:
        """Build repository context section for prompts.

        Args:
            context: Repository context

        Returns:
            Formatted repository context string
        """
        repo_name = context.get("repo_name", "Unknown Repository")
        repo_type = context.get("repo_type", "general")
        repo_description = context.get("repo_description", "")

        repo_prompt = f"Repository: {repo_name}"

        if repo_type and repo_type != "general":
            repo_prompt += f" (Type: {repo_type})"

        if repo_description:
            repo_prompt += f"\nDescription: {repo_description}"

        return repo_prompt
