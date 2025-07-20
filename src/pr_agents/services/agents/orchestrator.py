"""Main orchestrator for agent-based summary generation."""

import asyncio
import os
from datetime import datetime
from typing import Any

from loguru import logger

from ...pr_processing.analysis_models import AISummaries, PersonaSummary
from .context import PrebidContextEnricher, RepositoryContextProvider
from .context.batch_context import BatchContextProvider
from .personas import (
    DeveloperSummaryAgent,
    ExecutiveSummaryAgent,
    ProductSummaryAgent,
    ReviewerSummaryAgent,
)


class SummaryAgentOrchestrator:
    """Orchestrates multiple persona agents for summary generation."""

    def __init__(
        self, model: str = "gemini-2.0-flash", use_batch_context: bool = False
    ):
        """Initialize the orchestrator.

        Args:
            model: The LLM model to use for all agents
            use_batch_context: Whether to use batch-optimized context
        """
        self.model = model
        self.use_batch_context = use_batch_context

        # Initialize context providers
        if use_batch_context:
            self.batch_context_provider = BatchContextProvider()
            logger.info("Using batch-optimized context provider")
        else:
            self.batch_context_provider = None

        self.context_provider = RepositoryContextProvider()
        self.prebid_enricher = PrebidContextEnricher()

        # Initialize persona agents
        self.agents = {
            "executive": ExecutiveSummaryAgent(model=model),
            "product": ProductSummaryAgent(model=model),
            "developer": DeveloperSummaryAgent(model=model),
            "reviewer": ReviewerSummaryAgent(model=model),
        }

        logger.info(f"Initialized agent orchestrator with model: {model}")

    async def generate_summaries(
        self,
        code_changes: dict[str, Any],
        repo_name: str,
        repo_type: str | None = None,
    ) -> AISummaries:
        """Generate summaries for all personas using agents.

        Args:
            code_changes: Dictionary containing file diffs and statistics
            repo_name: Repository name (e.g., "prebid/Prebid.js")
            repo_type: Optional repository type

        Returns:
            AISummaries object with all persona summaries
        """
        start_time = datetime.now()

        # Get base repository context
        repo_context = self.context_provider.get_context(repo_name, repo_type)

        # Enrich context based on actual files
        file_list = [
            diff.get("filename", "") for diff in code_changes.get("file_diffs", [])
        ]
        enriched_context = self.context_provider.enrich_with_file_analysis(
            repo_context, file_list
        )

        # Additional enrichment for Prebid repositories
        if repo_type == "prebid" or "prebid" in repo_name.lower():
            # Detect adapter changes
            adapter_files = [
                f
                for f in file_list
                if "bidadapter" in f.lower()
                and f.endswith(".js")
                and "test" not in f.lower()
            ]

            if adapter_files:
                adapter_name = (
                    adapter_files[0].split("/")[-1].replace("BidAdapter.js", "")
                )
                adapter_context = self.prebid_enricher.enrich_adapter_context(
                    adapter_name, code_changes
                )
                enriched_context["adapter_context"] = adapter_context

            # Analyze bid patterns
            bid_patterns = self.prebid_enricher.analyze_bid_patterns(
                code_changes.get("file_diffs", [])
            )
            enriched_context["bid_patterns"] = bid_patterns

        logger.info(
            f"Generating summaries for repository: {repo_name} (type: {repo_type})"
        )

        # Check if specific personas are requested
        requested_personas = (
            os.getenv("AI_PERSONAS", "").split(",") if os.getenv("AI_PERSONAS") else []
        )
        if requested_personas and requested_personas[0]:  # Filter out empty string
            active_personas = {
                k: v for k, v in self.agents.items() if k in requested_personas
            }
            logger.info(
                f"Generating summaries for selected personas: {list(active_personas.keys())}"
            )
        else:
            active_personas = self.agents
            logger.info("Generating summaries for all personas")

        # Generate summaries concurrently
        summary_tasks = []
        for persona_name, agent in active_personas.items():
            task = self._generate_persona_summary(
                agent, persona_name, code_changes, enriched_context
            )
            summary_tasks.append(task)

        # Wait for all summaries
        persona_summaries = await asyncio.gather(*summary_tasks)

        # Calculate total generation time
        generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Create placeholder for missing personas
        def get_persona_or_placeholder(persona_name: str) -> PersonaSummary:
            found = next(
                (s for s in persona_summaries if s.persona == persona_name), None
            )
            if found:
                return found
            else:
                # Return a placeholder for personas that weren't requested
                return PersonaSummary(
                    persona=persona_name, summary="[Not requested]", confidence=0.0
                )

        # Create AISummaries object
        summaries = AISummaries(
            executive_summary=get_persona_or_placeholder("executive"),
            product_summary=get_persona_or_placeholder("product"),
            developer_summary=get_persona_or_placeholder("developer"),
            reviewer_summary=get_persona_or_placeholder("reviewer"),
            model_used=f"adk-{self.model}",
            generation_timestamp=datetime.now(),
            cached=False,
            total_tokens=sum(
                s.confidence for s in persona_summaries
            ),  # Using confidence as token placeholder
            generation_time_ms=generation_time_ms,
        )

        logger.info(f"Generated all summaries in {generation_time_ms}ms")

        return summaries

    def start_batch(self, repo_url: str) -> None:
        """Start a batch operation for a specific repository.

        This optimizes context loading for multiple PRs from the same repository.

        Args:
            repo_url: Repository URL for the batch
        """
        if self.batch_context_provider:
            self.batch_context_provider.start_batch(repo_url)
            logger.info(f"Started batch processing for {repo_url}")

    def end_batch(self) -> None:
        """End the current batch operation."""
        if self.batch_context_provider:
            stats = self.batch_context_provider.get_batch_statistics()
            logger.info(f"Ending batch. Stats: {stats}")
            self.batch_context_provider.end_batch()

    async def _generate_persona_summary(
        self,
        agent: Any,
        persona: str,
        code_changes: dict[str, Any],
        repo_context: dict[str, Any],
    ) -> PersonaSummary:
        """Generate summary for a specific persona.

        Args:
            agent: The persona agent
            persona: Persona name
            code_changes: Code change data
            repo_context: Enriched repository context

        Returns:
            PersonaSummary object
        """
        try:
            logger.debug(f"Generating {persona} summary")

            # Generate summary using the agent
            summary_text = agent.generate_summary(code_changes, repo_context)

            # Calculate confidence based on context richness
            confidence = self._calculate_confidence(repo_context, code_changes)

            return PersonaSummary(
                persona=persona, summary=summary_text, confidence=confidence
            )

        except Exception as e:
            logger.error(f"Error generating {persona} summary: {str(e)}")
            return PersonaSummary(
                persona=persona,
                summary=f"Error generating summary: {str(e)}",
                confidence=0.0,
            )

    def _calculate_confidence(
        self, repo_context: dict[str, Any], code_changes: dict[str, Any]
    ) -> float:
        """Calculate confidence score based on available context.

        Args:
            repo_context: Repository context
            code_changes: Code changes

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence

        # Boost for rich repository context
        if repo_context.get("module_patterns"):
            confidence += 0.1
        if repo_context.get("business_context"):
            confidence += 0.1
        if repo_context.get("technical_context"):
            confidence += 0.1

        # Boost for file analysis
        if repo_context.get("file_analysis", {}).get("detected_modules"):
            confidence += 0.1

        # Boost for test coverage
        if any(
            "test" in d.get("filename", "").lower()
            for d in code_changes.get("file_diffs", [])
        ):
            confidence += 0.1

        return min(confidence, 0.95)  # Cap at 0.95
