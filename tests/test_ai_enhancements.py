"""Tests for AI service enhancements."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.pr_agents.pr_processing.analysis_models import AISummaries
from src.pr_agents.pr_processing.models import CodeChanges, FileDiff
from src.pr_agents.services.ai.cost_optimizer import CostOptimizer, ProviderName
from src.pr_agents.services.ai.feedback import FeedbackStore
from src.pr_agents.services.ai.fine_tuning import FineTuningManager
from src.pr_agents.services.ai.service import AIService
from src.pr_agents.services.ai.streaming import StreamingHandler, StreamingResponse


class TestStreamingSupport:
    """Test streaming functionality."""

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Test StreamingResponse accumulation."""

        async def mock_stream():
            for chunk in ["Hello", " ", "world", "!"]:
                yield chunk

        response = StreamingResponse("test", mock_stream())

        chunks = []
        async for chunk in response:
            chunks.append(chunk)

        assert chunks == ["Hello", " ", "world", "!"]
        assert response.accumulated_text == "Hello world!"
        assert response.token_count == 3  # "Hello" + "world" + "!" = 3 tokens

    @pytest.mark.asyncio
    async def test_streaming_handler_merge(self):
        """Test StreamingHandler merges multiple streams."""

        async def stream1():
            for chunk in ["A1", "A2", "A3"]:
                yield chunk
                await asyncio.sleep(0.01)

        async def stream2():
            for chunk in ["B1", "B2", "B3"]:
                yield chunk
                await asyncio.sleep(0.01)

        handler = StreamingHandler()
        handler.add_response("persona1", stream1())
        handler.add_response("persona2", stream2())

        results = []
        async for persona, chunk in handler.stream_all():
            results.append((persona, chunk))

        # Should have all chunks from both streams
        assert len(results) == 6
        persona1_chunks = [c for p, c in results if p == "persona1"]
        persona2_chunks = [c for p, c in results if p == "persona2"]
        assert persona1_chunks == ["A1", "A2", "A3"]
        assert persona2_chunks == ["B1", "B2", "B3"]


class TestCostOptimizer:
    """Test cost optimization functionality."""

    def test_provider_selection(self):
        """Test optimal provider selection."""
        optimizer = CostOptimizer(quality_threshold=0.8)

        # Test basic selection
        provider = optimizer.select_optimal_provider(
            "Test prompt" * 100,  # ~400 chars = ~100 tokens
            expected_output_tokens=200,
        )

        # Should select Gemini as cheapest with good quality
        assert provider == ProviderName.GEMINI

    def test_budget_constraints(self):
        """Test budget limit enforcement."""
        optimizer = CostOptimizer(quality_threshold=0.8, budget_limit=0.001)

        # Record some usage to approach budget
        optimizer.record_usage(
            ProviderName.GEMINI,
            input_tokens=1000,
            output_tokens=500,
            persona="test",
            pr_url="test_url",
        )

        # Should avoid providers that would exceed budget
        optimizer.select_optimal_provider(
            "Test prompt",
            expected_output_tokens=1000,
        )

        # Check that budget is considered
        today = datetime.now().strftime("%Y-%m-%d")
        assert optimizer.daily_spend[today] > 0

    def test_usage_reporting(self):
        """Test usage report generation."""
        optimizer = CostOptimizer()

        # Record some usage
        optimizer.record_usage(
            ProviderName.GEMINI,
            input_tokens=1000,
            output_tokens=500,
            persona="executive",
            pr_url="test_pr_1",
        )

        optimizer.record_usage(
            ProviderName.CLAUDE,
            input_tokens=2000,
            output_tokens=1000,
            persona="developer",
            pr_url="test_pr_2",
        )

        # Get report
        report = optimizer.get_usage_report(days=1)

        assert report["total_requests"] == 2
        assert report["total_cost"] > 0
        assert "gemini" in report["by_provider"]
        assert "claude" in report["by_provider"]
        assert "executive" in report["by_persona"]
        assert "developer" in report["by_persona"]

    def test_cost_effectiveness_ranking(self):
        """Test provider ranking by cost-effectiveness."""
        optimizer = CostOptimizer()
        rankings = optimizer.get_provider_rankings()

        assert len(rankings) == 3
        assert all(isinstance(p, ProviderName) for p, _ in rankings)
        assert all(score > 0 for _, score in rankings)


