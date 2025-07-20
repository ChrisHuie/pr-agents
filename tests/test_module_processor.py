"""Tests for module processor."""

import pytest

from src.pr_agents.pr_processing.models import ProcessingResult
from src.pr_agents.pr_processing.processors.module_processor import ModuleProcessor


class TestModuleProcessor:
    """Test cases for ModuleProcessor."""

    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return ModuleProcessor()

    def test_process_prebid_js_modules(self, processor):
        """Test processing modules for Prebid.js repository."""
        component_data = {
            "modules": [
                {
                    "name": "appnexusBidAdapter",
                    "type": "bid_adapter",
                    "file": "modules/appnexusBidAdapter.js",
                    "category": "adapter",
                    "action": "modified",
                }
            ],
            "module_categories": {"adapter": 1},
            "primary_module_type": "adapter",
            "total_modules": 1,
            "repository": {
                "name": "Prebid.js",
                "full_name": "prebid/Prebid.js",
                "language": "JavaScript",
            },
        }

        result = processor.process(component_data)

        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.component == "modules"

        # Check data structure
        data = result.data
        assert data["total_modules"] == 1
        assert data["repository_type"] == "prebid-js"
        assert data["primary_type"] == "adapter"
        assert "modules" in data
        assert "changes_summary" in data
        assert data["changes_summary"] == "Modified 1 bid adapter"

    def test_process_prebid_server_modules(self, processor):
        """Test processing modules for Prebid Server repository."""
        component_data = {
            "modules": [
                {
                    "name": "appnexus",
                    "type": "bidder",
                    "file": "adapters/appnexus/appnexus.go",
                    "category": "adapter",
                }
            ],
            "module_categories": {"adapter": 1},
            "primary_module_type": "adapter",
            "total_modules": 1,
            "repository": {
                "name": "prebid-server",
                "full_name": "prebid/prebid-server",
                "language": "Go",
            },
        }

        result = processor.process(component_data)

        assert result.success is True
        data = result.data
        assert data["repository_type"] == "prebid-server"
        assert "package_changes" in data
        assert "bidder_changes" in data

    def test_process_mobile_modules(self, processor):
        """Test processing modules for mobile repository."""
        component_data = {
            "modules": [
                {
                    "name": "PrebidMobile",
                    "type": "core",
                    "file": "PrebidMobile/PrebidMobile.swift",
                    "category": "core",
                }
            ],
            "module_categories": {"core": 1},
            "primary_module_type": "core",
            "total_modules": 1,
            "repository": {
                "name": "prebid-mobile-ios",
                "full_name": "prebid/prebid-mobile-ios",
                "languages": {"Swift": 80, "Objective-C": 20},
            },
        }

        result = processor.process(component_data)

        assert result.success is True
        data = result.data
        assert data["repository_type"] == "prebid-mobile"
        assert data["platform"] == "ios"
        assert "core_changes" in data

    def test_process_new_adapters(self, processor):
        """Test detection of new adapters."""
        component_data = {
            "modules": [
                {
                    "name": "newBidAdapter",
                    "type": "bid_adapter",
                    "action": "added",
                    "category": "adapter",
                    "file": "modules/newBidAdapter.js",
                }
            ],
            "module_categories": {"adapter": 1},
            "primary_module_type": "adapter",
            "total_modules": 1,
            "repository": {"name": "Prebid.js", "full_name": "prebid/Prebid.js"},
        }

        result = processor.process(component_data)

        data = result.data
        assert "new_adapters" in data
        assert len(data["new_adapters"]) == 1
        assert data["new_adapters"][0]["name"] == "newBidAdapter"

    def test_process_important_modules(self, processor):
        """Test detection of important/core modules."""
        component_data = {
            "modules": [
                {
                    "name": "auctionManager",
                    "type": "core",
                    "file": "src/auctionManager.js",
                    "category": "core",
                }
            ],
            "module_categories": {"core": 1},
            "primary_module_type": "core",
            "total_modules": 1,
            "repository": {"name": "Prebid.js", "full_name": "prebid/Prebid.js"},
        }

        result = processor.process(component_data)

        data = result.data
        assert "important_modules" in data
        assert len(data["important_modules"]) > 0
        assert any("auction" in mod.lower() for mod in data["important_modules"])

    def test_process_multiple_adapter_types(self, processor):
        """Test processing multiple adapter types."""
        component_data = {
            "modules": [
                {
                    "name": "appnexusBidAdapter",
                    "type": "bid_adapter",
                    "category": "adapter",
                },
                {
                    "name": "googleAnalyticsAdapter",
                    "type": "analytics_adapter",
                    "category": "analytics",
                },
                {
                    "name": "brandmetricsRtdProvider",
                    "type": "rtd_module",
                    "category": "rtd",
                },
            ],
            "module_categories": {"adapter": 1, "analytics": 1, "rtd": 1},
            "primary_module_type": "adapter",
            "total_modules": 3,
            "repository": {"name": "Prebid.js", "full_name": "prebid/Prebid.js"},
        }

        result = processor.process(component_data)

        data = result.data
        assert data["adapter_changes"]["bid_adapters"] == 1
        assert data["adapter_changes"]["analytics_adapters"] == 1
        assert data["adapter_changes"]["rtd_providers"] == 1

    def test_process_empty_modules(self, processor):
        """Test processing with no modules."""
        component_data = {
            "modules": [],
            "module_categories": {},
            "primary_module_type": None,
            "total_modules": 0,
            "repository": {"name": "Prebid.js"},
        }

        result = processor.process(component_data)

        assert result.success is True
        data = result.data
        assert data["total_modules"] == 0
        assert data["changes_summary"] == "No module changes detected"

    def test_process_error_handling(self, processor):
        """Test error handling in processing."""
        # Invalid data structure
        component_data = "invalid"

        result = processor.process(component_data)

        assert result.success is False
        assert len(result.errors) > 0
        assert "Module processing error" in result.errors[0]

    def test_repository_type_detection(self, processor):
        """Test repository type detection logic."""
        test_cases = [
            ({"name": "Prebid.js", "full_name": "prebid/Prebid.js"}, "prebid-js"),
            (
                {"name": "prebid-server", "full_name": "prebid/prebid-server"},
                "prebid-server",
            ),
            (
                {
                    "name": "prebid-mobile-android",
                    "full_name": "prebid/prebid-mobile-android",
                },
                "prebid-mobile",
            ),
            (
                {"name": "SomeRepo", "full_name": "prebid/SomeRepo", "language": "Go"},
                "prebid-server",
            ),
            ({"name": "Unknown", "full_name": "owner/unknown"}, "generic"),
        ]

        for repo_data, expected_type in test_cases:
            component_data = {
                "modules": [],
                "repository": repo_data,
                "total_modules": 0,
            }

            result = processor.process(component_data)
            assert result.data["repository_type"] == expected_type

    def test_bidder_detection_in_server_repos(self, processor):
        """Test bidder detection in server repositories."""
        component_data = {
            "modules": [
                {"name": "appnexus", "file": "adapters/appnexus/appnexus.go"},
                {"name": "config", "file": "config/config.go"},
                {"name": "rubicon", "file": "adapters/rubicon/rubicon.go"},
            ],
            "repository": {"name": "prebid-server", "language": "Go"},
            "total_modules": 3,
        }

        result = processor.process(component_data)

        data = result.data
        assert "bidder_changes" in data
        assert len(data["bidder_changes"]) == 2  # appnexus and rubicon

        bidder_names = {b["name"] for b in data["bidder_changes"]}
        assert "appnexus" in bidder_names
        assert "rubicon" in bidder_names
