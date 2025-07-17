"""Tests for the Module Extractor."""

from unittest.mock import Mock

from src.pr_agents.pr_processing.extractors.modules import ModuleExtractor


class TestModuleExtractor:
    """Test cases for ModuleExtractor."""

    def setup_method(self):
        """Set up test fixtures."""
        mock_github = Mock()
        self.extractor = ModuleExtractor(mock_github)

        # Sample repository configuration
        self.repo_config = {
            "module_locations": {
                "bid_adapter": {
                    "paths": ["modules/*BidAdapter.js"],
                    "naming_pattern": "endsWith('BidAdapter')",
                },
                "analytics_adapter": {
                    "paths": ["modules/*AnalyticsAdapter.js"],
                    "naming_pattern": "endsWith('AnalyticsAdapter')",
                },
                "rtd_provider": {
                    "paths": ["modules/*RtdProvider.js"],
                    "naming_pattern": "endsWith('RtdProvider')",
                },
                "core": {"paths": ["src/*", "src/core/*"], "naming_pattern": ""},
            }
        }
        self.extractor.set_repository_config(self.repo_config)

    def test_extract_bid_adapter_module(self):
        """Test extracting bid adapter modules."""
        pr_data = {
            "files": [
                "modules/exampleBidAdapter.js",
                "test/spec/modules/exampleBidAdapter_spec.js",
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        assert result["total_modules"] == 1
        assert len(result["modules"]) == 1

        module = result["modules"][0]
        assert module["name"] == "exampleBidAdapter"
        assert module["type"] == "bid_adapter"
        assert module["category"] == "adapter"
        assert module["path"] == "modules/exampleBidAdapter.js"

    def test_extract_multiple_module_types(self):
        """Test extracting different module types."""
        pr_data = {
            "files": [
                "modules/exampleBidAdapter.js",
                "modules/exampleAnalyticsAdapter.js",
                "modules/exampleRtdProvider.js",
                "src/ajax.js",
                "test/spec/modules/exampleBidAdapter_spec.js",
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        assert result["total_modules"] == 4
        assert len(result["modules"]) == 4

        # Check module categories
        assert result["module_categories"]["adapter"] == 2
        assert result["module_categories"]["provider"] == 1
        assert result["module_categories"]["core"] == 1

        # Check primary type
        assert result["primary_module_type"] == "adapter"

    def test_ignore_test_files(self):
        """Test that test files are ignored."""
        pr_data = {
            "files": [
                "test/spec/modules/exampleBidAdapter_spec.js",
                "tests/unit/test_example.py",
                "__tests__/example.test.js",
            ],
            "repository": "test/repo",
        }

        result = self.extractor.extract(pr_data)

        assert result["total_modules"] == 0
        assert len(result["modules"]) == 0

    def test_extract_generic_modules(self):
        """Test extracting generic modules without specific patterns."""
        # Use a different config without patterns
        self.extractor.set_repository_config({"module_locations": {}})

        pr_data = {
            "files": ["src/utils.js", "lib/helpers.py", "modules/genericModule.js"],
            "repository": "generic/repo",
        }

        result = self.extractor.extract(pr_data)

        # Should find the generic module
        assert result["total_modules"] >= 1

        # Find the genericModule
        module_names = [m["name"] for m in result["modules"]]
        assert "genericModule" in module_names

    def test_module_dependencies(self):
        """Test module dependency extraction."""
        pr_data = {
            "files": ["modules/exampleBidAdapter.js", "src/core.js"],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        dependencies = result["module_dependencies"]
        assert "exampleBidAdapter" in dependencies
        # Adapters depend on core
        assert "core" in dependencies["exampleBidAdapter"]

    def test_empty_pr(self):
        """Test handling of PR with no files."""
        pr_data = {"files": [], "repository": "empty/repo"}

        result = self.extractor.extract(pr_data)

        assert result["total_modules"] == 0
        assert result["modules"] == []
        assert result["module_categories"] == {}
        assert result["primary_module_type"] is None

    def test_invalid_pr_data(self):
        """Test handling of invalid PR data."""
        result = self.extractor.extract(None)

        assert result["total_modules"] == 0
        assert result["repository"] == "unknown"

    def test_no_repository_config(self):
        """Test extraction without repository configuration."""
        mock_github = Mock()
        extractor = ModuleExtractor(mock_github)  # No config set

        pr_data = {"files": ["modules/exampleBidAdapter.js"], "repository": "test/repo"}

        result = extractor.extract(pr_data)

        # Should still work but might not categorize properly
        assert result is not None
        assert isinstance(result["modules"], list)

    def test_wildcard_pattern_matching(self):
        """Test wildcard pattern matching in paths."""
        pr_data = {
            "files": [
                "modules/prefixBidAdapter.js",
                "modules/anotherPrefixBidAdapter.js",
                "modules/notAnAdapter.js",
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        # Should match the two bid adapters
        bid_adapters = [m for m in result["modules"] if m["type"] == "bid_adapter"]
        assert len(bid_adapters) == 2

        adapter_names = [m["name"] for m in bid_adapters]
        assert "prefixBidAdapter" in adapter_names
        assert "anotherPrefixBidAdapter" in adapter_names
        assert "notAnAdapter" not in adapter_names

    def test_duplicate_module_handling(self):
        """Test that duplicate modules are not added multiple times."""
        pr_data = {
            "files": [
                "modules/exampleBidAdapter.js",
                "modules/exampleBidAdapter.js",  # Duplicate
                "src/modules/exampleBidAdapter.js",  # Different path, same module
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        # Should only have one instance of the module
        adapter_modules = [
            m for m in result["modules"] if m["name"] == "exampleBidAdapter"
        ]
        assert len(adapter_modules) == 1
