# Adding Repositories Guide

This guide walks you through adding a new repository to the PR Agents configuration system, enabling repository-specific module detection and analysis.

## Overview

PR Agents uses a JSON-based configuration system to define repository-specific patterns for module detection, file organization, and version-specific behaviors. Each repository configuration can:

- Define module detection patterns
- Specify file organization paths
- Handle version-specific behaviors
- Inherit from shared base configurations
- Support multiple detection strategies

## Quick Start

### Step 1: Create Repository Configuration File

Create a new JSON file in the appropriate subdirectory under `config/repositories/`:

```bash
# For a new organization
mkdir -p config/repositories/myorg
touch config/repositories/myorg/myrepo.json

# For an existing organization
touch config/repositories/existing-org/newrepo.json
```

### Step 2: Define Basic Configuration

Create a minimal configuration file:

```json
{
  "$schema": "../../schema/repository.schema.json",
  "repo_name": "myorg/myrepo",
  "repo_type": "custom",
  "description": "My Repository Description",
  "module_categories": {
    "component": {
      "paths": ["src/components/"],
      "patterns": [
        {
          "pattern": "*.component.js",
          "type": "suffix",
          "name_extraction": "remove_suffix:.component"
        }
      ]
    }
  },
  "paths": {
    "core": ["src/"],
    "test": ["tests/"],
    "docs": ["docs/"],
    "exclude": ["node_modules/", "dist/"]
  }
}
```

### Step 3: Register the Configuration

Add your configuration file to the master `config/repositories.json`:

```json
{
  "$schema": "./schema/repository.schema.json",
  "description": "Master configuration that imports all repository configurations",
  "repositories": [
    "./repositories/existing/configs.json",
    "./repositories/myorg/myrepo.json"  // Add your new config
  ]
}
```

### Step 4: Validate Configuration

Run the validation command to ensure your configuration is correct:

```bash
python -m src.pr_agents.config.cli validate
```

## Configuration Structure

### Required Fields

#### `repo_name`
The full GitHub repository name in `owner/repo` format.

```json
"repo_name": "facebook/react"
```

#### `repo_type`
A unique identifier for the repository type. Used for grouping similar repositories.

```json
"repo_type": "react-library"
```

#### `description`
A brief description of the repository.

```json
"description": "React - A JavaScript library for building user interfaces"
```

### Module Categories

Define different types of modules in your repository:

```json
"module_categories": {
  "component": {
    "paths": ["src/components/"],
    "patterns": [
      {
        "pattern": "*.component.js",
        "type": "suffix",
        "name_extraction": "remove_suffix:.component"
      }
    ]
  },
  "service": {
    "paths": ["src/services/"],
    "patterns": [
      {
        "pattern": "*Service.js",
        "type": "suffix",
        "name_extraction": "remove_suffix:Service"
      }
    ]
  }
}
```

#### Pattern Types

1. **suffix**: Matches files ending with a specific pattern
   ```json
   {
     "pattern": "*Controller.js",
     "type": "suffix",
     "name_extraction": "remove_suffix:Controller"
   }
   ```

2. **prefix**: Matches files starting with a specific pattern
   ```json
   {
     "pattern": "Base*",
     "type": "prefix",
     "name_extraction": "remove_prefix:Base"
   }
   ```

3. **glob**: General glob pattern matching
   ```json
   {
     "pattern": "*.spec.js",
     "type": "glob"
   }
   ```

4. **regex**: Regular expression matching
   ```json
   {
     "pattern": "^[A-Z][a-zA-Z]+\\.js$",
     "type": "regex"
   }
   ```

### Path Configuration

Define key paths in your repository:

```json
"paths": {
  "core": ["src/", "lib/"],           // Core source code
  "test": ["test/", "__tests__/"],    // Test files
  "docs": ["docs/", "documentation/"], // Documentation
  "exclude": ["node_modules/", "dist/", "coverage/"]  // Paths to ignore
}
```

## Advanced Features

### Inheritance

Extend from shared base configurations to avoid repetition:

```json
{
  "$schema": "../../schema/repository.schema.json",
  "extends": "../shared/javascript-base.json",
  "repo_name": "myorg/myrepo",
  "repo_type": "javascript-lib",
  "module_categories": {
    // Your specific categories (merged with base)
  }
}
```

### Version-Specific Overrides

Handle different behaviors across versions:

```json
"version_overrides": {
  "v2.0+": {
    "module_categories": {
      "component": {
        "paths": ["src/components/", "src/new-components/"],
        "patterns": [
          {
            "pattern": "*.component.tsx",  // Now using TypeScript
            "type": "suffix",
            "name_extraction": "remove_suffix:.component"
          }
        ]
      }
    }
  }
}
```

### Detection Strategies

Choose how modules are detected:

```json
"detection_strategy": "hybrid",  // Options: pattern, metadata_file, hybrid
"fetch_strategy": "filenames_only",  // Options: full_content, filenames_only
```

#### Detection Strategy Options

1. **pattern**: Use file naming patterns only
2. **metadata_file**: Look for metadata JSON files
3. **hybrid**: Combine both approaches

### Metadata File Detection

For projects with metadata files describing modules:

```json
"module_categories": {
  "plugin": {
    "paths": ["plugins/", "metadata/plugins/"],
    "detection_strategy": "metadata_file",
    "metadata_field": "type",
    "metadata_value": "plugin",
    "patterns": [
      {
        "pattern": "*.json",
        "type": "glob"
      }
    ]
  }
}
```

## Real-World Examples

### Example 1: React-Style Project

