"""Tests for module extractor without configuration."""

from unittest.mock import Mock

from src.pr_agents.pr_processing.extractors.modules import ModuleExtractor


class TestModuleExtractorNoConfig:
    """Test module extraction without repository configuration."""

    def setup_method(self):
        """Set up test fixtures."""
        mock_github = Mock()
        self.extractor = ModuleExtractor(mock_github)
        # No configuration set - testing detection based on naming patterns

    def test_detect_bid_adapter(self):
        """Test that bid adapters are detected based on naming pattern alone."""
        pr_data = {
            "files": [
                "modules/seedtagBidAdapter.js",
                "test/spec/modules/seedtagBidAdapter_spec.js",
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        assert result["total_modules"] == 1
        assert len(result["modules"]) == 1

        module = result["modules"][0]
        assert module["name"] == "seedtagBidAdapter"
        assert module["type"] == "bid_adapter"
        assert module["category"] == "adapter"
        assert result["primary_module_type"] == "adapter"

    def test_detect_rtd_module(self):
        """Test RTD module detection without configuration."""
        pr_data = {
            "files": [
                "modules/exampleRtdModule.js",
                "modules/anotherRtdProvider.js",
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        assert result["total_modules"] == 2

        # Check both RTD modules are detected
        rtd_modules = [m for m in result["modules"] if m["type"] == "rtd_module"]
        assert len(rtd_modules) == 2

        module_names = [m["name"] for m in rtd_modules]
        assert "exampleRtdModule" in module_names
        assert "anotherRtdProvider" in module_names

        # All should be categorized as RTD
        for module in rtd_modules:
            assert module["category"] == "rtd"

    def test_detect_analytics_adapter(self):
        """Test analytics adapter detection without configuration."""
        pr_data = {
            "files": [
                "modules/exampleAnalyticsAdapter.js",
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        assert result["total_modules"] == 1
        module = result["modules"][0]
        assert module["name"] == "exampleAnalyticsAdapter"
        assert module["type"] == "analytics_adapter"
        assert module["category"] == "analytics"

    def test_detect_id_system(self):
        """Test ID system detection without configuration."""
        pr_data = {
            "files": [
                "modules/sharedIdSystem.js",
                "modules/unifiedIdSystem.js",
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        assert result["total_modules"] == 2

        id_modules = [m for m in result["modules"] if m["type"] == "id_system"]
        assert len(id_modules) == 2

        for module in id_modules:
            assert module["category"] == "identity"
            assert module["name"].endswith("IdSystem")

    def test_detect_user_module(self):
        """Test user module detection without configuration."""
        pr_data = {
            "files": [
                "modules/exampleUserModule.js",
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        assert result["total_modules"] == 1
        module = result["modules"][0]
        assert module["name"] == "exampleUserModule"
        assert module["type"] == "user_module"
        assert module["category"] == "user"

    def test_detect_video_module(self):
        """Test video module detection without configuration."""
        pr_data = {
            "files": [
                "modules/exampleVideoModule.js",
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        assert result["total_modules"] == 1
        module = result["modules"][0]
        assert module["name"] == "exampleVideoModule"
        assert module["type"] == "video_module"
        assert module["category"] == "video"

    def test_mixed_modules(self):
        """Test detection of mixed module types without configuration."""
        pr_data = {
            "files": [
                "modules/appnexusBidAdapter.js",
                "modules/googleAnalyticsAdapter.js",
                "modules/brandmetricsRtdProvider.js",
                "modules/id5IdSystem.js",
                "modules/genericModule.js",  # This should be generic
                "test/spec/modules/appnexusBidAdapter_spec.js",  # Should be ignored
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        assert result["total_modules"] == 5  # Test file should be ignored

        # Check module types
        module_types = {m["type"] for m in result["modules"]}
        assert "bid_adapter" in module_types
        assert "analytics_adapter" in module_types
        assert "rtd_module" in module_types
        assert "id_system" in module_types
        assert "generic" in module_types

        # Check categories
        categories = result["module_categories"]
        assert categories["adapter"] == 1  # Only bid adapter
        assert categories["analytics"] == 1
        assert categories["rtd"] == 1
        assert categories["identity"] == 1
        assert categories["utility"] == 1  # Generic module

    def test_primary_module_type_calculation(self):
        """Test that primary module type is correctly calculated."""
        pr_data = {
            "files": [
                "modules/adapter1BidAdapter.js",
                "modules/adapter2BidAdapter.js",
                "modules/adapter3BidAdapter.js",
                "modules/analyticsAdapter.js",
                "modules/rtdProvider.js",
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        # Adapter category should have 3 bid adapters, making it primary
        assert result["primary_module_type"] == "adapter"
        assert result["module_categories"]["adapter"] == 3

    def test_case_sensitivity(self):
        """Test that module detection is case-sensitive for types."""
        pr_data = {
            "files": [
                "modules/examplebidadapter.js",  # lowercase - should not match
                "modules/exampleBidadapter.js",  # wrong case - should not match
                "modules/exampleBidAdapter.js",  # correct case - should match
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        # Only the correctly cased one should be detected as bid_adapter
        bid_adapters = [m for m in result["modules"] if m["type"] == "bid_adapter"]
        assert len(bid_adapters) == 1
        assert bid_adapters[0]["name"] == "exampleBidAdapter"

        # Others should be generic
        generic_modules = [m for m in result["modules"] if m["type"] == "generic"]
        assert len(generic_modules) == 2

    def test_non_module_files_ignored(self):
        """Test that non-module files are not detected as modules."""
        pr_data = {
            "files": [
                "README.md",
                "package.json",
                ".gitignore",
                "webpack.config.js",
            ],
            "repository": "prebid/Prebid.js",
        }

        result = self.extractor.extract(pr_data)

        # Should not detect any modules from these files
        assert result["total_modules"] == 0
        assert len(result["modules"]) == 0
