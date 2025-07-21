"""Google Gemini LLM provider implementation."""

import asyncio
import time
from typing import Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from loguru import logger

from src.pr_agents.services.ai.providers.base import BaseLLMProvider, LLMResponse


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""

    # Preferred models in order of preference
    PREFERRED_MODELS = [
        "gemini-2.0-flash-exp",  # Latest 2.0 Flash experimental
        "gemini-1.5-flash",  # Stable 1.5 Flash
        "gemini-1.5-pro",  # 1.5 Pro for more complex tasks
        "gemini-pro",  # Legacy (might be deprecated)
    ]

    def __init__(
        self,
        api_key: str,
        model_name: str | None = None,
        **kwargs,
    ):
        """Initialize Gemini provider.

        Args:
            api_key: Google AI API key
            model_name: Model to use (default: auto-detect best available)
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)

        # Configure the API
        genai.configure(api_key=api_key)

        # Get available models
        self.available_models = self._get_available_models()

        # Select model
        if model_name:
            # Validate requested model
            if not self._is_model_available(model_name):
                logger.warning(
                    f"Requested model '{model_name}' not available. Available models: {self.available_models}"
                )
                model_name = self._select_best_model()
        else:
            # Auto-select best available model
            model_name = self._select_best_model()

        self.model_name = model_name
        logger.info(f"Using Gemini model: {self.model_name}")
        self.model = genai.GenerativeModel(model_name)

    def _get_available_models(self) -> list[str]:
        """Get list of available Gemini models."""
        try:
            models = []
            for model in genai.list_models():
                # Only include models that support generateContent
                if "generateContent" in model.supported_generation_methods:
                    models.append(model.name.replace("models/", ""))
            return models
        except Exception as e:
            logger.error(f"Failed to list Gemini models: {e}")
            # Return default list if API call fails
            return ["gemini-1.5-flash", "gemini-1.5-pro"]

    def _is_model_available(self, model_name: str) -> bool:
        """Check if a model is available."""
        # Handle both with and without "models/" prefix
        clean_name = model_name.replace("models/", "")
        return clean_name in self.available_models

    def _select_best_model(self) -> str:
        """Select the best available model from preferred list."""
        for model in self.PREFERRED_MODELS:
            if self._is_model_available(model):
                return model

        # If no preferred model is available, use first available
        if self.available_models:
            return self.available_models[0]

        # Fallback to default
        logger.warning("No models found via API, using fallback")
        return "gemini-1.5-flash"

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
