"""Main AI service implementation."""

import asyncio
import os
from datetime import datetime
from typing import Any, AsyncIterator

from loguru import logger

from src.pr_agents.pr_processing.analysis_models import AISummaries, PersonaSummary
from src.pr_agents.pr_processing.models import CodeChanges
from src.pr_agents.services.ai.base import BaseAIService
from src.pr_agents.services.ai.cache import SummaryCache
from src.pr_agents.services.ai.config import AIConfig
from src.pr_agents.services.ai.cost_optimizer import CostOptimizer, ProviderName
from src.pr_agents.services.ai.feedback import FeedbackIntegrator, FeedbackStore
from src.pr_agents.services.ai.prompts import PromptBuilder
from src.pr_agents.services.ai.providers.base import BaseLLMProvider
from src.pr_agents.services.ai.streaming import StreamingHandler
from src.pr_agents.services.ai.validators import SummaryValidator


class AIService(BaseAIService):
    """Main AI service for generating code summaries."""

    def __init__(
        self,
        provider: BaseLLMProvider | None = None,
        config: AIConfig | None = None,
        enable_cost_optimization: bool = True,
        enable_feedback: bool = True,
    ):
        """Initialize AI service.

        Args:
            provider: LLM provider instance (if None, will create from env)
            config: AI configuration (if None, will use defaults from env)
            enable_cost_optimization: Whether to enable cost optimization
            enable_feedback: Whether to enable feedback system
        """
        self.config = config or AIConfig.from_env()
        self.provider = provider or self._create_provider_from_env()
        self.prompt_builder = PromptBuilder()
        self.validator = SummaryValidator()

        # Initialize cache based on config
        self.cache = (
            SummaryCache(ttl_seconds=self.config.cache_ttl_seconds)
            if self.config.cache_enabled
            else None
        )

        # Initialize cost optimizer
        self.cost_optimizer = (
            CostOptimizer(
                quality_threshold=0.8,
                budget_limit=float(os.getenv("AI_DAILY_BUDGET_USD", "10.0")),
            )
            if enable_cost_optimization
            else None
        )

        # Initialize feedback system
        if enable_feedback:
            self.feedback_store = FeedbackStore()
            self.feedback_integrator = FeedbackIntegrator(self.feedback_store)
        else:
            self.feedback_store = None
            self.feedback_integrator = None

    def _create_provider_from_env(self, provider_name: str | None = None) -> BaseLLMProvider:
        """Create provider based on environment configuration.
        
        Args:
            provider_name: Optional provider name override
            
        Returns:
            LLM provider instance
        """
        if not provider_name:
            provider_name = os.getenv("AI_PROVIDER", "gemini").lower()

        if provider_name == "gemini":
            from src.pr_agents.services.ai.providers.gemini import GeminiProvider

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set")
            return GeminiProvider(api_key)

        elif provider_name == "claude":
            from src.pr_agents.services.ai.providers.claude import ClaudeProvider

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            return ClaudeProvider(api_key)

        elif provider_name == "openai":
            from src.pr_agents.services.ai.providers.openai import OpenAIProvider

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            return OpenAIProvider(api_key)

        else:
            raise ValueError(f"Unknown AI provider: {provider_name}")

    async def generate_summaries(
        self,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
    ) -> AISummaries:
        """Generate AI-powered summaries for code changes.

        Args:
            code_changes: Extracted code change data
            repo_context: Repository-specific context
            pr_metadata: PR metadata

        Returns:
            AISummaries with persona-based summaries
        """
        start_time = datetime.now()

        # Check cache first
        if self.config.cache_enabled and self.cache:
            cache_key = self.cache.get_key(
                code_changes,
                repo_context.get("name", "unknown"),
                repo_context.get("type", "unknown"),
            )

            cached_summaries = self.cache.get(cache_key)
            if cached_summaries:
                logger.info(f"Found cached summaries for key: {cache_key}")
                cached_summaries.cached = True
                return cached_summaries

        # Select optimal provider if cost optimization is enabled
        if self.cost_optimizer:
            # Estimate tokens for each persona
            executive_tokens = 150
            product_tokens = 300
            developer_tokens = 500
            total_output_tokens = executive_tokens + product_tokens + developer_tokens

            # Build combined prompt for estimation
            sample_prompt = self.prompt_builder.build_prompt(
                "executive", code_changes, repo_context, pr_metadata
            )

            # Select provider
            optimal_provider = self.cost_optimizer.select_optimal_provider(
                sample_prompt, total_output_tokens
            )

            # Switch provider if different
            if optimal_provider.value != self.provider.name:
                logger.info(f"Switching to {optimal_provider.value} for cost optimization")
                self.provider = self._create_provider_from_env(optimal_provider.value)

        # Generate summaries for each persona
        personas = ["executive", "product", "developer"]
        summaries = {}
        total_tokens = 0

        # Check if we should adjust prompts based on feedback
        if self.feedback_integrator:
            for persona in personas:
                if self.feedback_integrator.should_adjust_prompt(persona, self.provider.name):
                    adjustments = self.feedback_integrator.get_prompt_adjustments(persona)
                    logger.info(f"Adjusting prompt for {persona} based on feedback: {adjustments}")
                    # Pass adjustments to prompt builder (would need to update PromptBuilder)

        # Run all persona generations concurrently
        tasks = []
        for persona in personas:
            task = self._generate_persona_summary(
                persona, code_changes, repo_context, pr_metadata
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Process results
        for persona, result in zip(personas, results, strict=False):
            summaries[f"{persona}_summary"] = result
            total_tokens += (
                result.confidence
            )  # We're storing tokens in confidence for now

        # Calculate total time
        generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Create AISummaries object
        ai_summaries = AISummaries(
            executive_summary=summaries["executive_summary"],
            product_summary=summaries["product_summary"],
            developer_summary=summaries["developer_summary"],
            model_used=self.provider.name,
            generation_timestamp=datetime.now(),
            cached=False,
            total_tokens=total_tokens,
            generation_time_ms=generation_time_ms,
        )

        # Cache the result
        if self.config.cache_enabled and self.cache and cache_key:
            self.cache.set(cache_key, ai_summaries)
            logger.info(f"Cached summaries with key: {cache_key}")

        # Record usage for cost tracking
        if self.cost_optimizer:
            pr_url = pr_metadata.get("url", "unknown")
            for persona in personas:
                # Estimate tokens per persona (rough estimate)
                tokens_map = {"executive": 150, "product": 300, "developer": 500}
                output_tokens = tokens_map.get(persona, 300)
                input_tokens = len(self.prompt_builder.build_prompt(
                    persona, code_changes, repo_context, pr_metadata
                )) // 4  # Rough estimate
                
                self.cost_optimizer.record_usage(
                    ProviderName(self.provider.name),
                    input_tokens,
                    output_tokens,
                    persona,
                    pr_url,
                )

        return ai_summaries

    async def _generate_persona_summary(
        self,
        persona: str,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
    ) -> PersonaSummary:
        """Generate summary for a specific persona.

        Args:
            persona: Target persona
            code_changes: Code change data
            repo_context: Repository context
            pr_metadata: PR metadata

        Returns:
            PersonaSummary for the specified persona
        """
        try:
            # Build prompt
            prompt = self.prompt_builder.build_prompt(
                persona, code_changes, repo_context, pr_metadata
            )

            # Get persona config
            persona_config = self.config.persona_configs.get(
                persona, self.config.persona_configs["developer"]  # Default fallback
            )

            # Generate summary with retry logic
            response = await self._generate_with_retry(
                prompt,
                max_tokens=persona_config.max_tokens,
                temperature=persona_config.temperature,
                persona=persona,
            )

            summary_text = response.content.strip()

            # Validate summary
            is_valid, issues = self.validator.validate_summary(
                summary_text,
                persona,
                code_context={"file_diffs": code_changes.file_diffs},
            )

            # Calculate confidence based on validation
            confidence = 0.95 if is_valid else max(0.5, 0.95 - (len(issues) * 0.1))

            # Log validation issues if any
            if not is_valid:
                logger.warning(f"Summary validation issues for {persona}: {issues}")

            # Create PersonaSummary
            return PersonaSummary(
                persona=persona,
                summary=summary_text,
                confidence=confidence,
            )

        except Exception as e:
            logger.error(f"Error generating {persona} summary: {str(e)}")
            return PersonaSummary(
                persona=persona,
                summary=f"Error generating summary: {str(e)}",
                confidence=0.0,
            )

    def _get_max_tokens_for_persona(self, persona: str) -> int:
        """Get appropriate max tokens for each persona."""
        token_limits = {
            "executive": 150,
            "product": 300,
            "developer": 500,
        }
        return token_limits.get(persona, 300)

    async def health_check(self) -> dict[str, Any]:
        """Check if the AI service is healthy.

        Returns:
            Health status dictionary
        """
        provider_health = await self.provider.health_check()

        cache_info = {}
        if self.cache:
            cache_info = {
                "enabled": True,
                "entries": len(self.cache.cache),
                "ttl_seconds": self.cache.ttl_seconds,
            }
        else:
            cache_info = {"enabled": False}

        return {
            "service": "ai_service",
            "healthy": provider_health["healthy"],
            "provider": provider_health,
            "cache": cache_info,
        }

    async def _generate_with_retry(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        persona: str,
    ):
        """Generate response with exponential backoff retry logic.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens for response
            temperature: Temperature setting
            persona: Persona type for logging

        Returns:
            LLM response

        Raises:
            Exception: If all retries fail
        """
        delay = self.config.initial_retry_delay
        last_error = None
        max_retries = self.config.max_retries

        for attempt in range(max_retries + 1):
            try:
                logger.debug(
                    f"Generating {persona} summary (attempt {attempt + 1}/{max_retries + 1})"
                )
                response = await self.provider.generate(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return response
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        f"LLM generation failed for {persona} (attempt {attempt + 1}), "
                        f"retrying in {delay}s: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                    delay *= self.config.retry_backoff_factor  # Exponential backoff
                else:
                    logger.error(f"All retry attempts failed for {persona}: {str(e)}")

        raise last_error or Exception("Failed to generate summary after all retries")

    async def generate_summaries_streaming(
        self,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
    ) -> AsyncIterator[tuple[str, str]]:
        """Generate AI summaries with streaming support.

        Args:
            code_changes: Code change data
            repo_context: Repository context
            pr_metadata: PR metadata

        Yields:
            Tuples of (persona, text_chunk)
        """
        # Create streaming handler
        handler = StreamingHandler()

        # Start streaming for each persona
        personas = ["executive", "product", "developer"]
        
        for persona in personas:
            # Build prompt
            prompt = self.prompt_builder.build_prompt(
                persona, code_changes, repo_context, pr_metadata
            )

            # Get persona config
            persona_config = self.config.persona_configs.get(
                persona, self.config.persona_configs["developer"]
            )

            # Check if provider supports streaming
            if hasattr(self.provider, "generate_streaming"):
                # Get streaming response
                stream = self.provider.generate_streaming(
                    prompt,
                    max_tokens=persona_config.max_tokens,
                    temperature=persona_config.temperature,
                )
                handler.add_response(persona, stream)
            else:
                # Fallback to non-streaming
                logger.warning(f"{self.provider.name} doesn't support streaming, using fallback")
                response = await self.provider.generate(
                    prompt,
                    max_tokens=persona_config.max_tokens,
                    temperature=persona_config.temperature,
                )
                # Create fake stream
                async def fake_stream():
                    yield response.content
                handler.add_response(persona, fake_stream())

        # Stream all responses
        async for persona, chunk in handler.stream_all():
            yield persona, chunk

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
            summary: Generated summary
            feedback_type: Type of feedback
            feedback_value: Feedback value
        """
        if self.feedback_store:
            self.feedback_store.add_feedback(
                pr_url=pr_url,
                persona=persona,
                summary_text=summary,
                feedback_type=feedback_type,
                feedback_value=feedback_value,
                model_used=self.provider.name,
            )
            logger.info(f"Recorded {feedback_type} feedback for {persona} summary")

    def get_cost_report(self, days: int = 7) -> dict[str, Any]:
        """Get cost report for the specified period.

        Args:
            days: Number of days to report

        Returns:
            Cost statistics
        """
        if not self.cost_optimizer:
            return {"error": "Cost optimization not enabled"}

        return self.cost_optimizer.get_usage_report(days)

    def get_feedback_stats(self) -> dict[str, Any]:
        """Get feedback statistics.

        Returns:
            Feedback statistics by persona
        """
        if not self.feedback_store:
            return {"error": "Feedback system not enabled"}

        stats = self.feedback_store.get_feedback_stats()
        return {
            persona: {
                "total_feedback": s.total_feedback,
                "average_rating": s.average_rating,
                "positive_count": s.positive_count,
                "negative_count": s.negative_count,
                "correction_count": s.correction_count,
            }
            for persona, s in stats.items()
        }
