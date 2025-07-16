"""Unit tests for prompt builder."""

import pytest

from src.pr_agents.pr_processing.models import CodeChanges, FileDiff
from src.pr_agents.services.ai.prompts import PromptBuilder


class TestPromptBuilder:
    """Test cases for PromptBuilder."""

    @pytest.fixture
    def prompt_builder(self):
        """Create a prompt builder instance."""
        return PromptBuilder()

    @pytest.fixture
    def sample_code_changes(self):
        """Create sample code changes."""
        return CodeChanges(
            file_diffs=[
                FileDiff(
                    filename="modules/sevioBidAdapter.js",
                    status="added",
                    additions=250,
                    deletions=0,
                    changes=250,
                    patch="+ adapter implementation",
                ),
                FileDiff(
                    filename="test/spec/modules/sevioBidAdapter_spec.js",
                    status="added",
                    additions=150,
                    deletions=0,
                    changes=150,
                    patch="+ test implementation",
                ),
                FileDiff(
                    filename="modules/sevioBidAdapter.md",
                    status="added",
                    additions=50,
                    deletions=0,
                    changes=50,
                    patch="+ documentation",
                ),
            ],
            total_additions=450,
            total_deletions=0,
            total_changes=450,
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
            "description": "Header bidding library for web advertising",
            "module_patterns": {
                "bid_adapter": ["modules/*BidAdapter.js"],
                "analytics": ["modules/*AnalyticsAdapter.js"],
            },
            "structure": {
                "core_paths": ["src/"],
                "test_paths": ["test/spec/"],
                "doc_paths": ["docs/"],
            },
            "primary_language": "JavaScript",
            "languages": ["JavaScript", "Markdown"],
        }

    @pytest.fixture
    def sample_pr_metadata(self):
        """Create sample PR metadata."""
        return {
            "title": "Add Sevio Bid Adapter",
            "description": "This PR adds a new bid adapter for Sevio DSP. It supports banner and native ad formats with digital wallet detection for Web3 targeting.",
            "base_branch": "master",
            "head_branch": "feature/sevio-adapter",
        }

    def test_build_prompt_executive(
        self,
        prompt_builder,
        sample_code_changes,
        sample_repo_context,
        sample_pr_metadata,
    ):
        """Test building executive prompt."""
        # Act
        prompt = prompt_builder.build_prompt(
            "executive", sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Assert
        assert "executive audience" in prompt
        assert "prebid/Prebid.js" in prompt
        assert "Add Sevio Bid Adapter" in prompt
        assert "Files Changed: 3" in prompt
        assert "Lines Added: 450" in prompt

    def test_build_prompt_product(
        self,
        prompt_builder,
        sample_code_changes,
        sample_repo_context,
        sample_pr_metadata,
    ):
        """Test building product manager prompt."""
        # Act
        prompt = prompt_builder.build_prompt(
            "product", sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Assert
        assert "product manager" in prompt
        assert "Add Sevio Bid Adapter" in prompt
        assert "supports banner and native" in prompt
        assert "File Types: js(2), md(1)" in prompt

    def test_build_prompt_developer(
        self,
        prompt_builder,
        sample_code_changes,
        sample_repo_context,
        sample_pr_metadata,
    ):
        """Test building developer prompt."""
        # Act
        prompt = prompt_builder.build_prompt(
            "developer", sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Assert
        assert "software engineer" in prompt
        assert "Base Branch: master" in prompt
        assert "Head Branch: feature/sevio-adapter" in prompt
        assert "Primary Language: JavaScript" in prompt
        assert "Modified Paths: modules, test" in prompt
        assert "Test files: 1" in prompt

    def test_build_prompt_invalid_persona(
        self,
        prompt_builder,
        sample_code_changes,
        sample_repo_context,
        sample_pr_metadata,
    ):
        """Test error with invalid persona."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown persona: invalid"):
            prompt_builder.build_prompt(
                "invalid", sample_code_changes, sample_repo_context, sample_pr_metadata
            )

    def test_extract_template_variables_file_types(
        self,
        prompt_builder,
        sample_code_changes,
        sample_repo_context,
        sample_pr_metadata,
    ):
        """Test file type extraction."""
        # Act
        variables = prompt_builder._extract_template_variables(
            "executive", sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Assert
        assert variables["file_types"] == "js(2), md(1)"
        assert variables["file_count"] == 3

    def test_extract_template_variables_modified_paths(
        self,
        prompt_builder,
        sample_code_changes,
        sample_repo_context,
        sample_pr_metadata,
    ):
        """Test modified paths extraction."""
        # Act
        variables = prompt_builder._extract_template_variables(
            "developer", sample_code_changes, sample_repo_context, sample_pr_metadata
        )

        # Assert
        assert "modules" in variables["modified_paths"]
        assert "test" in variables["modified_paths"]

    def test_format_repo_context_with_patterns(
        self, prompt_builder, sample_repo_context
    ):
        """Test repository context formatting."""
        # Act
        formatted = prompt_builder._format_repo_context(sample_repo_context)

        # Assert
        assert "Description: Header bidding library" in formatted
        assert "Module Types:" in formatted
        assert "bid_adapter: modules/*BidAdapter.js" in formatted
        assert "Repository Structure:" in formatted
        assert "core_paths: ['src/']" in formatted

    def test_format_repo_context_empty(self, prompt_builder):
        """Test empty repository context."""
        # Act
        formatted = prompt_builder._format_repo_context({})

        # Assert
        assert formatted == "No specific repository context available"

    def test_detect_code_patterns(self, prompt_builder, sample_code_changes):
        """Test code pattern detection."""
        # Act
        patterns = prompt_builder._detect_code_patterns(sample_code_changes)

        # Assert
        assert "Test files: 1" in patterns
        assert "Documentation files: 1" in patterns

    def test_description_preview_truncation(self, prompt_builder):
        """Test description preview truncation."""
        # Arrange
        long_description = "A" * 300
        metadata = {"description": long_description}

        # Act
        preview = prompt_builder._get_description_preview(metadata)

        # Assert
        assert len(preview) == 203  # 200 chars + "..."
        assert preview.endswith("...")

    def test_build_developer_diff_analysis(self, prompt_builder, sample_code_changes):
        """Test developer diff analysis building."""
        # Act
        analysis = prompt_builder._build_developer_diff_analysis(sample_code_changes)

        # Assert
        assert "modules/: 2 files, 300 total changes" in analysis
        # The test file is in test/spec/modules/, so it gets grouped there
        assert "test/spec/modules/: 1 files, 150 total changes" in analysis
