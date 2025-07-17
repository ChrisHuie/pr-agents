# Creating Custom Processors

This guide walks you through creating custom processors to extend PR Agents' analysis capabilities. Processors analyze extracted PR data and generate insights without making external API calls.

## Overview

Processors in PR Agents:
- Work with pre-extracted data (no GitHub API calls)
- Implement pure analysis logic
- Return structured results using dataclasses
- Maintain strict component isolation
- Can be easily extended for custom analysis needs

## Quick Start

Here's a minimal custom processor:

```python
from dataclasses import dataclass, asdict
from typing import Any

from src.pr_agents.pr_processing.processors.base import BaseProcessor
from src.pr_agents.pr_processing.models import ProcessingResult


@dataclass
class SecurityAnalysis:
    """Results from security analysis."""
    has_secrets: bool
    sensitive_patterns: list[str]
    risk_level: str


class SecurityProcessor(BaseProcessor):
    """Analyzes code changes for security concerns."""
    
    @property
    def component_name(self) -> str:
        return "security"
    
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """Analyze code for security issues."""
        try:
            # Extract code changes data
            file_diffs = component_data.get("file_diffs", [])
            
            # Perform analysis
            analysis = self._analyze_security(file_diffs)
            
            # Return result
            return ProcessingResult(
                component="security",
                success=True,
                data=asdict(analysis)
            )
        except Exception as e:
            return ProcessingResult(
                component="security",
                success=False,
                errors=[str(e)]
            )
    
    def _analyze_security(self, file_diffs: list[dict]) -> SecurityAnalysis:
        """Perform security analysis on file diffs."""
        sensitive_patterns = []
        
        for diff in file_diffs:
            patch = diff.get("patch", "")
            if "password" in patch.lower():
                sensitive_patterns.append("password in code")
            if "api_key" in patch.lower():
                sensitive_patterns.append("api_key in code")
        
        return SecurityAnalysis(
            has_secrets=len(sensitive_patterns) > 0,
            sensitive_patterns=sensitive_patterns,
            risk_level="high" if sensitive_patterns else "low"
        )
```

## Step-by-Step Guide

### Step 1: Define Your Analysis Model

Create a dataclass to represent your analysis results:

```python
# In src/pr_agents/pr_processing/analysis_models.py

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ComplexityMetrics:
    """Code complexity metrics."""
    cyclomatic_complexity: int
    cognitive_complexity: int
    max_nesting_depth: int
    long_methods: list[str] = field(default_factory=list)


@dataclass
class ComplexityAnalysis:
    """Complete complexity analysis result."""
    average_complexity: float
    high_complexity_files: list[str]
    metrics: ComplexityMetrics
    recommendations: list[str] = field(default_factory=list)
```

### Step 2: Create the Processor Class

Implement your processor by extending `BaseProcessor`:

```python
# In src/pr_agents/pr_processing/processors/complexity_processor.py

from dataclasses import asdict
from typing import Any

from ..analysis_models import ComplexityAnalysis, ComplexityMetrics
from ..models import ProcessingResult
from .base import BaseProcessor


class ComplexityProcessor(BaseProcessor):
    """Analyzes code complexity in PR changes."""
    
    @property
    def component_name(self) -> str:
        """Return the component name for registration."""
        return "complexity"
    
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """
        Process extracted code data to analyze complexity.
        
        Args:
            component_data: Dictionary containing code changes data
            
        Returns:
            ProcessingResult with complexity analysis
        """
        try:
            # Extract relevant data
            file_diffs = component_data.get("file_diffs", [])
            
            # Perform analysis
            analysis = self._analyze_complexity(file_diffs)
            
            # Convert to dict and return
            return ProcessingResult(
                component=self.component_name,
                success=True,
                data=asdict(analysis)
            )
            
        except Exception as e:
            return ProcessingResult(
                component=self.component_name,
                success=False,
                errors=[str(e)]
            )
```

### Step 3: Implement Analysis Logic

Add your core analysis methods:

