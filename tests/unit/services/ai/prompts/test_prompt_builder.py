"""Tests for prompt builder with agent context support."""

import pytest

from src.pr_agents.pr_processing.models import CodeChanges, FileDiff
from src.pr_agents.services.ai.prompts.builder import PromptBuilder


class TestPromptBuilder:
    """Test prompt builder functionality."""

    @pytest.fixture
    def code_changes(self):
        """Create sample code changes."""
        return CodeChanges(
            file_diffs=[
                FileDiff(
                    filename="modules/exampleBidAdapter.js",
                    status="added",
                    additions=100,
                    deletions=0,
                    patch="+ new bid adapter code",
                ),
                FileDiff(
                    filename="test/spec/modules/exampleBidAdapter_spec.js",
                    status="added",
                    additions=50,
                    deletions=0,
                    patch="+ test code",
                ),
            ],
            total_additions=150,
            total_deletions=0,
            commits=[],
            base_sha="abc123",
            head_sha="def456",
        )

    @pytest.fixture
    def repo_context(self):
        """Create sample repository context."""
        return {
            "name": "Prebid.js",
            "full_name": "prebid/Prebid.js",
            "type": "prebid-js",
            "description": "Header bidding library",
            "primary_language": "JavaScript",
            "module_patterns": {
                "bid_adapter": ["modules/*BidAdapter.js"],
                "analytics": ["modules/*AnalyticsAdapter.js"],
            },
            "structure": {
                "modules": "Plugin modules directory",
                "src": "Core library code",
            },
        }

    @pytest.fixture
    def pr_metadata(self):
        """Create sample PR metadata."""
        return {
            "title": "Add example bid adapter",
            "description": "This PR adds a new bid adapter for Example SSP",
            "base_branch": "main",
            "head_branch": "feature/example-adapter",
        }

    @pytest.fixture
    def builder(self):
        """Create prompt builder instance."""
        return PromptBuilder()

    def test_build_prompt_executive(
        self, builder, code_changes, repo_context, pr_metadata
    ):
        """Test building executive prompt."""
        prompt = builder.build_prompt(
            "executive", code_changes, repo_context, pr_metadata
        )

        assert "Executive Summary" in prompt
        assert "Prebid.js" in prompt
        assert "2 files modified" in prompt
        assert "150 additions" in prompt

    def test_build_prompt_product(
        self, builder, code_changes, repo_context, pr_metadata
    ):
        """Test building product prompt."""
        prompt = builder.build_prompt(
            "product", code_changes, repo_context, pr_metadata
        )

        assert "Product Summary:" in prompt
        assert "modules/exampleBidAdapter.js" in prompt
        assert "test/spec/modules/exampleBidAdapter_spec.js" in prompt

    def test_build_prompt_developer(
        self, builder, code_changes, repo_context, pr_metadata
    ):
        """Test building developer prompt."""
        prompt = builder.build_prompt(
            "developer", code_changes, repo_context, pr_metadata
        )

        assert "Technical Summary:" in prompt
        assert "Test files: 1" in prompt
        assert "modules/: 1 files, 100 total changes" in prompt

    def test_build_prompt_with_agent_context(
        self, builder, code_changes, repo_context, pr_metadata
    ):
        """Test building prompt with agent context."""
        agent_context = """# Repository Context for Prebid.js

        Prebid.js is a header bidding library that enables real-time auctions.
        
        ## Module Types
        - Bid Adapters: Connect to SSPs
        - Analytics Adapters: Track metrics
        """

        prompt = builder.build_prompt(
            "executive", code_changes, repo_context, pr_metadata, agent_context
        )

        # Should have agent context prepended
        assert prompt.startswith("# Repository Context for Prebid.js")
        assert "---" in prompt  # Separator
        assert "Executive Summary" in prompt  # Original prompt content

    def test_build_prompt_without_agent_context(
        self, builder, code_changes, repo_context, pr_metadata
    ):
        """Test building prompt without agent context."""
        prompt = builder.build_prompt(
            "executive", code_changes, repo_context, pr_metadata, agent_context=None
        )

        # Should not have agent context
        assert "Repository Context for Prebid.js" not in prompt
        assert not prompt.startswith("#")
        assert "Executive Summary" in prompt

    def test_build_prompt_unknown_persona(
        self, builder, code_changes, repo_context, pr_metadata
    ):
        """Test building prompt with unknown persona."""
        with pytest.raises(ValueError, match="Unknown persona: unknown"):
            builder.build_prompt("unknown", code_changes, repo_context, pr_metadata)

    def test_extract_template_variables(
        self, builder, code_changes, repo_context, pr_metadata
    ):
        """Test template variable extraction."""
        vars_dict = builder._extract_template_variables(
            "executive", code_changes, repo_context, pr_metadata
        )

        assert vars_dict["repo_name"] == "Prebid.js"
        assert vars_dict["repo_type"] == "prebid-js"
        assert vars_dict["pr_title"] == "Add example bid adapter"
        assert vars_dict["file_count"] == 2
        assert vars_dict["additions"] == 150
        assert vars_dict["deletions"] == 0
        assert "js(2)" in vars_dict["file_types"]

    def test_get_description_preview(self, builder):
        """Test description preview generation."""
        # Short description
        pr_meta = {"description": "Short description"}
        preview = builder._get_description_preview(pr_meta)
        assert preview == "Short description"

        # Long description
        pr_meta = {"description": "A" * 250}
        preview = builder._get_description_preview(pr_meta)
        assert len(preview) == 203  # 200 + "..."
        assert preview.endswith("...")

        # No description
        pr_meta = {}
        preview = builder._get_description_preview(pr_meta)
        assert preview == "No description provided"

    def test_get_file_types(self, builder, code_changes):
        """Test file type extraction."""
        file_types = builder._get_file_types(code_changes)
        assert "js(2)" in file_types

    def test_get_modified_paths(self, builder, code_changes):
        """Test modified path extraction."""
        paths = builder._get_modified_paths(code_changes)
        assert paths == "modules, test"

    def test_format_repo_context(self, builder, repo_context):
        """Test repository context formatting."""
        formatted = builder._format_repo_context(repo_context)

        assert "Description: Header bidding library" in formatted
        assert "Module Types:" in formatted
        assert "bid_adapter: modules/*BidAdapter.js" in formatted
        assert "Repository Structure:" in formatted

    def test_build_executive_summary(self, builder, code_changes):
        """Test executive summary building."""
        summary = builder._build_executive_summary(code_changes)

        assert "2 files modified" in summary
        assert "150 additions and 0 deletions" in summary
        assert "Key files: modules/exampleBidAdapter.js" in summary

    def test_detect_code_patterns(self, builder, code_changes):
        """Test code pattern detection."""
        patterns = builder._detect_code_patterns(code_changes)

        assert "Test files: 1" in patterns

    def test_build_developer_diff_analysis(self, builder, code_changes):
        """Test developer diff analysis."""
        analysis = builder._build_developer_diff_analysis(code_changes)

        assert "modules/: 1 files, 100 total changes" in analysis
        assert "test/spec/modules/: 1 files, 50 total changes" in analysis

    def test_empty_code_changes(self, builder, repo_context, pr_metadata):
        """Test handling empty code changes."""
        empty_changes = CodeChanges(
            file_diffs=[],
            total_additions=0,
            total_deletions=0,
            commits=[],
            base_sha="abc123",
            head_sha="def456",
        )

        prompt = builder.build_prompt(
            "executive", empty_changes, repo_context, pr_metadata
        )

        assert "0 files modified" in prompt
        assert "0 additions" in prompt

    @pytest.mark.parametrize("persona", ["executive", "product", "developer"])
    def test_all_personas_with_agent_context(
        self, builder, code_changes, repo_context, pr_metadata, persona
    ):
        """Test all personas work with agent context."""
        agent_context = "# Test Agent Context"

        prompt = builder.build_prompt(
            persona, code_changes, repo_context, pr_metadata, agent_context
        )

        assert prompt.startswith("# Test Agent Context")
        assert "---" in prompt
