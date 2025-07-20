"""Tests for agent context loader."""

from pathlib import Path

import pytest
import yaml

from src.pr_agents.config.agent_context_loader import AgentContextLoader


class TestAgentContextLoader:
    """Test agent context loader functionality."""

    @pytest.fixture
    def loader(self, tmp_path):
        """Create a loader with temporary directory."""
        return AgentContextLoader(tmp_path)

    def test_initialization(self, tmp_path):
        """Test loader initializes with proper directory structure."""
        loader = AgentContextLoader(tmp_path)

        assert loader.config_dir == Path(tmp_path)
        assert loader.agent_context_dir == tmp_path / "agent-contexts"
        assert loader.agent_context_dir.exists()

    def test_load_missing_context(self, loader):
        """Test loading context for repository with no config."""
        context = loader.load_agent_context("owner/repo")

        # Should return default context
        assert "pr_analysis" in context
        assert "common_patterns" in context["pr_analysis"]
        assert len(context["pr_analysis"]["common_patterns"]) == 0
        assert "quality_indicators" in context["pr_analysis"]
        assert len(context["pr_analysis"]["quality_indicators"]["good_pr"]) > 0
        assert "code_review_guidelines" in context

    def test_load_existing_context(self, loader):
        """Test loading existing agent context."""
        # Create test context file
        test_context = {
            "pr_analysis": {
                "common_patterns": [
                    {
                        "pattern": "Test pattern",
                        "indicators": ["test indicator"],
                        "review_focus": ["test focus"],
                    }
                ],
                "quality_indicators": {
                    "good_pr": ["Custom good indicator"],
                    "red_flags": ["Custom red flag"],
                },
            },
            "code_review_guidelines": {"required_checks": ["Custom check"]},
        }

        context_file = loader.agent_context_dir / "test-repo-agent.yaml"
        with open(context_file, "w") as f:
            yaml.safe_dump(test_context, f)

        # Load context
        loaded = loader.load_agent_context("owner/test-repo")

        assert loaded["pr_analysis"]["common_patterns"][0]["pattern"] == "Test pattern"
        assert loaded["pr_analysis"]["quality_indicators"]["good_pr"] == [
            "Custom good indicator"
        ]
        assert loaded["code_review_guidelines"]["required_checks"] == ["Custom check"]

    def test_load_invalid_yaml(self, loader):
        """Test handling of invalid YAML files."""
        # Create invalid YAML file
        context_file = loader.agent_context_dir / "invalid-agent.yaml"
        with open(context_file, "w") as f:
            f.write("invalid: yaml: content: [")

        # Should return default context without crashing
        context = loader.load_agent_context("owner/invalid")
        assert "pr_analysis" in context
        assert isinstance(context["pr_analysis"]["quality_indicators"]["good_pr"], list)

    def test_save_agent_context(self, loader):
        """Test saving agent context."""
        test_context = {
            "pr_analysis": {
                "common_patterns": [
                    {"pattern": "Saved pattern", "indicators": ["saved indicator"]}
                ]
            }
        }

        # Save context
        saved_path = loader.save_agent_context("owner/saved-repo", test_context)

        assert saved_path.exists()
        assert saved_path.name == "saved-repo-agent.yaml"

        # Verify content
        with open(saved_path) as f:
            loaded = yaml.safe_load(f)

        assert loaded["pr_analysis"]["common_patterns"][0]["pattern"] == "Saved pattern"

    def test_repo_name_normalization(self, loader):
        """Test repository name normalization for file paths."""
        # Test various repo name formats
        test_cases = [
            ("owner/Repo.Name", "repo-name-agent.yaml"),
            ("owner/repo_name", "repo_name-agent.yaml"),
            ("owner/REPO", "repo-agent.yaml"),
            ("owner/repo.js", "repo-js-agent.yaml"),
        ]

        for repo_name, expected_filename in test_cases:
            # Save with normalized name
            context = {"test": "data"}
            saved_path = loader.save_agent_context(repo_name, context)
            assert saved_path.name == expected_filename

    def test_default_context_structure(self, loader):
        """Test the structure of default agent context."""
        context = loader._get_default_agent_context()

        # Check structure
        assert "pr_analysis" in context
        assert "code_review_guidelines" in context

        # Check pr_analysis sub-structure
        pr_analysis = context["pr_analysis"]
        assert "common_patterns" in pr_analysis
        assert "quality_indicators" in pr_analysis
        assert "review_focus" in pr_analysis

        # Check quality indicators
        qi = pr_analysis["quality_indicators"]
        assert "good_pr" in qi
        assert "red_flags" in qi
        assert isinstance(qi["good_pr"], list)
        assert isinstance(qi["red_flags"], list)

        # Check code review guidelines
        crg = context["code_review_guidelines"]
        assert "required_checks" in crg
        assert "performance_considerations" in crg
        assert "security_considerations" in crg
        assert isinstance(crg["required_checks"], list)