```python
def _analyze_complexity(self, file_diffs: list[dict]) -> ComplexityAnalysis:
    """Analyze complexity of changed files."""
    
    complexity_scores = []
    high_complexity_files = []
    
    for diff in file_diffs:
        if self._is_code_file(diff["filename"]):
            score = self._calculate_file_complexity(diff)
            complexity_scores.append(score)
            
            if score > 10:  # Threshold for high complexity
                high_complexity_files.append(diff["filename"])
    
    avg_complexity = (
        sum(complexity_scores) / len(complexity_scores) 
        if complexity_scores else 0
    )
    
    metrics = ComplexityMetrics(
        cyclomatic_complexity=int(avg_complexity),
        cognitive_complexity=int(avg_complexity * 1.2),
        max_nesting_depth=self._find_max_nesting(file_diffs),
        long_methods=self._find_long_methods(file_diffs)
    )
    
    return ComplexityAnalysis(
        average_complexity=avg_complexity,
        high_complexity_files=high_complexity_files,
        metrics=metrics,
        recommendations=self._generate_recommendations(avg_complexity)
    )

def _is_code_file(self, filename: str) -> bool:
    """Check if file is a code file."""
    code_extensions = {".py", ".js", ".ts", ".java", ".go", ".rs"}
    return any(filename.endswith(ext) for ext in code_extensions)

def _calculate_file_complexity(self, diff: dict) -> float:
    """Calculate complexity score for a file."""
    # Simplified complexity calculation
    additions = diff.get("additions", 0)
    deletions = diff.get("deletions", 0)
    
    # Basic heuristic: more changes = more complexity
    base_score = (additions + deletions) / 50
    
    # Check for complex patterns in patch
    patch = diff.get("patch", "")
    if patch:
        # Count control flow statements
        control_flow = sum(
            patch.count(keyword)
            for keyword in ["if ", "for ", "while ", "switch ", "case "]
        )
        base_score += control_flow * 0.5
    
    return min(base_score, 20)  # Cap at 20
```

### Step 4: Register the Processor

Add your processor to the component registry:

```python
# In src/pr_agents/pr_processing/coordinators/component_manager.py

from ..processors import (
    MetadataProcessor,
    CodeProcessor,
    RepoProcessor,
    ComplexityProcessor  # Add your processor
)

class ComponentManager:
    def __init__(self):
        self._processors = {
            "metadata": MetadataProcessor,
            "code_changes": CodeProcessor,
            "repository": RepoProcessor,
            "complexity": ComplexityProcessor  # Register it
        }
```

### Step 5: Add Constants

Define any constants your processor needs:

```python
# In src/pr_agents/pr_processing/constants.py

# Add to existing constants
COMPLEXITY_THRESHOLDS = {
    "low": 5,
    "medium": 10,
    "high": 15,
    "very_high": 20
}

COMPLEXITY_RECOMMENDATIONS = {
    "low": ["Code complexity is well-managed"],
    "medium": ["Consider refactoring complex methods"],
    "high": ["Break down complex logic into smaller functions"],
    "very_high": ["Urgent: Refactor to reduce complexity"]
}
```

## Advanced Processor Patterns

### Pattern 1: Multi-Component Processor

Process data from multiple components:

```python
class CrossComponentProcessor(BaseProcessor):
    """Analyzes relationships between components."""
    
    @property
    def component_name(self) -> str:
        return "cross_component"
    
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """Analyze relationships between metadata and code."""
        try:
            # Access multiple components
            metadata = component_data.get("metadata", {})
            code_changes = component_data.get("code_changes", {})
            
            # Analyze relationships
            title = metadata.get("title", "")
            changed_files = code_changes.get("changed_files", 0)
            
            consistency_score = self._check_consistency(title, changed_files)
            
            return ProcessingResult(
                component=self.component_name,
                success=True,
                data={
                    "consistency_score": consistency_score,
                    "title_mentions_scope": self._title_mentions_scope(title),
                    "change_size_matches_description": changed_files < 10
                }
            )
        except Exception as e:
            return ProcessingResult(
                component=self.component_name,
                success=False,
                errors=[str(e)]
            )
```

### Pattern 2: Configuration-Aware Processor

Use repository configuration in your processor:

```python
class ModuleAwareProcessor(BaseProcessor):
    """Processor that uses repository configuration."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
    
    @property
    def component_name(self) -> str:
        return "module_analysis"
    
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """Analyze modules based on repository configuration."""
        try:
            repo_name = component_data.get("repo_name")
            repo_config = self.config_manager.get_repo_config(repo_name)
            
            # Use configuration to identify modules
            module_patterns = repo_config.get("module_categories", {})
            
            # Analyze based on patterns
            results = self._analyze_modules(
                component_data.get("file_diffs", []),
                module_patterns
            )
            
            return ProcessingResult(
                component=self.component_name,
                success=True,
                data=results
            )
        except Exception as e:
            return ProcessingResult(
                component=self.component_name,
                success=False,
                errors=[str(e)]
            )
```

