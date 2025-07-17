"""Base interface for AI services."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from src.pr_agents.pr_processing.analysis_models import AISummaries
from src.pr_agents.pr_processing.models import CodeChanges


class BaseAIService(ABC):
    """Abstract base class for AI service implementations."""

    @abstractmethod
    async def generate_summaries(
        self,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
    ) -> AISummaries:
        """Generate AI-powered summaries for code changes.

        Args:
            code_changes: Extracted code change data
            repo_context: Repository-specific context and patterns
            pr_metadata: PR metadata including title and description

        Returns:
            AISummaries containing persona-based summaries

        Raises:
            AIServiceError: If summary generation fails
        """
        pass

    async def generate_summaries_streaming(
        self,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
    ) -> AsyncIterator[tuple[str, str]]:
        """Generate AI summaries with streaming support.

        Args:
            code_changes: Extracted code change data
            repo_context: Repository-specific context
            pr_metadata: PR metadata

        Yields:
            Tuples of (persona, text_chunk) as they are generated

        Note:
            Default implementation falls back to non-streaming.
            Override in subclasses for true streaming support.
        """
        # Default: Generate non-streaming and yield complete summaries
        summaries = await self.generate_summaries(code_changes, repo_context, pr_metadata)
        
        yield ("executive", summaries.executive_summary.summary)
        yield ("product", summaries.product_summary.summary)
        yield ("developer", summaries.developer_summary.summary)

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check if the AI service is healthy and configured properly.

        Returns:
            Dictionary with health status and any diagnostic information
        """
        pass

    def add_feedback(
        self,
        pr_url: str,
        persona: str,
        summary: str,
        feedback_type: str,
        feedback_value: Any,
    ) -> None:
        """Add feedback for a generated summary.

        Args:
            pr_url: PR URL
            persona: Persona type
            summary: Generated summary text
            feedback_type: Type of feedback (rating, correction, comment)
            feedback_value: Feedback value

        Note:
            Default implementation does nothing.
            Override in subclasses to support feedback.
        """
        pass
