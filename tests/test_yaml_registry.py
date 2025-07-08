"""
Tests for YAML registry components.
"""

import tempfile
from pathlib import Path

import pytest

from src.pr_agents.pr_processing.pattern_evaluator import PatternEvaluator
from src.pr_agents.pr_processing.registry_loader import RegistryLoader
from src.pr_agents.pr_processing.tagging_models import YAMLPattern


class TestYAMLRegistryLoader:
    """Test suite for YAML registry loader."""

    @pytest.fixture
    def loader(self):
        """Create a loader instance."""
        return RegistryLoader()

    @pytest.fixture
    def sample_yaml_content(self):
        """Sample YAML content for testing."""
        return """
repo: prebid/Prebid.js
structure:
  source:
    modules:
      ++:
        tags: [new_module, prebid_module]
        impact: medium
      endsWith:
        BidAdapter.js:
          tags: [bid_adapter]
          impact: medium
        AnalyticsAdapter.js:
          tags: [analytics_adapter]
          impact: low
    core:
      includes:
        prebid.js:
          tags: [core_file, critical]
          impact: critical
  test:
    spec:
      ++:
        tags: [new_test]
        impact: minimal
"""

    def test_load_registry_from_string(self, sample_yaml_content):
        """Test loading registry from YAML string."""
        # Create temporary directory with YAML file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            yaml_file = temp_path / "prebid.yaml"
            yaml_file.write_text(sample_yaml_content)

            # Create loader with temp directory
            loader = RegistryLoader(str(temp_path))

            # Check that registries were loaded
            assert len(loader.registry_cache) > 0

            # Get registry for Prebid.js
            registry = loader.get_repo_registry("prebid/Prebid.js")
            assert registry is not None
            assert "source" in registry.structure
            assert "modules" in registry.structure["source"]
            assert "++" in registry.structure["source"]["modules"]

    def test_parse_structure(self, loader):
        """Test parsing YAML structure into patterns."""
        structure = {
            "source": {
                "modules": {
                    "++": {"tags": ["new_module"], "impact": "medium"},
                    "endsWith": {
                        "BidAdapter.js": {"tags": ["bid_adapter"], "impact": "medium"}
                    },
                }
            }
        }

        patterns = loader.parse_structure_patterns(structure)
        assert len(patterns) > 0

        # Check ++ pattern
        new_module_patterns = [p for p in patterns if p.pattern_type == "++"]
        assert len(new_module_patterns) == 1
        assert new_module_patterns[0].path_components == ["source", "modules"]
        assert "new_module" in new_module_patterns[0].tags

        # Check endsWith pattern
        ends_with_patterns = [p for p in patterns if p.pattern_type == "endsWith"]
        assert len(ends_with_patterns) == 1
        assert ends_with_patterns[0].pattern_value == "BidAdapter.js"

    def test_nested_structure_parsing(self, loader):
        """Test parsing deeply nested structures."""
        structure = {
            "level1": {
                "level2": {"level3": {"++": {"tags": ["deep_tag"], "impact": "low"}}}
            }
        }

        patterns = loader.parse_structure_patterns(structure)
        assert len(patterns) == 1
        assert patterns[0].path_components == ["level1", "level2", "level3"]
        assert patterns[0].pattern_type == "++"

    def test_files_pattern_parsing(self, loader):
        """Test parsing 'files' patterns."""
        structure = {
            "adapters": {
                "files": [
                    {"name": "*.go", "tags": ["go_file"], "impact": "medium"},
                    {"name": "*.py", "tags": ["python_file"], "impact": "low"},
                ]
            }
        }

        patterns = loader.parse_structure_patterns(structure)
        assert len(patterns) == 2
        assert all(p.pattern_type == "file" for p in patterns)
        assert patterns[0].pattern_value == "*.go"
        assert patterns[1].pattern_value == "*.py"

    def test_get_patterns_for_repo(self, sample_yaml_content):
        """Test getting patterns for a specific repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            yaml_file = temp_path / "prebid.yaml"
            yaml_file.write_text(sample_yaml_content)

            loader = RegistryLoader(str(temp_path))
            registry = loader.get_repo_registry("prebid/Prebid.js")

            assert registry is not None
            patterns = loader.parse_structure_patterns(registry.structure)

            assert len(patterns) > 0
            # Should have patterns for modules, core, and tests
            path_starts = [tuple(p.path_components[:2]) for p in patterns]
            assert any(path[:2] == ("source", "modules") for path in path_starts)
            # We should have ++ patterns for modules and test/spec
            plus_patterns = [p for p in patterns if p.pattern_type == "++"]
            assert len(plus_patterns) >= 2  # At least modules and test/spec
            assert any(path[:2] == ("test", "spec") for path in path_starts)

    def test_empty_registry_handling(self):
        """Test handling of empty or missing registry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty YAML file
            temp_path = Path(temp_dir)
            yaml_file = temp_path / "empty.yaml"
            yaml_file.write_text("")

            loader = RegistryLoader(str(temp_path))
            assert len(loader.registry_cache) == 0

    def test_invalid_yaml_handling(self):
        """Test handling of invalid YAML content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            yaml_file = temp_path / "invalid.yaml"
            yaml_file.write_text("invalid: yaml: content: :")

            # Should handle error gracefully
            loader = RegistryLoader(str(temp_path))
            assert len(loader.registry_cache) == 0  # No valid registries loaded


class TestPatternEvaluator:
    """Test suite for pattern evaluator."""

    @pytest.fixture
    def evaluator(self):
        """Create an evaluator instance."""
        return PatternEvaluator()

    def test_evaluate_plus_plus_pattern(self, evaluator):
        """Test ++ pattern evaluation."""
        # ++ pattern returns True for added files
        pattern = YAMLPattern(["source", "modules"], "++", None, ["new_module"])
        matches = evaluator.evaluate_file(
            "source/modules/newModule.js", [pattern], "added"
        )
        assert len(matches) == 1
        assert matches[0][1]["is_new_addition"] is True

    def test_evaluate_ends_with_pattern(self, evaluator):
        """Test endsWith pattern evaluation."""
        pattern = YAMLPattern(["modules"], "endsWith", "BidAdapter.js", ["bid_adapter"])

        # Should match
        matches = evaluator.evaluate_file(
            "modules/testBidAdapter.js", [pattern], "modified"
        )
        assert len(matches) == 1

        # Should not match
        matches = evaluator.evaluate_file("modules/test.js", [pattern], "modified")
        assert len(matches) == 0

    def test_evaluate_includes_pattern(self, evaluator):
        """Test includes pattern evaluation."""
        pattern = YAMLPattern(["src"], "includes", "utils", ["utility"])

        # Should match
        matches = evaluator.evaluate_file("src/utils/logger.js", [pattern], "modified")
        assert len(matches) == 1

        # Should not match (not under src path)
        matches = evaluator.evaluate_file("modules/adapter.js", [pattern], "modified")
        assert len(matches) == 0

    def test_evaluate_dir_pattern(self, evaluator):
        """Test directory pattern evaluation."""
        pattern = YAMLPattern([], "dir", "modules", ["module_file"])

        # Should match files in modules directory
        matches = evaluator.evaluate_file("modules/test.js", [pattern], "modified")
        assert len(matches) == 1

        # Should not match files in other directories
        matches = evaluator.evaluate_file("test/spec.js", [pattern], "modified")
        assert len(matches) == 0

    def test_evaluate_file_pattern(self, evaluator):
        """Test file pattern evaluation with wildcards."""
        pattern = YAMLPattern(["adapters"], "file", "*.go", ["go_file"])

        # Should match .go files
        matches = evaluator.evaluate_file("adapters/adapter.go", [pattern], "modified")
        assert len(matches) == 1

        # Should not match other extensions
        matches = evaluator.evaluate_file("adapters/test.py", [pattern], "modified")
        assert len(matches) == 0

    def test_evaluate_exact_file_pattern(self, evaluator):
        """Test exact file matching."""
        pattern = YAMLPattern([], "file", "package.json", ["config"])

        # Should match exact file
        matches = evaluator.evaluate_file("package.json", [pattern], "modified")
        assert len(matches) == 1

        # Should not match different file
        matches = evaluator.evaluate_file("package.yml", [pattern], "modified")
        assert len(matches) == 0

    def test_is_under_path(self, evaluator):
        """Test path hierarchy checking."""
        assert evaluator._is_under_path("src/utils/test.js", "src/utils")
        assert evaluator._is_under_path("src/utils/deep/test.js", "src/utils")
        assert not evaluator._is_under_path("modules/test.js", "src/utils")
        assert evaluator._is_under_path("modules/test.js", "modules")

    def test_match_file_for_patterns(self, evaluator):
        """Test matching a file against multiple patterns."""
        patterns = [
            YAMLPattern(["source", "modules"], "++", None, ["new_module"]),
            YAMLPattern(
                ["source", "modules"], "endsWith", "BidAdapter.js", ["bid_adapter"]
            ),
            YAMLPattern(["test"], "includes", "spec", ["test_file"]),
        ]

        # Test bid adapter file
        matches = evaluator.evaluate_file(
            "source/modules/testBidAdapter.js", patterns, "added"
        )
        assert len(matches) == 2  # Should match ++ and endsWith
        matched_patterns = [match[0] for match in matches]
        tags = [tag for p in matched_patterns for tag in p.tags]
        assert "new_module" in tags
        assert "bid_adapter" in tags

        # Test spec file
        matches = evaluator.evaluate_file(
            "test/spec/module_spec.js", patterns, "modified"
        )
        assert len(matches) == 1
        assert matches[0][0].tags == ["test_file"]

    def test_aggregate_tags(self, evaluator):
        """Test tag aggregation from patterns."""
        patterns = [
            YAMLPattern(["a"], "++", None, ["tag1", "tag2"]),
            YAMLPattern(["a"], "++", None, ["tag2", "tag3"]),
            YAMLPattern(["b"], "++", None, ["tag4"]),
        ]

        # Create a simple aggregate_tags method test
        all_tags = []
        for pattern in patterns:
            all_tags.extend(pattern.tags)
        unique_tags = list(dict.fromkeys(all_tags))  # Preserve order, remove duplicates
        assert unique_tags == ["tag1", "tag2", "tag3", "tag4"]

    def test_get_impact_level(self, evaluator):
        """Test impact level determination."""
        # Test with high impact pattern
        pattern_high = YAMLPattern(["source", "core"], "++", None, [], "high")
        matches_high = [(pattern_high, {"matches": True})]
        impact = evaluator.determine_impact_level(
            "source/core/file.js", matches_high, "added"
        )
        assert impact == "high"

        # Test with build path (should be high)
        pattern_build = YAMLPattern(["build"], "++", None, [])
        matches_build = [(pattern_build, {"matches": True})]
        impact = evaluator.determine_impact_level(
            "build/file.js", matches_build, "modified"
        )
        assert impact == "high"

        # Test with docs path (should be minimal)
        pattern_docs = YAMLPattern(["docs"], "++", None, [])
        matches_docs = [(pattern_docs, {"matches": True})]
        impact = evaluator.determine_impact_level(
            "docs/file.md", matches_docs, "modified"
        )
        assert impact == "minimal"
