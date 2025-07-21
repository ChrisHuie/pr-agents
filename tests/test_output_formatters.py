"""
Tests for output formatters.
"""

import json

import pytest

from src.pr_agents.output import (
    JSONFormatter,
    MarkdownFormatter,
    OutputManager,
    TextFormatter,
)


class TestBaseFormatter:
    """Test base formatter functionality."""

    def test_file_extensions(self):
        """Test that formatters return correct file extensions."""
        assert MarkdownFormatter().get_file_extension() == ".md"
        assert TextFormatter().get_file_extension() == ".txt"
        assert JSONFormatter().get_file_extension() == ".json"


class TestMarkdownFormatter:
    """Test Markdown formatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return MarkdownFormatter()

    @pytest.fixture
    def sample_data(self):
        """Sample PR analysis data."""
        return {
            "pr_url": "https://github.com/owner/repo/pull/123",
            "pr_number": 123,
            "repository": "owner/repo",
            "metadata": {
                "title_quality": {
                    "score": 85,
                    "quality_level": "excellent",
                    "issues": [],
                },
                "description_quality": {
                    "score": 70,
                    "quality_level": "good",
                    "issues": ["Could be more detailed"],
                },
                "label_analysis": {
                    "total_count": 3,
                    "categorized": {
                        "type": ["feature", "enhancement"],
                        "priority": ["high"],
                    },
                },
            },
            "code_changes": {
                "change_stats": {
                    "total_changes": 150,
                    "total_additions": 100,
                    "total_deletions": 50,
                    "changed_files": 5,
                },
                "risk_assessment": {
                    "risk_level": "medium",
                    "risk_score": 3,
                    "risk_factors": ["Large change size", "Critical files modified"],
                },
            },
        }

    def test_format_basic(self, formatter, sample_data):
        """Test basic markdown formatting."""
        result = formatter.format(sample_data)

        # Check header
        assert "# PR Analysis Report" in result
        assert "**Pull Request:** https://github.com/owner/repo/pull/123" in result
        assert "**PR Number:** #123" in result

        # Check sections
        assert "## 📋 Metadata Analysis" in result
        assert "## 💻 Files Changed" in result

        # Check content
        assert "Title Quality: excellent (85/100)" in result
        assert "Risk Level: medium" in result

    def test_format_empty_data(self, formatter):
        """Test formatting with minimal data."""
        result = formatter.format({})
        assert "# PR Analysis Report" in result

    def test_save_to_file(self, formatter, sample_data, tmp_path):
        """Test saving to file."""
        file_path = tmp_path / "test.md"
        formatter.save_to_file(sample_data, file_path)

        assert file_path.exists()
        content = file_path.read_text()
        assert "# PR Analysis Report" in content


class TestTextFormatter:
    """Test plain text formatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return TextFormatter()

    def test_format_basic(self, formatter):
        """Test basic text formatting."""
        data = {
            "pr_url": "https://github.com/owner/repo/pull/123",
            "metadata": {"title_quality": {"score": 85, "quality_level": "excellent"}},
        }

        result = formatter.format(data)

        # Check header
        assert "PR ANALYSIS REPORT" in result
        assert "=" * 80 in result

        # Check content
        assert "Pull Request: https://github.com/owner/repo/pull/123" in result
        assert "METADATA ANALYSIS" in result
        assert "Title Quality: excellent (85/100)" in result


class TestJSONFormatter:
    """Test JSON formatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return JSONFormatter()

    def test_format_basic(self, formatter):
        """Test basic JSON formatting."""
        data = {
            "pr_url": "https://github.com/owner/repo/pull/123",
            "metadata": {"score": 85},
        }

        result = formatter.format(data)
        parsed = json.loads(result)

        assert parsed["pr_url"] == "https://github.com/owner/repo/pull/123"
        assert parsed["metadata"]["score"] == 85

    def test_format_with_non_serializable(self, formatter):
        """Test formatting with non-serializable objects."""

        class CustomObject:
            def __str__(self):
                return "custom"

        data = {"object": CustomObject(), "none_value": None}

        result = formatter.format(data)
        parsed = json.loads(result)

        assert parsed["object"] == "custom"
        assert "none_value" not in parsed  # None values are filtered

    def test_validate_data(self, formatter):
        """Test data validation."""
        valid_data = {"key": "value", "number": 123}
        assert formatter.validate_data(valid_data) is True


class TestOutputManager:
    """Test output manager."""

    @pytest.fixture
    def manager(self):
        """Create output manager instance."""
        return OutputManager()

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return {
            "pr_url": "https://github.com/owner/repo/pull/123",
            "summary": "Test PR",
        }

    def test_format_with_different_types(self, manager, sample_data):
        """Test formatting with different output types."""
        markdown = manager.format(sample_data, "markdown")
        assert "# PR Analysis Report" in markdown

        text = manager.format(sample_data, "text")
        assert "PR ANALYSIS REPORT" in text

        json_output = manager.format(sample_data, "json")
        parsed = json.loads(json_output)
        assert parsed["pr_url"] == sample_data["pr_url"]

    def test_save_single_format(self, manager, sample_data, tmp_path):
        """Test saving in a single format."""
        file_path = tmp_path / "test"
        saved_path = manager.save(sample_data, file_path, "markdown")

        assert saved_path.exists()
        assert saved_path.suffix == ".md"
        assert saved_path.read_text().startswith("# PR Analysis Report")

    def test_save_multiple_formats(self, manager, sample_data, tmp_path):
        """Test saving in multiple formats."""
        base_path = tmp_path / "test"
        formats = ["markdown", "json", "text"]

        saved_files = manager.save_multiple_formats(sample_data, base_path, formats)

        assert len(saved_files) == 3

        # Check each file
        for file_path in saved_files:
            assert file_path.exists()

        # Verify extensions
        extensions = {f.suffix for f in saved_files}
        assert extensions == {".md", ".json", ".txt"}

    def test_infer_format_from_extension(self, manager, sample_data, tmp_path):
        """Test format inference from file extension."""
        # Test with .md extension
        file_path = tmp_path / "test.md"
        saved_path = manager.save(sample_data, file_path)
        assert saved_path.read_text().startswith("# PR Analysis Report")

        # Test with .json extension
        file_path = tmp_path / "test.json"
        saved_path = manager.save(sample_data, file_path)
        json.loads(saved_path.read_text())  # Should parse as valid JSON

    def test_unsupported_format(self, manager, sample_data):
        """Test error handling for unsupported formats."""
        with pytest.raises(ValueError, match="Unsupported format"):
            manager.format(sample_data, "invalid")

    def test_get_supported_formats(self, manager):
        """Test getting list of supported formats."""
        formats = manager.get_supported_formats()
        assert "markdown" in formats
        assert "text" in formats
        assert "json" in formats
