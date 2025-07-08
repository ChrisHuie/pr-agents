# Advanced Configuration Usage

## Builder Pattern

The configuration system provides a fluent builder API for creating configurations programmatically:

```python
from src.pr_agents.config.builder import repository, category, pattern
from src.pr_agents.config.models import DetectionStrategy, FetchStrategy

# Build a repository configuration
repo = (
    repository("myorg/myrepo")
    .of_type("custom-type")
    .with_description("My custom repository")
    .with_strategies(
        detection=DetectionStrategy.HYBRID,
        fetch=FetchStrategy.FILENAMES_ONLY
    )
    .add_module_category(
        category("custom_adapter")
        .display_name("Custom Adapters")
        .with_paths("src/adapters/")
        .with_pattern(
            pattern("*Adapter.js")
            .with_type("suffix")
            .with_name_extraction("remove_suffix:Adapter")
            .exclude("test/*", "mock/*")
        )
        .with_detection(DetectionStrategy.FILENAME_PATTERN)
    )
    .with_paths(
        core=["src/core/", "lib/"],
        test=["test/", "spec/"],
        exclude=["node_modules/", "build/"]
    )
    .add_relationship("extends", "base/config", "Inherits base configuration")
    .build()
)
```

## Pattern Matching

The enhanced pattern matcher provides more sophisticated matching capabilities:

```python
from src.pr_agents.config.pattern_matcher import PatternMatcher
from src.pr_agents.config.models import ModulePattern

matcher = PatternMatcher()

# Create patterns
patterns = [
    ModulePattern(
        pattern="*BidAdapter.js",
        pattern_type="suffix",
        name_extraction="remove_suffix:BidAdapter"
    ),
    ModulePattern(
        pattern=r"^modules/.*Adapter\.js$",
        pattern_type="regex",
        exclude_patterns=["test/*"]
    )
]

# Find best match
best_pattern, confidence = matcher.find_best_match(
    "modules/rubiconBidAdapter.js",
    patterns
)

# Extract name
if best_pattern:
    name = matcher.extract_name("modules/rubiconBidAdapter.js", best_pattern)
    print(f"Module name: {name}, Confidence: {confidence}")
```

## Version Management

Use proper semantic versioning with the packaging library:

```python
from src.pr_agents.config.version_utils import version_matches_range

# Check version compatibility
if version_matches_range("v10.5.2", ">=10.0,<11.0"):
    print("Version is compatible")

# Version-specific configuration
version_config = {
    "v9.0": {
        "module_categories": {
            "bid_adapter": {
                "detection_strategy": "filename_pattern"
            }
        }
    },
    "v10.0+": {
        "module_categories": {
            "bid_adapter": {
                "detection_strategy": "metadata_file",
                "metadata_field": "componentType"
            }
        }
    }
}
```

## Error Handling

The improved error handling provides better debugging:

```python
from src.pr_agents.config.manager import RepositoryStructureManager
from src.pr_agents.config.exceptions import (
    ConfigurationLoadError,
    ConfigurationNotFoundError,
    InvalidPatternError
)

try:
    manager = RepositoryStructureManager("config")
except ConfigurationLoadError as e:
    # Handle configuration loading errors
    logger.error(f"Failed to load configuration: {e}")
    # Fallback to default or exit
    
try:
    repo = manager.get_repository("unknown/repo")
    if not repo:
        raise ConfigurationNotFoundError("Repository not configured")
except ConfigurationNotFoundError as e:
    # Handle missing repository
    logger.warning(f"Repository not found: {e}")
```

## Configuration Sources

Support different configuration sources:

```python
from src.pr_agents.config.loader_interface import (
    FileConfigSource,
    DictConfigSource,
    ConfigCache
)

# File-based configuration
file_source = FileConfigSource(Path("config/repo.json"))

# In-memory configuration (useful for testing)
dict_source = DictConfigSource({
    "repo_name": "test/repo",
    "repo_type": "test",
    "module_categories": {}
})

# Caching for performance
cache = ConfigCache(max_size=50)
config = cache.get("myrepo") or load_and_cache("myrepo")
```

## Custom Validation

Add custom validation rules:

```python
from src.pr_agents.config.validator import ConfigurationValidator

class CustomValidator(ConfigurationValidator):
    def validate_custom_rules(self, config_data: dict) -> list[str]:
        """Add custom validation rules."""
        issues = []
        
        # Check for required module categories
        if "module_categories" in config_data:
            categories = config_data["module_categories"]
            if "bid_adapter" not in categories:
                issues.append("Missing required 'bid_adapter' category")
        
        # Check naming conventions
        repo_name = config_data.get("repo_name", "")
        if not repo_name.islower():
            issues.append("Repository name should be lowercase")
        
        return issues

# Use custom validator
validator = CustomValidator()
is_valid, errors = validator.validate_file(Path("config/repo.json"))
custom_issues = validator.validate_custom_rules(config_data)
```

## Performance Optimization

Tips for optimizing configuration loading:

```python
# 1. Use lazy loading for large configurations
class LazyConfigManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._configs = {}
    
    def get_repository(self, repo_name: str) -> RepositoryStructure:
        if repo_name not in self._configs:
            # Load only the specific repository config
            self._configs[repo_name] = self._load_single_repo(repo_name)
        return self._configs[repo_name]

# 2. Pre-compile patterns for repeated use
from functools import lru_cache

@lru_cache(maxsize=100)
def get_compiled_pattern(pattern: str, pattern_type: str):
    if pattern_type == "regex":
        return re.compile(pattern)
    return pattern

# 3. Use configuration watching for auto-reload
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigWatcher(FileSystemEventHandler):
    def __init__(self, manager: RepositoryStructureManager):
        self.manager = manager
    
    def on_modified(self, event):
        if event.src_path.endswith(".json"):
            logger.info(f"Reloading configuration: {event.src_path}")
            self.manager.reload()
```

## Integration with CI/CD

Validate configurations in your CI pipeline:

```yaml
# .github/workflows/validate-config.yml
name: Validate Configurations
on:
  pull_request:
    paths:
      - 'config/**/*.json'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: |
          pip install -e .
          python -m src.pr_agents.config.cli validate
```