### Pattern 3: Statistical Analysis Processor

Perform statistical analysis on PR data:

```python
@dataclass
class StatisticalMetrics:
    """Statistical analysis metrics."""
    mean_file_changes: float
    median_file_changes: float
    std_dev: float
    outliers: list[str]
    percentiles: dict[int, float]


class StatisticalProcessor(BaseProcessor):
    """Performs statistical analysis on code changes."""
    
    @property
    def component_name(self) -> str:
        return "statistics"
    
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """Calculate statistical metrics for the PR."""
        try:
            file_diffs = component_data.get("file_diffs", [])
            
            # Calculate statistics
            changes_per_file = [
                diff.get("changes", 0) for diff in file_diffs
            ]
            
            if not changes_per_file:
                return ProcessingResult(
                    component=self.component_name,
                    success=True,
                    data={"no_changes": True}
                )
            
            import statistics
            
            metrics = StatisticalMetrics(
                mean_file_changes=statistics.mean(changes_per_file),
                median_file_changes=statistics.median(changes_per_file),
                std_dev=statistics.stdev(changes_per_file) if len(changes_per_file) > 1 else 0,
                outliers=self._find_outliers(file_diffs, changes_per_file),
                percentiles={
                    25: statistics.quantiles(changes_per_file, n=4)[0],
                    50: statistics.median(changes_per_file),
                    75: statistics.quantiles(changes_per_file, n=4)[2],
                    90: statistics.quantiles(changes_per_file, n=10)[8]
                }
            )
            
            return ProcessingResult(
                component=self.component_name,
                success=True,
                data=asdict(metrics)
            )
        except Exception as e:
            return ProcessingResult(
                component=self.component_name,
                success=False,
                errors=[str(e)]
            )
```

## Testing Your Processor

### Unit Tests

Create comprehensive unit tests:

```python
# In tests/unit/test_complexity_processor.py

import pytest
from src.pr_agents.pr_processing.processors.complexity_processor import ComplexityProcessor
from src.pr_agents.pr_processing.models import ProcessingResult


class TestComplexityProcessor:
    """Test suite for ComplexityProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return ComplexityProcessor()
    
    @pytest.fixture
    def sample_data(self):
        """Sample component data for testing."""
        return {
            "file_diffs": [
                {
                    "filename": "src/main.py",
                    "additions": 50,
                    "deletions": 10,
                    "patch": "if condition:\n    for item in items:\n        process(item)"
                },
                {
                    "filename": "src/utils.py",
                    "additions": 20,
                    "deletions": 5,
                    "patch": "def simple_function():\n    return True"
                }
            ]
        }
    
    def test_process_success(self, processor, sample_data):
        """Test successful processing."""
        result = processor.process(sample_data)
        
        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.component == "complexity"
        assert "average_complexity" in result.data
        assert "high_complexity_files" in result.data
    
    def test_empty_data(self, processor):
        """Test processing with empty data."""
        result = processor.process({"file_diffs": []})
        
        assert result.success is True
        assert result.data["average_complexity"] == 0
    
    def test_error_handling(self, processor):
        """Test error handling."""
        result = processor.process({"invalid": "data"})
        
        assert result.success is False
        assert len(result.errors) > 0
    
    @pytest.mark.parametrize("additions,deletions,expected_complexity", [
        (10, 5, "low"),
        (100, 50, "medium"),
        (500, 200, "high"),
    ])
    def test_complexity_levels(self, processor, additions, deletions, expected_complexity):
        """Test different complexity levels."""
        data = {
            "file_diffs": [{
                "filename": "test.py",
                "additions": additions,
                "deletions": deletions,
                "patch": "complex code" * additions
            }]
        }
        
        result = processor.process(data)
        complexity = result.data["average_complexity"]
        
        # Verify complexity matches expected level
        if expected_complexity == "low":
            assert complexity < 5
        elif expected_complexity == "medium":
            assert 5 <= complexity < 15
        else:  # high
            assert complexity >= 15
```

### Integration Tests

Test your processor in the full pipeline:

```python
# In tests/integration/test_processor_integration.py

def test_complexity_processor_integration(github_token):
    """Test ComplexityProcessor in full pipeline."""
    from src.pr_agents.pr_processing.coordinator import PRCoordinator
    
    # Initialize coordinator with custom processor
    coordinator = PRCoordinator(github_token)
    
    # Analyze a PR
    results = coordinator.analyze_pr(
        "https://github.com/test/repo/pull/123",
        components=["metadata", "code_changes", "complexity"]
    )
    
    # Verify complexity analysis is included
    assert "complexity" in results
    assert results["complexity"]["success"] is True
    assert "average_complexity" in results["complexity"]["data"]
```

## Best Practices

### 1. Keep Processors Pure

Processors should:
- Not make external API calls
- Not modify input data
- Not have side effects
- Be deterministic (same input → same output)

### 2. Handle Missing Data Gracefully

```python
def process(self, component_data: dict[str, Any]) -> ProcessingResult:
    """Process with proper null handling."""
    try:
        # Safe data extraction with defaults
        file_diffs = component_data.get("file_diffs", [])
        metadata = component_data.get("metadata", {})
        
        # Check for required data
        if not file_diffs:
            return ProcessingResult(
                component=self.component_name,
                success=True,
                data={"message": "No file changes to analyze"}
            )
        
        # Continue processing...
```

### 3. Use Meaningful Error Messages

```python
except KeyError as e:
    return ProcessingResult(
        component=self.component_name,
        success=False,
        errors=[f"Missing required field: {e}"]
    )
except ValueError as e:
    return ProcessingResult(
        component=self.component_name,
        success=False,
        errors=[f"Invalid data format: {e}"]
    )
```

### 4. Document Your Analysis Logic

```python
def _calculate_risk_score(self, changes: int, complexity: float) -> int:
    """
    Calculate risk score based on change size and complexity.
    
    Risk scoring algorithm:
    - Base score from change size (0-3 points)
    - Complexity multiplier (1.0-2.0x)
    - Final score capped at 10
    
    Args:
        changes: Total lines changed
        complexity: Calculated complexity score
        
    Returns:
        Risk score from 0-10
    """
    base_score = min(changes / 100, 3)
    multiplier = 1 + (complexity / 20)
    return int(min(base_score * multiplier, 10))
```

### 5. Make Processors Configurable

```python
class ConfigurableProcessor(BaseProcessor):
    """Processor with configurable thresholds."""
    
    def __init__(self, thresholds: dict[str, float] = None):
        self.thresholds = thresholds or {
            "low": 5,
            "medium": 10,
            "high": 20
        }
```

## Common Patterns

### Pattern: Scoring Systems

Many processors implement scoring systems:

```python
def _calculate_score(self, metrics: dict) -> tuple[int, str]:
    """Calculate score and level."""
    score = 0
    
    # Add points for positive factors
    if metrics["has_tests"]:
        score += 20
    if metrics["has_documentation"]:
        score += 15
    if metrics["follows_conventions"]:
        score += 25
    
    # Determine level
    if score >= 80:
        level = "excellent"
    elif score >= 60:
        level = "good"
    elif score >= 40:
        level = "fair"
    else:
        level = "poor"
    
    return score, level
```

### Pattern: Recommendation Generation

Generate actionable recommendations:

```python
def _generate_recommendations(self, analysis: dict) -> list[str]:
    """Generate recommendations based on analysis."""
    recommendations = []
    
    if analysis["complexity"] > 15:
        recommendations.append("Consider breaking down complex methods")
    
    if analysis["test_coverage"] < 0.8:
        recommendations.append("Add tests to improve coverage")
    
    if analysis["documentation_score"] < 50:
        recommendations.append("Add docstrings to public methods")
    
    return recommendations
```

## Troubleshooting

### Common Issues

1. **Processor not found**
   - Ensure processor is registered in ComponentManager
   - Check component_name matches registration

2. **Data not available**
   - Verify the required extractor has run
   - Check component_data keys match expected structure

3. **Serialization errors**
   - Ensure all data in results is JSON-serializable
   - Use `asdict()` for dataclasses

### Debug Tips

```python
# Enable debug logging
import logging
logger = logging.getLogger(__name__)

def process(self, component_data: dict[str, Any]) -> ProcessingResult:
    logger.debug(f"Processing with data keys: {component_data.keys()}")
    # ... rest of processing
```

## Next Steps

- Review [Testing Guide](./testing.md) for comprehensive testing strategies
- Explore [Error Handling](./error-handling.md) patterns
- Learn about [Performance Optimization](./performance-optimization.md)
- Check existing processors in `src/pr_agents/pr_processing/processors/` for examples