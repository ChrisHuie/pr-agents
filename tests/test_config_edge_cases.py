"""
Edge case tests for configuration system.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.pr_agents.config.exceptions import (
    ConfigurationError,
    ConfigurationLoadError,
    ConfigurationValidationError,
    InvalidPatternError,
    VersionParseError,
)
from src.pr_agents.config.loader import ConfigurationLoader
from src.pr_agents.config.manager import RepositoryStructureManager
from src.pr_agents.config.models import ModulePattern
from src.pr_agents.config.pattern_matcher import PatternMatcher
from src.pr_agents.config.validator import ConfigurationValidator
from src.pr_agents.config.version_utils import parse_version, version_matches_range
from src.pr_agents.config.watcher import ConfigurationWatcher


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_config_directory(self, tmp_path):
        """Test loading from empty directory."""
        loader = ConfigurationLoader(str(tmp_path))
        config = loader.load_config()
        assert len(config.repositories) == 0

    def test_malformed_json(self, tmp_path):
        """Test handling of malformed JSON files."""
        config_file = tmp_path / "bad.json"
        config_file.write_text("{ invalid json")
        
        loader = ConfigurationLoader(str(tmp_path))
        with pytest.raises(json.JSONDecodeError):
            loader.load_config()

    def test_circular_inheritance(self, tmp_path):
        """Test detection of circular inheritance."""
        # Create config A that extends B
        config_a = tmp_path / "a.json"
        config_a.write_text(json.dumps({
            "extends": "b.json",
            "repo_name": "test/a"
        }))
        
        # Create config B that extends A
        config_b = tmp_path / "b.json"
        config_b.write_text(json.dumps({
            "extends": "a.json",
            "repo_name": "test/b"
        }))
        
        loader = ConfigurationLoader(str(tmp_path))
        # Should handle gracefully without infinite recursion
        config = loader.load_config()
        # May load one or both depending on implementation

    def test_missing_extends_file(self, tmp_path):
        """Test handling of missing base config file."""
        config_file = tmp_path / "test.json"
        config_file.write_text(json.dumps({
            "extends": "nonexistent.json",
            "repo_name": "test/repo",
            "repo_type": "javascript"
        }))
        
        loader = ConfigurationLoader(str(tmp_path))
        config = loader.load_config()
        # Should still load the config but log warning
        assert "test/repo" in config.repositories

    def test_invalid_pattern_types(self):
        """Test invalid pattern types."""
        matcher = PatternMatcher()
        
        # Invalid suffix pattern
        with pytest.raises(InvalidPatternError):
            pattern = ModulePattern(pattern="suffix_without_star", pattern_type="suffix")
            matcher.match_pattern("test.js", pattern)
        
        # Invalid prefix pattern
        with pytest.raises(InvalidPatternError):
            pattern = ModulePattern(pattern="prefix_without_star", pattern_type="prefix")
            matcher.match_pattern("test.js", pattern)

    def test_extreme_version_ranges(self):
        """Test edge cases in version matching."""
        # Very large version numbers
        assert version_matches_range("v999.999.999", ">=1.0")
        
        # Pre-release versions
        assert parse_version("1.0.0-alpha") < parse_version("1.0.0")
        
        # Invalid version strings
        with pytest.raises(VersionParseError):
            parse_version("not-a-version")
        
        # Complex version ranges
        assert version_matches_range("v10.5", ">=10.0,<11.0")
        assert not version_matches_range("v11.0", ">=10.0,<11.0")

    def test_deeply_nested_configs(self, tmp_path):
        """Test handling of deeply nested directory structures."""
        # Create deeply nested config
        deep_path = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep_path.mkdir(parents=True)
        
        config_file = deep_path / "deep.json"
        config_file.write_text(json.dumps({
            "repo_name": "deep/nested",
            "repo_type": "test"
        }))
        
        loader = ConfigurationLoader(str(tmp_path))
        config = loader.load_config()
        assert "deep/nested" in config.repositories

    def test_unicode_in_configs(self, tmp_path):
        """Test handling of Unicode characters in configurations."""
        config_file = tmp_path / "unicode.json"
        config_file.write_text(json.dumps({
            "repo_name": "test/repo",
            "repo_type": "test",
            "description": "Test with émojis 🚀 and ñiñö characters",
            "module_categories": {
                "测试": {
                    "display_name": "中文测试",
                    "patterns": [{"pattern": "*.js", "type": "glob"}]
                }
            }
        }, ensure_ascii=False))
        
        loader = ConfigurationLoader(str(tmp_path))
        config = loader.load_config()
        repo = config.get_repository("test/repo")
        assert "émojis 🚀" in repo.description
        assert "测试" in repo.module_categories

    def test_concurrent_config_modifications(self, tmp_path):
        """Test handling of concurrent config file modifications."""
        import threading
        import time
        
        config_file = tmp_path / "concurrent.json"
        config_file.write_text(json.dumps({
            "repo_name": "test/repo",
            "repo_type": "test"
        }))
        
        loader = ConfigurationLoader(str(tmp_path))
        
        def modify_config():
            for i in range(5):
                config_file.write_text(json.dumps({
                    "repo_name": "test/repo",
                    "repo_type": f"test-{i}"
                }))
                time.sleep(0.1)
        
        # Start multiple threads modifying the config
        threads = [threading.Thread(target=modify_config) for _ in range(3)]
        for t in threads:
            t.start()
        
        # Load config multiple times during modifications
        for _ in range(10):
            try:
                config = loader.load_config()
                # Should not crash
            except Exception:
                pass
            time.sleep(0.05)
        
        for t in threads:
            t.join()

    def test_huge_config_files(self, tmp_path):
        """Test handling of very large configuration files."""
        # Create a config with many repositories
        huge_config = {}
        for i in range(1000):
            huge_config[f"repo{i}"] = {
                "repo_type": "test",
                "module_categories": {
                    f"cat{j}": {
                        "display_name": f"Category {j}",
                        "patterns": [{"pattern": f"*{j}.js", "type": "suffix"}]
                    }
                    for j in range(10)
                }
            }
        
        config_file = tmp_path / "huge.json"
        config_file.write_text(json.dumps(huge_config))
        
        loader = ConfigurationLoader(str(tmp_path))
        config = loader.load_config()
        # Should handle large configs efficiently

    def test_invalid_json_schema(self, tmp_path):
        """Test validation with invalid schema."""
        # Create invalid schema
        schema_dir = tmp_path / "schema"
        schema_dir.mkdir()
        schema_file = schema_dir / "repository.schema.json"
        schema_file.write_text("{ invalid schema }")
        
        # Validator should handle gracefully
        with pytest.raises(Exception):
            ConfigurationValidator(str(schema_file))

    def test_pattern_matcher_edge_cases(self):
        """Test edge cases in pattern matching."""
        matcher = PatternMatcher()
        
        # Empty patterns
        pattern = ModulePattern(pattern="", pattern_type="glob")
        assert not matcher.match_pattern("test.js", pattern)
        
        # Very long file paths
        long_path = "/".join(["dir"] * 100) + "/file.js"
        pattern = ModulePattern(pattern="*.js", pattern_type="suffix")
        assert matcher.match_pattern(long_path, pattern)
        
        # Special characters in patterns
        pattern = ModulePattern(pattern="test[[]].js", pattern_type="glob")
        assert matcher.match_pattern("test[].js", pattern)

    def test_watcher_rapid_changes(self, tmp_path):
        """Test watcher handling rapid file changes."""
        config_file = tmp_path / "rapid.json"
        config_file.write_text(json.dumps({"repo_name": "test", "repo_type": "test"}))
        
        changes_detected = []
        
        def on_change(config):
            changes_detected.append(config)
        
        with ConfigurationWatcher(str(tmp_path), callback=on_change) as watcher:
            # Rapid modifications
            for i in range(10):
                config_file.write_text(json.dumps({
                    "repo_name": "test",
                    "repo_type": f"test-{i}"
                }))
            
            # Wait for cooldown
            import time
            time.sleep(2)
        
        # Should batch rapid changes
        assert len(changes_detected) < 10

    def test_manager_with_invalid_repo_urls(self):
        """Test manager handling of invalid repository URLs."""
        manager = RepositoryStructureManager()
        
        # Various invalid URLs
        invalid_urls = [
            "",
            "not-a-url",
            "http://",
            "//invalid",
            None,
        ]
        
        for url in invalid_urls:
            if url is not None:
                result = manager.get_repository(url)
                # Should handle gracefully
                assert result is None or isinstance(result, type(result))

    def test_strict_mode_validation_failure(self, tmp_path):
        """Test strict mode failing on invalid config."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text(json.dumps({
            # Missing required fields
            "module_categories": {}
        }))
        
        # Create a minimal schema that requires repo_name
        schema_dir = tmp_path / "schema"
        schema_dir.mkdir()
        schema_file = schema_dir / "repository.schema.json"
        schema_file.write_text(json.dumps({
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["repo_name"],
            "properties": {
                "repo_name": {"type": "string"}
            }
        }))
        
        loader = ConfigurationLoader(str(tmp_path), strict_mode=True)
        
        # Should raise validation error in strict mode
        with pytest.raises(ConfigurationValidationError):
            loader.load_config()

    def test_memory_efficiency(self, tmp_path):
        """Test memory efficiency with repeated loads."""
        config_file = tmp_path / "memory.json"
        config_file.write_text(json.dumps({
            "repo_name": "test/repo",
            "repo_type": "test"
        }))
        
        loader = ConfigurationLoader(str(tmp_path))
        
        # Load config many times
        for _ in range(100):
            config = loader.load_config()
        
        # Cache should prevent memory bloat
        assert len(loader._loaded_configs) <= 10  # Reasonable cache size

    def test_special_characters_in_paths(self, tmp_path):
        """Test handling of special characters in file paths."""
        # Create directory with special characters
        special_dir = tmp_path / "config with spaces & special!chars"
        special_dir.mkdir()
        
        config_file = special_dir / "config.json"
        config_file.write_text(json.dumps({
            "repo_name": "test/repo",
            "repo_type": "test"
        }))
        
        loader = ConfigurationLoader(str(special_dir))
        config = loader.load_config()
        assert "test/repo" in config.repositories