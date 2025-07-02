"""
Tests for Repository Structure Configuration system.
"""

import json

import pytest

from src.pr_agents.config.loader import ConfigurationLoader
from src.pr_agents.config.manager import RepositoryStructureManager
from src.pr_agents.config.models import (
    DetectionStrategy,
    FetchStrategy,
    ModuleCategory,
    ModulePattern,
    RepositoryStructure,
)


class TestConfigurationModels:
    """Test configuration data models."""

    def test_module_pattern_creation(self):
        """Test ModulePattern creation."""
        pattern = ModulePattern(
            pattern="*BidAdapter.js",
            pattern_type="suffix",
            name_extraction="remove_suffix:BidAdapter",
            exclude_patterns=["test/*"],
        )

        assert pattern.pattern == "*BidAdapter.js"
        assert pattern.pattern_type == "suffix"
        assert pattern.name_extraction == "remove_suffix:BidAdapter"
        assert "test/*" in pattern.exclude_patterns

    def test_module_category_creation(self):
        """Test ModuleCategory creation."""
        pattern = ModulePattern("*BidAdapter.js", "suffix")
        category = ModuleCategory(
            name="bid_adapter",
            display_name="Bid Adapters",
            paths=["modules/"],
            patterns=[pattern],
            detection_strategy=DetectionStrategy.FILENAME_PATTERN,
            metadata_field="componentType",
            metadata_value="bidder",
        )

        assert category.name == "bid_adapter"
        assert category.display_name == "Bid Adapters"
        assert len(category.patterns) == 1
        assert category.metadata_field == "componentType"
        assert category.metadata_value == "bidder"

    def test_repository_structure_version_matching(self):
        """Test version matching in RepositoryStructure."""
        repo = RepositoryStructure(repo_name="prebid/Prebid.js", repo_type="prebid-js")

        from src.pr_agents.config.models import VersionConfig

        # Add version configs
        v9_config = VersionConfig(version="v9.0", version_range=None)
        v10_config = VersionConfig(version="v10.0", version_range=">=10.0")
        repo.version_configs = [v9_config, v10_config]

        # Test exact match
        assert repo._version_matches("v9.0", v9_config) is True
        assert repo._version_matches("v10.0", v10_config) is True

        # Test version range
        assert repo._version_matches("v10.5", v10_config) is True
        assert repo._version_matches("v11.0", v10_config) is True
        assert repo._version_matches("v9.5", v10_config) is False


class TestConfigurationLoader:
    """Test configuration loader."""

    @pytest.fixture
    def sample_config(self):
        """Sample configuration data."""
        return {
            "prebid/Prebid.js": {
                "repo_type": "prebid-js",
                "description": "Test repo",
                "default_detection_strategy": "hybrid",
                "fetch_strategy": "filenames_only",
                "module_categories": {
                    "bid_adapter": {
                        "name": "bid_adapter",
                        "display_name": "Bid Adapters",
                        "paths": ["modules/"],
                        "patterns": [
                            {
                                "pattern": "*BidAdapter.js",
                                "pattern_type": "suffix",
                                "name_extraction": "remove_suffix:BidAdapter",
                            }
                        ],
                        "detection_strategy": "filename_pattern",
                    }
                },
                "core_paths": ["src/"],
                "test_paths": ["test/"],
                "version_configs": [
                    {
                        "version": "v10.0",
                        "version_range": ">=10.0",
                        "metadata_path": "metadata/modules/",
                        "module_categories": {
                            "bid_adapter": {
                                "name": "bid_adapter",
                                "display_name": "Bid Adapters",
                                "paths": ["metadata/modules/"],
                                "detection_strategy": "metadata_file",
                                "metadata_field": "componentType",
                                "metadata_value": "bidder",
                            }
                        },
                    }
                ],
            }
        }

    def test_load_config(self, sample_config, tmp_path):
        """Test loading configuration from JSON."""
        # Create temporary config file
        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(sample_config))

        # Load configuration
        loader = ConfigurationLoader(str(config_file))
        config = loader.load_config()

        assert len(config.repositories) == 1
        assert "prebid/Prebid.js" in config.repositories

        repo = config.repositories["prebid/Prebid.js"]
        assert repo.repo_type == "prebid-js"
        assert repo.default_detection_strategy == DetectionStrategy.HYBRID
        assert repo.fetch_strategy == FetchStrategy.FILENAMES_ONLY
        assert len(repo.module_categories) == 1
        assert len(repo.version_configs) == 1

    def test_parse_module_categories(self, sample_config):
        """Test parsing module categories."""
        loader = ConfigurationLoader("dummy.json")
        categories_data = sample_config["prebid/Prebid.js"]["module_categories"]

        categories = loader._parse_module_categories(categories_data)

        assert len(categories) == 1
        assert "bid_adapter" in categories

        bid_adapter = categories["bid_adapter"]
        assert bid_adapter.name == "bid_adapter"
        assert bid_adapter.display_name == "Bid Adapters"
        assert len(bid_adapter.patterns) == 1
        assert bid_adapter.patterns[0].pattern == "*BidAdapter.js"

    def test_parse_version_configs(self, sample_config):
        """Test parsing version configurations."""
        loader = ConfigurationLoader("dummy.json")
        versions_data = sample_config["prebid/Prebid.js"]["version_configs"]

        versions = loader._parse_version_configs(versions_data)

        assert len(versions) == 1
        v10 = versions[0]
        assert v10.version == "v10.0"
        assert v10.version_range == ">=10.0"
        assert v10.metadata_path == "metadata/modules/"
        assert len(v10.module_categories) == 1


