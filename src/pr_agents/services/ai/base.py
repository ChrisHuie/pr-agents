"""Base interface for AI services."""

from abc import ABC, abstractmethod
from typing import Any

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

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check if the AI service is healthy and configured properly.

        Returns:
            Dictionary with health status and any diagnostic information
        """
        pass
