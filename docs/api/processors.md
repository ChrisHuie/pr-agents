# Processors API Reference

## Overview

Processors analyze pre-extracted PR data to provide insights and assessments. They work with data already fetched by extractors, maintaining strict isolation and never making external API calls.

## Base Processor

All processors inherit from the base class:

```python
from abc import ABC, abstractmethod
from typing import Any
from src.pr_agents.pr_processing.models import ProcessingResult

class BaseProcessor(ABC):
    """Base class for all PR data processors."""
    
    @abstractmethod
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """
        Process extracted component data.
        
        Args:
            component_data: Pre-extracted data from extractors
            
        Returns:
            ProcessingResult with analysis
        """
        pass
    
    @property
    @abstractmethod
    def component_name(self) -> str:
        """Name of the component this processor handles."""
        pass
```

## Available Processors

### MetadataProcessor

Analyzes PR metadata quality and extracts insights.

```python
from src.pr_agents.pr_processing.processors.metadata_processor import MetadataProcessor

processor = MetadataProcessor()
result = processor.process(metadata_data)
```

**Analysis Includes:**
- **Quality Score** (0-100): Overall metadata quality
- **Title Analysis**: 
  - Length appropriateness
  - Conventional commit format
  - Clarity score
- **Description Analysis**:
  - Completeness
  - Section detection (Summary, Testing, etc.)
  - Markdown quality
- **Label Categorization**:
  - Type (bug, feature, etc.)
  - Priority level
  - Component tags

**Example Output:**
```python
ProcessingResult(
    component="metadata",
    success=True,
    data={
        "quality_score": 85,
        "quality_rating": "excellent",
        "title_analysis": {
            "length": 45,
            "has_prefix": True,
            "prefix": "feat",
            "is_clear": True,
            "suggestions": []
        },
        "description_analysis": {
            "length": 350,
            "has_sections": True,
            "sections_found": ["summary", "testing"],
            "completeness_score": 0.9
        },
        "label_analysis": {
            "categories": {
                "type": ["enhancement"],
                "component": ["bid-adapter"],
                "priority": ["medium"]
            },
            "missing_labels": ["size"]
        }
    }
)
```

### CodeProcessor

Analyzes code changes for risk and patterns.

```python
from src.pr_agents.pr_processing.processors.code_processor import CodeProcessor

processor = CodeProcessor()
result = processor.process(code_data)
```

**Analysis Includes:**
- **Risk Assessment**: Overall change risk level
- **Size Analysis**: Change size categorization
- **File Analysis**: Per-file risk and patterns
- **Pattern Detection**: Common code patterns
- **Critical Files**: Identification of important files

**Risk Scoring Algorithm:**
- 0 points: Minimal risk
- 1-2 points: Low risk
- 3-4 points: Medium risk
- 5+ points: High risk

Points assigned for:
- Large changes (>100, >500, >1000 lines)
- Many files changed (>10, >20)
- Critical file modifications
- Configuration changes
- Test coverage

**Example Output:**
```python
ProcessingResult(
    component="code_changes",
    success=True,
    data={
        "risk_assessment": {
            "risk_score": 3,
            "risk_level": "medium",
            "factors": [
                "large_change_size",
                "multiple_files",
                "critical_file_modified"
            ]
        },
        "size_analysis": {
            "total_changes": 450,
            "size_category": "large",
            "files_changed": 12
        },
        "file_analysis": [
            {
                "path": "src/core/config.js",
                "risk": "high",
                "is_critical": True,
                "patterns": ["configuration_change"]
            }
        ],
        "pattern_analysis": {
            "has_tests": True,
            "has_documentation": False,
            "new_dependencies": []
        }
    }
)
```

### RepoProcessor

Analyzes repository health and structure.

```python
from src.pr_agents.pr_processing.processors.repo_processor import RepoProcessor

processor = RepoProcessor()
result = processor.process(repo_data)
```

**Analysis Includes:**
- **Health Score** (0-70): Repository health assessment
- **Language Analysis**: Primary and secondary languages
- **Structure Assessment**: Repository organization
- **Maintenance Status**: Activity and update frequency

**Health Scoring:**
- Has description: 10 points
- Has topics (≥3): 10 points  
- Multi-language: 15 points
- Public visibility: 10 points
- Active maintenance: 20 points
- Standard practices: 5 points

**Example Output:**
```python
ProcessingResult(
    component="repository_info",
    success=True,
    data={
        "health_score": 55,
        "health_rating": "excellent",
        "language_analysis": {
            "primary_language": "JavaScript",
            "language_diversity": 0.15,
            "languages": ["JavaScript", "HTML", "CSS"]
        },
        "structure_assessment": {
            "has_standard_files": True,
            "branch_pattern": "standard",
            "is_monorepo": False
        },
        "maintenance_status": {
            "is_active": True,
            "days_since_update": 2,
            "update_frequency": "high"
        }
    }
)
```

