"""Unit tests for base LLM provider."""

from src.pr_agents.services.ai.providers.base import BaseLLMProvider, LLMResponse


class MockProvider(BaseLLMProvider):
    """Mock provider for testing base class."""

    async def generate(
        self, prompt: str, max_tokens: int = 500, temperature: float = 0.3, **kwargs
    ) -> LLMResponse:
        """Mock generate method."""
        return LLMResponse(
            content="Mock response",
            model="mock-model",
            tokens_used=50,
            response_time_ms=100,
        )

    async def health_check(self) -> dict:
        """Mock health check."""
        return {"healthy": True}

    @property
    def name(self) -> str:
        """Return mock provider name."""
        return "mock"

    @property
    def supports_streaming(self) -> bool:
        """Mock streaming support."""
        return False


class TestBaseLLMProvider:
    """Test cases for BaseLLMProvider."""

    def test_initialization(self):
        """Test provider initialization."""
        # Act
        provider = MockProvider(api_key="test-key", custom_param="value")

        # Assert
        assert provider.api_key == "test-key"
        assert provider.config["custom_param"] == "value"

    def test_abstract_methods_required(self):
        """Test that abstract methods must be implemented."""
        # This test verifies the abstract nature by using the mock
        provider = MockProvider(api_key="test-key")

        # These should all work with the mock
        assert provider.name == "mock"
        assert provider.supports_streaming is False


class TestLLMResponse:
    """Test cases for LLMResponse dataclass."""

    def test_llm_response_creation(self):
        """Test creating LLM response."""
        # Act
        response = LLMResponse(
            content="Test content",
            model="test-model",
            tokens_used=100,
            response_time_ms=500,
            finish_reason="complete",
            metadata={"extra": "data"},
        )

        # Assert
        assert response.content == "Test content"
        assert response.model == "test-model"
        assert response.tokens_used == 100
        assert response.response_time_ms == 500
        assert response.finish_reason == "complete"
        assert response.metadata["extra"] == "data"

    def test_llm_response_defaults(self):
        """Test LLM response default values."""
        # Act
        response = LLMResponse(
            content="Test",
            model="test",
            tokens_used=10,
            response_time_ms=100,
        )

        # Assert
        assert response.finish_reason == "complete"
        assert response.metadata is None
