"""
Tests for PR Tagging Processor.
"""

from unittest.mock import Mock, patch

import pytest
import yaml

from src.pr_agents.pr_processing.pattern_evaluator import PatternEvaluator
from src.pr_agents.pr_processing.processors.pr_tagger import PRTaggerProcessor
from src.pr_agents.pr_processing.registry_loader import RegistryLoader
from src.pr_agents.pr_processing.tagging_models import (
    FileTag,
    HierarchicalTag,
    ImpactLevel,
    TaggingResult,
    YAMLPattern,
    YAMLRegistryStructure,
)


class TestHierarchicalTag:
    """Test HierarchicalTag model."""

    def test_hierarchical_tag_creation(self):
        """Test creating hierarchical tags."""
        tag = HierarchicalTag(
            primary="source", secondary="libraries", tertiary="analytics"
        )

        assert tag.primary == "source"
        assert tag.secondary == "libraries"
        assert tag.tertiary == "analytics"
        assert tag.to_string() == "source.libraries.analytics"

    def test_hierarchical_tag_from_path(self):
        """Test creating tag from path."""
        tag = HierarchicalTag.from_path(["build", "webpack"])
        assert tag.primary == "build"
        assert tag.secondary == "webpack"
        assert tag.tertiary is None
        assert tag.to_string() == "build.webpack"

        # Test with single component
        tag = HierarchicalTag.from_path(["docs"])
        assert tag.primary == "docs"
        assert tag.secondary is None
        assert tag.to_string() == "docs"


class TestFileTag:
    """Test FileTag model."""

    def test_file_tag_creation(self):
        """Test creating file tags."""
        file_tag = FileTag(filepath="modules/rubiconBidAdapter.js", is_new_file=True)

        assert file_tag.filepath == "modules/rubiconBidAdapter.js"
        assert file_tag.is_new_file is True
        assert file_tag.impact_level == ImpactLevel.MINIMAL
        assert len(file_tag.hierarchical_tags) == 0

    def test_add_hierarchical_tag(self):
        """Test adding hierarchical tags."""
        file_tag = FileTag(filepath="src/core.js")
        file_tag.add_hierarchical_tag("source", "core")

        assert len(file_tag.hierarchical_tags) == 1
        assert file_tag.hierarchical_tags[0].primary == "source"
        assert file_tag.hierarchical_tags[0].secondary == "core"
        assert "source.core" in file_tag.flat_tags


class TestTaggingResult:
    """Test TaggingResult model."""

    def test_add_file_to_hierarchy(self):
        """Test adding files to hierarchy structure."""
        result = TaggingResult()

        # Add files with secondary tags
        result.add_file_to_hierarchy("src/core.js", "source", "core")
        result.add_file_to_hierarchy("src/utils.js", "source", "core")
        result.add_file_to_hierarchy("modules/adapter.js", "source", "adapters")

        # Add file with only primary tag
        result.add_file_to_hierarchy("README.md", "docs")

        assert "source" in result.tag_hierarchy
        assert "core" in result.tag_hierarchy["source"]
        assert len(result.tag_hierarchy["source"]["core"]) == 2
        assert "src/core.js" in result.tag_hierarchy["source"]["core"]
        assert "adapters" in result.tag_hierarchy["source"]
        assert "_root" in result.tag_hierarchy["docs"]


