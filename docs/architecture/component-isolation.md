# Component Isolation Architecture

## Overview

Component isolation is a fundamental design principle in PR Agents. Each component operates independently, preventing "context bleeding" and ensuring clean, maintainable code.

## Isolation Principles

### 1. No Shared State
Components never share mutable state:
```python
# BAD: Shared state
class SharedAnalyzer:
    results = {}  # Shared across instances
    
# GOOD: Isolated state
class IsolatedAnalyzer:
    def __init__(self):
        self.results = {}  # Instance-specific
```

### 2. Clear Boundaries
Each component has well-defined inputs and outputs:
```python
class MetadataExtractor(BaseExtractor):
    def extract(self, pr_data: Any) -> dict[str, Any]:
        # Input: PR data from GitHub
        # Output: Metadata dictionary
        # No side effects or external dependencies
```

### 3. Immutable Data Transfer
Data passed between components is immutable:
```python
@dataclass(frozen=True)
class ProcessingResult:
    component: str
    success: bool
    data: dict[str, Any]
    # All fields are read-only
```

## Component Types

### Extractors
Extract data from external sources (GitHub API):
- **Single Responsibility**: Each extracts one type of data
- **No Cross-Dependencies**: Don't call other extractors
- **Pure Functions**: Same input always produces same output

### Processors  
Analyze pre-extracted data:
- **Input Only**: Work only with provided data
- **No External Calls**: Never fetch additional data
- **Deterministic**: Results depend only on input

### Models
Define data structures:
- **Pydantic Models**: For external API data
- **Dataclasses**: For internal processing
- **No Business Logic**: Pure data containers

## Isolation Patterns

### 1. Dependency Injection
```python
class PRCoordinator:
    def __init__(self, extractors: dict[str, BaseExtractor]):
        # Extractors are injected, not created internally
        self.extractors = extractors or self._get_default_extractors()
```

### 2. Interface Segregation
```python
# Each component type has its own interface
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, pr_data: Any) -> dict[str, Any]:
        pass

class BaseProcessor(ABC):
    @abstractmethod
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        pass
```

### 3. Component Registry
```python
# Components are registered, not hard-coded
AVAILABLE_EXTRACTORS = {
    "metadata": MetadataExtractor,
    "code_changes": CodeChangesExtractor,
    "repository_info": RepositoryExtractor,
    "reviews": ReviewsExtractor,
}
```

## Benefits of Isolation

### 1. Independent Testing
Each component can be tested in isolation:
```python
def test_metadata_extractor():
    # Create mock PR data
    mock_pr = create_mock_pr()
    
    # Test only the metadata extractor
    extractor = MetadataExtractor()
    result = extractor.extract(mock_pr)
    
    # Verify results without dependencies
    assert result["title"] == "Expected Title"
```

### 2. Parallel Processing
Components can run concurrently:
```python
async def extract_all_components(pr_data, components):
    tasks = []
    for component in components:
        extractor = get_extractor(component)
        tasks.append(extractor.extract_async(pr_data))
    
    results = await asyncio.gather(*tasks)
    return combine_results(results)
```

### 3. Selective Processing
Process only needed components:
```python
# Extract only metadata and code changes
results = coordinator.process_pr(
    pr_url,
    components=["metadata", "code_changes"]
)
# Repository and review data not extracted
```

### 4. Easy Extension
Add new components without modifying existing ones:
```python
# New component added without changing others
class SecurityExtractor(BaseExtractor):
    def extract(self, pr_data: Any) -> dict[str, Any]:
        # Extract security-related information
        return {"vulnerabilities": [], "security_score": 0.95}

# Register the new component
AVAILABLE_EXTRACTORS["security"] = SecurityExtractor
```

## Cross-Component Communication

When components need to share information:

### 1. Through Coordinator
```python
class PRCoordinator:
    def process_pr(self, pr_url: str):
        # Extract all data first
        extracted_data = self.extract_all(pr_url)
        
        # Pass relevant data to processors
        metadata_results = self.processors["metadata"].process(
            extracted_data["metadata"]
        )
        
        # Cross-component validation gets pre-processed results
        accuracy_results = self.processors["accuracy"].process({
            "metadata_results": metadata_results,
            "code_results": code_results
        })
```

### 2. Explicit Data Passing
```python
# Validator receives pre-processed results
class AccuracyValidator(BaseProcessor):
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        # Receives results from other processors
        metadata_results = component_data.get("metadata_results")
        code_results = component_data.get("code_results")
        
        # Performs cross-component validation
        accuracy_score = self._calculate_accuracy(
            metadata_results, 
            code_results
        )
```

## Anti-Patterns to Avoid

### 1. Direct Component Communication
```python
# BAD: Components calling each other
class BadProcessor:
    def process(self, data):
        # Don't do this!
        other_processor = CodeProcessor()
        other_results = other_processor.process(data)
```

### 2. Shared Configuration
```python
# BAD: Global configuration
GLOBAL_CONFIG = {"threshold": 0.8}

# GOOD: Injected configuration
class GoodProcessor:
    def __init__(self, config: dict):
        self.config = config
```

### 3. Stateful Processing
```python
# BAD: Maintaining state between calls
class StatefulProcessor:
    def __init__(self):
        self.previous_results = []
    
    def process(self, data):
        # Results depend on previous calls
        self.previous_results.append(data)
```

## Best Practices

1. **Keep Components Small**: Single responsibility per component
2. **Use Interfaces**: Define clear contracts
3. **Inject Dependencies**: Don't create them internally  
4. **Return Immutable Results**: Prevent modification
5. **Document Boundaries**: Clear input/output specifications
6. **Test in Isolation**: Mock all dependencies
7. **Avoid Side Effects**: Pure functions where possible