"""Tests for output manager repository structure and auto-naming."""

from pathlib import Path

import pytest

from src.pr_agents.output import OutputManager


class TestOutputManagerRepoStructure:
    """Test output manager with repository structure and auto-naming."""

    @pytest.fixture
    def manager(self):
        """Create output manager instance."""
        return OutputManager()

    @pytest.fixture
    def sample_pr_data(self):
        """Sample PR data with repository and module information."""
        return {
            "pr_url": "https://github.com/prebid/Prebid.js/pull/12440",
            "pr_number": 12440,
            "repository": {"full_name": "prebid/Prebid.js"},
            "modules": {
                "modules": [{"name": "seedtagBidAdapter", "type": "bid_adapter"}],
                "total_modules": 1,
            },
        }

    def test_repo_structure_enabled(self, manager, sample_pr_data, tmp_path):
        """Test saving with repository structure enabled."""
        # Change to tmp_path for testing
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Save with repo structure
            saved_path = manager.save(
                sample_pr_data,
                "test-file",
                format_type="markdown",
                repo_structure=True,
            )

            # Check path structure
            assert saved_path.exists()
            assert "output/Prebid.js/test-file.md" in str(saved_path)

            # Verify directory structure was created
            output_dir = Path("output/Prebid.js")
            assert output_dir.exists()
            assert output_dir.is_dir()
        finally:
            os.chdir(original_cwd)

    def test_repo_structure_disabled(self, manager, sample_pr_data, tmp_path):
        """Test saving with repository structure disabled."""
        # Save without repo structure
        saved_path = manager.save(
            sample_pr_data,
            tmp_path / "test-file",
            format_type="markdown",
            repo_structure=False,
        )

        # Should save directly to specified path
        assert saved_path == tmp_path / "test-file.md"
        assert saved_path.exists()

    def test_auto_naming_with_pr_number(self, manager, sample_pr_data, tmp_path):
        """Test auto-naming with PR number."""
        # Change to tmp_path
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            saved_path = manager.save(
                sample_pr_data,
                "analysis",  # Use generic name that should be replaced
                format_type="markdown",
                auto_name=True,
            )

            # Should use PR number and module in filename
            assert saved_path.name == "PR12440-seedtagBidAdapter.md"
        finally:
            os.chdir(original_cwd)

    def test_auto_naming_with_module(self, manager, sample_pr_data, tmp_path):
        """Test auto-naming includes module name."""
        # Add module to trigger module naming
        sample_pr_data["modules"]["modules"][0]["name"] = "appnexusBidAdapter"

        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            saved_path = manager.save(
                sample_pr_data,
                "analysis",  # Use generic name
                format_type="markdown",
                auto_name=True,
            )

            # Should include PR number and module
            assert saved_path.name == "PR12440-appnexusBidAdapter.md"
        finally:
            os.chdir(original_cwd)

    def test_auto_naming_multiple_modules(self, manager, tmp_path):
        """Test auto-naming with multiple modules."""
        data = {
            "pr_number": 123,
            "modules": {
                "modules": [
                    {"name": "module1BidAdapter", "type": "bid_adapter"},
                    {"name": "module2BidAdapter", "type": "bid_adapter"},
                    {"name": "module3BidAdapter", "type": "bid_adapter"},
                ],
            },
        }

        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            saved_path = manager.save(
                data,
                "analysis",  # Use generic name
                format_type="markdown",
                auto_name=True,
            )

            # Should show "multiple" when more than 2 modules
            assert saved_path.name == "PR123-multiple-modules.md"
        finally:
            os.chdir(original_cwd)

    def test_auto_naming_no_pr_number(self, manager, tmp_path):
        """Test auto-naming without PR number."""
        data = {
            "modules": {
                "modules": [{"name": "testModule", "type": "generic"}],
            },
        }

        saved_path = manager.save(
            data,
            tmp_path / "fallback-name",
            format_type="markdown",
            auto_name=True,
        )

        # Should use provided name when no PR number
        assert saved_path.name == "fallback-name.md"

    def test_absolute_path_ignores_repo_structure(
        self, manager, sample_pr_data, tmp_path
    ):
        """Test that absolute paths ignore repository structure."""
        absolute_path = tmp_path / "custom" / "location" / "file"

        saved_path = manager.save(
            sample_pr_data,
            absolute_path,
            format_type="markdown",
            repo_structure=True,  # Should be ignored for absolute paths
        )

        # Should save to absolute path
        assert saved_path == absolute_path.with_suffix(".md")
        assert saved_path.parent == tmp_path / "custom" / "location"

    def test_missing_repository_info(self, manager, tmp_path):
        """Test handling of missing repository information."""
        data = {"pr_number": 123}  # No repository info

        saved_path = manager.save(
            data,
            tmp_path / "test",
            format_type="markdown",
            repo_structure=True,
        )

        # Should save without repo structure when info is missing
        assert saved_path == tmp_path / "test.md"

    def test_special_characters_in_module_names(self, manager, tmp_path):
        """Test that special characters are cleaned from module names."""
        data = {
            "pr_number": 123,
            "modules": {
                "modules": [{"name": "test/module@adapter!", "type": "generic"}],
            },
        }

        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            saved_path = manager.save(
                data,
                "analysis",  # Use generic name
                format_type="markdown",
                auto_name=True,
            )

            # Special characters should be removed
            assert saved_path.name == "PR123-testmoduleadapter.md"
        finally:
            os.chdir(original_cwd)

    def test_combined_repo_structure_and_auto_naming(
        self, manager, sample_pr_data, tmp_path
    ):
        """Test using both repository structure and auto-naming together."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            saved_path = manager.save(
                sample_pr_data,
                "analysis",  # Use generic name
                format_type="markdown",
                repo_structure=True,
                auto_name=True,
            )

            # Should have both repo structure and auto-generated name
            assert "output/Prebid.js/PR12440-seedtagBidAdapter.md" in str(
                saved_path
            )
            assert saved_path.exists()
        finally:
            os.chdir(original_cwd)