class TestFeedbackSystem:
    """Test feedback integration."""

    def test_feedback_storage(self, tmp_path):
        """Test feedback storage and retrieval."""
        storage_path = tmp_path / "feedback.json"
        store = FeedbackStore(storage_path)

        # Add feedback
        store.add_feedback(
            pr_url="https://github.com/test/pr/1",
            persona="executive",
            summary_text="Test summary",
            feedback_type="rating",
            feedback_value=5,
            model_used="gemini",
        )

        # Check stats
        stats = store.get_feedback_stats()
        assert "executive" in stats
        assert stats["executive"].total_feedback == 1
        assert stats["executive"].average_rating == 5.0

    def test_feedback_corrections(self, tmp_path):
        """Test handling of corrections."""
        store = FeedbackStore(tmp_path / "feedback.json")

        # Add correction
        store.add_feedback(
            pr_url="test_pr",
            persona="developer",
            summary_text="Original summary with errors",
            feedback_type="correction",
            feedback_value="Corrected summary without errors",
            model_used="gemini",
        )

        # Get corrections
        corrections = store.get_corrections()
        assert len(corrections) == 1
        assert corrections[0][0] == "Original summary with errors"
        assert corrections[0][1] == "Corrected summary without errors"

    def test_low_rated_summaries(self, tmp_path):
        """Test finding low-rated summaries."""
        store = FeedbackStore(tmp_path / "feedback.json")

        # Add various ratings
        for rating in [1, 2, 3, 4, 5]:
            store.add_feedback(
                pr_url=f"pr_{rating}",
                persona="executive",
                summary_text=f"Summary rated {rating}",
                feedback_type="rating",
                feedback_value=rating,
                model_used="gemini",
            )

        # Get low rated
        low_rated = store.get_low_rated_summaries(threshold=2)
        assert len(low_rated) == 2


class TestFineTuningSupport:
    """Test fine-tuning management."""

    def test_model_registration(self, tmp_path):
        """Test registering fine-tuned models."""
        manager = FineTuningManager(tmp_path / "models.json")

        # Register model
        model = manager.register_model(
            model_id="ft-gemini-v1",
            base_model="gemini",
            version="1.0.0",
            training_date="2024-01-15",
            metrics={"accuracy": 0.95, "loss": 0.05},
            description="Fine-tuned for Prebid.js PRs",
        )

        assert model.model_id == "ft-gemini-v1"
        assert not model.is_active

    def test_model_activation(self, tmp_path):
        """Test activating models."""
        manager = FineTuningManager(tmp_path / "models.json")

        # Register two models
        manager.register_model(
            model_id="ft-v1",
            base_model="gemini",
            version="1.0.0",
            training_date="2024-01-01",
            metrics={},
            description="Version 1",
        )

        manager.register_model(
            model_id="ft-v2",
            base_model="gemini",
            version="2.0.0",
            training_date="2024-01-15",
            metrics={},
            description="Version 2",
        )

        # Activate v2
        manager.activate_model("ft-v2")

        # Check active model
        active = manager.get_active_model("gemini")
        assert active is not None
        assert active.model_id == "ft-v2"

    def test_custom_prompts(self, tmp_path):
        """Test custom prompt management."""
        manager = FineTuningManager(tmp_path / "models.json")

        # Add custom prompt
        manager.add_custom_prompt(
            repository_type="prebid",
            persona="executive",
            prompt_template="Custom prompt for Prebid executive summaries",
        )

        # Retrieve prompt
        prompt = manager.get_custom_prompt("prebid", "executive")
        assert prompt == "Custom prompt for Prebid executive summaries"

        # Non-existent prompt
        assert manager.get_custom_prompt("android", "executive") is None


