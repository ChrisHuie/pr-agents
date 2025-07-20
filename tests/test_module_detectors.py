"""Tests for module detector strategies."""

from src.pr_agents.pr_processing.extractors.module_detectors import (
    AnalyticsAdapterDetector,
    BidAdapterDetector,
    ConfigBasedDetector,
    IdSystemDetector,
    ModuleDetectorRegistry,
    RtdModuleDetector,
    UserModuleDetector,
    VideoModuleDetector,
)


class TestModuleDetectors:
    """Test individual module detectors."""

    def test_bid_adapter_detector(self):
        """Test bid adapter detection."""
        detector = BidAdapterDetector()

        # Should detect bid adapters
        assert detector.detect("exampleBidAdapter", "modules/exampleBidAdapter.js") == (
            "bid_adapter",
            "adapter",
        )
        assert detector.detect(
            "appnexusBidAdapter", "modules/appnexusBidAdapter.js"
        ) == ("bid_adapter", "adapter")

        # Should not detect non-bid adapters
        assert detector.detect("exampleModule", "modules/exampleModule.js") == (
            None,
            None,
        )
        assert detector.detect(
            "exampleRtdProvider", "modules/exampleRtdProvider.js"
        ) == (None, None)

    def test_rtd_module_detector(self):
        """Test RTD module detection."""
        detector = RtdModuleDetector()

        # Should detect RTD modules
        assert detector.detect("exampleRtdModule", "modules/exampleRtdModule.js") == (
            "rtd_module",
            "rtd",
        )
        assert detector.detect(
            "brandmetricsRtdProvider", "modules/brandmetricsRtdProvider.js"
        ) == ("rtd_module", "rtd")

        # Should not detect non-RTD modules
        assert detector.detect("exampleBidAdapter", "modules/exampleBidAdapter.js") == (
            None,
            None,
        )

    def test_analytics_adapter_detector(self):
        """Test analytics adapter detection."""
        detector = AnalyticsAdapterDetector()

        assert detector.detect(
            "googleAnalyticsAdapter", "modules/googleAnalyticsAdapter.js"
        ) == ("analytics_adapter", "analytics")
        assert detector.detect("exampleModule", "modules/exampleModule.js") == (
            None,
            None,
        )

    def test_id_system_detector(self):
        """Test ID system detection."""
        detector = IdSystemDetector()

        assert detector.detect("unifiedIdSystem", "modules/unifiedIdSystem.js") == (
            "id_system",
            "identity",
        )
        assert detector.detect("sharedIdSystem", "modules/sharedIdSystem.js") == (
            "id_system",
            "identity",
        )
        assert detector.detect("exampleModule", "modules/exampleModule.js") == (
            None,
            None,
        )

    def test_user_module_detector(self):
        """Test user module detection."""
        detector = UserModuleDetector()

        assert detector.detect("exampleUserModule", "modules/exampleUserModule.js") == (
            "user_module",
            "user",
        )
        assert detector.detect("exampleModule", "modules/exampleModule.js") == (
            None,
            None,
        )

    def test_video_module_detector(self):
        """Test video module detection."""
        detector = VideoModuleDetector()

        assert detector.detect(
            "exampleVideoModule", "modules/exampleVideoModule.js"
        ) == ("video_module", "video")
        assert detector.detect("exampleModule", "modules/exampleModule.js") == (
            None,
            None,
        )


class TestConfigBasedDetector:
    """Test configuration-based detector."""

    def test_path_based_detection(self):
        """Test detection based on file paths."""
        config = {"paths": ["modules/*BidAdapter.js"], "category": "adapter"}
        detector = ConfigBasedDetector("bid_adapter", config)

        # Should match path pattern
        assert detector.detect("seedtagBidAdapter", "modules/seedtagBidAdapter.js") == (
            "bid_adapter",
            "adapter",
        )

        # Should not match wrong path
        assert detector.detect("seedtagBidAdapter", "src/seedtagBidAdapter.js") == (
            None,
            None,
        )

    def test_naming_pattern_detection(self):
        """Test detection with naming patterns."""
        config = {
            "paths": ["modules/*.js"],
            "naming_pattern": "endsWith('BidAdapter')",
            "category": "adapter",
        }
        detector = ConfigBasedDetector("bid_adapter", config)

        # Should match both path and naming pattern
        assert detector.detect("exampleBidAdapter", "modules/exampleBidAdapter.js") == (
            "bid_adapter",
            "adapter",
        )

        # Should not match if naming pattern doesn't match
        assert detector.detect("exampleModule", "modules/exampleModule.js") == (
            None,
            None,
        )

    def test_starts_with_pattern(self):
        """Test startsWith naming pattern."""
        config = {
            "paths": ["libraries/*"],
            "naming_pattern": "startsWith('prebid')",
            "category": "core",
        }
        detector = ConfigBasedDetector("core_library", config)

        assert detector.detect("prebidUtils", "libraries/prebidUtils.js") == (
            "core_library",
            "core",
        )
        assert detector.detect("utilsLibrary", "libraries/utilsLibrary.js") == (
            None,
            None,
        )


