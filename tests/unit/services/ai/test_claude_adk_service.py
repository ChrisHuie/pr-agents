"""Unit tests for Claude ADK service."""

from unittest.mock import AsyncMock, patch

import pytest

from src.pr_agents.pr_processing.analysis_models import PersonaSummary
from src.pr_agents.pr_processing.models import CodeChanges, FileDiff
from src.pr_agents.services.ai.claude_adk_service import ClaudeADKService


@pytest.fixture
def claude_adk_service():
    """Create a Claude ADK service instance."""
    with patch("src.pr_agents.services.ai.claude_adk_service.ClaudeAgentOrchestrator"):
        service = ClaudeADKService()
        yield service


@pytest.fixture
def sample_code_changes():
    """Create sample code changes."""
    return CodeChanges(
        file_diffs=[
            FileDiff(
                filename="src/processor.py",
                additions=80,
                deletions=20,
                changes=100,
                patch="",
                status="modified",
            ),
            FileDiff(
                filename="src/pipeline.py",
                additions=50,
                deletions=10,
                changes=60,
                patch="",
                status="modified",
            ),
            FileDiff(
                filename="tests/test_processor.py",
                additions=20,
                deletions=0,
                changes=20,
                patch="",
                status="added",
            ),
        ],
        total_additions=150,
        total_deletions=30,
        total_changes=180,
        changed_files=3,
        base_sha="abc123",
        head_sha="def456",
    )


@pytest.fixture
def sample_pr_metadata():
    """Create sample PR metadata."""
    return {
        "title": "Add new feature for data processing",
        "body": "This PR adds a new data processing pipeline with improved performance",
        "number": 123,
        "state": "open",
        "user": {"login": "testuser"},
    }


@pytest.fixture
def sample_repo_context():
    """Create sample repository context."""
    return {
        "name": "data-processor",
        "repo_type": "library",
        "description": "High-performance data processing library",
        "module_patterns": {
            "processors": {"paths": ["src/processors/*.py"]},
            "pipelines": {"paths": ["src/pipelines/*.py"]},
        },
    }


class TestClaudeADKService:
    """Test suite for Claude ADK service."""

    @pytest.mark.asyncio
    async def test_generate_summaries_success(
        self,
        claude_adk_service,
        sample_code_changes,
        sample_repo_context,
        sample_pr_metadata,
    ):
        """Test successful summary generation."""
        # Mock the orchestrator's generate_summaries method
        mock_summaries = {
            "executive": PersonaSummary(
                persona="executive",
                summary="New data processing feature improves performance by 40%",
                confidence=0.9,
            ),
            "product": PersonaSummary(
                persona="product",
                summary="Enhanced data pipeline with better error handling and monitoring",
                confidence=0.85,
            ),
            "developer": PersonaSummary(
                persona="developer",
                summary="Implemented async processing in pipeline.py with new Processor class",
                confidence=0.95,
            ),
        }

        claude_adk_service.orchestrator.generate_summaries = AsyncMock(
            return_value=mock_summaries
        )

        # Generate summaries
        result = await claude_adk_service.generate_summaries(
            sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Verify results
        assert result.executive_summary.summary == mock_summaries["executive"].summary
        assert result.product_summary.summary == mock_summaries["product"].summary
        assert result.developer_summary.summary == mock_summaries["developer"].summary
        assert result.model_used == "claude-adk-claude-3-opus"
        assert result.total_tokens > 0  # Based on confidence scores
        assert result.cached is False

    @pytest.mark.asyncio
    async def test_generate_summaries_with_error(
        self,
        claude_adk_service,
        sample_code_changes,
        sample_repo_context,
        sample_pr_metadata,
    ):
        """Test summary generation with error handling."""
        # Mock the orchestrator to raise an exception
        claude_adk_service.orchestrator.generate_summaries = AsyncMock(
            side_effect=Exception("API error")
        )

        # Generate summaries
        result = await claude_adk_service.generate_summaries(
            sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Verify error summaries
        assert "Error generating summary" in result.executive_summary.summary
        assert result.executive_summary.confidence == 0.0
        assert result.product_summary.confidence == 0.0
        assert result.developer_summary.confidence == 0.0
        assert result.model_used == "claude-adk-claude-3-opus"
        assert result.total_tokens == 0

    def test_prepare_agent_context(
        self,
        claude_adk_service,
        sample_code_changes,
        sample_repo_context,
        sample_pr_metadata,
    ):
        """Test context preparation for agents."""
        context = claude_adk_service._prepare_agent_context(
            sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Verify PR context fields
        assert context["pr_title"] == "Add new feature for data processing"
        assert context["total_changes"] == 180
        assert context["files_changed"] == 3
        assert context["has_tests"] is True
        assert "tests" in context["change_categories"]

        # Verify repo context fields
        assert context["repo_name"] == "data-processor"
        assert context["repo_type"] == "library"
        assert "module_patterns" in context

    @pytest.mark.asyncio
    async def test_async_context_manager(self, claude_adk_service):
        """Test async context manager behavior."""
        async with claude_adk_service as service:
            assert service is claude_adk_service


class TestClaudeAgentIntegration:
    """Integration tests for Claude agents."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test that orchestrator initializes with all persona agents."""
        with patch("os.getenv", return_value="test-api-key"):
            from src.pr_agents.services.agents.claude_orchestrator import (
                ClaudeAgentOrchestrator,
            )

            orchestrator = ClaudeAgentOrchestrator()

            assert "executive" in orchestrator.agents
            assert "product" in orchestrator.agents
            assert "developer" in orchestrator.agents
            assert orchestrator.api_key == "test-api-key"

    def test_orchestrator_api_key_validation(self):
        """Test API key validation."""
        with patch("os.getenv", return_value=None):
            from src.pr_agents.services.agents.claude_orchestrator import (
                ClaudeAgentOrchestrator,
            )

            orchestrator = ClaudeAgentOrchestrator()
            assert not orchestrator.validate_api_key()