```json
{
  "$schema": "../../schema/repository.schema.json",
  "repo_name": "mycompany/react-app",
  "repo_type": "react-application",
  "description": "React application with components and hooks",
  "module_categories": {
    "component": {
      "paths": ["src/components/"],
      "patterns": [
        {
          "pattern": "*.jsx",
          "type": "glob"
        },
        {
          "pattern": "*.tsx",
          "type": "glob"
        }
      ]
    },
    "hook": {
      "paths": ["src/hooks/"],
      "patterns": [
        {
          "pattern": "use*.js",
          "type": "prefix",
          "name_extraction": "none"
        }
      ]
    },
    "page": {
      "paths": ["src/pages/"],
      "patterns": [
        {
          "pattern": "*Page.jsx",
          "type": "suffix",
          "name_extraction": "remove_suffix:Page"
        }
      ]
    }
  },
  "paths": {
    "core": ["src/"],
    "test": ["src/__tests__/", "src/**/*.test.js"],
    "docs": ["docs/"],
    "config": ["config/", ".config/"],
    "exclude": ["node_modules/", "build/", "dist/"]
  }
}
```

### Example 2: Python Package

```json
{
  "$schema": "../../schema/repository.schema.json",
  "repo_name": "myorg/python-lib",
  "repo_type": "python-package",
  "description": "Python package with modules and plugins",
  "module_categories": {
    "module": {
      "paths": ["src/mylib/"],
      "patterns": [
        {
          "pattern": "*.py",
          "type": "glob"
        }
      ]
    },
    "plugin": {
      "paths": ["src/mylib/plugins/"],
      "patterns": [
        {
          "pattern": "*_plugin.py",
          "type": "suffix",
          "name_extraction": "remove_suffix:_plugin"
        }
      ]
    },
    "model": {
      "paths": ["src/mylib/models/"],
      "patterns": [
        {
          "pattern": "*.py",
          "type": "glob"
        }
      ]
    }
  },
  "paths": {
    "core": ["src/"],
    "test": ["tests/", "test/"],
    "docs": ["docs/", "documentation/"],
    "exclude": ["__pycache__/", "*.egg-info/", "dist/"]
  }
}
```

### Example 3: Monorepo with Multiple Packages

```json
{
  "$schema": "../../schema/repository.schema.json",
  "repo_name": "myorg/monorepo",
  "repo_type": "monorepo",
  "description": "Monorepo with multiple packages",
  "module_categories": {
    "package": {
      "paths": ["packages/"],
      "patterns": [
        {
          "pattern": "*/package.json",
          "type": "glob",
          "name_extraction": "parent_directory"
        }
      ]
    },
    "shared_component": {
      "paths": ["packages/shared/src/components/"],
      "patterns": [
        {
          "pattern": "*.component.tsx",
          "type": "suffix",
          "name_extraction": "remove_suffix:.component"
        }
      ]
    },
    "service": {
      "paths": ["services/"],
      "patterns": [
        {
          "pattern": "*/src/index.js",
          "type": "glob",
          "name_extraction": "parent_directory:2"
        }
      ]
    }
  },
  "paths": {
    "core": ["packages/", "services/"],
    "test": ["**/test/", "**/__tests__/"],
    "docs": ["docs/"],
    "config": ["config/", ".config/"],
    "exclude": ["**/node_modules/", "**/dist/", "**/build/"]
  }
}
```

## Testing Your Configuration

### 1. Validate Schema

Ensure your configuration follows the schema:

```bash
python -m src.pr_agents.config.cli validate
```

### 2. Test Pattern Matching

Test if your patterns correctly identify modules:

```bash
python -m src.pr_agents.config.cli test-pattern "src/components/Button.component.js"
```

### 3. List Configured Repositories

Verify your repository appears in the list:

```bash
python -m src.pr_agents.config.cli list
```

### 4. Watch for Changes (Development)

During development, watch for configuration changes:

```bash
python -m src.pr_agents.config.cli watch
```

## Troubleshooting

### Common Issues

1. **Pattern Not Matching**
   - Check path separators (use forward slashes)
   - Verify the path exists in `paths` configuration
   - Test with the CLI pattern tester

2. **Validation Errors**
   - Ensure all required fields are present
   - Check JSON syntax (trailing commas, quotes)
   - Verify schema path is correct

3. **Inheritance Not Working**
   - Check the `extends` path is relative to the current file
   - Ensure the base configuration exists
   - Verify no circular dependencies

### Debug Tips

1. Enable debug logging:
   ```bash
   export LOG_LEVEL=DEBUG
   python -m src.pr_agents.config.cli validate
   ```

2. Check loaded configuration:
   ```python
   from src.pr_agents.config import ConfigManager
   
   config = ConfigManager()
   repo_config = config.get_repo_config("myorg/myrepo")
   print(repo_config)
   ```

## Best Practices

1. **Use Descriptive Names**: Choose clear `repo_type` values that describe the repository's purpose

2. **Leverage Inheritance**: Create shared base configurations for common patterns

3. **Document Special Cases**: Add comments in the `description` field for unusual patterns

4. **Test Thoroughly**: Always validate and test pattern matching after changes

5. **Version Carefully**: Use version overrides only when necessary to avoid complexity

6. **Keep Paths Organized**: Follow consistent path naming conventions

7. **Exclude Appropriately**: Always exclude build artifacts and dependencies

## Next Steps

- Learn about [Module Detection Patterns](../configuration/module-detection.md)
- Explore [Version Management](../configuration/version-management.md)
- Create [Custom Processors](./custom-processors.md) for your modules
- Set up [Testing](./testing.md) for your configuration