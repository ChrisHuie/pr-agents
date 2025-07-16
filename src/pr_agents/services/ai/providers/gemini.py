"""Google Gemini LLM provider implementation."""

import asyncio
import time
from typing import Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from src.pr_agents.services.ai.providers.base import BaseLLMProvider, LLMResponse


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-pro",
        **kwargs,
    ):
        """Initialize Gemini provider.

        Args:
            api_key: Google AI API key
            model_name: Model to use (default: gemini-pro)
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)
        self.model_name = model_name

        # Configure the API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        **kwargs,
    ) -> LLMResponse:
        """Generate text completion using Gemini.

        Args:
            prompt: The prompt to send to Gemini
            max_tokens: Maximum tokens to generate
            temperature: Temperature for response randomness
            **kwargs: Additional Gemini-specific parameters

        Returns:
            LLMResponse with generated text and metadata

        Raises:
            Exception: If Gemini API call fails
        """
        start_time = time.time()

        try:
            # Create generation config
            generation_config = GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                candidate_count=1,
            )

            # Add any additional parameters
            for key, value in kwargs.items():
                if hasattr(generation_config, key):
                    setattr(generation_config, key, value)

            # Generate response (Gemini SDK is sync, so we run in executor)
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=generation_config,
                ),
            )

            # Extract response text
            if response.candidates:
                content = response.candidates[0].content.parts[0].text
            else:
                content = ""

            # Calculate metrics
            response_time_ms = int((time.time() - start_time) * 1000)

            # Estimate token count (rough approximation)
            # Gemini doesn't provide token counts in the same way
            estimated_tokens = len(prompt.split()) + len(content.split())

            return LLMResponse(
                content=content,
                model=self.model_name,
                tokens_used=estimated_tokens,
                response_time_ms=response_time_ms,
                finish_reason="stop",
                metadata={
                    "safety_ratings": (
                        [
                            {
                                "category": rating.category.name,
                                "probability": rating.probability.name,
                            }
                            for rating in response.candidates[0].safety_ratings
                        ]
                        if response.candidates
                        else []
                    ),
                },
            )

        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}") from e

    async def health_check(self) -> dict[str, Any]:
        """Check if Gemini provider is healthy.

        Returns:
            Health status dictionary
        """
        try:
            # Try a simple generation to test the API
            response = await self.generate(
                "Hello",
                max_tokens=10,
                temperature=0,
            )

            return {
                "healthy": True,
                "provider": self.name,
                "model": self.model_name,
                "response_time_ms": response.response_time_ms,
            }
        except Exception as e:
            return {
                "healthy": False,
                "provider": self.name,
                "model": self.model_name,
                "error": str(e),
            }

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "gemini"

    @property
    def supports_streaming(self) -> bool:
        """Gemini supports streaming responses."""
        return True