class TestModuleDetectorRegistry:
    """Test module detector registry."""

    def test_default_detection(self):
        """Test detection with default detectors."""
        registry = ModuleDetectorRegistry()

        # Test various module types
        assert registry.detect_module_type(
            "exampleBidAdapter", "modules/exampleBidAdapter.js"
        ) == {"type": "bid_adapter", "category": "adapter"}
        assert registry.detect_module_type(
            "googleAnalyticsAdapter", "modules/googleAnalyticsAdapter.js"
        ) == {"type": "analytics_adapter", "category": "analytics"}
        assert registry.detect_module_type(
            "brandmetricsRtdProvider", "modules/brandmetricsRtdProvider.js"
        ) == {"type": "rtd_module", "category": "rtd"}
        assert registry.detect_module_type("id5IdSystem", "modules/id5IdSystem.js") == {
            "type": "id_system",
            "category": "identity",
        }

        # Generic module
        assert registry.detect_module_type(
            "unknownModule", "modules/unknownModule.js"
        ) == {"type": "generic", "category": "utility"}

    def test_config_based_detection(self):
        """Test detection with configuration."""
        registry = ModuleDetectorRegistry()

        # Load configuration
        config = {
            "module_locations": {
                "floors_module": {
                    "paths": ["modules/*FloorsModule.js"],
                    "naming_pattern": "endsWith('FloorsModule')",
                    "category": "monetization",
                }
            }
        }
        registry.load_repository_config(config)

        # Config-based detector should take precedence
        assert registry.detect_module_type(
            "priceFloorsModule", "modules/priceFloorsModule.js"
        ) == {"type": "floors_module", "category": "monetization"}

        # Default detectors should still work
        assert registry.detect_module_type(
            "exampleBidAdapter", "modules/exampleBidAdapter.js"
        ) == {"type": "bid_adapter", "category": "adapter"}

    def test_config_override(self):
        """Test that config detectors are checked before defaults."""
        registry = ModuleDetectorRegistry()

        # Configure a custom bid adapter detection
        config = {
            "module_locations": {
                "custom_adapter": {
                    "paths": ["custom/*BidAdapter.js"],
                    "category": "custom",
                }
            }
        }
        registry.load_repository_config(config)

        # Custom path should match first
        assert registry.detect_module_type(
            "testBidAdapter", "custom/testBidAdapter.js"
        ) == {"type": "custom_adapter", "category": "custom"}

        # Default path should still work
        assert registry.detect_module_type(
            "testBidAdapter", "modules/testBidAdapter.js"
        ) == {"type": "bid_adapter", "category": "adapter"}

    def test_register_custom_detector(self):
        """Test registering custom detectors."""
        registry = ModuleDetectorRegistry()

        # Create custom detector
        class CustomDetector:
            def detect(self, module_name, file_path):
                if module_name.endswith("Custom"):
                    return "custom_type", "custom_category"
                return None, None

        # Register as default detector
        registry.register_detector(CustomDetector(), use_config=False)

        assert registry.detect_module_type(
            "exampleCustom", "modules/exampleCustom.js"
        ) == {"type": "custom_type", "category": "custom_category"}

    def test_empty_config(self):
        """Test loading empty configuration."""
        registry = ModuleDetectorRegistry()

        # Empty config should not break anything
        registry.load_repository_config({})

        # Default detection should still work
        assert registry.detect_module_type(
            "exampleBidAdapter", "modules/exampleBidAdapter.js"
        ) == {"type": "bid_adapter", "category": "adapter"}
