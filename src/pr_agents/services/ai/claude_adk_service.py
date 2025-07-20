"""Claude-based Agent Development Kit service for AI-powered code summarization."""

from datetime import datetime
from typing import Any

from src.pr_agents.logging_config import (
    log_error_with_context,
    log_function_entry,
    log_function_exit,
    log_processing_step,
)
from src.pr_agents.pr_processing.analysis_models import AISummaries, PersonaSummary
from src.pr_agents.pr_processing.models import CodeChanges
from src.pr_agents.services.agents.claude_orchestrator import ClaudeAgentOrchestrator
from src.pr_agents.services.ai.base import BaseAIService


class ClaudeADKService(BaseAIService):
    """AI service using Claude-powered agents for persona-based summaries."""

    def __init__(self):
        """Initialize Claude ADK service."""
        log_function_entry(self.__class__.__name__)
        super().__init__()
        self.orchestrator = ClaudeAgentOrchestrator()
        log_function_exit(self.__class__.__name__)

    async def generate_summaries(
        self,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
    ) -> AISummaries:
        """Generate AI summaries using Claude agents.

        Args:
            code_changes: Extracted code change data
            repo_context: Repository-specific context
            pr_metadata: PR metadata

        Returns:
            AISummaries with persona-based summaries
        """
        log_function_entry(
            "generate_summaries",
            pr_title=pr_metadata.get("title", "Unknown"),
            total_changes=code_changes.total_changes,
        )

        try:
            start_time = datetime.now()

            # Prepare context for agents
            context = self._prepare_agent_context(
                code_changes, repo_context, pr_metadata
            )

            # Run agents concurrently for all personas
            log_processing_step("Running Claude agents for all personas")
            summaries = await self.orchestrator.generate_summaries(context)

            # Calculate generation time
            generation_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )

            # Create AISummaries object
            result = AISummaries(
                executive_summary=summaries.get(
                    "executive",
                    PersonaSummary(
                        persona="executive",
                        summary="Error generating executive summary",
                        confidence=0.0,
                    ),
                ),
                product_summary=summaries.get(
                    "product",
                    PersonaSummary(
                        persona="product",
                        summary="Error generating product summary",
                        confidence=0.0,
                    ),
                ),
                developer_summary=summaries.get(
                    "developer",
                    PersonaSummary(
                        persona="developer",
                        summary="Error generating developer summary",
                        confidence=0.0,
                    ),
                ),
                model_used="claude-adk-claude-3-opus",
                generation_timestamp=datetime.now(),
                cached=False,
                total_tokens=int(
                    sum(s.confidence * 100 for s in summaries.values())
                ),  # Approximate
                generation_time_ms=generation_time_ms,
            )

            log_function_exit("generate_summaries")

            return result

        except Exception as e:
            log_error_with_context(e, "claude_adk_summary_generation")
            # Return error summaries
            return self._create_error_summaries(str(e))

    def _prepare_agent_context(
        self,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare context for Claude agents.

        Args:
            code_changes: Code changes data
            repo_context: Repository context
            pr_metadata: PR metadata

        Returns:
            Context dictionary for agents
        """
        # Extract file categories from code changes
        change_categories = {}
        for diff in code_changes.file_diffs:
            # Simple categorization based on file path
            if "test" in diff.filename.lower() or "spec" in diff.filename.lower():
                category = "tests"
            elif "adapter" in diff.filename.lower():
                category = "adapters"
            elif any(ext in diff.filename for ext in [".md", ".rst", ".txt"]):
                category = "documentation"
            else:
                category = "core"

            if category not in change_categories:
                change_categories[category] = []
            change_categories[category].append(diff.filename)

        # Check if any test files were modified
        has_tests = any(
            "test" in diff.filename.lower() or "spec" in diff.filename.lower()
            for diff in code_changes.file_diffs
        )

        context = {
            "pr_title": pr_metadata.get("title", ""),
            "pr_description": pr_metadata.get("body", ""),
            "total_changes": code_changes.total_changes,
            "files_changed": code_changes.changed_files,
            "additions": code_changes.total_additions,
            "deletions": code_changes.total_deletions,
            "change_categories": change_categories,
            "primary_language": repo_context.get("primary_language", "Unknown"),
            "has_tests": has_tests,
        }

        # Add repository context
        context.update(
            {
                "repo_name": repo_context.get("name", ""),
                "repo_type": repo_context.get("repo_type", ""),
                "repo_description": repo_context.get("description", ""),
                "module_patterns": repo_context.get("module_patterns", {}),
            }
        )

        return context

    def _create_error_summaries(self, error_message: str) -> AISummaries:
        """Create error summaries for all personas.

        Args:
            error_message: Error description

        Returns:
            AISummaries with error messages
        """
        error_summary = f"Error generating summary: {error_message}"

        return AISummaries(
            executive_summary=PersonaSummary(
                persona="executive", summary=error_summary, confidence=0.0
            ),
            product_summary=PersonaSummary(
                persona="product", summary=error_summary, confidence=0.0
            ),
            developer_summary=PersonaSummary(
                persona="developer", summary=error_summary, confidence=0.0
            ),
            model_used="claude-adk-claude-3-opus",
            generation_timestamp=datetime.now(),
            cached=False,
            total_tokens=0,
            generation_time_ms=0,
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Cleanup if needed
        pass

    async def health_check(self) -> dict[str, Any]:
        """Check if the Claude ADK service is healthy.

        Returns:
            Health status dictionary
        """
        try:
            # Check if orchestrator is initialized and has agents
            has_orchestrator = (
                hasattr(self, "orchestrator") and self.orchestrator is not None
            )

            if has_orchestrator:
                # Check if API key is configured
                api_key_valid = self.orchestrator.validate_api_key()
                agent_count = len(self.orchestrator.agents)

                return {
                    "service": "claude_adk_service",
                    "healthy": has_orchestrator and api_key_valid and agent_count == 3,
                    "provider": "claude-adk",
                    "model": "claude-3-opus",
                    "agents_initialized": agent_count,
                    "api_key_configured": api_key_valid,
                }
            else:
                return {
                    "service": "claude_adk_service",
                    "healthy": False,
                    "error": "Orchestrator not initialized",
                    "provider": "claude-adk",
                }

        except Exception as e:
            return {
                "service": "claude_adk_service",
                "healthy": False,
                "error": str(e),
                "provider": "claude-adk",
            }
