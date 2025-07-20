"""Tests for repository knowledge loader."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from src.pr_agents.config.knowledge_loader import RepositoryKnowledgeLoader


class TestRepositoryKnowledgeLoader:
    """Test repository knowledge loading and merging."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create directory structure
            (config_dir / "repositories" / "prebid").mkdir(parents=True)
            (config_dir / "repository-knowledge").mkdir(parents=True)

            yield config_dir

    @pytest.fixture
    def sample_json_config(self, temp_config_dir):
        """Create sample JSON configuration."""
        config = {
            "repo_name": "prebid/Prebid.js",
            "repo_type": "prebid-js",
            "module_locations": {
                "bid_adapter": {
                    "paths": ["modules/*BidAdapter.js"],
                    "naming_pattern": "endsWith('BidAdapter')",
                    "category": "adapter",
                },
                "rtd_module": {
                    "paths": ["modules/*RtdProvider.js"],
                    "naming_pattern": "endsWith('RtdProvider')",
                    "category": "rtd",
                },
            },
        }

        json_path = temp_config_dir / "repositories" / "prebid" / "prebid-js.json"
        with open(json_path, "w") as f:
            json.dump(config, f)

        return config

    @pytest.fixture
    def sample_yaml_knowledge(self, temp_config_dir):
        """Create sample YAML knowledge."""
        knowledge = {
            "repository": "prebid/Prebid.js",
            "overview": {
                "purpose": "Header bidding library",
                "key_features": ["Real-time bidding", "Multi-format support"],
                "architecture": {
                    "core_components": {"auction_manager": "Manages bid auctions"}
                },
            },
            "directory_structure": {
                "modules": {
                    "patterns": {
                        "*BidAdapter.js": "Bid adapters for SSPs/DSPs",
                        "*RtdProvider.js": "Real-time data providers",
                    }
                }
            },
            "patterns": {
                "error_handling": {"try_catch": {"description": "Wrap JSON parsing"}}
            },
            "code_examples": {
                "bid_adapter": {"description": "Full bid adapter example"}
            },
            "testing": {
                "required_coverage": {
                    "unit_tests": ["isBidRequestValid", "buildRequests"]
                }
            },
        }

        yaml_path = temp_config_dir / "repository-knowledge" / "prebid-js.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(knowledge, f)

        return knowledge

    def test_load_repository_config(
        self, temp_config_dir, sample_json_config, sample_yaml_knowledge
    ):
        """Test loading and merging repository configuration."""
        loader = RepositoryKnowledgeLoader(temp_config_dir)

        config = loader.load_repository_config("prebid/Prebid.js")

        # Check JSON config loaded
        assert config["repo_name"] == "prebid/Prebid.js"
        assert "module_locations" in config
        assert "bid_adapter" in config["module_locations"]

        # Check YAML knowledge merged
        assert "repository_context" in config
        assert config["repository_context"]["purpose"] == "Header bidding library"
        assert len(config["repository_context"]["key_features"]) == 2

        # Check code patterns added
        assert "code_patterns" in config
        assert "error_handling" in config["code_patterns"]

        # Check PR patterns extracted
        assert "pr_patterns" in config
        assert "bid_adapter" in config["pr_patterns"]

        # Check testing requirements added
        assert "testing_requirements" in config

    def test_module_location_enrichment(
        self, temp_config_dir, sample_json_config, sample_yaml_knowledge
    ):
        """Test that module locations are enriched with descriptions."""
        loader = RepositoryKnowledgeLoader(temp_config_dir)

        config = loader.load_repository_config("prebid/Prebid.js")

        # Check bid_adapter has description from YAML
        bid_adapter = config["module_locations"]["bid_adapter"]
        assert "description" in bid_adapter
        assert bid_adapter["description"] == "Bid adapters for SSPs/DSPs"

        # Check rtd_module has description
        rtd_module = config["module_locations"]["rtd_module"]
        assert "description" in rtd_module
        assert rtd_module["description"] == "Real-time data providers"

    def test_missing_json_config(self, temp_config_dir):
        """Test handling of missing JSON configuration."""
        loader = RepositoryKnowledgeLoader(temp_config_dir)

        config = loader.load_repository_config("unknown/repo")

        # Should return empty config
        assert config == {}

    def test_missing_yaml_knowledge(self, temp_config_dir, sample_json_config):
        """Test handling of missing YAML knowledge."""
        loader = RepositoryKnowledgeLoader(temp_config_dir)

        # Remove YAML file
        yaml_path = temp_config_dir / "repository-knowledge" / "prebid-js.yaml"
        if yaml_path.exists():
            yaml_path.unlink()

        config = loader.load_repository_config("prebid/Prebid.js")

        # Should still have JSON config
        assert config["repo_name"] == "prebid/Prebid.js"
        assert "module_locations" in config

        # But no enriched fields
        assert "repository_context" not in config
        assert "code_patterns" not in config

    def test_malformed_json(self, temp_config_dir):
        """Test handling of malformed JSON."""
        json_path = temp_config_dir / "repositories" / "prebid" / "prebid-js.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)

        with open(json_path, "w") as f:
            f.write("{ invalid json")

        loader = RepositoryKnowledgeLoader(temp_config_dir)
        config = loader.load_repository_config("prebid/Prebid.js")

        # Should return empty config
        assert config == {}

    def test_malformed_yaml(self, temp_config_dir, sample_json_config):
        """Test handling of malformed YAML."""
        yaml_path = temp_config_dir / "repository-knowledge" / "prebid-js.yaml"
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        with open(yaml_path, "w") as f:
            f.write("invalid:\n  - yaml\n    bad indent")

        loader = RepositoryKnowledgeLoader(temp_config_dir)
        config = loader.load_repository_config("prebid/Prebid.js")

        # Should still have JSON config
        assert config["repo_name"] == "prebid/Prebid.js"
        # But no YAML enrichment
        assert "repository_context" not in config

    def test_pattern_to_module_type_mapping(self, temp_config_dir):
        """Test pattern to module type mapping."""
        loader = RepositoryKnowledgeLoader(temp_config_dir)

        # Test known patterns
        assert loader._pattern_to_module_type("*BidAdapter.js") == "bid_adapter"
        assert (
            loader._pattern_to_module_type("*AnalyticsAdapter.js")
            == "analytics_adapter"
        )
        assert loader._pattern_to_module_type("*IdSystem.js") == "id_system"
        assert loader._pattern_to_module_type("*RtdProvider.js") == "rtd_module"

        # Test unknown pattern
        assert loader._pattern_to_module_type("*Unknown.js") is None

    def test_repository_name_normalization(self, temp_config_dir, sample_json_config):
        """Test that repository names are normalized correctly."""
        loader = RepositoryKnowledgeLoader(temp_config_dir)

        # Should normalize dots in repo name
        config = loader.load_repository_config("prebid/Prebid.js")
        assert "repo_name" in config

        # File should be at prebid-js.json (dots replaced with dashes)
        json_path = temp_config_dir / "repositories" / "prebid" / "prebid-js.json"
        assert json_path.exists()