class TestRegistryLoader:
    """Test YAML registry loader."""

    @pytest.fixture
    def sample_yaml_content(self):
        """Sample YAML registry content."""
        return """
repo: https://github.com/prebid/Prebid.js
structure:
  source:
    core: ++
    libraries:
      - ++
      - files('.js')
    adapters:
      - modules/++ endsWith('BidAdapter', file)
  build:
    webpack: ++
    gulp: file:gulpfile.js
  testing:
    unit: test/spec/++
    integration: test/integration/++
  docs: ++
definitions:
  - name: "adapter_rule"
    description: "Rule for adapters"
    rules_class: "AdapterRule"
    scope: "per_file"
    tags: ["adapter", "bidding"]
rules: []
"""

    def test_load_registry_file(self, tmp_path, sample_yaml_content):
        """Test loading a YAML registry file."""
        # Create temporary YAML file
        yaml_file = tmp_path / "prebid.js.yaml"
        yaml_file.write_text(sample_yaml_content)

        loader = RegistryLoader(str(tmp_path))

        # Check that registry was loaded
        assert len(loader.registry_cache) == 1
        assert "prebid.js" in loader.registry_cache

        registry = loader.registry_cache["prebid.js"]
        assert registry.repo_url == "https://github.com/prebid/Prebid.js"
        assert "source" in registry.structure
        assert len(registry.definitions) == 1

    def test_parse_structure_patterns(self, sample_yaml_content):
        """Test parsing structure into patterns."""
        data = yaml.safe_load(sample_yaml_content)
        loader = RegistryLoader("dummy")

        patterns = loader.parse_structure_patterns(data["structure"])

        # Should have patterns for all paths
        assert len(patterns) > 0

        # Check for specific patterns
        path_components_set = {tuple(p.path_components) for p in patterns}
        assert ("source", "core") in path_components_set
        assert ("source", "libraries") in path_components_set
        assert ("build", "webpack") in path_components_set

        # Check pattern types
        pattern_types = {p.pattern_type for p in patterns}
        assert "++" in pattern_types
        assert "file" in pattern_types
        assert "endsWith" in pattern_types

    def test_parse_pattern_types(self):
        """Test parsing different pattern types."""
        loader = RegistryLoader("dummy")

        # Test ++ pattern
        pattern = loader._parse_pattern_item("++", ["source", "core"])
        assert pattern.pattern_type == "++"
        assert pattern.path_components == ["source", "core"]

        # Test dir pattern
        pattern = loader._parse_pattern_item("dir:modules", ["source"])
        assert pattern.pattern_type == "dir"
        assert pattern.pattern_value == "modules"

        # Test file pattern
        pattern = loader._parse_pattern_item("file:gulpfile.js", ["build"])
        assert pattern.pattern_type == "file"
        assert pattern.pattern_value == "gulpfile.js"

        # Test complex patterns
        pattern = loader._parse_pattern_item("files('.js')", ["source"])
        assert pattern.pattern_type == "files"
        assert pattern.pattern_value == ".js"

        pattern = loader._parse_pattern_item(
            "endsWith('BidAdapter', file)", ["modules"]
        )
        assert pattern.pattern_type == "endsWith"
        assert pattern.pattern_value == "BidAdapter"


class TestPatternEvaluator:
    """Test pattern evaluation system."""

    def test_evaluate_file_new_addition(self):
        """Test evaluating new file additions with ++ pattern."""
        evaluator = PatternEvaluator()

        # Create ++ pattern
        pattern = YAMLPattern(
            path_components=["source", "core"], pattern_type="++", pattern_value=None
        )

        # Test new file addition
        matches = evaluator.evaluate_file(
            "source/core/newfile.js", [pattern], file_status="added"
        )

        assert len(matches) == 1
        pattern_match, match_info = matches[0]
        assert match_info["matches"] is True
        assert match_info["is_new_addition"] is True

        # Test modified file (should match but not as new addition)
        matches = evaluator.evaluate_file(
            "source/core/existing.js", [pattern], file_status="modified"
        )

        assert len(matches) == 1
        pattern_match, match_info = matches[0]
        assert match_info["matches"] is True
        assert match_info["is_new_addition"] is False

    def test_evaluate_specific_patterns(self):
        """Test evaluating specific pattern types."""
        evaluator = PatternEvaluator()

        # Test endsWith pattern
        pattern = YAMLPattern(
            path_components=["modules"],
            pattern_type="endsWith",
            pattern_value="BidAdapter",
        )

        matches = evaluator.evaluate_file(
            "modules/rubiconBidAdapter.js", [pattern], file_status="modified"
        )

        assert len(matches) == 1
        assert matches[0][1]["matches"] is True

        # Test files pattern
        pattern = YAMLPattern(
            path_components=["source", "libraries"],
            pattern_type="files",
            pattern_value=".js",
        )

        matches = evaluator.evaluate_file(
            "source/libraries/utils.js", [pattern], file_status="modified"
        )

        assert len(matches) == 1
        assert matches[0][1]["matches"] is True

        # Should not match non-.js file
        matches = evaluator.evaluate_file(
            "source/libraries/config.json", [pattern], file_status="modified"
        )

        assert len(matches) == 0

    def test_determine_impact_level(self):
        """Test impact level determination."""
        evaluator = PatternEvaluator()

        # Build files should be high impact
        build_pattern = YAMLPattern(["build"], "++", None)
        matches = [(build_pattern, {"matches": True})]

        impact = evaluator.determine_impact_level(
            "build/webpack.config.js", matches, "modified"
        )
        assert impact == "high"

        # Core source files should be high impact
        core_pattern = YAMLPattern(["source", "core"], "++", None)
        matches = [(core_pattern, {"matches": True})]

        impact = evaluator.determine_impact_level(
            "source/core/auction.js", matches, "modified"
        )
        assert impact == "high"

        # Test files should be low impact
        test_pattern = YAMLPattern(["testing"], "++", None)
        matches = [(test_pattern, {"matches": True})]

        impact = evaluator.determine_impact_level(
            "testing/unit/test.js", matches, "modified"
        )
        assert impact == "low"