class TestAIServiceIntegration:
    """Test integrated AI service with enhancements."""

    @pytest.mark.asyncio
    async def test_cost_optimized_generation(self):
        """Test AI service with cost optimization."""
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.name = "gemini"
        mock_provider.generate = AsyncMock(return_value=Mock(content="Test summary"))

        # Create service with cost optimization
        service = AIService(
            provider=mock_provider,
            enable_cost_optimization=True,
            enable_feedback=False,
        )

        # Create test data
        code_changes = CodeChanges(
            file_diffs=[
                FileDiff(
                    filename="test.js",
                    status="modified",
                    additions=10,
                    deletions=5,
                    changes=15,
                    patch="test patch",
                )
            ],
            total_additions=10,
            total_deletions=5,
            total_changes=15,
            changed_files=1,
            base_sha="abc123",
            head_sha="def456",
        )

        repo_context = {"name": "test/repo", "type": "javascript"}
        pr_metadata = {"title": "Test PR", "url": "https://github.com/test/pr/1"}

        # Generate summaries
        with patch.object(
            service.cost_optimizer,
            "select_optimal_provider",
            return_value=ProviderName.GEMINI,
        ):
            summaries = await service.generate_summaries(
                code_changes, repo_context, pr_metadata
            )

        assert isinstance(summaries, AISummaries)
        assert service.cost_optimizer is not None

    @pytest.mark.skip(reason="Streaming implementation needs further work")
    @pytest.mark.asyncio
    async def test_streaming_generation(self):
        """Test streaming summary generation."""
        # Mock streaming provider
        mock_provider = AsyncMock()
        mock_provider.name = "gemini"

        async def mock_stream(*args, **kwargs):
            for chunk in ["Part 1", " Part 2"]:
                yield chunk

        mock_provider.generate_streaming = mock_stream

        # Mock the non-streaming generate method for fallback
        mock_provider.generate = AsyncMock(
            return_value=Mock(content="Fallback summary")
        )

        # Mock config and prompt builder
        with (
            patch("src.pr_agents.services.ai.service.AIConfig") as mock_config,
            patch(
                "src.pr_agents.services.ai.service.PromptBuilder"
            ) as mock_prompt_builder,
        ):

            # Setup mock config
            mock_config.from_env.return_value.cache_enabled = False
            mock_config.from_env.return_value.persona_configs = {
                "executive": Mock(max_tokens=150, temperature=0.7),
                "product": Mock(max_tokens=300, temperature=0.7),
                "developer": Mock(max_tokens=500, temperature=0.7),
            }

            # Setup mock prompt builder
            mock_prompt_instance = Mock()
            mock_prompt_instance.build_prompt.return_value = "Test prompt"
            mock_prompt_builder.return_value = mock_prompt_instance

            service = AIService(provider=mock_provider, enable_cost_optimization=False)

            # Test data
            code_changes = CodeChanges(
                file_diffs=[],
                base_sha="abc123",
                head_sha="def456",
            )
            repo_context = {}
            pr_metadata = {}

            # Collect streamed chunks
            chunks = []
            async for persona, chunk in service.generate_summaries_streaming(
                code_changes, repo_context, pr_metadata
            ):
                chunks.append((persona, chunk))

            # Should have chunks for all personas
            # Note: Because the mock provider doesn't have generate_streaming as an actual method,
            # it will use the fallback non-streaming approach
            assert len(chunks) == 3  # One complete summary per persona
            personas_seen = {p for p, _ in chunks}
            assert len(personas_seen) == 3

    def test_feedback_integration(self, tmp_path):
        """Test feedback recording."""
        mock_provider = Mock()
        mock_provider.name = "gemini"

        # Create service with custom feedback path
        with patch.object(
            FeedbackStore,
            "__init__",
            lambda self: setattr(self, "storage_path", tmp_path / "feedback.json")
            or setattr(self, "feedback_entries", []),
        ):
            service = AIService(
                provider=mock_provider,
                enable_feedback=True,
            )

            # Add feedback
            service.add_feedback(
                pr_url="test_pr",
                persona="executive",
                summary="Test summary",
                feedback_type="rating",
                feedback_value=5,
            )

            # Get stats
            stats = service.get_feedback_stats()
            assert isinstance(stats, dict)
