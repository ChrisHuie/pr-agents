"""Base interface for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    tokens_used: int
    response_time_ms: int
    finish_reason: str = "complete"
    metadata: dict[str, Any] | None = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM provider implementations."""

    def __init__(self, api_key: str, **kwargs):
        """Initialize the provider with API credentials.

        Args:
            api_key: API key for the provider
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        **kwargs,
    ) -> LLMResponse:
        """Generate text completion from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens to generate
            temperature: Temperature for response randomness (0-1)
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse containing the generated text and metadata

        Raises:
            LLMProviderError: If generation fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check if the provider is healthy and configured properly.

        Returns:
            Dictionary with health status and provider info
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Return whether this provider supports streaming responses."""
        pass
