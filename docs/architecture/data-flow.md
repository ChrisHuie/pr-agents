# Data Flow Architecture

This document describes how data flows through the PR Agents system, from GitHub API to final output.

## Overview

PR Agents follows a strict unidirectional data flow pattern:

```
GitHub API → Fetchers → Coordinators → Extractors → Processors → Output Formatters → Files
```

Each stage transforms data while maintaining component isolation and preventing context bleeding between different PR aspects.

## Data Flow Stages

### 1. Data Retrieval (Fetchers)

**Purpose**: Retrieve raw PR data from GitHub API

**Flow**:
```
GitHub API Request
    ↓
Fetcher (e.g., ReleasePRFetcher)
    ↓
Raw GitHub PR Objects (PyGithub)
    ↓
List of PRs for Processing
```

**Key Points**:
- Fetchers handle API authentication and rate limiting
- Each fetcher specializes in different query patterns (release, date, label)
- Returns standardized PR objects regardless of fetcher type
- No data transformation occurs at this stage

### 2. Orchestration (Coordinators)

**Purpose**: Manage the analysis pipeline and component lifecycle

**Flow**:
```
PR List from Fetcher
    ↓
Coordinator Selection (Single/Batch)
    ↓
Component Manager Initialization
    ↓
Extraction & Processing Pipeline
    ↓
Aggregated Results
```

**Coordinator Types**:
- **PRCoordinator**: Main facade, delegates to sub-coordinators
- **SinglePRCoordinator**: Handles individual PR analysis
- **BatchCoordinator**: Manages multi-PR operations
- **ComponentManager**: Provides component registry and lifecycle

### 3. Data Extraction (Extractors)

**Purpose**: Transform GitHub API data into isolated components

**Flow**:
```
Raw PR Data (PyGithub objects)
    ↓
Component-Specific Extractor
    ↓
Pydantic Model Validation
    ↓
Isolated Component Data
```

**Extraction Process**:
1. Each extractor receives the full PR object
2. Extracts only relevant data for its component
3. Validates data using Pydantic models
4. Returns typed, validated component data
5. Errors are captured but don't stop the pipeline

**Component Isolation**:
- **MetadataExtractor** → `PRMetadata`
- **CodeChangesExtractor** → `CodeChanges`
- **RepositoryExtractor** → `RepositoryInfo`
- **ReviewsExtractor** → `ReviewData`

### 4. Data Processing (Processors)

**Purpose**: Analyze extracted data and generate insights

**Flow**:
```
Validated Component Data
    ↓
Component-Specific Processor
    ↓
Analysis & Scoring Algorithms
    ↓
Processing Results (Dataclasses)
```

**Processing Characteristics**:
- Processors work only with pre-extracted data
- No external API calls during processing
- Pure functions for analysis logic
- Results stored as immutable dataclasses
- Each processor is independent

**Analysis Types**:
- **MetadataProcessor**: Title/description quality scoring
- **CodeProcessor**: Risk assessment, pattern detection
- **RepoProcessor**: Health scoring, language analysis
- **AIProcessor**: LLM-based summarization (if enabled)

### 5. Output Formatting

**Purpose**: Transform processing results into desired output format

**Flow**:
```
Processing Results (Dict)
    ↓
Output Manager
    ↓
Format-Specific Formatter
    ↓
Formatted Output
    ↓
File System / Console
```

**Output Formats**:
- **Markdown**: Human-readable reports with sections
- **JSON**: Machine-readable, structured data
- **Text**: Plain text summaries

## Complete Data Flow Example

Here's a complete example of analyzing a single PR:

```python
# 1. User initiates analysis
coordinator.analyze_pr("https://github.com/owner/repo/pull/123")
    ↓
# 2. Fetcher retrieves PR data
pr_obj = github.get_repo("owner/repo").get_pull(123)
    ↓
# 3. Coordinator routes to SinglePRCoordinator
single_pr_coordinator.analyze(pr_obj)
    ↓
# 4. Extract components in parallel
extracted_data = {
    "metadata": MetadataExtractor().extract(pr_obj),
    "code_changes": CodeChangesExtractor().extract(pr_obj),
    "repository": RepositoryExtractor().extract(pr_obj),
    "reviews": ReviewsExtractor().extract(pr_obj)
}
    ↓
# 5. Process each component
processing_results = [
    MetadataProcessor().process(extracted_data),
    CodeProcessor().process(extracted_data),
    RepoProcessor().process(extracted_data)
]
    ↓
# 6. Build summary
summary = SummaryBuilder.build(processing_results)
    ↓
# 7. Format output
markdown_output = MarkdownFormatter().format(all_results)
    ↓
# 8. Save to file
output_manager.save(results, "output/analysis", "markdown")
```

## Data Models Throughout the Flow

### Stage 1: Raw GitHub Data
- PyGithub objects (PullRequest, Repository, etc.)
- Direct API responses

### Stage 2: Extracted Components
- Pydantic models for validation
- Typed, structured data
- Examples: `PRMetadata`, `CodeChanges`

### Stage 3: Processing Results
- Dataclasses for performance
- Immutable analysis results
- Examples: `MetadataAnalysisResult`, `RiskAssessment`

### Stage 4: Output Data
- Dictionary representations
- Cleaned and serializable
- Ready for formatting

## Error Handling in Data Flow

### Extraction Errors
```
Failed Extraction
    ↓
Return None for Component
    ↓
Log Error
    ↓
Continue with Other Components
```

### Processing Errors
```
Processing Exception
    ↓
Return ProcessingResult with success=False
    ↓
Include Error Details
    ↓
Continue Pipeline
```

### Output Errors
```
Formatting/Save Error
    ↓
Log Error with Context
    ↓
Return Partial Results
    ↓
Indicate Failure in Response
```

## Performance Considerations

### Parallel Extraction
- Multiple extractors can run concurrently
- No dependencies between extractors
- Reduces total extraction time

### Lazy Processing
- Components extracted only when needed
- Processing happens only for extracted components
- Minimal memory footprint

### Caching Opportunities
- Configuration caching
- AI summary caching (24-hour TTL)
- No PR data caching (always fresh)

## Data Isolation Benefits

### 1. **Independent Testing**
Each component can be tested in isolation without mocking other components.

### 2. **Flexible Processing**
Users can choose which components to analyze, reducing unnecessary API calls.

### 3. **Error Resilience**
Failures in one component don't affect others.

### 4. **Easy Extension**
New components can be added without modifying existing ones.

### 5. **Clear Boundaries**
Each stage has well-defined inputs and outputs.

## Best Practices

### For Fetchers
- Handle rate limiting gracefully
- Return consistent data structures
- Log API interactions for debugging

### For Extractors
- Extract only what belongs to your component
- Validate data thoroughly
- Handle missing fields gracefully

### For Processors
- Keep processing logic pure (no side effects)
- Use efficient algorithms for large PRs
- Provide meaningful error messages

### For Output
- Ensure all data is serializable
- Handle special characters properly
- Provide consistent formatting

## Monitoring Data Flow

### Logging Points
1. API calls (fetcher level)
2. Extraction start/completion
3. Processing duration
4. Output generation
5. Error occurrences

### Metrics to Track
- API rate limit usage
- Component extraction times
- Processing performance
- Output file sizes
- Error rates by component

## Future Enhancements

### Streaming Support
- Process large PRs in chunks
- Stream output for very large results

### Caching Layer
- Cache extracted components
- Intelligent cache invalidation
- Configurable cache strategies

### Pipeline Optimization
- Skip unchanged components
- Parallel processing improvements
- Smarter batching strategies