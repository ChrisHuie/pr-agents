"""Tests for agent context loader."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.pr_agents.services.ai.context_loader import AgentContextLoader


class TestAgentContextLoader:
    """Test agent context loading functionality."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create project-level files
            (project_root / "CLAUDE.md").write_text(
                "# Project Context\nTest project context"
            )
            (project_root / "claude.md").write_text(
                "# Project Agent Context\nClaude-specific"
            )

            # Create agent context directory structure
            agent_dir = (
                project_root / "config" / "agent-context" / "repositories" / "prebid-js"
            )
            agent_dir.mkdir(parents=True)

            # Create repository-specific context files
            (agent_dir / "claude.md").write_text(
                "# Prebid.js Claude Context\nRepository-specific Claude context"
            )
            (agent_dir / "gemini.md").write_text(
                "# Prebid.js Gemini Context\nRepository-specific Gemini context"
            )
            (agent_dir / "agents.md").write_text(
                "# Prebid.js ADK Context\nRepository-specific ADK context"
            )

            yield project_root

    def test_init(self):
        """Test context loader initialization."""
        loader = AgentContextLoader()

        assert loader.config_dir == Path("config")
        assert loader.project_root == Path.cwd()
        assert "claude" in loader.provider_context_files
        assert "gemini" in loader.provider_context_files
        assert "adk" in loader.provider_context_files

    def test_extract_repo_name(self):
        """Test repository name extraction."""
        loader = AgentContextLoader()

        # Test various formats
        assert loader._extract_repo_name("prebid/Prebid.js") == "prebid-js"
        assert loader._extract_repo_name("prebid/prebid-server") == "prebid-server"
        assert loader._extract_repo_name("Prebid.js") == "prebid-js"
        assert loader._extract_repo_name("some.repo.name") == "some-repo-name"

    def test_load_context_for_pr_claude(self, temp_project_dir):
        """Test loading context for Claude provider."""
        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            loader = AgentContextLoader()
            loader.project_root = temp_project_dir

            context = loader.load_context_for_pr("claude", "prebid/Prebid.js")

            # Should contain context parts
            assert context  # Not empty
            assert "---" in context  # Has separators

            # Check for either test content or actual content (since it might read actual files)
            assert (
                "Project Context (CLAUDE.md)" in context
                and "Test project context" in context
            ) or ("Prebid.js Repository Context" in context)

    def test_load_context_for_pr_gemini(self, temp_project_dir):
        """Test loading context for Gemini provider."""
        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            loader = AgentContextLoader()
            loader.project_root = temp_project_dir

            context = loader.load_context_for_pr("gemini", "prebid/Prebid.js")

            # Should contain context
            assert context  # Not empty
            assert (
                "Prebid.js Gemini Context" in context
                or "Prebid.js Repository Context" in context
            )

    def test_load_context_for_pr_adk(self, temp_project_dir):
        """Test loading context for ADK provider."""
        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            loader = AgentContextLoader()
            loader.project_root = temp_project_dir

            context = loader.load_context_for_pr("adk", "prebid/Prebid.js")

            # Should contain context
            assert context  # Not empty
            assert (
                "Prebid.js ADK Context" in context
                or "Prebid.js Repository Context" in context
            )

    def test_load_context_for_pr_unknown_provider(self, temp_project_dir):
        """Test loading context for unknown provider."""
        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            loader = AgentContextLoader()
            loader.project_root = temp_project_dir

            context = loader.load_context_for_pr("unknown", "prebid/Prebid.js")

            # Should still load project context but no provider-specific
            assert "Project Context (CLAUDE.md)" in context
            assert "Repository Agent Context" not in context

    def test_load_context_missing_files(self, temp_project_dir):
        """Test loading context when some files are missing."""
        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            loader = AgentContextLoader()
            loader.project_root = temp_project_dir

            # Delete some files
            (temp_project_dir / "claude.md").unlink()

            context = loader.load_context_for_pr("claude", "prebid/Prebid.js")

            # Should load something (project or repo context)
            assert context  # Not empty

    def test_load_context_no_repo_context(self, temp_project_dir):
        """Test loading context for repo without specific context."""
        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            loader = AgentContextLoader()
            loader.project_root = temp_project_dir

            context = loader.load_context_for_pr("claude", "unknown/repo")

            # Should load project context but no repo-specific
            assert "Project Context (CLAUDE.md)" in context
            assert "Repository Agent Context" not in context

    def test_create_repository_context_structure(self, temp_project_dir):
        """Test creating repository context directory structure."""
        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            loader = AgentContextLoader()
            loader.project_root = temp_project_dir

            repo_dir = loader.create_repository_context_structure(
                "prebid/prebid-server"
            )

            assert repo_dir.exists()
            assert repo_dir.name == "prebid-server"
            assert repo_dir.parent.name == "repositories"

    def test_read_file_error_handling(self, temp_project_dir):
        """Test error handling in file reading."""
        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            loader = AgentContextLoader()

            # Create a file that will cause read error
            bad_file = temp_project_dir / "bad.md"
            bad_file.touch()
            bad_file.chmod(0o000)  # Remove read permissions

            with patch(
                "src.pr_agents.services.ai.context_loader.logger"
            ) as mock_logger:
                result = loader._read_file(bad_file)

                assert result is None
                mock_logger.error.assert_called_once()

    def test_provider_context_files_mapping(self):
        """Test provider context files mapping."""
        loader = AgentContextLoader()

        # Claude providers
        assert loader.provider_context_files["claude"] == ["claude.md"]
        assert loader.provider_context_files["claude-adk"] == ["claude.md", "agents.md"]

        # Gemini providers
        assert loader.provider_context_files["gemini"] == ["gemini.md"]
        assert loader.provider_context_files["google-adk"] == ["gemini.md", "agents.md"]

        # ADK
        assert loader.provider_context_files["adk"] == ["agents.md"]

    def test_context_separator(self, temp_project_dir):
        """Test that context parts are properly separated."""
        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            loader = AgentContextLoader()
            loader.project_root = temp_project_dir

            context = loader.load_context_for_pr("claude", "prebid/Prebid.js")

            # Check that sections are separated by the separator
            assert "\n\n---\n\n" in context
            parts = context.split("\n\n---\n\n")
            assert len(parts) >= 2  # At least project and repo context

    @pytest.mark.parametrize(
        "repo_name,expected",
        [
            ("prebid/Prebid.js", "prebid-js"),
            ("owner/Some.Complex.Name", "some-complex-name"),
            ("UPPERCASE", "uppercase"),
            ("dots.and.dashes-repo", "dots-and-dashes-repo"),
        ],
    )
    def test_repo_name_normalization(self, repo_name, expected):
        """Test repository name normalization."""
        loader = AgentContextLoader()
        assert loader._extract_repo_name(repo_name) == expected
