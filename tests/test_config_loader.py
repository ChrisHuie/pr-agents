"""
Tests for the configuration loader with multi-file support.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.pr_agents.config.loader import ConfigurationLoader
from src.pr_agents.config.models import DetectionStrategy
from src.pr_agents.config.validator import ConfigurationValidator


class TestMultiFileConfigLoader:
    """Test the configuration loader."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            # Create directory structure
            (config_dir / "repositories" / "prebid").mkdir(parents=True)
            (config_dir / "repositories" / "shared").mkdir(parents=True)
            (config_dir / "schema").mkdir(parents=True)

            yield config_dir

    @pytest.fixture
    def base_config(self):
        """Sample base configuration."""
        return {
            "$schema": "../schema/repository.schema.json",
            "description": "Base configuration",
            "module_categories": {
                "bid_adapter": {
                    "display_name": "Bid Adapters",
                    "patterns": [
                        {
                            "pattern": "*BidAdapter.js",
                            "type": "suffix",
                            "name_extraction": "remove_suffix:BidAdapter",
                        }
                    ],
                }
            },
        }

    @pytest.fixture
    def repo_config(self):
        """Sample repository configuration."""
        return {
            "$schema": "../../schema/repository.schema.json",
            "repo_name": "prebid/Prebid.js",
            "repo_type": "prebid-js",
            "description": "Test repository",
            "extends": "../shared/prebid-base.json",
            "detection_strategy": "hybrid",
            "fetch_strategy": "filenames_only",
            "module_categories": {"bid_adapter": {"paths": ["modules/"]}},
            "paths": {
                "core": ["src/"],
                "test": ["test/"],
                "docs": ["docs/"],
                "exclude": ["node_modules/"],
            },
        }

    def test_load_from_master_file(self, temp_config_dir, base_config, repo_config):
        """Test loading configurations from a master file."""
        # Create base config
        base_path = temp_config_dir / "repositories" / "shared" / "prebid-base.json"
        with open(base_path, "w") as f:
            json.dump(base_config, f)

        # Create repo config
        repo_path = temp_config_dir / "repositories" / "prebid" / "prebid-js.json"
        with open(repo_path, "w") as f:
            json.dump(repo_config, f)

        # Create master file
        master_config = {"repositories": ["./repositories/prebid/prebid-js.json"]}
        master_path = temp_config_dir / "repositories.json"
        with open(master_path, "w") as f:
            json.dump(master_config, f)

        # Load configuration
        loader = ConfigurationLoader(str(temp_config_dir))
        config = loader.load_config()

        # Verify
        assert len(config.repositories) == 1
        assert "prebid/Prebid.js" in config.repositories

        repo = config.repositories["prebid/Prebid.js"]
        assert repo.repo_type == "prebid-js"
        assert repo.default_detection_strategy == DetectionStrategy.HYBRID
        assert len(repo.module_categories) == 1
        assert "bid_adapter" in repo.module_categories

    def test_inheritance(self, temp_config_dir, base_config, repo_config):
        """Test configuration inheritance."""
        # Create base config with multiple categories
        base_config["module_categories"]["analytics_adapter"] = {
            "display_name": "Analytics Adapters",
            "patterns": [{"pattern": "*AnalyticsAdapter.js", "type": "suffix"}],
        }

        base_path = temp_config_dir / "repositories" / "shared" / "prebid-base.json"
        with open(base_path, "w") as f:
            json.dump(base_config, f)

        # Create repo config that extends base
        repo_path = temp_config_dir / "repositories" / "prebid" / "prebid-js.json"
        with open(repo_path, "w") as f:
            json.dump(repo_config, f)

        # Load configuration
        loader = ConfigurationLoader(str(repo_path))
        config = loader.load_config()

        # Verify inheritance
        repo = config.repositories["prebid/Prebid.js"]
        assert len(repo.module_categories) == 2  # Should have both categories
        assert "bid_adapter" in repo.module_categories
        assert "analytics_adapter" in repo.module_categories

        # Check that patterns were inherited
        bid_adapter = repo.module_categories["bid_adapter"]
        assert len(bid_adapter.patterns) == 1
        assert bid_adapter.patterns[0].pattern == "*BidAdapter.js"

    def test_version_overrides(self, temp_config_dir):
        """Test version-specific overrides."""
        config_data = {
            "repo_name": "prebid/Prebid.js",
            "repo_type": "prebid-js",
            "module_categories": {
                "bid_adapter": {
                    "display_name": "Bid Adapters",
                    "paths": ["modules/"],
                    "patterns": [{"pattern": "*BidAdapter.js", "type": "suffix"}],
                }
            },
            "version_overrides": {
                "v10.0+": {
                    "module_categories": {
                        "bid_adapter": {
                            "paths": ["modules/", "metadata/modules/"],
                            "detection_strategy": "metadata_file",
                            "metadata_field": "componentType",
                            "metadata_value": "bidder",
                        }
                    }
                }
            },
        }

        config_path = temp_config_dir / "test.json"
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        loader = ConfigurationLoader(str(config_path))
        config = loader.load_config()

        repo = config.repositories["prebid/Prebid.js"]
        assert len(repo.version_configs) == 1

        # Check version config
        ver_config = repo.version_configs[0]
        assert ver_config.version == "v10.0"
        assert ver_config.version_range == ">=10.0"
        assert "bid_adapter" in ver_config.module_categories

    def test_backward_compatibility(self, temp_config_dir):
        """Test loading old single-file format."""
        old_format = {
            "prebid/Prebid.js": {
                "repo_type": "prebid-js",
                "default_detection_strategy": "hybrid",
                "module_categories": {
                    "bid_adapter": {
                        "name": "bid_adapter",
                        "display_name": "Bid Adapters",
                        "paths": ["modules/"],
                    }
                },
                "core_paths": ["src/"],
                "test_paths": ["test/"],
            }
        }

        config_path = temp_config_dir / "old_format.json"
        with open(config_path, "w") as f:
            json.dump(old_format, f)

        loader = ConfigurationLoader(str(config_path))
        config = loader.load_config()

        assert len(config.repositories) == 1
        repo = config.repositories["prebid/Prebid.js"]
        assert repo.repo_type == "prebid-js"
        assert repo.core_paths == ["src/"]

    def test_deep_merge(self, temp_config_dir):
        """Test deep merging of configurations."""
        base = {
            "module_categories": {
                "bid_adapter": {
                    "display_name": "Bid Adapters",
                    "patterns": [{"pattern": "*BidAdapter.js"}],
                    "paths": ["modules/"],
                }
            },
            "paths": {"core": ["src/"], "test": ["test/"]},
        }

        override = {
            "module_categories": {
                "bid_adapter": {
                    "paths": ["modules/", "new_modules/"],  # Override paths
                    "detection_strategy": "hybrid",  # Add new field
                },
                "analytics_adapter": {  # Add new category
                    "display_name": "Analytics",
                    "paths": ["analytics/"],
                },
            },
            "paths": {"docs": ["docs/"]},  # Add new path type
        }

        loader = ConfigurationLoader(str(temp_config_dir))
        merged = loader._deep_merge(base, override)

        # Check merge results
        assert len(merged["module_categories"]) == 2
        assert merged["module_categories"]["bid_adapter"]["paths"] == [
            "modules/",
            "new_modules/",
        ]
        assert (
            merged["module_categories"]["bid_adapter"]["display_name"] == "Bid Adapters"
        )  # Preserved
        assert (
            merged["module_categories"]["bid_adapter"]["detection_strategy"] == "hybrid"
        )  # Added
        assert "analytics_adapter" in merged["module_categories"]
        assert merged["paths"]["core"] == ["src/"]  # Preserved
        assert merged["paths"]["docs"] == ["docs/"]  # Added

    def test_pattern_parsing(self, temp_config_dir):
        """Test parsing of different pattern formats."""
        config_data = {
            "repo_name": "test/repo",
            "repo_type": "test",
            "module_categories": {
                "test_category": {
                    "display_name": "Test",
                    "patterns": [
                        {
                            "pattern": "*Adapter.js",
                            "type": "suffix",
                            "name_extraction": "remove_suffix:Adapter",
                            "exclude": ["test/*", "mock/*"],
                        },
                        {"pattern": "modules/*", "type": "directory"},
                    ],
                }
            },
        }

        config_path = temp_config_dir / "test.json"
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        loader = ConfigurationLoader(str(config_path))
        config = loader.load_config()

        repo = config.repositories["test/repo"]
        category = repo.module_categories["test_category"]
        assert len(category.patterns) == 2

        # Check first pattern
        pattern1 = category.patterns[0]
        assert pattern1.pattern == "*Adapter.js"
        assert pattern1.pattern_type == "suffix"
        assert pattern1.name_extraction == "remove_suffix:Adapter"
        assert pattern1.exclude_patterns == ["test/*", "mock/*"]

        # Check second pattern
        pattern2 = category.patterns[1]
        assert pattern2.pattern == "modules/*"
        assert pattern2.pattern_type == "directory"


