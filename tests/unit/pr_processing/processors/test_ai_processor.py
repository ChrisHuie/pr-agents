"""Unit tests for AI processor."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.pr_agents.pr_processing.analysis_models import AISummaries, PersonaSummary
from src.pr_agents.pr_processing.models import CodeChanges, FileDiff
from src.pr_agents.pr_processing.processors.ai_processor import AIProcessor
from src.pr_agents.pr_processing.processors.base import ProcessingResult


class TestAIProcessor:
    """Test cases for AIProcessor."""

    @pytest.fixture
    def mock_ai_service(self):
        """Create a mock AI service."""
        service = Mock()
        service.generate_summaries = AsyncMock(
            return_value=AISummaries(
                executive_summary=PersonaSummary(
                    persona="executive",
                    summary="Executive summary of changes",
                    confidence=0.95,
                ),
                product_summary=PersonaSummary(
                    persona="product",
                    summary="Product manager summary of changes",
                    confidence=0.90,
                ),
                developer_summary=PersonaSummary(
                    persona="developer",
                    summary="Developer technical summary",
                    confidence=0.85,
                ),
                model_used="test-model",
                generation_timestamp=datetime.now(),
                cached=False,
                total_tokens=500,
                generation_time_ms=1000,
            )
        )
        return service

    @pytest.fixture
    def mock_repo_config_manager(self):
        """Create a mock repository config manager."""
        manager = Mock()
        manager.get_config_for_url = Mock(
            return_value={
                "repo_type": "prebid-js",
                "description": "Header bidding library",
                "module_locations": {
                    "bid_adapter": ["modules/*BidAdapter.js"],
                },
                "core_paths": ["src/"],
                "test_paths": ["test/"],
                "doc_paths": ["docs/"],
            }
        )
        return manager

    @pytest.fixture
    def ai_processor(self, mock_ai_service, mock_repo_config_manager):
        """Create AI processor with mocks."""
        return AIProcessor(
            ai_service=mock_ai_service,
            repo_config_manager=mock_repo_config_manager,
        )

    @pytest.fixture
    def sample_component_data(self):
        """Create sample component data for processing."""
        return {
            "code": CodeChanges(
                file_diffs=[
                    FileDiff(
                        filename="modules/exampleBidAdapter.js",
                        status="added",
                        additions=200,
                        deletions=0,
                        changes=200,
                        patch="+ adapter code",
                    ),
                    FileDiff(
                        filename="test/spec/modules/exampleBidAdapter_spec.js",
                        status="added",
                        additions=100,
                        deletions=0,
                        changes=100,
                        patch="+ test code",
                    ),
                ],
                total_additions=300,
                total_deletions=0,
                total_changes=300,
                changed_files=2,
                base_sha="abc123",
                head_sha="def456",
            ),
            "metadata": {
                "title": "Add Example Bid Adapter",
                "description": "This PR adds support for Example DSP",
                "base": {"ref": "master"},
                "head": {"ref": "feature/example-adapter"},
            },
            "repo_url": "https://github.com/prebid/Prebid.js",
        }

    def test_component_name(self, ai_processor):
        """Test component name property."""
        assert ai_processor.component_name == "ai_summaries"

    def test_process_success(
        self, ai_processor, sample_component_data, mock_ai_service
    ):
        """Test successful processing."""
        # Act
        result = ai_processor.process(sample_component_data)

        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.component == "ai_summaries"
        assert result.success is True
        assert "executive_summary" in result.data
        assert "product_summary" in result.data
        assert "developer_summary" in result.data
        assert result.data["model_used"] == "test-model"

        # Verify AI service was called
        mock_ai_service.generate_summaries.assert_called_once()

    def test_process_no_code_data(self, ai_processor):
        """Test processing with missing code data."""
        # Arrange
        component_data = {"metadata": {}, "repo_url": ""}

        # Act
        result = ai_processor.process(component_data)

        # Assert
        assert result.success is False
        assert result.errors == ["No code data provided for AI analysis"]

    def test_process_with_exception(
        self, ai_processor, sample_component_data, mock_ai_service
    ):
        """Test processing with AI service exception."""
        # Arrange
        mock_ai_service.generate_summaries.side_effect = Exception("AI service error")

        # Act
        result = ai_processor.process(sample_component_data)

        # Assert
        assert result.success is False
        assert len(result.errors) == 1
        assert "AI processing error: AI service error" in result.errors[0]

    def test_build_repo_context_with_config(
        self, ai_processor, mock_repo_config_manager
    ):
        """Test building repository context with config."""
        # Arrange
        repo_url = "https://github.com/prebid/Prebid.js"
        code_data = {"file_diffs": []}

        # Act
        context = ai_processor._build_repo_context(repo_url, code_data)

        # Assert
        assert context["name"] == "prebid/Prebid.js"
        assert context["url"] == repo_url
        assert context["type"] == "prebid-js"
        assert context["description"] == "Header bidding library"
        assert "module_patterns" in context
        assert "structure" in context

    def test_build_repo_context_without_config(self, ai_processor):
        """Test building repository context without config."""
        # Arrange
        ai_processor.repo_config_manager = None
        repo_url = "https://github.com/example/repo"
        code_data = {"file_diffs": []}

        # Act
        context = ai_processor._build_repo_context(repo_url, code_data)

        # Assert
        assert context["name"] == "example/repo"
        assert context["url"] == repo_url
        assert "type" not in context

    def test_extract_repo_name_github(self, ai_processor):
        """Test extracting repository name from GitHub URL."""
        # Test various GitHub URL formats
        urls = [
            ("https://github.com/owner/repo", "owner/repo"),
            ("https://github.com/owner/repo/", "owner/repo"),
            ("https://github.com/owner/repo.git", "owner/repo.git"),
            ("http://github.com/owner/repo", "owner/repo"),
        ]

        for url, expected in urls:
            assert ai_processor._extract_repo_name(url) == expected

    def test_extract_repo_name_non_github(self, ai_processor):
        """Test extracting repository name from non-GitHub URL."""
        assert (
            ai_processor._extract_repo_name("https://gitlab.com/owner/repo")
            == "https://gitlab.com/owner/repo"
        )
        assert ai_processor._extract_repo_name("") == "unknown"

    def test_detect_languages(self, ai_processor):
        """Test language detection from file extensions."""
        # Arrange
        file_diffs = [
            {"filename": "src/main.js"},
            {"filename": "src/utils.ts"},
            {"filename": "test/test.js"},
            {"filename": "docs/README.md"},
            {"filename": "config.json"},
            {"filename": "styles.css"},
        ]

        # Act
        languages = ai_processor._detect_languages(file_diffs)

        # Assert
        assert languages[0] == "JavaScript"  # Most common
        assert "TypeScript" in languages
        assert "Markdown" in languages
        assert "JSON" in languages
        assert "CSS" in languages

    def test_detect_languages_prebid_specific(self, ai_processor):
        """Test language detection for Prebid-specific files."""
        # Arrange
        file_diffs = [
            {"filename": "modules/exampleBidAdapter.js"},
            {"filename": "src/main.go"},
            {"filename": "Example.java"},
            {"filename": "Example.swift"},
            {"filename": "Example.m"},
            {"filename": "Example.kt"},
        ]

        # Act
        languages = ai_processor._detect_languages(file_diffs)

        # Assert
        assert "JavaScript" in languages
        assert "Go" in languages
        assert "Java" in languages
        assert "Swift" in languages
        assert "Objective-C" in languages
        assert "Kotlin" in languages

    def test_repo_config_manager_error_handling(
        self, ai_processor, mock_repo_config_manager
    ):
        """Test handling of repo config manager errors."""
        # Arrange
        mock_repo_config_manager.get_config_for_url.side_effect = Exception(
            "Config error"
        )
        repo_url = "https://github.com/prebid/Prebid.js"
        code_data = {"file_diffs": []}

        # Act
        context = ai_processor._build_repo_context(repo_url, code_data)

        # Assert
        # Should still return basic context despite error
        assert context["name"] == "prebid/Prebid.js"
        assert context["url"] == repo_url
        assert "type" not in context  # Config-specific field should be missing
