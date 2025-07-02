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
        """Set up test environment with config and registry files."""
        # Create repository structure config
        config_data = {
            "prebid/Prebid.js": {
                "repo_type": "prebid-js",
                "description": "Prebid.js - Header Bidding Library",
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
                        "display_name": "Real-Time Data Modules",
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

        config_file = tmp_path / "config" / "repository_structures.json"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(json.dumps(config_data))

        # Create YAML registry
        registry_data = """
repo: https://github.com/prebid/Prebid.js
structure:
  source:
    core:
      - ++
      - files('.js')
    libraries:
      analytics: ++
      video: ++
    adapters:
      - modules/++ endsWith('BidAdapter', file)
      - modules/++ endsWith('AnalyticsAdapter', file)
  build:
    webpack: ++
    gulp: file:gulpfile.js
  testing:
    unit: test/spec/++
    integration: test/integration/++
  docs:
    - ++
    - files('.md')
  dev:
    config: files('.json')
definitions: []
rules: []
"""

        registry_dir = tmp_path / "registry" / "prebid"
        registry_dir.mkdir(parents=True)
        registry_file = registry_dir / "prebid.js.yaml"
        registry_file.write_text(registry_data)

        return {
            "config_file": str(config_file),
            "registry_path": str(registry_dir),
            "tmp_path": tmp_path,
        }

    def test_complete_pr_tagging_flow(self, setup_test_environment):
        """Test complete PR tagging flow with real files."""
        # Create processor with test paths
        processor = PRTaggerProcessor(
            registry_path=setup_test_environment["registry_path"],
            config_file=setup_test_environment["config_file"],
        )

        # Sample PR data
        component_data = {
            "repository": {
                "clone_url": "https://github.com/prebid/Prebid.js",
                "repo_type": "prebid-js",
            },
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
        assert any("source.adapters" in tag for tag in adapter_tags["tags"])

        # Check core file tagging
        core_tags = data["file_tags"]["src/core/newAuctionModule.js"]
        assert core_tags["is_core"] is True
        assert core_tags["is_new_file"] is True
        assert any("source.core" in tag for tag in core_tags["tags"])
        assert core_tags["impact_level"] == "high"  # New core file = high impact

        # Check library file tagging
        lib_tags = data["file_tags"]["libraries/analytics/newTracker.js"]
        assert lib_tags["is_core"] is True  # libraries/ is in core_paths
        assert lib_tags["is_new_file"] is True
        assert any("source.libraries.analytics" in tag for tag in lib_tags["tags"])

        # Check test file tagging
        test_tags = data["file_tags"]["test/spec/modules/rubiconBidAdapter_spec.js"]
        assert test_tags["is_test"] is True
        assert any("testing.unit" in tag for tag in test_tags["tags"])
        assert test_tags["impact_level"] == "low"

        # Check build file tagging
        build_tags = data["file_tags"]["build/webpack/optimization.js"]
        assert build_tags["is_new_file"] is True
        assert any("build.webpack" in tag for tag in build_tags["tags"])
        assert build_tags["impact_level"] == "high"  # Build files = high impact

        # Check documentation tagging
        doc_tags = data["file_tags"]["docs/bidders/rubicon.md"]
        assert doc_tags["is_doc"] is True
        assert any("docs" in tag for tag in doc_tags["tags"])
        assert doc_tags["impact_level"] == "minimal"

        # Check v10+ metadata file
        metadata_tags = data["file_tags"]["metadata/modules/rubiconBidAdapter.json"]
        # Should be categorized as bid_adapter in v10+
        assert "bid_adapter" in metadata_tags["module_categories"]

        # Verify PR-level analysis
        assert data["pr_impact_level"] == "high"  # Due to core and build changes

        # Check tag hierarchy
        hierarchy = data["tag_hierarchy"]
        assert "source" in hierarchy
        assert "core" in hierarchy["source"]
        assert "libraries" in hierarchy["source"]
        assert "analytics" in hierarchy["source"]["libraries"]
        assert "build" in hierarchy
        assert "webpack" in hierarchy["build"]

        # Check statistics
        stats = data["stats"]
        assert stats["total_files"] == 7
        assert stats["new_files_count"] == 3
        assert stats["core_files_count"] == 2  # src/core and libraries
        assert stats["test_files_count"] == 1
        assert stats["doc_files_count"] == 1
        assert stats["files_by_impact"]["high"] >= 2  # At least core and build
        assert stats["files_by_impact"]["minimal"] >= 1  # At least docs

        # Check affected modules
        assert "bid_adapter" in data["affected_modules"]
        assert "rubicon" in data["affected_modules"]["bid_adapter"]

    def test_version_aware_processing(self, setup_test_environment):
        """Test version-aware file processing."""
        processor = PRTaggerProcessor(
            registry_path=setup_test_environment["registry_path"],
            config_file=setup_test_environment["config_file"],
        )

        # Test with v10+ version
        component_data = {
            "repository": {
                "clone_url": "https://github.com/prebid/Prebid.js",
                "repo_type": "prebid-js",
                "default_branch": "master",  # Will use as version
            },
            "code_changes": {
                "files": [
                    # v10+ metadata file
                    {
                        "filename": "metadata/modules/appnexusBidAdapter.json",
                        "status": "added",
                        "additions": 20,
                        "deletions": 0,
                    },
                    # Traditional adapter file
                    {
                        "filename": "modules/appnexusBidAdapter.js",
                        "status": "modified",
                        "additions": 10,
                        "deletions": 5,
                    },
                ]
            },
        }

        # Mock version detection to return v10.0
        with patch.object(processor, "_detect_version", return_value="v10.0"):
            result = processor.process(component_data)

        assert result.success is True
        data = result.data

        # Both files should be categorized as bid_adapter
        metadata_file = data["file_tags"]["metadata/modules/appnexusBidAdapter.json"]
        js_file = data["file_tags"]["modules/appnexusBidAdapter.js"]

        assert "bid_adapter" in metadata_file["module_categories"]
        assert "bid_adapter" in js_file["module_categories"]
        assert metadata_file["module_name"] == "appnexus"
        assert js_file["module_name"] == "appnexus"

    def test_hierarchical_tag_aggregation(self, setup_test_environment):
        """Test hierarchical tag aggregation at PR level."""
        processor = PRTaggerProcessor(
            registry_path=setup_test_environment["registry_path"],
            config_file=setup_test_environment["config_file"],
        )

        component_data = {
            "repository": {
                "clone_url": "https://github.com/prebid/Prebid.js",
                "repo_type": "prebid-js",
            },
            "code_changes": {
                "files": [
                    {"filename": "src/core/auction.js", "status": "modified"},
                    {"filename": "libraries/analytics/tracker.js", "status": "added"},
                    {"filename": "libraries/video/player.js", "status": "modified"},
                    {"filename": "build/webpack/config.js", "status": "modified"},
                ]
            },
        }

        result = processor.process(component_data)
        data = result.data

        # Check PR-level hierarchical tags
        pr_tags = data["pr_hierarchical_tags"]

        # Should have tags for all touched areas
        primary_tags = {tag["primary"] for tag in pr_tags}
        assert "source" in primary_tags
        assert "build" in primary_tags

        # Check for specific hierarchical paths
        tag_strings = {
            f"{tag['primary']}.{tag.get('secondary', '')}"
            for tag in pr_tags
            if tag.get("secondary")
        }
        assert "source.core" in tag_strings
        assert "source.libraries" in tag_strings
        assert "build.webpack" in tag_strings

        # Verify tag hierarchy structure
        hierarchy = data["tag_hierarchy"]
        assert len(hierarchy["source"]["libraries"]) == 2  # analytics and video
        assert "libraries/analytics/tracker.js" in hierarchy["source"]["libraries"]
        assert "libraries/video/player.js" in hierarchy["source"]["libraries"]
