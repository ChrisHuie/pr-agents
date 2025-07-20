"""ADK-based AI service implementation."""

import os
from datetime import datetime
from typing import Any

from loguru import logger

from ...pr_processing.analysis_models import AISummaries
from ...pr_processing.models import CodeChanges
from ...services.agents import SummaryAgentOrchestrator
from .base import BaseAIService


class ADKAIService(BaseAIService):
    """AI service using Google ADK agents for summary generation."""

    def __init__(self, model: str = None, use_batch_context: bool = False):
        """Initialize ADK AI service.

        Args:
            model: Model to use (defaults to GEMINI_MODEL env var or gemini-2.0-flash)
            use_batch_context: Whether to use batch-optimized context
        """
        if model is None:
            model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

        self.model = model
        self.use_batch_context = use_batch_context
        self.orchestrator = SummaryAgentOrchestrator(model=model, use_batch_context=use_batch_context)
        logger.info(f"Initialized ADK AI service with model: {model}, batch_context: {use_batch_context}")

    async def generate_summaries(
        self,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
    ) -> AISummaries:
        """Generate AI-powered summaries using ADK agents.

        Args:
            code_changes: Extracted code change data
            repo_context: Repository-specific context
            pr_metadata: PR metadata (NOT used for summaries, only for context)

        Returns:
            AISummaries with persona-based summaries
        """
        start_time = datetime.now()

        # Convert CodeChanges to dictionary for agents
        code_changes_dict = {
            "file_diffs": [
                {
                    "filename": diff.filename,
                    "additions": diff.additions,
                    "deletions": diff.deletions,
                    "changes": diff.changes,
                    "status": diff.status,
                    "patch": diff.patch,  # Include the actual code diff
                }
                for diff in code_changes.file_diffs
            ],
            "total_additions": code_changes.total_additions,
            "total_deletions": code_changes.total_deletions,
            "total_changes": code_changes.total_changes,
            "changed_files": code_changes.changed_files,
            # Add PR title for Level 3 context (title only, no description)
            "pr_title": pr_metadata.get("title", ""),
        }

        # Extract repository info (NOT PR metadata)
        repo_name = repo_context.get("name", "unknown")
        repo_type = repo_context.get("type", "generic")

        logger.info(f"Generating ADK agent summaries for {repo_name}")

        # Generate summaries using agents
        summaries = await self.orchestrator.generate_summaries(
            code_changes_dict, repo_name, repo_type
        )

        # Log generation time
        total_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"ADK summary generation completed in {total_time:.2f}s")

        return summaries
    
    def start_batch(self, repo_url: str) -> None:
        """Start batch processing for a repository.
        
        Args:
            repo_url: Repository URL for the batch
        """
        if self.use_batch_context:
            self.orchestrator.start_batch(repo_url)
    
    def end_batch(self) -> None:
        """End the current batch processing."""
        if self.use_batch_context:
            self.orchestrator.end_batch()

    async def health_check(self) -> dict[str, Any]:
        """Check if the ADK AI service is healthy.

        Returns:
            Health status dictionary
        """
        try:
            # Simple health check - verify agents are initialized
            agent_count = len(self.orchestrator.agents)

            return {
                "service": "adk_ai_service",
                "healthy": agent_count == 3,  # Should have 3 persona agents
                "model": self.model,
                "agents_initialized": agent_count,
                "provider": "google-adk",
            }
        except Exception as e:
            logger.error(f"ADK AI service health check failed: {str(e)}")
            return {"service": "adk_ai_service", "healthy": False, "error": str(e)}
