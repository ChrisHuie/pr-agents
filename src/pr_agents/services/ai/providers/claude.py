"""Anthropic Claude LLM provider implementation."""

import time
from typing import Any

import anthropic

from src.pr_agents.services.ai.providers.base import BaseLLMProvider, LLMResponse


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude API provider."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-sonnet-20240229",
        **kwargs,
    ):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key
            model_name: Model to use (default: claude-3-sonnet)
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)
        self.model_name = model_name
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        **kwargs,
    ) -> LLMResponse:
        """Generate text completion using Claude.

        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum tokens to generate
            temperature: Temperature for response randomness
            **kwargs: Additional Claude-specific parameters

        Returns:
            LLMResponse with generated text and metadata

        Raises:
            Exception: If Claude API call fails
        """
        start_time = time.time()

        try:
            # Create the message
            message = await self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                **kwargs,
            )

            # Extract response
            content = message.content[0].text if message.content else ""

            # Calculate metrics
            response_time_ms = int((time.time() - start_time) * 1000)

            return LLMResponse(
                content=content,
                model=self.model_name,
                tokens_used=message.usage.input_tokens + message.usage.output_tokens,
                response_time_ms=response_time_ms,
                finish_reason=message.stop_reason or "stop",
                metadata={
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                    "stop_sequence": message.stop_sequence,
                },
            )

        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}") from e

    async def health_check(self) -> dict[str, Any]:
        """Check if Claude provider is healthy.

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
        return "claude"

    @property
    def supports_streaming(self) -> bool:
        """Claude supports streaming responses."""
        return True
