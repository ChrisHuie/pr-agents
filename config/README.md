# PR Agents Configuration System

This directory contains the configuration files that define how different repositories are structured and how their components should be identified and categorized.

## Quick Start

The configuration system uses a multi-file JSON structure with inheritance support for better maintainability and scalability.

### Directory Structure

```
config/
├── README.md                 # This file
├── repositories.json         # Master list of all repository configs
├── schema/                   # JSON schemas for validation
│   └── repository.schema.json
└── repositories/            # Individual repository configurations
    ├── prebid/              # Prebid-specific repositories
    │   ├── prebid-js.json
    │   ├── prebid-server.json
    │   └── ...
    └── shared/              # Shared base configurations
        └── prebid-base.json # Common patterns for Prebid repos
```

## Key Concepts

### 1. Repository Configuration
Each repository has its own JSON file that defines:
- Module categories (bid adapters, analytics, etc.)
- File patterns for identifying modules
- Version-specific overrides
- Core/test/docs path definitions

### 2. Configuration Inheritance
Configurations can extend base configurations using the `extends` field:
```json
{
  "extends": "../shared/prebid-base.json",
  "repo_name": "prebid/Prebid.js",
  "repo_type": "javascript"
}
```

### 3. Pattern Matching
Multiple pattern types are supported:
- `suffix`: Match file suffixes (e.g., `*BidAdapter.js`)
- `prefix`: Match file prefixes (e.g., `test_*`)
- `glob`: Standard glob patterns (e.g., `modules/*.js`)
- `regex`: Regular expressions for complex matching
- `directory`: Match files in specific directories

### 4. Version-Specific Configurations
Handle repository evolution across versions:
```json
{
  "version_overrides": {
    "v10.0+": {
      "module_categories": {
        "bid_adapter": {
          "detection_strategy": "metadata_file"
        }
      }
    }
  }
}
```

## CLI Tools

The configuration system includes comprehensive CLI tools:

```bash
# Validate all configurations
python -m src.pr_agents.config.cli validate

# Test loading configurations
python -m src.pr_agents.config.cli test --strict

# Check how a file is categorized
python -m src.pr_agents.config.cli check prebid/Prebid.js modules/appnexusBidAdapter.js

# Watch for configuration changes (hot-reload)
python -m src.pr_agents.config.cli watch

# List all configured repositories
python -m src.pr_agents.config.cli list

# Show detailed info about a repository
python -m src.pr_agents.config.cli show prebid/Prebid.js --verbose

# Migrate from old single-file format
python -m src.pr_agents.config.cli migrate old_config.json config/
```

## Hot-Reloading

The configuration system supports automatic reloading when files change:

```python
from src.pr_agents.config.manager import RepositoryStructureManager

# Enable hot-reloading
manager = RepositoryStructureManager(enable_hot_reload=True)

# Configuration will automatically reload when files change
```

## Validation

All configuration files are validated against JSON schemas:
- Schema validation runs automatically during loading
- Use `--strict` mode in CI/CD to fail on validation errors
- Run `validate` command to check files before committing

## Best Practices

1. **Use Inheritance**: Define common patterns in base configs
2. **Be Specific**: Use the most specific pattern type (suffix/prefix vs glob)
3. **Document Changes**: Add descriptions to explain complex patterns
4. **Test First**: Use the CLI to test file categorization before deploying
5. **Version Carefully**: Use version overrides for breaking changes

## Adding a New Repository

1. Create a new JSON file in `config/repositories/[category]/`
2. Define the repository structure:
   ```json
   {
     "$schema": "../../schema/repository.schema.json",
     "extends": "../shared/prebid-base.json",
     "repo_name": "org/repo",
     "repo_type": "javascript",
     "description": "Repository description",
     "module_categories": {
       "custom_module": {
         "display_name": "Custom Modules",
         "paths": ["src/custom/"],
         "patterns": [
           {
             "pattern": "*Module.js",
             "type": "suffix",
             "name_extraction": "remove_suffix:Module"
           }
         ]
       }
     }
   }
   ```
3. Add the file path to `repositories.json`
4. Validate: `python -m src.pr_agents.config.cli validate`
5. Test: `python -m src.pr_agents.config.cli test`

## Troubleshooting

### Configuration Not Loading
- Check JSON syntax with `validate` command
- Ensure file paths in `extends` are correct
- Look for error messages in logs

### Pattern Not Matching
- Use `check` command to test file categorization
- Try different pattern types (suffix vs glob)
- Check for typos in patterns

### Performance Issues
- Enable caching in production
- Use specific pattern types over regex when possible
- Consider breaking large configs into smaller files

## Further Documentation

For more detailed information, see:
- [Architecture Overview](../docs/architecture/config-system.md)
- [API Reference](../docs/api/configuration.md)
- [Migration Guide](../docs/guides/config-migration.md)