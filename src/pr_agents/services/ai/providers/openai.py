"""OpenAI LLM provider implementation."""

import time
from typing import Any

import openai

from src.pr_agents.services.ai.providers.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4-turbo-preview",
        **kwargs,
    ):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model_name: Model to use (default: gpt-4-turbo-preview)
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)
        self.model_name = model_name
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        **kwargs,
    ) -> LLMResponse:
        """Generate text completion using OpenAI.

        Args:
            prompt: The prompt to send to OpenAI
            max_tokens: Maximum tokens to generate
            temperature: Temperature for response randomness
            **kwargs: Additional OpenAI-specific parameters

        Returns:
            LLMResponse with generated text and metadata

        Raises:
            Exception: If OpenAI API call fails
        """
        start_time = time.time()

        try:
            # Create the chat completion
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that summarizes code changes.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )

            # Extract response
            content = response.choices[0].message.content or ""

            # Calculate metrics
            response_time_ms = int((time.time() - start_time) * 1000)

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=response.usage.total_tokens,
                response_time_ms=response_time_ms,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                },
            )

        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}") from e

    async def health_check(self) -> dict[str, Any]:
        """Check if OpenAI provider is healthy.

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
        return "openai"

    @property
    def supports_streaming(self) -> bool:
        """OpenAI supports streaming responses."""
        return True
