"""Tests for markdown formatter module and file list functionality."""

import pytest

from src.pr_agents.output import MarkdownFormatter


class TestMarkdownFormatterModules:
    """Test markdown formatter with modules and file lists."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return MarkdownFormatter()

    @pytest.fixture
    def sample_data_with_modules(self):
        """Sample data with modules and file information."""
        return {
            "pr_url": "https://github.com/prebid/Prebid.js/pull/12440",
            "pr_number": 12440,
            "repository": {"full_name": "prebid/Prebid.js"},
            "release_version": None,  # Unreleased
            "modules": {
                "modules": [
                    {
                        "name": "seedtagBidAdapter",
                        "type": "bid_adapter",
                        "path": "modules/seedtagBidAdapter.js",
                        "category": "adapter",
                    }
                ],
                "total_modules": 1,
                "repository_type": "prebid-js",
                "primary_type": "adapter",
                "changes_summary": "Modified 1 bid adapter",
                "adapter_changes": {"bid_adapters": 1},
            },
            "code_changes": {
                "change_stats": {
                    "total_changes": 69,
                    "total_additions": 50,
                    "total_deletions": 19,
                    "changed_files": 2,
                },
                "file_analysis": {
                    "changed_files": [
                        "modules/seedtagBidAdapter.js",
                        "test/spec/modules/seedtagBidAdapter_spec.js",
                    ],
                    "file_types": {"js": 2},
                },
            },
            "metadata": {
                "label_analysis": {
                    "total_count": 1,
                    "uncategorized": ["maintenance"],
                }
            },
            "processing_metrics": {
                "total_duration": 0.5,
                "component_durations": {
                    "metadata": 0.1,
                    "code_changes": 0.2,
                    "modules": 0.2,
                },
            },
        }

    def test_format_modules_section(self, formatter, sample_data_with_modules):
        """Test that modules section is properly formatted."""
        result = formatter.format(sample_data_with_modules)

        # Check modules section exists
        assert "## 📦 Modules Analysis" in result
        assert "### Modules Found (1)" in result
        assert "- **seedtagBidAdapter** (bid_adapter)" in result

        # Check module metadata
        assert "**Total Modules:** 1" in result
        assert "**Repository Type:** prebid-js" in result
        assert "**Primary Module Type:** adapter" in result
        assert "**Summary:** Modified 1 bid adapter" in result

        # Check adapter changes subsection
        assert "### Adapter Changes" in result
        assert "- Bid Adapters: 1" in result

    def test_format_files_section(self, formatter, sample_data_with_modules):
        """Test that files section shows actual file list."""
        result = formatter.format(sample_data_with_modules)

        # Check files section exists
        assert "## 💻 Files Changed" in result
        assert "### Files" in result
        assert "- `modules/seedtagBidAdapter.js`" in result
        assert "- `test/spec/modules/seedtagBidAdapter_spec.js`" in result

    def test_format_multiple_modules(self, formatter):
        """Test formatting with multiple module types."""
        data = {
            "pr_url": "https://github.com/prebid/Prebid.js/pull/123",
            "modules": {
                "modules": [
                    {"name": "appnexusBidAdapter", "type": "bid_adapter"},
                    {"name": "googleAnalyticsAdapter", "type": "analytics_adapter"},
                    {"name": "brandmetricsRtdProvider", "type": "rtd_module"},
                ],
                "total_modules": 3,
                "repository_type": "prebid-js",
                "adapter_changes": {
                    "bid_adapters": 1,
                    "analytics_adapters": 1,
                    "rtd_providers": 1,
                },
                "new_adapters": [{"name": "appnexusBidAdapter", "type": "bid_adapter"}],
                "important_modules": ["Core auction logic updated"],
            },
        }

        result = formatter.format(data)

        # Check multiple modules listed
        assert "### Modules Found (3)" in result
        assert "- **appnexusBidAdapter** (bid_adapter)" in result
        assert "- **googleAnalyticsAdapter** (analytics_adapter)" in result
        assert "- **brandmetricsRtdProvider** (rtd_module)" in result

        # Check new adapters section
        assert "### New Adapters" in result
        assert "- **appnexusBidAdapter** (bid_adapter)" in result

        # Check important modules section
        assert "### Important Module Changes" in result
        assert "- Core auction logic updated" in result

    def test_format_no_modules(self, formatter):
        """Test formatting when no modules are present."""
        data = {
            "pr_url": "https://github.com/owner/repo/pull/123",
            "code_changes": {
                "change_stats": {"changed_files": 2},
                "file_analysis": {
                    "changed_files": ["README.md", "package.json"],
                    "file_types": {"md": 1, "json": 1},
                },
            },
        }

        result = formatter.format(data)

        # Should not have modules section
        assert "## 📦 Modules Analysis" not in result

        # But should still have files
        assert "## 💻 Files Changed" in result
        assert "- `README.md`" in result
        assert "- `package.json`" in result

    def test_format_release_status(self, formatter):
        """Test release status formatting."""
        # Test unreleased
        data = {"pr_url": "https://github.com/owner/repo/pull/123"}
        result = formatter.format(data)
        assert "**Release:** Unreleased" in result

        # Test with release version
        data["release_version"] = "v1.2.3"
        result = formatter.format(data)
        assert "**Release:** v1.2.3" in result

    def test_format_labels_only(self, formatter):
        """Test that labels are shown without quality metrics."""
        data = {
            "pr_url": "https://github.com/owner/repo/pull/123",
            "metadata": {
                "label_analysis": {
                    "total_count": 3,
                    "categorized": {
                        "type": ["bug", "enhancement"],
                        "priority": ["high"],
                    },
                }
            },
        }

        result = formatter.format(data)

        # Check labels section
        assert "## 🏷️ Labels (3)" in result
        assert "- **type:** bug, enhancement" in result
        assert "- **priority:** high" in result

        # Ensure no quality metrics
        assert "Title Quality" not in result
        assert "Description Quality" not in result

    def test_format_processing_metrics(self, formatter):
        """Test processing metrics formatting."""
        data = {
            "pr_url": "https://github.com/owner/repo/pull/123",
            "processing_metrics": {
                "total_duration": 1.234,
                "component_durations": {
                    "metadata": 0.100,
                    "code_changes": 0.500,
                    "repository": 0.300,
                    "modules": 0.334,
                },
            },
        }

        result = formatter.format(data)

        # Check metrics section
        assert "## ⚡ Processing Metrics" in result
        assert "**Total Processing Time:** 1.23s" in result
        assert "- metadata: 0.100s" in result
        assert "- code_changes: 0.500s" in result
        assert "- repository: 0.300s" in result
        assert "- modules: 0.334s" in result

    def test_excluded_sections(self, formatter):
        """Test that excluded sections are not present."""
        data = {
            "pr_url": "https://github.com/owner/repo/pull/123",
            "metadata": {
                "title_quality": {"score": 85, "quality_level": "excellent"},
                "description_quality": {"score": 70, "quality_level": "good"},
            },
            "code_changes": {
                "risk_assessment": {
                    "risk_level": "high",
                    "risk_score": 5,
                    "risk_factors": ["Large changeset"],
                }
            },
            "repository_info": {
                "health_assessment": {
                    "health_level": "good",
                    "health_score": 45,
                }
            },
        }

        result = formatter.format(data)

        # These sections should NOT be present
        assert "Title Quality" not in result
        assert "Description Quality" not in result
        assert "Risk Level" not in result
        assert "Risk Assessment" not in result
        assert "Repository Health" not in result
        assert "## 🏗️ Repository Analysis" not in result