class TestRepositoryStructureManager:
    """Test repository structure manager."""

    @pytest.fixture
    def manager_with_config(self, tmp_path):
        """Create manager with test configuration."""
        config_data = {
            "prebid/Prebid.js": {
                "repo_type": "prebid-js",
                "module_categories": {
                    "bid_adapter": {
                        "name": "bid_adapter",
                        "display_name": "Bid Adapters",
                        "paths": ["modules/"],
                        "patterns": [
                            {
                                "pattern": "*BidAdapter.js",
                                "pattern_type": "suffix",
                                "name_extraction": "remove_suffix:BidAdapter",
                            }
                        ],
                    },
                    "rtd_module": {
                        "name": "rtd_module",
                        "display_name": "RTD Modules",
                        "paths": ["modules/"],
                        "patterns": [
                            {
                                "pattern": "*RtdProvider.js",
                                "pattern_type": "suffix",
                                "name_extraction": "remove_suffix:RtdProvider",
                            }
                        ],
                    },
                },
                "core_paths": ["src/", "libraries/"],
                "test_paths": ["test/spec/"],
                "doc_paths": ["docs/"],
                "version_configs": [
                    {
                        "version": "v10.0",
                        "version_range": ">=10.0",
                        "metadata_path": "metadata/modules/",
                        "module_categories": {
                            "bid_adapter": {
                                "name": "bid_adapter",
                                "display_name": "Bid Adapters",
                                "paths": ["metadata/modules/"],
                                "patterns": [
                                    {
                                        "pattern": "*BidAdapter.json",
                                        "pattern_type": "suffix",
                                    }
                                ],
                                "detection_strategy": "metadata_file",
                            }
                        },
                    }
                ],
            }
        }

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))

        return RepositoryStructureManager(str(config_file))

    def test_extract_repo_name(self, manager_with_config):
        """Test repository name extraction from URLs."""
        test_cases = [
            ("https://github.com/prebid/Prebid.js", "prebid/Prebid.js"),
            ("https://github.com/prebid/Prebid.js.git", "prebid/Prebid.js"),
            ("git@github.com:prebid/Prebid.js.git", "prebid/Prebid.js"),
            ("prebid/Prebid.js", "prebid/Prebid.js"),
        ]

        for url, expected in test_cases:
            assert manager_with_config._extract_repo_name(url) == expected

    def test_categorize_file_pre_v10(self, manager_with_config):
        """Test file categorization for pre-v10 files."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Test bid adapter
        result = manager_with_config.categorize_file(
            repo_url, "modules/rubiconBidAdapter.js"
        )
        assert "bid_adapter" in result["categories"]
        assert result["is_core"] is False
        assert result["is_test"] is False

        # Test RTD module
        result = manager_with_config.categorize_file(
            repo_url, "modules/browsiRtdProvider.js"
        )
        assert "rtd_module" in result["categories"]

        # Test core file
        result = manager_with_config.categorize_file(repo_url, "src/auction.js")
        assert result["is_core"] is True

        # Test test file
        result = manager_with_config.categorize_file(
            repo_url, "test/spec/modules/rubiconBidAdapter_spec.js"
        )
        assert result["is_test"] is True

    def test_categorize_file_v10_plus(self, manager_with_config):
        """Test file categorization for v10+ metadata files."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Test v10+ metadata file
        result = manager_with_config.categorize_file(
            repo_url, "metadata/modules/rubiconBidAdapter.json", version="v10.0"
        )
        assert "bid_adapter" in result["categories"]

    def test_get_module_info(self, manager_with_config):
        """Test getting detailed module information."""
        repo_url = "https://github.com/prebid/Prebid.js"

        info = manager_with_config.get_module_info(
            repo_url, "modules/appnexusBidAdapter.js"
        )

        assert info["module_name"] == "appnexus"
        assert "bid_adapter" in info["categories"]
        assert info["module_type"] == "Bid Adapters"
        assert info["repo_type"] == "prebid-js"

    def test_pattern_matching(self, manager_with_config):
        """Test various pattern matching scenarios."""
        # Test suffix pattern
        assert (
            manager_with_config._simple_match(
                "modules/rubiconBidAdapter.js", "*BidAdapter.js", "suffix"
            )
            is True
        )

        # Test glob pattern
        assert (
            manager_with_config._simple_match(
                "test/spec/modules/test.js", "test/spec/*/*.js", "glob"
            )
            is True
        )

        # Test directory pattern
        assert (
            manager_with_config._simple_match(
                "adapters/rubicon/adapter.go", "adapters/*", "directory"
            )
            is True
        )
