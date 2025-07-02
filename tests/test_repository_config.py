"""
Tests for repository configuration components.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.pr_agents.config.loader import ConfigurationLoader
from src.pr_agents.config.manager import RepositoryStructureManager
from src.pr_agents.config.models import (
    DetectionStrategy,
    ModuleCategory,
    ModulePattern,
    RepositoryConfig,
    RepositoryStructure,
    VersionConfig,
)


class TestRepositoryModels:
    """Test suite for repository configuration models."""

    def test_module_pattern_creation(self):
        """Test ModulePattern creation and attributes."""
        pattern = ModulePattern(
            pattern="*BidAdapter.js",
            pattern_type="suffix",
            name_extraction="remove_suffix:BidAdapter",
            exclude_patterns=["test*.js"],
        )

        assert pattern.pattern == "*BidAdapter.js"
        assert pattern.pattern_type == "suffix"
        assert pattern.name_extraction == "remove_suffix:BidAdapter"
        assert "test*.js" in pattern.exclude_patterns

    def test_module_category_creation(self):
        """Test ModuleCategory creation."""
        patterns = [
            ModulePattern(pattern="*BidAdapter.js", pattern_type="suffix"),
            ModulePattern(pattern="*Adapter.js", pattern_type="suffix"),
        ]

        category = ModuleCategory(
            name="bid_adapter",
            display_name="Bid Adapters",
            paths=["modules/"],
            patterns=patterns,
            detection_strategy=DetectionStrategy.FILENAME_PATTERN,
        )

        assert category.name == "bid_adapter"
        assert category.display_name == "Bid Adapters"
        assert len(category.patterns) == 2
        assert category.detection_strategy == DetectionStrategy.FILENAME_PATTERN

    def test_version_config(self):
        """Test VersionConfig functionality."""
        version = VersionConfig(
            version="v10.0",
            version_range=">=10.0",
            metadata_path="modules/.submodules.json",
            notes="Prebid.js v10+ uses metadata files",
        )

        assert version.version == "v10.0"
        assert version.version_range == ">=10.0"
        assert version.metadata_path == "modules/.submodules.json"

    def test_repository_structure_version_matching(self):
        """Test version matching in RepositoryStructure."""
        repo = RepositoryStructure(
            repo_name="prebid/Prebid.js",
            repo_type="prebid-js",
        )

        # Add version configs
        v10_config = VersionConfig(version="v10.0", version_range=">=10.0")
        v9_config = VersionConfig(version="v9.0", version_range=">=9.0,<10.0")
        repo.version_configs = [v10_config, v9_config]

        # Test exact match
        assert repo._version_matches("v10.0", v10_config)
        assert not repo._version_matches("v10.0", v9_config)

        # Test range matching
        assert repo._version_matches("v10.5", v10_config)
        assert repo._version_matches("v11.0", v10_config)
        assert not repo._version_matches("v8.5", v9_config)

    def test_version_normalization(self):
        """Test version string normalization."""
        repo = RepositoryStructure(
            repo_name="test/repo",
            repo_type="test",
        )

        # Test the normalize_version function within _version_matches
        v_config = VersionConfig(version="v10.0", version_range=">=10.0")

        assert repo._version_matches("v10.5", v_config)
        assert repo._version_matches("10.5", v_config)
        assert repo._version_matches("v10.5.1", v_config)
        assert not repo._version_matches("v9.8", v_config)

    def test_get_module_category(self):
        """Test getting module category with version fallback."""
        # Default category
        default_cat = ModuleCategory(
            name="adapter",
            display_name="Adapters",
            paths=["adapters/"],
            patterns=[],
        )

        # Version-specific category
        v10_cat = ModuleCategory(
            name="adapter",
            display_name="V10 Adapters",
            paths=["modules/"],
            patterns=[],
            detection_strategy=DetectionStrategy.METADATA_FILE,
        )

        v10_config = VersionConfig(
            version="v10.0",
            version_range=">=10.0",
            module_categories={"adapter": v10_cat},
        )

        repo = RepositoryStructure(
            repo_name="test/repo",
            repo_type="test",
            module_categories={"adapter": default_cat},
            version_configs=[v10_config],
        )

        # Should get version-specific category for v10
        cat = repo.get_module_category("adapter", "v10.5")
        assert cat.display_name == "V10 Adapters"
        assert cat.detection_strategy == DetectionStrategy.METADATA_FILE

        # Should get default category for v9
        cat = repo.get_module_category("adapter", "v9.0")
        assert cat.display_name == "Adapters"

        # Should get default when no version specified
        cat = repo.get_module_category("adapter")
        assert cat.display_name == "Adapters"


class TestConfigurationLoader:
    """Test suite for configuration loader."""

    @pytest.fixture
    def sample_config(self):
        """Sample configuration data."""
        return {
            "prebid/Prebid.js": {
                "repo_type": "prebid-js",
                "description": "Prebid.js repository",
                "default_detection_strategy": "filename_pattern",
                "fetch_strategy": "filenames_only",
                "module_categories": {
                    "bid_adapter": {
                        "display_name": "Bid Adapters",
                        "paths": ["modules/"],
                        "patterns": [
                            {
                                "pattern": "*BidAdapter.js",
                                "pattern_type": "suffix",
                                "name_extraction": "remove_suffix:BidAdapter",
                            }
                        ],
                    }
                },
                "version_configs": [
                    {
                        "version": "v10.0",
                        "version_range": ">=10.0",
                        "metadata_path": "modules/.submodules.json",
                        "module_categories": {
                            "bid_adapter": {
                                "display_name": "Bid Adapters (v10+)",
                                "paths": ["modules/"],
                                "detection_strategy": "metadata_file",
                                "patterns": [
                                    {
                                        "pattern": "*.json",
                                        "pattern_type": "suffix",
                                    }
                                ],
                            }
                        },
                    }
                ],
                "core_paths": ["src/"],
                "test_paths": ["test/"],
                "doc_paths": ["docs/", "*.md"],
            }
        }

    def test_load_config(self, sample_config):
        """Test loading configuration from JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_config, f)
            temp_path = f.name

        try:
            loader = ConfigurationLoader(temp_path)
            config = loader.load_config()

            assert isinstance(config, RepositoryConfig)
            assert "prebid/Prebid.js" in config.repositories

            repo = config.repositories["prebid/Prebid.js"]
            assert repo.repo_type == "prebid-js"
            assert repo.default_detection_strategy == DetectionStrategy.FILENAME_PATTERN
            assert "bid_adapter" in repo.module_categories
            assert len(repo.version_configs) == 1
        finally:
            Path(temp_path).unlink()

    def test_parse_repository(self, sample_config):
        """Test parsing individual repository configuration."""
        loader = ConfigurationLoader("dummy.json")
        repo_data = sample_config["prebid/Prebid.js"]

        repo = loader._parse_repository("prebid/Prebid.js", repo_data)

        assert repo.repo_name == "prebid/Prebid.js"
        assert repo.description == "Prebid.js repository"
        assert len(repo.core_paths) == 1
        assert "src/" in repo.core_paths
        assert len(repo.test_paths) == 1
        assert "test/" in repo.test_paths

    def test_parse_patterns(self):
        """Test pattern parsing."""
        loader = ConfigurationLoader("dummy.json")
        patterns_data = [
            {
                "pattern": "*BidAdapter.js",
                "pattern_type": "suffix",
                "name_extraction": "remove_suffix:BidAdapter",
                "exclude_patterns": ["test*.js"],
            },
            {
                "pattern": "adapters/*",
                "pattern_type": "glob",
            },
        ]

        patterns = loader._parse_patterns(patterns_data)
        assert len(patterns) == 2
        assert patterns[0].pattern == "*BidAdapter.js"
        assert patterns[0].name_extraction == "remove_suffix:BidAdapter"
        assert len(patterns[0].exclude_patterns) == 1
        assert patterns[1].pattern_type == "glob"

    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        loader = ConfigurationLoader("nonexistent.json")
        with pytest.raises(FileNotFoundError):
            loader.load_config()


