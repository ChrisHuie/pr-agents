"""Orchestrator for Claude-powered agents."""

import asyncio
import os
from typing import Any

from loguru import logger

from src.pr_agents.logging_config import (
    log_function_entry,
    log_function_exit,
    log_processing_step,
)
from src.pr_agents.pr_processing.analysis_models import PersonaSummary
from src.pr_agents.services.agents.claude_personas import (
    ClaudeDeveloperAgent,
    ClaudeExecutiveAgent,
    ClaudeProductAgent,
)


class ClaudeAgentOrchestrator:
    """Orchestrates Claude agents for generating persona-based summaries."""

    def __init__(self, api_key: str | None = None):
        """Initialize the orchestrator with Claude agents.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
        """
        log_function_entry(self.__class__.__name__)

        # Get API key from environment if not provided
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        # Initialize agents
        self.agents = {
            "executive": ClaudeExecutiveAgent(self.api_key),
            "product": ClaudeProductAgent(self.api_key),
            "developer": ClaudeDeveloperAgent(self.api_key),
        }

        log_function_exit(self.__class__.__name__)

    async def generate_summaries(
        self, context: dict[str, Any]
    ) -> dict[str, PersonaSummary]:
        """Generate summaries for all personas concurrently.

        Args:
            context: PR and repository context

        Returns:
            Dictionary mapping persona names to PersonaSummary objects
        """
        log_function_entry(
            "generate_summaries",
            pr_title=context.get("pr_title"),
            total_changes=context.get("total_changes"),
        )

        # Create tasks for each persona
        tasks = []
        for persona_name, agent in self.agents.items():
            log_processing_step(f"Creating task for {persona_name} agent")
            task = asyncio.create_task(
                self._generate_persona_summary(persona_name, agent, context)
            )
            tasks.append((persona_name, task))

        # Run all tasks concurrently
        log_processing_step("Running all persona agents concurrently")
        results = {}

        for persona_name, task in tasks:
            try:
                summary = await task
                results[persona_name] = summary
                logger.info(
                    f"Generated {persona_name} summary with confidence: {summary.confidence}"
                )
            except Exception as e:
                logger.error(f"Error generating {persona_name} summary: {str(e)}")
                results[persona_name] = PersonaSummary(
                    persona=persona_name,
                    summary=f"Error generating summary: {str(e)}",
                    confidence=0.0,
                )

        log_function_exit("generate_summaries")

        return results

    async def _generate_persona_summary(
        self, persona_name: str, agent: Any, context: dict[str, Any]
    ) -> PersonaSummary:
        """Generate summary for a specific persona.

        Args:
            persona_name: Name of the persona
            agent: The Claude agent instance
            context: PR and repository context

        Returns:
            PersonaSummary object
        """
        try:
            log_processing_step(f"Generating {persona_name} summary")
            summary = await agent.generate_summary(context)
            return summary
        except Exception as e:
            logger.error(f"Failed to generate {persona_name} summary: {str(e)}")
            return PersonaSummary(
                persona=persona_name,
                summary=f"Error: {str(e)}",
                confidence=0.0,
            )

    def validate_api_key(self) -> bool:
        """Validate that the API key is configured.

        Returns:
            True if API key is available, False otherwise
        """
        if not self.api_key:
            logger.error(
                "No Anthropic API key found. Set ANTHROPIC_API_KEY environment variable."
            )
            return False
        return True