class TestPRTaggerProcessor:
    """Test PR Tagging Processor."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock registry."""
        registry = Mock(spec=YAMLRegistryStructure)
        registry.repo_url = "https://github.com/prebid/Prebid.js"
        registry.structure = {
            "source": {
                "core": "++",
                "libraries": ["++"],
                "modules": ["modules/++ endsWith('BidAdapter', file)"],
            },
            "build": "++",
            "testing": {"unit": "test/spec/++"},
            "docs": "++",
        }
        registry.rules = []
        registry.definitions = []
        return registry

    @pytest.fixture
    def mock_repo_structure(self):
        """Create mock repository structure."""
        structure = Mock()
        structure.repo_type = "prebid-js"
        return structure

    @pytest.fixture
    def sample_component_data(self):
        """Sample component data for processing."""
        return {
            "repository": {
                "clone_url": "https://github.com/prebid/Prebid.js",
                "repo_type": "prebid-js",
            },
            "code_changes": {
                "files": [
                    {
                        "filename": "modules/rubiconBidAdapter.js",
                        "status": "modified",
                        "additions": 10,
                        "deletions": 5,
                    },
                    {
                        "filename": "source/core/auction.js",
                        "status": "added",
                        "additions": 100,
                        "deletions": 0,
                    },
                    {
                        "filename": "test/spec/modules/rubiconBidAdapter_spec.js",
                        "status": "modified",
                        "additions": 20,
                        "deletions": 10,
                    },
                    {
                        "filename": "docs/README.md",
                        "status": "modified",
                        "additions": 5,
                        "deletions": 2,
                    },
                ]
            },
        }

    @patch("src.pr_agents.pr_processing.processors.pr_tagger.RegistryLoader")
    @patch(
        "src.pr_agents.pr_processing.processors.pr_tagger.RepositoryStructureManager"
    )
    def test_process_pr(
        self,
        mock_repo_manager,
        mock_registry_loader,
        sample_component_data,
        mock_registry,
        mock_repo_structure,
    ):
        """Test processing a PR."""
        # Setup mocks
        mock_registry_loader.return_value.get_repo_registry.return_value = mock_registry
        mock_registry_loader.return_value.parse_structure_patterns.return_value = [
            YAMLPattern(["source", "modules"], "endsWith", "BidAdapter"),
            YAMLPattern(["source", "core"], "++", None),
            YAMLPattern(["testing", "unit"], "++", None),
            YAMLPattern(["docs"], "++", None),
        ]

        mock_repo_manager.return_value.get_repository.return_value = mock_repo_structure
        mock_repo_manager.return_value.categorize_file.side_effect = [
            {
                "categories": ["bid_adapter"],
                "module_name": "rubicon",
                "is_core": False,
                "is_test": False,
                "is_doc": False,
            },
            {
                "categories": [],
                "module_name": None,
                "is_core": True,
                "is_test": False,
                "is_doc": False,
            },
            {
                "categories": [],
                "module_name": None,
                "is_core": False,
                "is_test": True,
                "is_doc": False,
            },
            {
                "categories": [],
                "module_name": None,
                "is_core": False,
                "is_test": False,
                "is_doc": True,
            },
        ]

        # Create processor and process
        processor = PRTaggerProcessor()
        result = processor.process(sample_component_data)

        assert result.success is True
        data = result.data

        # Check file tags
        assert len(data["file_tags"]) == 4

        # Check module file
        module_tags = data["file_tags"]["modules/rubiconBidAdapter.js"]
        assert "bid_adapter" in module_tags["module_categories"]
        assert module_tags["module_name"] == "rubicon"

        # Check core file (added)
        core_tags = data["file_tags"]["source/core/auction.js"]
        assert core_tags["is_core"] is True
        assert core_tags["is_new_file"] is True

        # Check impact levels
        assert data["pr_impact_level"] in ["high", "medium", "low", "minimal"]

        # Check statistics
        assert data["stats"]["total_files"] == 4
        assert data["stats"]["core_files_count"] == 1
        assert data["stats"]["test_files_count"] == 1
        assert data["stats"]["doc_files_count"] == 1
        assert data["stats"]["new_files_count"] == 1
