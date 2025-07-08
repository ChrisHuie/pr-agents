# Repository Configuration System

## Overview

The PR Agents project uses a flexible, scalable configuration system to define repository-specific structures, module patterns, and analysis rules. The system supports inheritance, version-specific overrides, and multiple repository types.

## Configuration Structure

```
config/
├── repositories.json          # Master file listing all repo configs
├── schema/
│   └── repository.schema.json # JSON Schema for validation
└── repositories/
    ├── shared/
    │   └── prebid-base.json   # Base configuration for inheritance
    └── prebid/
        ├── prebid-js.json
        ├── prebid-server-go.json
        └── prebid-server-java.json
```

## Key Features

### 1. Multi-File Organization
Each repository has its own configuration file, making it easy to:
- Find and modify specific repo configs
- Add new repositories without affecting others
- Track changes in version control

### 2. Inheritance
Repositories can extend base configurations to avoid duplication:
```json
{
  "extends": "../shared/prebid-base.json",
  "repo_name": "prebid/Prebid.js",
  // Override or add specific configurations
}
```

### 3. Version-Specific Overrides
Handle repository evolution with version-specific configurations:
```json
{
  "version_overrides": {
    "v10.0+": {
      "module_categories": {
        "bid_adapter": {
          "detection_strategy": "metadata_file",
          "metadata_field": "componentType"
        }
      }
    }
  }
}
```

### 4. Module Pattern Detection
Define how different module types are identified:
```json
{
  "module_categories": {
    "bid_adapter": {
      "display_name": "Bid Adapters",
      "paths": ["modules/"],
      "patterns": [
        {
          "pattern": "*BidAdapter.js",
          "type": "suffix",
          "name_extraction": "remove_suffix:BidAdapter"
        }
      ]
    }
  }
}
```

## Configuration Schema

### Repository Configuration
- `repo_name` (required): Full repository name (e.g., "prebid/Prebid.js")
- `repo_type` (required): Repository type identifier
- `description`: Human-readable description
- `extends`: Path to base configuration file
- `detection_strategy`: How to detect modules (filename_pattern, directory_based, metadata_file, hybrid)
- `fetch_strategy`: How to fetch content (full_content, filenames_only, directory_names)

### Module Categories
Each module category defines:
- `display_name`: Human-readable name
- `paths`: Directories where modules are located
- `patterns`: Pattern rules for identifying modules
- `detection_strategy`: Override detection method for this category
- `metadata_field/value`: For metadata-based detection

### Pattern Types
- `suffix`: Match files ending with pattern (e.g., "*BidAdapter.js")
- `prefix`: Match files starting with pattern
- `glob`: Standard glob pattern matching
- `directory`: Match directory names
- `regex`: Regular expression matching

## Usage Examples

### Loading Configuration
```python
from src.pr_agents.config.loader import ConfigurationLoader

# Load all configurations
loader = ConfigurationLoader("config")
config = loader.load_config()

# Get specific repository
repo = config.get_repository("prebid/Prebid.js")
```

### Categorizing Files
```python
from src.pr_agents.config.manager import RepositoryStructureManager

manager = RepositoryStructureManager()
result = manager.categorize_file(
    "https://github.com/prebid/Prebid.js",
    "modules/rubiconBidAdapter.js",
    version="v10.0"
)
# Returns: {"categories": ["bid_adapter"], "module_type": "Bid Adapters", ...}
```

## Complete Example

Here's a complete repository configuration example:

```json
{
  "$schema": "../../schema/repository.schema.json",
  "repo_name": "prebid/Prebid.js",
  "repo_type": "prebid-js",
  "description": "Prebid.js - Header Bidding Library",
  "extends": "../shared/prebid-base.json",
  "detection_strategy": "hybrid",
  "fetch_strategy": "filenames_only",
  
  "module_categories": {
    "bid_adapter": {
      "display_name": "Bid Adapters",
      "paths": ["modules/"],
      "patterns": [
        {
          "pattern": "*BidAdapter.js",
          "type": "suffix",
          "name_extraction": "remove_suffix:BidAdapter"
        }
      ],
      "detection_strategy": "filename_pattern"
    },
    "analytics_adapter": {
      "display_name": "Analytics Adapters",
      "paths": ["modules/"],
      "patterns": [
        {
          "pattern": "*AnalyticsAdapter.js",
          "type": "suffix",
          "name_extraction": "remove_suffix:AnalyticsAdapter"
        }
      ]
    }
  },
  
  "version_overrides": {
    "v10.0+": {
      "module_categories": {
        "bid_adapter": {
          "paths": ["modules/", "metadata/modules/"],
          "detection_strategy": "metadata_file",
          "metadata_field": "componentType",
          "metadata_value": "bidder"
        }
      }
    }
  },
  
  "paths": {
    "core": ["src/", "libraries/"],
    "test": ["test/spec/modules/", "test/spec/unit/"],
    "docs": ["docs/"],
    "exclude": ["node_modules/", "build/", "dist/"]
  },
  
  "relationships": [
    {
      "type": "documents",
      "target": "prebid/prebid.github.io",
      "description": "Documentation repository"
    }
  ]
}
```

## Adding New Repositories

1. Create a new JSON file in the appropriate subdirectory:
   ```bash
   config/repositories/your-org/your-repo.json
   ```

2. Define the repository configuration following the schema

3. Add the file path to `config/repositories.json`:
   ```json
   {
     "repositories": [
       "./repositories/your-org/your-repo.json"
     ]
   }
   ```

4. Validate your configuration:
   ```bash
   python -m src.pr_agents.config.cli validate --file config/repositories/your-org/your-repo.json
   ```

## CLI Tools

### Validate Configurations
```bash
# Validate all configs
python -m src.pr_agents.config.cli validate

# Validate specific file
python -m src.pr_agents.config.cli validate --file config/repositories/prebid/prebid-js.json
```

### Migrate from Single File
```bash
# Convert old single-file format to multi-file
python -m src.pr_agents.config.cli migrate config/old_config.json config/new/
```

### Test Loading
```bash
# Test configuration loading
python -m src.pr_agents.config.cli test --path config
```

## Best Practices

1. **Use Inheritance**: Extract common patterns into base configurations
2. **Version Carefully**: Use version overrides only when behavior changes significantly
3. **Validate Changes**: Always run validation after modifying configurations
4. **Document Patterns**: Include comments explaining complex patterns
5. **Test Thoroughly**: Add test cases for new module categories

## Migration from Legacy Format

If you have an existing single-file configuration:

1. Run the migration tool:
   ```bash
   python -m src.pr_agents.config.cli migrate config/repository_structures.json config/
   ```

2. Review and adjust generated files
3. Update your code to use the new loader
4. Remove the old configuration file after verification