class TestConfigurationValidator:
    """Test configuration validation."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        # Create a minimal schema for testing
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["repo_name", "repo_type", "module_categories"],
            "properties": {
                "repo_name": {"type": "string"},
                "repo_type": {"type": "string"},
                "module_categories": {"type": "object"},
            },
        }

        from jsonschema import Draft7Validator

        validator = ConfigurationValidator()
        validator.schema = schema
        validator.validator = Draft7Validator(schema)
        return validator

    def test_validate_valid_config(self, validator):
        """Test validation of valid configuration."""
        config = {
            "repo_name": "test/repo",
            "repo_type": "test",
            "module_categories": {"test": {"display_name": "Test"}},
        }

        is_valid, errors = validator.validate_config(config)
        assert is_valid
        assert len(errors) == 0

    def test_validate_missing_required_field(self, validator):
        """Test validation with missing required field."""
        config = {
            "repo_name": "test/repo",
            # Missing repo_type
            "module_categories": {},
        }

        is_valid, errors = validator.validate_config(config)
        assert not is_valid
        assert any("repo_type" in error for error in errors)

    def test_check_pattern_consistency(self, validator):
        """Test pattern consistency checking."""
        config = {
            "module_categories": {
                "test": {
                    "patterns": [
                        {
                            "pattern": "Adapter.js",
                            "type": "suffix",
                        },  # Should start with *
                        {"pattern": "test", "type": "prefix"},  # Should end with *
                        {"pattern": "*Test.js", "type": "suffix"},  # Valid
                        {"pattern": "*Test.js", "type": "suffix"},  # Duplicate
                    ]
                }
            }
        }

        issues = validator.check_pattern_consistency(config)
        # Should find: suffix without *, prefix without *, and duplicates
        assert len(issues) == 3
        assert any("should start with '*'" in issue for issue in issues)
        assert any("should end with '*'" in issue for issue in issues)
        assert any("Duplicate patterns" in issue for issue in issues)