class TestRepositoryStructureManager:
    """Test suite for repository structure manager."""

    @pytest.fixture
    def manager_with_config(self, sample_config):
        """Create manager with test configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_config, f)
            temp_path = f.name

        manager = RepositoryStructureManager(temp_path)
        yield manager
        Path(temp_path).unlink()

    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return {
            "prebid/Prebid.js": {
                "repo_type": "prebid-js",
                "module_categories": {
                    "bid_adapter": {
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
                    "analytics_adapter": {
                        "display_name": "Analytics Adapters",
                        "paths": ["modules/"],
                        "patterns": [
                            {
                                "pattern": "*AnalyticsAdapter.js",
                                "pattern_type": "suffix",
                                "name_extraction": "remove_suffix:AnalyticsAdapter",
                            }
                        ],
                    },
                },
                "core_paths": ["src/"],
                "test_paths": ["test/"],
                "exclude_paths": ["node_modules/", "build/"],
            }
        }

    def test_extract_repo_name(self):
        """Test repository name extraction from URLs."""
        manager = RepositoryStructureManager()

        # HTTPS URLs
        assert (
            manager._extract_repo_name("https://github.com/prebid/Prebid.js")
            == "prebid/Prebid.js"
        )
        assert (
            manager._extract_repo_name("https://github.com/prebid/Prebid.js.git")
            == "prebid/Prebid.js"
        )

        # SSH URLs
        assert (
            manager._extract_repo_name("git@github.com:prebid/Prebid.js.git")
            == "prebid/Prebid.js"
        )

        # Already extracted
        assert manager._extract_repo_name("prebid/Prebid.js") == "prebid/Prebid.js"

    def test_categorize_file(self, manager_with_config):
        """Test file categorization."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Test bid adapter file
        result = manager_with_config.categorize_file(
            repo_url, "modules/testBidAdapter.js"
        )
        assert "bid_adapter" in result["categories"]
        assert result["module_type"] == "Bid Adapters"
        assert not result["is_core"]
        assert not result["is_test"]

        # Test analytics adapter
        result = manager_with_config.categorize_file(
            repo_url, "modules/googleAnalyticsAdapter.js"
        )
        assert "analytics_adapter" in result["categories"]
        assert result["module_type"] == "Analytics Adapters"

        # Test core file
        result = manager_with_config.categorize_file(repo_url, "src/prebid.js")
        assert result["is_core"]
        assert len(result["categories"]) == 0

        # Test excluded file
        result = manager_with_config.categorize_file(
            repo_url, "node_modules/some-package/index.js"
        )
        assert len(result["categories"]) == 0
        assert not result["is_core"]

    def test_pattern_matching(self, manager_with_config):
        """Test various pattern matching scenarios."""
        manager = manager_with_config

        # Test suffix pattern
        pattern = ModulePattern(pattern="*BidAdapter.js", pattern_type="suffix")
        assert manager._matches_pattern("modules/testBidAdapter.js", pattern)
        assert not manager._matches_pattern("modules/test.js", pattern)

        # Test prefix pattern
        pattern = ModulePattern(pattern="test*", pattern_type="prefix")
        assert manager._matches_pattern("modules/testAdapter.js", pattern)
        assert not manager._matches_pattern("modules/adapterTest.js", pattern)

        # Test glob pattern
        pattern = ModulePattern(pattern="modules/*.js", pattern_type="glob")
        assert manager._matches_pattern("modules/adapter.js", pattern)
        assert not manager._matches_pattern("src/adapter.js", pattern)

    def test_module_info_extraction(self, manager_with_config):
        """Test extracting module information."""
        repo_url = "https://github.com/prebid/Prebid.js"

        info = manager_with_config.get_module_info(
            repo_url, "modules/rubiconBidAdapter.js"
        )
        assert info["module_name"] == "rubicon"
        assert info["module_type"] == "Bid Adapters"
        assert "bid_adapter" in info["categories"]
        assert info["repo_type"] == "prebid-js"

    def test_is_path_type(self, manager_with_config):
        """Test path type checking."""
        manager = manager_with_config

        # Simple path matching
        assert manager._is_path_type("src/utils/test.js", ["src/"])
        assert not manager._is_path_type("modules/test.js", ["src/"])

        # Glob pattern matching
        assert manager._is_path_type("test.md", ["*.md"])
        assert manager._is_path_type("docs/guide.md", ["docs/", "*.md"])

    def test_unknown_repository(self, manager_with_config):
        """Test handling of unknown repository."""
        result = manager_with_config.categorize_file(
            "https://github.com/unknown/repo", "some/file.js"
        )
        assert result["categories"] == []
        assert result["module_type"] is None
        assert not result["is_core"]
