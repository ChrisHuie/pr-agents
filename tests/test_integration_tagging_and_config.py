"""
Integration tests for Repository Configuration and PR Tagging working together.
"""

import json
from unittest.mock import patch

import pytest

from src.pr_agents.pr_processing.processors.pr_tagger import PRTaggerProcessor


class TestIntegrationTaggingAndConfig:
    """Test integration between repository config and PR tagging."""

    @pytest.fixture
    def setup_test_environment(self, tmp_path):
        """Set up test environment with config files."""
        # Create repository structure config using new format
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)

        # Create repositories directory
        repos_dir = config_dir / "repositories" / "prebid"
        repos_dir.mkdir(parents=True)

        # Create repository configuration
        repo_config = {
            "repo_name": "prebid/Prebid.js",
            "repo_type": "prebid-js",
            "description": "Prebid.js - Header Bidding Library",
            "detection_strategy": "hybrid",
            "fetch_strategy": "filenames_only",
            "default_version": "v10.0",
            "module_categories": {
                "bid_adapter": {
                    "paths": ["modules/"],
                    "patterns": [
                        {
                            "pattern": "*BidAdapter.js",
                            "type": "suffix",
                            "name_extraction": "remove_suffix:BidAdapter",
                        }
                    ],
                },
                "rtd_module": {
                    "paths": ["modules/"],
                    "patterns": [
                        {
                            "pattern": "*RtdProvider.js",
                            "type": "suffix",
                            "name_extraction": "remove_suffix:RtdProvider",
                        }
                    ],
                },
            },
            "version_overrides": {
                "v10.0+": {
                    "metadata_path": "metadata/modules/",
                    "module_categories": {
                        "bid_adapter": {
                            "paths": ["modules/", "metadata/modules/"],
                            "patterns": [
                                {
                                    "pattern": "*BidAdapter.js",
                                    "type": "suffix",
                                    "name_extraction": "remove_suffix:BidAdapter",
                                },
                                {
                                    "pattern": "*BidAdapter.json",
                                    "type": "suffix",
                                    "name_extraction": "remove_suffix:BidAdapter",
                                },
                            ],
                            "detection_strategy": "metadata_file",
                        }
                    },
                }
            },
            "paths": {
                "core": ["src/", "libraries/"],
                "test": ["test/spec/"],
                "docs": ["docs/"],
            },
        }

        repo_file = repos_dir / "prebid-js.json"
        repo_file.write_text(json.dumps(repo_config))

        # Create master repositories.json file
        master_config = {"repositories": ["./repositories/prebid/prebid-js.json"]}

        master_file = config_dir / "repositories.json"
        master_file.write_text(json.dumps(master_config))

        return {
            "config_dir": str(config_dir),
            "tmp_path": tmp_path,
        }

    def test_complete_pr_tagging_flow(self, setup_test_environment):
        """Test complete PR tagging flow with JSON configuration."""
        # Mock the registry loader to avoid YAML parsing issues
        with patch(
            "src.pr_agents.pr_processing.processors.pr_tagger.RegistryLoader"
        ) as mock_registry_loader:
            mock_registry_loader.return_value.get_repo_registry.return_value = None

            # Create processor with test paths
            processor = PRTaggerProcessor(
                config_file=setup_test_environment["config_dir"],
            )

            # Sample PR data
            component_data = {
                "repository": {
                    "clone_url": "https://github.com/prebid/Prebid.js",
                    "repo_type": "prebid-js",
                },
                "version": "v10.5",  # Add version info for v10+ features
                "code_changes": {
                    "files": [
                        # Bid adapter (modified)
                        {
                            "filename": "modules/rubiconBidAdapter.js",
                            "status": "modified",
                            "additions": 50,
                            "deletions": 20,
                        },
                        # Core file (new)
                        {
                            "filename": "src/core/newAuctionModule.js",
                            "status": "added",
                            "additions": 200,
                            "deletions": 0,
                        },
                        # Library file (new)
                        {
                            "filename": "libraries/analytics/newTracker.js",
                            "status": "added",
                            "additions": 100,
                            "deletions": 0,
                        },
                        # Test file
                        {
                            "filename": "test/spec/modules/rubiconBidAdapter_spec.js",
                            "status": "modified",
                            "additions": 30,
                            "deletions": 10,
                        },
                        # Build file
                        {
                            "filename": "build/webpack/optimization.js",
                            "status": "added",
                            "additions": 50,
                            "deletions": 0,
                        },
                        # Documentation
                        {
                            "filename": "docs/bidders/rubicon.md",
                            "status": "modified",
                            "additions": 10,
                            "deletions": 5,
                        },
                        # v10+ metadata file
                        {
                            "filename": "metadata/modules/rubiconBidAdapter.json",
                            "status": "modified",
                            "additions": 5,
                            "deletions": 2,
                        },
                    ]
                },
            }

            # Process the PR
            result = processor.process(component_data)

            assert result.success is True
            data = result.data

            # Verify file categorization
            assert len(data["file_tags"]) == 7

            # Check bid adapter tagging
            adapter_tags = data["file_tags"]["modules/rubiconBidAdapter.js"]
            assert "bid_adapter" in adapter_tags["module_categories"]
            assert adapter_tags["module_name"] == "rubicon"
            assert not adapter_tags["is_new_file"]

            # Check core file tagging
            core_tags = data["file_tags"]["src/core/newAuctionModule.js"]
            assert core_tags["is_core"] is True
            assert core_tags["is_new_file"] is True

            # Check library file tagging
            lib_tags = data["file_tags"]["libraries/analytics/newTracker.js"]
            assert lib_tags["is_core"] is True  # libraries/ is in core_paths
            assert lib_tags["is_new_file"] is True

            # Check test file tagging
            test_tags = data["file_tags"]["test/spec/modules/rubiconBidAdapter_spec.js"]
            assert test_tags["is_test"] is True

            # Check build file tagging
            build_tags = data["file_tags"]["build/webpack/optimization.js"]
            assert build_tags["is_new_file"] is True

            # Check documentation tagging
            doc_tags = data["file_tags"]["docs/bidders/rubicon.md"]
            assert doc_tags["is_doc"] is True

            # Check v10+ metadata file
            metadata_tags = data["file_tags"]["metadata/modules/rubiconBidAdapter.json"]
            # Should be categorized as bid_adapter in v10+
            assert "bid_adapter" in metadata_tags["module_categories"]

            # Verify PR-level analysis
            assert data["pr_impact_level"] in [
                "critical",
                "high",
                "medium",
                "low",
                "minimal",
            ]

            # Check statistics
            stats = data["stats"]
            assert stats["total_files"] == 7
            assert stats["new_files_count"] == 3
            assert stats["core_files_count"] == 2  # src/core and libraries
            assert stats["test_files_count"] == 1
            assert stats["doc_files_count"] == 1

            # Check affected modules
            assert "bid_adapter" in data["affected_modules"]
            assert "rubicon" in data["affected_modules"]["bid_adapter"]

    def test_version_aware_processing(self, setup_test_environment):
        """Test version-aware file processing."""
        # Mock the registry loader to avoid YAML parsing issues
        with patch(
            "src.pr_agents.pr_processing.processors.pr_tagger.RegistryLoader"
        ) as mock_registry_loader:
            mock_registry_loader.return_value.get_repo_registry.return_value = None

            processor = PRTaggerProcessor(
                config_file=setup_test_environment["config_dir"],
            )

            # Test with v10+ version
            component_data = {
                "repository": {
                    "clone_url": "https://github.com/prebid/Prebid.js",
                    "repo_type": "prebid-js",
                    "default_branch": "master",
                },
                "version": "v10.5",
                "code_changes": {
                    "files": [
                        # v10+ metadata file
                        {
                            "filename": "metadata/modules/testBidAdapter.json",
                            "status": "added",
                            "additions": 50,
                            "deletions": 0,
                        },
                        # Regular module file
                        {
                            "filename": "modules/testBidAdapter.js",
                            "status": "added",
                            "additions": 200,
                            "deletions": 0,
                        },
                    ]
                },
            }

            result = processor.process(component_data)

            assert result.success is True
            data = result.data

            # Check metadata file detection
            metadata_tags = data["file_tags"]["metadata/modules/testBidAdapter.json"]
            assert "bid_adapter" in metadata_tags["module_categories"]

            # Check module file detection
            module_tags = data["file_tags"]["modules/testBidAdapter.js"]
            assert "bid_adapter" in module_tags["module_categories"]
            assert module_tags["module_name"] == "test"

            # Check affected modules
            assert "bid_adapter" in data["affected_modules"]
            assert "test" in data["affected_modules"]["bid_adapter"]

    def test_hierarchical_tag_aggregation(self, setup_test_environment):
        """Test hierarchical tag aggregation without YAML registry."""
        # Mock the registry loader to avoid YAML parsing issues
        with patch(
            "src.pr_agents.pr_processing.processors.pr_tagger.RegistryLoader"
        ) as mock_registry_loader:
            mock_registry_loader.return_value.get_repo_registry.return_value = None

            processor = PRTaggerProcessor(
                config_file=setup_test_environment["config_dir"],
            )

            # Test with files in different categories
            component_data = {
                "repository": {
                    "clone_url": "https://github.com/prebid/Prebid.js",
                    "repo_type": "prebid-js",
                },
                "code_changes": {
                    "files": [
                        # Multiple bid adapters
                        {
                            "filename": "modules/adapter1BidAdapter.js",
                            "status": "added",
                            "additions": 100,
                            "deletions": 0,
                        },
                        {
                            "filename": "modules/adapter2BidAdapter.js",
                            "status": "modified",
                            "additions": 50,
                            "deletions": 20,
                        },
                        # RTD module
                        {
                            "filename": "modules/testRtdProvider.js",
                            "status": "added",
                            "additions": 150,
                            "deletions": 0,
                        },
                    ]
                },
            }

            result = processor.process(component_data)

            assert result.success is True
            data = result.data

            # Check module categories
            assert len(data["module_categories"]) >= 1
            assert "bid_adapter" in data["module_categories"]
            assert "rtd_module" in data["module_categories"]

            # Check affected modules
            affected = data["affected_modules"]
            assert "bid_adapter" in affected
            assert "rtd_module" in affected
            assert "adapter1" in affected["bid_adapter"]
            assert "adapter2" in affected["bid_adapter"]
            assert "test" in affected["rtd_module"]

            # Check statistics
            stats = data["stats"]
            assert stats["total_files"] == 3
            assert stats["new_files_count"] == 2
            assert stats["module_count"] == 3  # 2 bid adapters + 1 rtd module
