# Output System Architecture

## Overview

The output system provides a flexible, extensible framework for exporting PR analysis results in multiple formats. It follows the project's principles of modularity and clean interfaces.

## System Components

### OutputManager

The central orchestrator for all output operations.

**Location**: `src/pr_agents/output/manager.py`

**Responsibilities**:
- Format detection and inference
- Formatter selection and initialization
- File path management
- Error handling

**Key Features**:
- Automatic file extension handling
- Format aliases (e.g., "md" → "markdown")
- Extensible formatter registry

### Base Output Formatter

Abstract base class defining the formatter interface.

**Location**: `src/pr_agents/output/base.py`

**Interface**:
```python
class BaseOutputFormatter(ABC):
    @abstractmethod
    def format(self, data: dict[str, Any]) -> str:
        """Format data into output string."""
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        """Return appropriate file extension."""
        pass
    
    def save_to_file(self, data: dict[str, Any], file_path: Path) -> Path:
        """Save formatted data to file."""
        pass
```

## Formatter Implementations

### MarkdownFormatter

Generates rich markdown output with structured sections.

**Location**: `src/pr_agents/output/markdown.py`

**Features**:
- Structured sections with headers
- Code block formatting for diffs
- Tables for metrics and statistics
- Linked PR references
- Quality indicators with emoji

**Output Structure**:
```markdown
# PR Analysis Report

## PR Information
- **URL**: [#123](https://github.com/owner/repo/pull/123)
- **Repository**: owner/repo

## Metadata Analysis
### Title Quality
- Score: 85/100 (Excellent)
- Length: Optimal
...
```

### JSONFormatter

Provides clean JSON output with data sanitization.

**Location**: `src/pr_agents/output/json_formatter.py`

**Features**:
- Handles non-serializable objects
- Datetime formatting
- Clean null handling
- Pretty printing with indentation

**Data Cleaning**:
- Converts datetime objects to ISO format
- Handles Pydantic models
- Removes non-serializable objects
- Preserves structure

### TextFormatter

Simple plain text output for basic reporting.

**Location**: `src/pr_agents/output/text.py`

**Features**:
- Clean, readable format
- Section separators
- Minimal formatting
- Suitable for logs or emails

**Output Structure**:
```
PR Analysis Report
==================

PR Information:
- URL: https://github.com/owner/repo/pull/123
- Repository: owner/repo

------------------

Metadata Analysis:
...
```

## Usage Patterns

### Basic Usage

```python
from pr_agents.output import OutputManager

output_manager = OutputManager()

# Format data as markdown
markdown_content = output_manager.format(analysis_results, "markdown")

# Save to file with automatic extension
saved_path = output_manager.save(
    analysis_results,
    "pr_analysis",  # .md extension added automatically
    "markdown"
)
```

### Integration with Coordinators

```python
# Analyze and save in one operation
results, output_path = coordinator.analyze_pr_and_save(
    pr_url="https://github.com/owner/repo/pull/123",
    output_path="analysis_report",
    output_format="json"
)
```

### Multiple Format Export

```python
# Export in multiple formats
formats = ["markdown", "json", "text"]
for format in formats:
    path = output_manager.save(
        results,
        f"report_{format}",
        format
    )
    print(f"Saved {format} to: {path}")
```

## Data Flow

```
Analysis Results (dict)
        ↓
OutputManager.save()
        ↓
Format Detection/Validation
        ↓
Formatter Selection
        ↓
Data Formatting (formatter.format())
        ↓
File Writing (formatter.save_to_file())
        ↓
Return Path
```

## Extensibility

### Adding a New Formatter

1. Create a new formatter class inheriting from `BaseOutputFormatter`
2. Implement required methods
3. Register in OutputManager
4. Add tests

Example:
```python
from pr_agents.output.base import BaseOutputFormatter

class XMLFormatter(BaseOutputFormatter):
    def format(self, data: dict[str, Any]) -> str:
        # Convert to XML
        return xml_content
    
    def get_file_extension(self) -> str:
        return ".xml"
```

### Registering the Formatter

```python
# In OutputManager.__init__
self.formatters["xml"] = XMLFormatter()
```

## Error Handling

The system handles various error cases:

1. **Invalid Format**: Clear error message with available formats
2. **Serialization Errors**: Graceful handling of non-serializable data
3. **File System Errors**: Proper exception handling with context
4. **Empty Data**: Generates minimal valid output

## Best Practices

### For Formatter Implementation

1. **Handle Empty Data**: Always produce valid output
2. **Type Safety**: Handle various data types gracefully
3. **Consistent Structure**: Follow established patterns
4. **Error Messages**: Provide helpful error context

### For Data Preparation

1. **Use ResultFormatter**: Prepare data before output
2. **Clean Data**: Remove internal fields not meant for output
3. **Structure Consistently**: Follow expected data structure

## Performance Considerations

1. **Lazy Formatting**: Format only when needed
2. **Streaming**: Large outputs could use streaming (future)
3. **Memory Efficiency**: Avoid holding large strings in memory
4. **File I/O**: Use efficient file writing methods

## Testing

Each formatter should be tested for:

1. **Valid Data**: Normal operation
2. **Empty Data**: Edge case handling
3. **Invalid Data**: Error scenarios
4. **Large Data**: Performance testing
5. **Special Characters**: Encoding issues

Example test:
```python
def test_markdown_formatter_empty_data():
    formatter = MarkdownFormatter()
    result = formatter.format({})
    assert "# PR Analysis Report" in result
    assert len(result) > 0
```

## Future Enhancements

1. **Template Support**: User-defined templates
2. **Streaming Output**: For large data sets
3. **Compression**: Optional output compression
4. **Cloud Export**: Direct export to S3/GCS
5. **Format Conversion**: Convert between formats
6. **Custom Sections**: User-defined sections