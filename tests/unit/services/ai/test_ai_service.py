"""Unit tests for AI service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.pr_agents.pr_processing.analysis_models import AISummaries
from src.pr_agents.pr_processing.models import CodeChanges, FileDiff
from src.pr_agents.services.ai import AIService
from src.pr_agents.services.ai.providers.base import LLMResponse


class TestAIService:
    """Test cases for AIService."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = Mock()
        provider.name = "test-provider"
        provider.generate = AsyncMock(
            return_value=LLMResponse(
                content="Test summary",
                model="test-model",
                tokens_used=100,
                response_time_ms=500,
            )
        )
        provider.health_check = AsyncMock(
            return_value={"healthy": True, "provider": "test-provider"}
        )
        return provider

    @pytest.fixture
    def ai_service(self, mock_provider):
        """Create AI service with mock provider."""
        return AIService(provider=mock_provider, enable_cache=False)

    @pytest.fixture
    def sample_code_changes(self):
        """Create sample code changes for testing."""
        return CodeChanges(
            file_diffs=[
                FileDiff(
                    filename="modules/sevioBidAdapter.js",
                    status="added",
                    additions=250,
                    deletions=0,
                    changes=250,
                    patch="+ new adapter code...",
                ),
                FileDiff(
                    filename="test/spec/modules/sevioBidAdapter_spec.js",
                    status="added",
                    additions=150,
                    deletions=0,
                    changes=150,
                    patch="+ test code...",
                ),
            ],
            total_additions=400,
            total_deletions=0,
            total_changes=400,
            changed_files=3,
            base_sha="abc123",
            head_sha="def456",
        )

    @pytest.fixture
    def sample_repo_context(self):
        """Create sample repository context."""
        return {
            "name": "prebid/Prebid.js",
            "type": "prebid-js",
            "description": "Header bidding library",
            "module_patterns": {
                "bid_adapter": ["modules/*BidAdapter.js"],
                "test": ["test/spec/modules/*"],
            },
            "primary_language": "JavaScript",
        }

    @pytest.fixture
    def sample_pr_metadata(self):
        """Create sample PR metadata."""
        return {
            "title": "Add Sevio Bid Adapter",
            "description": "This PR adds support for Sevio bid adapter with banner and native formats.",
            "base_branch": "master",
            "head_branch": "feature/sevio-adapter",
        }

    @pytest.mark.asyncio
    async def test_generate_summaries_success(
        self, ai_service, sample_code_changes, sample_repo_context, sample_pr_metadata
    ):
        """Test successful summary generation."""
        # Act
        result = await ai_service.generate_summaries(
            sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Assert
        assert isinstance(result, AISummaries)
        assert result.executive_summary.persona == "executive"
        assert result.product_summary.persona == "product"
        assert result.developer_summary.persona == "developer"
        assert result.model_used == "test-provider"
        assert not result.cached
        assert result.total_tokens > 0

    @pytest.mark.asyncio
    async def test_generate_summaries_with_cache(
        self,
        mock_provider,
        sample_code_changes,
        sample_repo_context,
        sample_pr_metadata,
    ):
        """Test summary generation with caching enabled."""
        # Arrange
        ai_service = AIService(provider=mock_provider, enable_cache=True)

        # Clear any existing cache
        ai_service.cache.clear()

        # Act - First call
        result1 = await ai_service.generate_summaries(
            sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Act - Second call (should use cache)
        result2 = await ai_service.generate_summaries(
            sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Assert
        assert not result1.cached
        assert result2.cached
        # Provider should only be called 3 times (once per persona)
        assert mock_provider.generate.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_summaries_provider_error(
        self,
        mock_provider,
        sample_code_changes,
        sample_repo_context,
        sample_pr_metadata,
    ):
        """Test handling of provider errors."""
        # Arrange
        mock_provider.generate.side_effect = Exception("API error")
        ai_service = AIService(provider=mock_provider, enable_cache=False)

        # Act
        result = await ai_service.generate_summaries(
            sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Assert
        assert isinstance(result, AISummaries)
        assert "Error generating summary" in result.executive_summary.summary
        assert result.executive_summary.confidence == 0.0

    @pytest.mark.asyncio
    async def test_health_check(self, ai_service):
        """Test health check functionality."""
        # Act
        result = await ai_service.health_check()

        # Assert
        assert result["service"] == "ai_service"
        assert result["healthy"] is True
        assert "provider" in result
        assert "cache" in result

    def test_create_provider_from_env_gemini(self):
        """Test creating Gemini provider from environment."""
        with patch.dict(
            "os.environ", {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"}
        ):
            service = AIService()
            assert service.provider.name == "gemini"

    def test_create_provider_from_env_claude(self):
        """Test creating Claude provider from environment."""
        with patch.dict(
            "os.environ", {"AI_PROVIDER": "claude", "ANTHROPIC_API_KEY": "test-key"}
        ):
            service = AIService()
            assert service.provider.name == "claude"

    def test_create_provider_from_env_openai(self):
        """Test creating OpenAI provider from environment."""
        with patch.dict(
            "os.environ", {"AI_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}
        ):
            service = AIService()
            assert service.provider.name == "openai"

    def test_create_provider_from_env_missing_key(self):
        """Test error when API key is missing."""
        with patch.dict("os.environ", {"AI_PROVIDER": "gemini"}, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY not set"):
                AIService()

    def test_create_provider_from_env_unknown_provider(self):
        """Test error with unknown provider."""
        with patch.dict("os.environ", {"AI_PROVIDER": "unknown"}):
            with pytest.raises(ValueError, match="Unknown AI provider"):
                AIService()

    @pytest.mark.asyncio
    async def test_persona_max_tokens(self, ai_service):
        """Test that different personas use different max tokens."""
        # Arrange
        personas = ["executive", "product", "developer"]
        expected_tokens = {"executive": 150, "product": 300, "developer": 500}

        # Act & Assert
        for persona in personas:
            max_tokens = ai_service._get_max_tokens_for_persona(persona)
            assert max_tokens == expected_tokens[persona]
