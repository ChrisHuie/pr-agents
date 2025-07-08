# PR Agents Documentation

Welcome to the PR Agents documentation. This project provides modular Python tools for analyzing GitHub Pull Requests with a focus on component isolation and type safety.

## Documentation Structure

### [Architecture](./architecture/)
- [System Overview](./architecture/overview.md) - High-level architecture and design principles
- [Component Isolation](./architecture/component-isolation.md) - How components maintain independence
- [Data Flow](./architecture/data-flow.md) - How data moves through the system

### [Configuration](./configuration/)
- [Repository Configuration](./configuration/repository-config.md) - Configure repository-specific patterns
- [Module Detection](./configuration/module-detection.md) - How modules are identified
- [Version Management](./configuration/version-management.md) - Handle version-specific behaviors

### [API Reference](./api/)
- [Extractors](./api/extractors.md) - Components that fetch data from GitHub
- [Processors](./api/processors.md) - Components that analyze extracted data
- [Models](./api/models.md) - Data structures and schemas

### [Guides](./guides/)
- [Quick Start](./guides/quickstart.md) - Get up and running quickly
- [Adding New Repositories](./guides/adding-repositories.md) - Configure new repositories
- [Creating Custom Processors](./guides/custom-processors.md) - Extend the analysis capabilities
- [Testing](./guides/testing.md) - Write and run tests

## Key Concepts

### Component Isolation
Each component operates independently with no shared state or dependencies between:
- **Metadata** - PR title, description, labels, author
- **Code Changes** - Files modified, additions/deletions, patches
- **Repository Info** - Languages, structure, configuration
- **Reviews** - Comments, approvals, review status

### Processing Pipeline
```
GitHub API → Extractors → Pydantic Models → Processors → Analysis Results
```

### Configuration System
- Multi-file configuration with inheritance
- Version-specific overrides
- Pattern-based module detection
- Repository-specific rules

## Getting Started

1. **Installation**: See the [Quick Start Guide](./guides/quickstart.md)
2. **Basic Usage**: Review the [API Reference](./api/)
3. **Configuration**: Set up repositories in [Configuration Guide](./configuration/repository-config.md)
4. **Development**: Create custom components with our [guides](./guides/)

## Project Links

- [GitHub Repository](https://github.com/ChrisHuie/pr-agents)
- [Issue Tracker](https://github.com/ChrisHuie/pr-agents/issues)
- [Contributing Guidelines](../CONTRIBUTING.md)