"""ADK-based AI service implementation."""

import os
from typing import Any, Dict
from datetime import datetime
from loguru import logger

from ...services.agents import SummaryAgentOrchestrator
from ...pr_processing.models import CodeChanges
from ...pr_processing.analysis_models import AISummaries
from .base import BaseAIService


class ADKAIService(BaseAIService):
    """AI service using Google ADK agents for summary generation."""
    
    def __init__(self, model: str = None):
        """Initialize ADK AI service.
        
        Args:
            model: Model to use (defaults to GEMINI_MODEL env var or gemini-2.0-flash)
        """
        if model is None:
            model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        
        self.model = model
        self.orchestrator = SummaryAgentOrchestrator(model=model)
        logger.info(f"Initialized ADK AI service with model: {model}")
    
    async def generate_summaries(
        self,
        code_changes: CodeChanges,
        repo_context: Dict[str, Any],
        pr_metadata: Dict[str, Any]
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
                    "status": diff.status
                }
                for diff in code_changes.file_diffs
            ],
            "total_additions": code_changes.total_additions,
            "total_deletions": code_changes.total_deletions,
            "total_changes": code_changes.total_changes,
            "changed_files": code_changes.changed_files
        }
        
        # Extract repository info (NOT PR metadata)
        repo_name = repo_context.get("name", "unknown")
        repo_type = repo_context.get("type", "generic")
        
        logger.info(f"Generating ADK agent summaries for {repo_name}")
        
        # Generate summaries using agents
        summaries = await self.orchestrator.generate_summaries(
            code_changes_dict,
            repo_name,
            repo_type
        )
        
        # Log generation time
        total_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"ADK summary generation completed in {total_time:.2f}s")
        
        return summaries
    
    async def health_check(self) -> Dict[str, Any]:
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
                "provider": "google-adk"
            }
        except Exception as e:
            logger.error(f"ADK AI service health check failed: {str(e)}")
            return {
                "service": "adk_ai_service",
                "healthy": False,
                "error": str(e)
            }