### AccuracyValidator

Cross-component validator that checks if PR metadata accurately reflects code changes.

```python
from src.pr_agents.pr_processing.processors.accuracy_validator import AccuracyValidator

validator = AccuracyValidator()
result = validator.process({
    "metadata_results": metadata_results,
    "code_results": code_results
})
```

**Validation Includes:**
- **Title Accuracy**: Does title match changes?
- **Description Coverage**: Are all changes documented?
- **Completeness**: Any missing information?
- **Specificity**: Technical accuracy

**Example Output:**
```python
ProcessingResult(
    component="accuracy_validation", 
    success=True,
    data={
        "total_score": 0.85,
        "component_scores": {
            "title_accuracy": 0.9,
            "description_accuracy": 0.8,
            "completeness": 0.85,
            "specificity": 0.85
        },
        "recommendations": [
            "Mention the config file changes in description",
            "Add more technical details about the implementation"
        ],
        "unmentioned_files": ["config/settings.json"],
        "accuracy_rating": "good"
    }
)
```

## Using Processors

### Basic Usage

```python
# Process extracted data
from src.pr_agents.pr_processing.processors import MetadataProcessor

# Assume we have extracted data
extracted_metadata = {
    "title": "feat: Add new bid adapter for Example",
    "body": "## Summary\nThis PR adds a new bid adapter...",
    "labels": ["enhancement", "bid-adapter"]
}

# Create and run processor
processor = MetadataProcessor()
result = processor.process(extracted_metadata)

if result.success:
    print(f"Quality Score: {result.data['quality_score']}")
    print(f"Title Analysis: {result.data['title_analysis']}")
```

### Using with Coordinator

```python
from src.pr_agents.pr_processing.coordinator import PRCoordinator

coordinator = PRCoordinator(github_token="your-token")

# Extract and process
results = coordinator.process_pr(
    "https://github.com/owner/repo/pull/123",
    components=["metadata", "code_changes"]
)

# Access processed results
metadata_results = results["metadata"]["processed"]
code_results = results["code_changes"]["processed"]
```

### Chaining Processors

```python
# First process individual components
metadata_proc = MetadataProcessor()
code_proc = CodeProcessor()

metadata_results = metadata_proc.process(metadata_data)
code_results = code_proc.process(code_data)

# Then run cross-component validation
validator = AccuracyValidator()
accuracy_results = validator.process({
    "metadata_results": metadata_results.data,
    "code_results": code_results.data
})
```

## Creating Custom Processors

```python
from src.pr_agents.pr_processing.processors.base import BaseProcessor
from src.pr_agents.pr_processing.models import ProcessingResult

class CustomProcessor(BaseProcessor):
    """Custom analysis processor."""
    
    @property
    def component_name(self) -> str:
        return "custom_analysis"
    
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """Perform custom analysis."""
        try:
            # Your analysis logic
            analysis = self._analyze_data(component_data)
            
            return ProcessingResult(
                component=self.component_name,
                success=True,
                data=analysis,
                errors=[]
            )
        except Exception as e:
            return ProcessingResult(
                component=self.component_name,
                success=False,
                data={},
                errors=[str(e)]
            )
    
    def _analyze_data(self, data: dict) -> dict:
        """Custom analysis implementation."""
        return {
            "custom_metric": 0.95,
            "insights": ["insight1", "insight2"]
        }
```

## Best Practices

1. **Pure Functions**: Processors should be stateless
2. **No External Calls**: Work only with provided data
3. **Error Handling**: Always return ProcessingResult
4. **Consistent Scoring**: Use documented scales
5. **Clear Recommendations**: Provide actionable feedback
6. **Immutable Results**: Don't modify input data

## Advanced Features

### Configurable Thresholds

```python
class ConfigurableProcessor(BaseProcessor):
    def __init__(self, config: dict | None = None):
        self.config = config or self._default_config()
        
    def _default_config(self) -> dict:
        return {
            "quality_threshold": 0.7,
            "risk_weights": {
                "size": 0.3,
                "complexity": 0.5,
                "critical_files": 0.2
            }
        }
```

### Batch Processing

```python
def process_multiple_prs(pr_list: list[dict]) -> list[ProcessingResult]:
    """Process multiple PRs efficiently."""
    processor = MetadataProcessor()
    results = []
    
    for pr_data in pr_list:
        result = processor.process(pr_data)
        results.append(result)
        
    return results
```

### Result Aggregation

```python
def aggregate_results(results: dict[str, ProcessingResult]) -> dict:
    """Aggregate results from multiple processors."""
    return {
        "overall_score": calculate_weighted_score(results),
        "risk_level": determine_overall_risk(results),
        "recommendations": collect_all_recommendations(results),
        "summary": generate_summary(results)
    }
```