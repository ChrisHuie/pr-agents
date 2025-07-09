# System Architecture Overview

## Design Philosophy

PR Agents is built on principles of modularity, type safety, and component isolation. The system analyzes GitHub Pull Requests by breaking them down into independent components that can be processed separately or together.

## High-Level Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   GitHub API    │────▶│  Extractors  │────▶│ Pydantic Models │
└─────────────────┘     └──────────────┘     └─────────────────┘
                                                      │
                                                      ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Analysis Results│◀────│  Processors  │◀────│   Dataclasses   │
└─────────────────┘     └──────────────┘     └─────────────────┘
```

## Core Components

### 1. Extractors
Extract specific data from GitHub PRs via PyGithub API:
- **MetadataExtractor**: PR title, description, labels, author
- **CodeChangesExtractor**: Files, diffs, additions/deletions
- **RepositoryExtractor**: Repo info, languages, structure
- **ReviewsExtractor**: Comments, approvals, review status

### 2. Models
Type-safe data structures using Pydantic and dataclasses:
- **Pydantic Models**: For external API data validation
- **Dataclasses**: For internal processing results
- **Immutable Design**: Results cannot be modified after creation

### 3. Processors
Analyze extracted data to provide insights:
- **MetadataProcessor**: Title and description quality scoring (separate 1-100 scales)
- **CodeProcessor**: Risk assessment, pattern detection
- **RepoProcessor**: Health scoring, structure analysis
- **AccuracyValidator**: Cross-component validation

### 4. Coordinator
Orchestrates the extraction and processing pipeline:
- Manages component selection
- Handles data flow between stages
- Ensures isolation boundaries

## Key Design Patterns

### Dependency Injection
Components receive dependencies rather than creating them:
```python
class PRCoordinator:
    def __init__(self, 
                 github_token: str,
                 extractors: dict[str, BaseExtractor] | None = None,
                 processors: dict[str, BaseProcessor] | None = None):
        # Dependencies are injected, not hard-coded
```

### Interface-Based Design
All components implement base interfaces:
```python
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, pr_data: Any) -> dict[str, Any]:
        pass

class BaseProcessor(ABC):
    @abstractmethod
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        pass
```

### Immutable Results
Processing results are immutable dataclasses:
```python
@dataclass(frozen=True)
class MetadataAnalysis:
    quality_score: float
    title_analysis: TitleAnalysis
    # Cannot be modified after creation
```

## Data Flow

1. **Request**: User requests PR analysis with specific components
2. **Extraction**: Selected extractors fetch data from GitHub
3. **Validation**: Pydantic models validate external data
4. **Transformation**: Data converted to internal dataclasses
5. **Processing**: Processors analyze the data
6. **Results**: Immutable analysis results returned

## Component Isolation

Each component is completely isolated:
- No shared state between components
- No direct dependencies between extractors
- Processors only receive pre-extracted data
- Results are immutable and independent

This isolation enables:
- **Selective Processing**: Analyze only needed components
- **Parallel Execution**: Components can run concurrently
- **Easy Testing**: Mock individual components
- **Extensibility**: Add new components without affecting others

## Configuration System

Repository-specific behaviors are configured through:
- **JSON Configuration Files**: Define patterns and rules
- **Inheritance**: Share common patterns across repos
- **Version Management**: Handle evolving repositories
- **Validation**: Schema-based configuration validation

## Error Handling

The system uses structured error handling:
- **Extraction Errors**: Logged but don't stop processing
- **Validation Errors**: Pydantic provides detailed messages
- **Processing Errors**: Each component handles its own errors
- **Result Status**: Success/failure tracked per component

## Performance Considerations

- **Lazy Loading**: Components loaded only when needed
- **Caching**: Configuration and patterns cached
- **Selective Extraction**: Only fetch required data
- **Efficient Processing**: Algorithms optimized for large PRs

## Security

- **Token Management**: GitHub tokens never logged
- **Data Sanitization**: Sensitive data removed from logs
- **Input Validation**: All external data validated
- **Secure Defaults**: Conservative security settings