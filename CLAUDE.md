# PR Agents Project

## Quick Reference

### Essential Commands
```bash
# Development workflow
uv run black .              # Format code
uv run ruff check .         # Lint code  
uv run pytest              # Run tests
uv run pytest -m unit      # Run unit tests only

# Configuration management
python -m src.pr_agents.config.cli validate  # Validate configs
python -m src.pr_agents.config.cli list      # List repositories
```

### Key Components
- **Fetchers**: `src/pr_agents/pr_processing/fetchers/` - Retrieve PR data from GitHub
- **Coordinators**: `src/pr_agents/pr_processing/coordinators/` - Orchestrate analysis
- **Extractors**: `src/pr_agents/pr_processing/extractors/` - Extract component data
- **Processors**: `src/pr_agents/pr_processing/processors/` - Analyze data
- **Output**: `src/pr_agents/output/` - Format and export results

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Key Design Principles](#key-design-principles)
4. [Code Quality Standards](#code-quality-standards)
5. [Development Workflow](#development-workflow)
6. [Dependencies](#dependencies)
7. [Git Workflow](#git-workflow)
8. [Logging Standards](#logging-standards)
9. [Testing Standards](#testing-standards)
10. [Project Structure](#project-structure)
11. [Analysis Algorithms](#analysis-algorithms)
12. [Configuration](#configuration)
13. [Configuration System](#configuration-system)
14. [Code Documentation Standards](#code-documentation-standards)
15. [Usage Patterns](#usage-patterns)
16. [Fetcher System Details](#fetcher-system-details)
17. [Common Development Tasks](#common-development-tasks)
18. [Performance Considerations](#performance-considerations)
19. [Security Considerations](#security-considerations)
20. [PR Metadata-Code Accuracy Validator](#pr-metadata-code-accuracy-validator)
21. [Additional Components](#additional-components-for-enhanced-pr-analysis)
22. [PR Analysis Enhancement Components](#pr-analysis-enhancement-components)
23. [Error Handling Patterns](#error-handling-patterns)
24. [Performance Optimization](#performance-optimization)
25. [Debugging Tips](#debugging-tips)
26. [Future Enhancements](#future-enhancements)
27. [AI-Powered Code Summarization](#ai-powered-code-summarization)

## Project Overview
PR Agents is a modular Python library for analyzing GitHub Pull Requests with strict component isolation. The project emphasizes type safety, preventing "context bleeding" between different analysis components, and provides comprehensive PR insights through a structured pipeline architecture.

### Project Goals
- **Modular Analysis**: Each PR component (metadata, code, repository, reviews) analyzed independently
- **Type Safety**: Strong typing throughout with Pydantic and dataclasses
- **Extensibility**: Easy to add new extractors, processors, and output formats
- **Performance**: Efficient processing of large PRs and batch operations
- **Flexibility**: Support for various output formats and analysis configurations

### Architecture
```
GitHub API → Fetchers → Coordinators → Extractors → Processors → Output Formatters
                              ↓
                    ComponentManager (lifecycle)
```

#### Pipeline Components

1. **Fetchers**: Retrieve PR data from GitHub API
   - Handle different query patterns (release, date, label)
   - Manage API rate limiting
   - Return standardized PR data

2. **Coordinators**: Orchestrate the analysis pipeline
   - Route requests to appropriate sub-coordinators
   - Manage component lifecycle
   - Handle error aggregation

3. **Extractors**: Transform GitHub data into components
   - Strict isolation per component
   - No cross-component dependencies
   - Return structured data

4. **Processors**: Analyze extracted data
   - Pure functions for analysis
   - Generate insights and scores
   - No external API calls

5. **Output Formatters**: Export results
   - Multiple format support
   - Clean data serialization
   - File management

#### Modular Coordinator System
The project uses a modular coordinator architecture to maintain separation of concerns:

1. **PRCoordinator** (`coordinator.py`): Main facade maintaining backward compatibility
   - Delegates to specialized sub-coordinators
   - Integrates output formatting
   - ~328 lines (reduced from 725)

2. **SinglePRCoordinator** (`coordinators/single_pr.py`): Handles individual PR analysis
   - Manages extraction pipeline
   - Coordinates processing flow
   - Generates summaries

3. **BatchCoordinator** (`coordinators/batch.py`): Manages batch operations
   - Release-based analysis
   - Date range analysis  
   - Multi-PR operations

4. **ComponentManager** (`coordinators/component_manager.py`): Component lifecycle
   - Initializes extractors and processors
   - Provides component registry
   - Maps data between components

5. **Analysis Utilities**:
   - `SummaryBuilder`: Pure functions for generating summaries
   - `ResultFormatter`: Formats results for output systems

### Key Design Principles
- **Strict Component Isolation**: Each component (metadata, code changes, repository info, reviews) is extracted and processed in complete isolation
- **Type Safety**: Pydantic models for external APIs, dataclasses for internal processing
- **Dependency Injection**: Components are injected rather than hard-coded
- **Interface-Based Design**: Easy to mock and extend through base classes
- **Immutable Processing**: Results are immutable dataclass instances

## Code Quality Standards
- Use Python 3.13
- Follow PEP 8 style guidelines
- Line length: 88 characters
- Use double quotes for strings
- Use type hints for all functions
- Use dataclasses for internal result models
- Use Pydantic for external API models

## Development Workflow
- Always run code quality checks before completing tasks
- Format code with black: `uv run black .`
- Lint code with ruff: `uv run ruff check .`
- Run tests with pytest: `uv run pytest`
- Run type checking with mypy when available

## Required Commands After Code Changes
When making code changes, ALWAYS run these commands in order:
1. `uv run black .` - Format code
2. `uv run ruff check .` - Check for linting issues
3. `uv run pytest` - Run all tests

If any of these commands fail, fix the issues before considering the task complete.

## Dependencies
- Use `uv` for dependency management
- Add new dependencies to pyproject.toml
- Keep dev dependencies separate in [dependency-groups.dev]
- Core dependencies: PyGithub, Pydantic, Loguru
- Dev dependencies: Black, Ruff, Pytest, Mypy

## Git Workflow
- Never commit without running the quality checks above
- Write clear, descriptive commit messages
- Only commit when explicitly asked by the user
- Follow conventional commit format when applicable

## Logging Standards
- Use loguru for all logging throughout the codebase
- Import logging utilities from `src.pr_agents.logging_config`
- Follow established logging patterns:
  - Use `log_function_entry()` and `log_function_exit()` for function tracking
  - Use `log_processing_step()` for major operation milestones
  - Use `log_data_flow()` to track data transformations
  - Use `log_api_call()` for external API interactions
  - Use `log_error_with_context()` for error handling
  - Use `@log_calls` decorator for automatic function logging
- Sensitive data is automatically sanitized in logs
- Respect environment-aware logging (dev/staging/prod)
- Log files rotate at 10MB with 7-day retention

## Testing Standards
- Use pytest for all testing
- Organize tests into unit and integration categories
- Follow pytest naming conventions (Test* classes, test_* methods)
- Use fixtures for setup and mocking
- Use parametrized tests for comprehensive coverage
- Test markers available: unit, integration, parametrized, matrix, live, slow
- Mock objects should match PyGithub interfaces
- Always test edge cases and error conditions
- Live tests require GitHub token and are marked with @pytest.mark.live

## Project Structure

### Core Components
1. **Models** (`src/pr_agents/pr_processing/`)
   - `models.py`: Pydantic models for external API data
   - `analysis_models.py`: Dataclass models for processing results

2. **Fetchers** (`src/pr_agents/pr_processing/fetchers/`)
   - `base.py`: Base fetcher interface for all PR fetchers
   - `date_range.py`: Fetch PRs within date ranges
   - `release.py`: Fetch PRs by release tags
   - `label.py`: Fetch PRs by labels
   - `multi_repo.py`: Fetch PRs across multiple repositories
   - `pr_fetcher.py`: Original fetcher with legacy methods

3. **Extractors** (`src/pr_agents/pr_processing/extractors/`)
   - `metadata.py`: Extracts PR title, description, labels, author
   - `code_changes.py`: Extracts diffs, additions/deletions, patches
   - `repository.py`: Extracts repo info, languages, branches, topics
   - `reviews.py`: Extracts reviews, comments, approval status

4. **Processors** (`src/pr_agents/pr_processing/processors/`)
   - `metadata_processor.py`: Title quality scoring, description quality scoring
   - `code_processor.py`: Risk assessment, pattern detection, file analysis
   - `repo_processor.py`: Health scoring, language analysis, branch patterns

5. **Coordinators** (`src/pr_agents/pr_processing/coordinators/`)
   - `base.py`: Base coordinator interface
   - `component_manager.py`: Component lifecycle management
   - `single_pr.py`: Single PR analysis orchestration
   - `batch.py`: Batch operations (releases, date ranges)

6. **Analysis** (`src/pr_agents/pr_processing/analysis/`)
   - `summary_builder.py`: Generate summaries and statistics
   - `result_formatter.py`: Format results for output

7. **Output System** (`src/pr_agents/output/`)
   - `base.py`: Base output formatter interface
   - `manager.py`: Output orchestration and file management
   - `markdown.py`: Markdown formatting with sections
   - `json_formatter.py`: JSON serialization with data cleaning
   - `text.py`: Plain text formatting

### Analysis Algorithms

#### Code Risk Assessment (CodeProcessor)
- Points-based system (0-6+ points):
  - 3 points: >1000 total changes (very large)
  - 2 points: >500 total changes (large)
  - 1 point: >100 total changes (medium)
  - 2 points: >20 files changed
  - 1 point: >10 files changed
  - 1 point per critical file modified
- Risk levels: minimal (0), low (1-2), medium (3-4), high (5+)

#### Metadata Quality Scoring (MetadataProcessor)
Separate scoring for title and description on independent 1-100 scales:

**Title Quality (1-100 scale):**
- Length assessment: 25 points (optimal: 15-80 characters)
- Word count: 15 points (optimal: 3-12 words)
- Conventional prefix: 20 points (feat/fix/docs/etc)
- Ticket reference: 15 points (optional)
- Clarity indicators: 25 points (not WIP, not a question, proper capitalization)
- Quality levels: poor (<50), fair (50-69), good (70-84), excellent (85+)

**Description Quality (1-100 scale):**
- Has description: 20 points (0 if missing)
- Length assessment: 20 points (100+ chars for full points)
- Structure: 25 points (sections with headers)
- Content richness: 35 points (checklists, links, code blocks)
- Quality levels: poor (<50), fair (50-69), good (70-84), excellent (85+)

#### Repository Health Assessment (RepoProcessor)
- 70-point scale:
  - 10 points: Has description
  - 10 points: ≥3 topics
  - 15 points: Multi-language support
  - 10 points: Public visibility
  - 5 points: Active fork status
  - 10 points: Standard branch naming
- Health levels: needs_improvement (<20), fair (20-34), good (35-49), excellent (50+)

## Configuration

### Environment Variables
Create a `.env` file with:
```
# Required
GITHUB_TOKEN=your_github_token  # GitHub API access

# Optional AI Integrations (future)
OPENAI_API_KEY=your_openai_key  # For OpenAI integration
GEMINI_API_KEY=your_gemini_key  # For Google Gemini
ANTHROPIC_API_KEY=your_anthropic_key  # For Claude/Anthropic
GITHUB_COPILOT_API_KEY=your_copilot_key  # For GitHub Copilot

# Logging Configuration
PR_AGENTS_ENV=development  # Options: development, staging, production
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR
LOG_SHOW_FUNCTIONS=true  # Show function names in logs
LOG_SHOW_DATA_FLOW=true  # Show data flow details
LOG_FILE=/tmp/pr-agents.log  # Optional log file path
```

### Test Configuration
- Test markers defined in pytest.ini
- Use appropriate markers: unit, integration, parametrized, matrix, live, slow
- Run specific test sets: `uv run pytest -m unit`
- Skip live tests: `uv run pytest -m "not live"`
- Run with coverage: `uv run pytest --cov=src/pr_agents --cov-report=html`

## Code Documentation Standards
All code must be consistently documented inline:

### Required for All Functions/Classes
- **Docstrings**: Follow existing project style with clear purpose, Args, Returns
- **Type hints**: Complete type annotations for all function parameters and returns
- **Consistent style**: Match existing docstring format in the codebase

### Documentation Consistency
- Follow existing patterns and style in the codebase
- Keep docstrings concise but complete
- Include practical examples only when they clarify complex usage

## Usage Patterns

### Basic PR Analysis
```python
from src.pr_agents.pr_processing.coordinator import PRCoordinator

coordinator = PRCoordinator(github_token="your-token")
results = coordinator.analyze_pr("https://github.com/owner/repo/pull/123")
```

### Batch Processing & Release Analysis
```python
# Analyze all PRs in a release
release_results = coordinator.analyze_release_prs("owner/repo", "v1.2.3")

# Analyze unreleased PRs
unreleased = coordinator.analyze_unreleased_prs("owner/repo", base_branch="main")

# Analyze PRs between releases
version_diff = coordinator.analyze_prs_between_releases(
    "owner/repo", from_tag="v1.0.0", to_tag="v1.1.0"
)

# Batch analyze specific PRs
batch = coordinator.analyze_prs_batch([
    "https://github.com/owner/repo/pull/1",
    "https://github.com/owner/repo/pull/2"
])
```

### Output Formatting
```python
# Analyze and save to file
results, path = coordinator.analyze_pr_and_save(
    "https://github.com/owner/repo/pull/123",
    output_path="analysis",
    output_format="markdown"  # Options: markdown, json, text
)

# Use output manager directly
from src.pr_agents.output import OutputManager

output_mgr = OutputManager()
for format in ["markdown", "json", "text"]:
    output_mgr.save(results, f"report_{format}", format)
```

### Component Isolation
Each component can be processed independently:
- Extract only what you need
- Process specific aspects in isolation
- Prevent unnecessary API calls
- No context bleeding between components

### Extending the System
1. Create new extractors by inheriting from base classes
2. Implement new processors following the BaseProcessor interface
3. Add corresponding analysis models as dataclasses
4. Update constants for new component names
5. Add comprehensive tests for new components
6. Register new components in ComponentManager
7. Update documentation

### Adding a New Output Format
1. Create formatter class inheriting from BaseOutputFormatter
2. Implement `format()` and `get_file_extension()` methods
3. Register in OutputManager
4. Add tests for edge cases
5. Document format structure

## Configuration System

### Repository Configuration
The project uses a multi-file JSON configuration system:

```
config/
├── repositories.json          # Master list of repositories
├── schema/                    # JSON schemas for validation
│   └── repository.schema.json
└── repositories/              # Individual repo configurations
    ├── prebid/
    │   ├── prebid-js.json
    │   ├── prebid-server.json
    │   └── ...
    └── shared/               # Shared base configurations
```

### Configuration Features
- **Inheritance**: Repositories can extend shared base configurations
- **Version Overrides**: Handle version-specific behaviors
- **Pattern Matching**: Flexible module detection patterns
- **Validation**: Schema-based validation with strict mode
- **Hot Reload**: Automatic configuration reload in development

### CLI Tools
```bash
# Validate all configurations
python -m src.pr_agents.config.cli validate

# List all configured repositories
python -m src.pr_agents.config.cli list

# Watch for configuration changes
python -m src.pr_agents.config.cli watch

# Test pattern matching
python -m src.pr_agents.config.cli test-pattern "modules/exampleBidAdapter.js"
```

## Common Development Tasks

### Adding a New Processor
1. Create processor class inheriting from BaseProcessor
2. Implement `process()` method and `component_name` property
3. Define analysis models in `analysis_models.py`
4. Add constants to `constants.py`
5. Write unit and integration tests
6. Update documentation

### Modifying Analysis Algorithms
1. Update the relevant processor's analysis methods
2. Adjust scoring thresholds if needed
3. Update tests to match new logic
4. Document algorithm changes in docstrings
5. Ensure backward compatibility when possible

### Working with Fixtures
- Use mock objects from `tests/fixtures/mock_github.py`
- Create realistic test data matching PyGithub interfaces
- Leverage parametrized fixtures for multiple scenarios
- Keep fixtures focused and reusable

## Performance Considerations
- Processors work with already-extracted data (no API calls)
- Use component selection to minimize data extraction
- Leverage caching where appropriate
- Keep processing logic efficient for large PRs

## Security Considerations
- Never log sensitive data (automatically sanitized)
- Validate all external inputs
- Use environment variables for secrets
- Follow secure coding practices
- Don't expose internal implementation details in logs

## PR Metadata-Code Accuracy Validator

### Overview
A focused cross-component validator that verifies PR metadata (title, description) accurately reflects actual code changes. Maintains strict isolation by operating only on pre-processed results from metadata and code processors.

### Architecture Design

#### Component Isolation
The accuracy validator strictly follows the project's isolation principles:
- **Input**: Only pre-processed results from metadata and code processors
- **Processing**: Pure validation logic with no external dependencies
- **Output**: Accuracy scores and recommendations
- **No API calls**: Works only with already-extracted data
- **No side effects**: Stateless validation

#### Validation Flow
```python
class AccuracyValidator(BaseProcessor):
    """Validates metadata accuracy against code changes."""
    
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        # Receives processed results from:
        # - metadata processor (title, description analysis)
        # - code processor (file changes, patterns)
        
        # Performs accuracy scoring
        # Returns validation results
```

### Scoring Algorithm

#### Components and Weights
1. **Title Accuracy (30%)**
   - Module mention accuracy
   - Action verb correctness
   - Scope precision
   
2. **Description Accuracy (40%)**
   - File coverage ratio
   - Technical detail alignment
   - Change type matching
   
3. **Completeness (20%)**
   - Unmentioned significant changes
   - Coverage of all modified areas
   
4. **Specificity (10%)**
   - Technical term usage
   - Concrete vs vague language

#### Advanced Matching Techniques
- **Fuzzy Matching**: For file and module names
- **Semantic Analysis**: Extract meaning from natural language
- **Technical Vocabulary**: Domain-specific term recognition
- **Context-Aware Scoring**: Adjust based on PR size and complexity

### Implementation Components

#### 1. Accuracy Validator
```python
class AccuracyValidator(BaseProcessor):
    """Pure validation logic for metadata-code accuracy."""
    
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        # Extract pre-processed results
        metadata_results = component_data.get("metadata_results")
        code_results = component_data.get("code_results")
        
        # Calculate accuracy scores
        accuracy_score = self._calculate_accuracy(metadata_results, code_results)
        
        return ProcessingResult(
            component="accuracy_validation",
            success=True,
            data=asdict(accuracy_score)
        )
```

#### 2. Accuracy Scoring Logic
```python
def _calculate_accuracy(self, metadata: dict, code: dict) -> AccuracyScore:
    """Calculate accuracy score between metadata and code."""
    
    # Extract relevant data from pre-processed results
    title_analysis = metadata.get("title_analysis", {})
    description_analysis = metadata.get("description_analysis", {})
    file_analysis = code.get("file_analysis", {})
    pattern_analysis = code.get("pattern_analysis", {})
    
    # Calculate component scores
    scores = {
        "title_accuracy": self._score_title_accuracy(
            title_analysis, file_analysis
        ),
        "description_accuracy": self._score_description_accuracy(
            description_analysis, file_analysis, pattern_analysis
        ),
        "completeness": self._score_completeness(
            metadata, code
        ),
        "specificity": self._score_specificity(
            title_analysis, description_analysis
        )
    }
    
    return AccuracyScore(
        total_score=self._calculate_weighted_score(scores),
        component_scores=scores,
        recommendations=self._generate_recommendations(scores)
    )
```

### Testing Strategy
- **Parametrized Test Scenarios**: Cover various accuracy levels
- **Mock GitHub Data**: Realistic test fixtures
- **Edge Case Coverage**: Handle missing data, large PRs
- **Integration Tests**: Test with coordinator pipeline

### Key Benefits
1. **Pure Validation Logic**: No external dependencies or API calls
2. **Maintains Isolation**: Respects component boundaries
3. **Extensible Design**: Easy to add new validation rules
4. **Actionable Feedback**: Provides specific improvement suggestions
5. **Testable**: Pure functions with predictable inputs/outputs

## Additional Components for Enhanced PR Analysis

### 1. Repository Configuration System
A separate configuration management system for repository-specific settings:
```python
# src/pr_agents/config/repository_config.py
class RepositoryConfigManager:
    """Manages repository-specific configurations."""
    
    def get_repo_config(self, repo_url: str) -> dict:
        """Returns configuration for module patterns, file structures, etc."""
```

**Configuration Format** (similar to documentation-toolkit):
```json
{
  "prebid/Prebid.js": {
    "type": "prebid",
    "module_paths": {
      "adapters": ["modules/*BidAdapter.js"],
      "core": ["src/"],
      "tests": ["test/spec/"]
    }
  }
}
```

### 2. Module Extractor (New Component)
A dedicated extractor for module information:
```python
# src/pr_agents/pr_processing/extractors/modules.py
class ModuleExtractor(BaseExtractor):
    """Extracts module structure from repositories."""
    
    def extract(self, pr_data: Any) -> dict[str, Any]:
        """Extract module categorization and relationships."""
```

**Extracted Data**:
- Module categorization (adapters, core, utilities)
- Module dependencies
- File-to-module mapping

### 3. Rate Limit Manager (Shared Utility)
A shared utility for API rate limit management:
```python
# src/pr_agents/utilities/rate_limit_manager.py
class RateLimitManager:
    """Manages GitHub API rate limits across all components."""
    
    def check_and_wait(self):
        """Check rate limit and wait if necessary."""
```

**Features**:
- Batch processing support
- Configurable delays
- Rate limit monitoring
- Shared across all extractors

### Integration Strategy
These components work together while maintaining isolation:
1. **Configuration** is loaded once and passed to relevant components
2. **Module extraction** runs as a separate extraction phase
3. **Rate limiting** is used by extractors, not processors
4. **Accuracy validation** uses the results from all components without direct dependencies

## Fetcher System Details

### Fetcher Architecture
The fetcher system provides flexible ways to retrieve groups of PRs:

#### Base Fetcher Interface
```python
class BasePRFetcher(ABC):
    @abstractmethod
    def fetch(self, **kwargs) -> list[dict[str, Any]]:
        """Fetch PRs based on implementation-specific criteria."""
        pass
```

#### Available Fetchers
1. **PRFetcher** (Legacy)
   - Original implementation with multiple methods
   - Methods: `get_prs_by_release()`, `get_unreleased_prs()`, etc.
   - Used internally by BatchCoordinator

2. **ReleasePRFetcher**
   - Fetches PRs included in a specific release
   - Handles date range calculation between releases
   - Supports release comparison

3. **DateRangePRFetcher**
   - Fetches PRs within specified date ranges
   - Supports various PR states (open, closed, merged)
   - Useful for time-based analysis

4. **LabelPRFetcher**
   - Fetches PRs with specific labels
   - Supports multiple labels (AND/OR logic)
   - Useful for categorized analysis

5. **MultiRepoPRFetcher**
   - Fetches PRs across multiple repositories
   - Aggregates results from different repos
   - Supports parallel fetching (future)

### Fetcher Usage Patterns
```python
# Direct fetcher usage
fetcher = ReleasePRFetcher(github_token)
prs = fetcher.fetch(repo_name="owner/repo", release_tag="v1.0.0")

# Through coordinator (recommended)
results = coordinator.analyze_release_prs("owner/repo", "v1.0.0")
```

## PR Analysis Enhancement Components

### Overview
Two separate components enhance PR analysis with repository-specific understanding:
1. **PR Tagging Processor** - Uses YAML registry to tag and categorize PRs
2. **Repository Structure Configuration** - JSON-based module location mapping

### Component 2: Repository Structure Configuration

#### Purpose
Lightweight configuration system defining where different module types are located in each repository.

#### Architecture
- **Type**: Configuration system
- **Location**: `src/pr_agents/config/repo_structure.py`
- **Config File**: `config/repository_structures.json`
- **Usage**: By extractors and processors needing module locations

#### JSON Configuration Format
```json
{
  "prebid/Prebid.js": {
    "repo_type": "prebid-js",
    "module_locations": {
      "bid_adapter": {
        "paths": ["modules/*BidAdapter.js"],
        "naming_pattern": "endsWith('BidAdapter')"
      }
    },
    "core_paths": ["src/", "libraries/"],
    "test_paths": ["test/spec/modules/"],
    "doc_paths": ["docs/"]
  }
}
```

### Key Design Decisions
- **Separation of Concerns**: Tagging (analysis) vs Structure (configuration)
- **Isolation Maintained**: Each component operates independently
- **Extensibility**: Easy to add new repos by adding YAML/JSON files
- **Composability**: Components can be used together or separately

## Error Handling Patterns

### Extraction Errors
- Extractors return `None` on failure
- Errors logged but don't stop pipeline
- Each component fails independently

### Processing Errors
- Processors return ProcessingResult with success=False
- Error details in the errors field
- Processing continues for other components

### Batch Processing Errors
- Individual PR failures don't stop batch
- Failed PRs tracked in results
- Summary includes failure statistics

## Performance Optimization

### API Rate Limits
- GitHub: 5000 requests/hour (authenticated)
- Consider batch size for large operations
- Future: Rate limit manager implementation

### Memory Management
- Process PRs one at a time in batches
- Stream large outputs when possible
- Clear extracted data after processing

### Caching Strategy
- Configuration cached on first load
- Component registry cached
- PR data not cached (always fresh)

## Debugging Tips

### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
export LOG_SHOW_FUNCTIONS=true
export LOG_SHOW_DATA_FLOW=true
python your_script.py
```

### Common Issues
1. **Empty extraction results**: Check GitHub token permissions
2. **Processing failures**: Verify data structure matches expectations
3. **Output errors**: Ensure data is serializable
4. **Test failures**: Mock objects may need updating

### Useful Debug Commands
```python
# Print component registry
print(coordinator.component_manager.list_extractors())
print(coordinator.component_manager.list_processors())

# Check extracted data
pr_data = coordinator.extract_pr_components(pr_url)
print(pr_data.model_dump(exclude_none=True))

# Inspect processing results
for result in processing_results:
    if not result.success:
        print(f"Failed: {result.component}")
        print(f"Errors: {result.errors}")
```


## AI-Powered Code Summarization

### Overview
The AI service layer provides intelligent, persona-based summarization of code changes using LLMs (Large Language Models). It generates three levels of summaries tailored for different audiences: executives, product managers, and developers.

### Architecture Design

#### Service Layer Architecture
The AI functionality is implemented as a service layer to maintain separation from the core processing logic:

```
PRCoordinator (ai_enabled=True)
    ↓
AIProcessor (registered dynamically)
    ↓
AIService (orchestrates LLM calls)
    ↓
LLM Providers (Gemini, Claude, OpenAI)
```

#### Key Components

1. **AIService** (`src/pr_agents/services/ai/service.py`)
   - Main orchestrator for AI functionality
   - Manages provider lifecycle
   - Handles caching for consistency
   - Concurrent persona summary generation

2. **LLM Providers** (`src/pr_agents/services/ai/providers/`)
   - `BaseLLMProvider`: Abstract interface
   - `GeminiProvider`: Google Gemini integration
   - `ClaudeProvider`: Anthropic Claude integration
   - `OpenAIProvider`: OpenAI GPT integration

3. **Prompt Management** (`src/pr_agents/services/ai/prompts/`)
   - `PromptBuilder`: Constructs context-aware prompts
   - `templates.py`: Persona-specific templates
   - Repository context integration

4. **Caching System** (`src/pr_agents/services/ai/cache/`)
   - `SummaryCache`: In-memory caching
   - Key generation based on change patterns
   - TTL-based expiration

5. **AIProcessor** (`src/pr_agents/pr_processing/processors/ai_processor.py`)
   - Integrates with existing processor architecture
   - Builds repository context
   - Language detection

### Configuration

#### Environment Variables
```env
# LLM Provider Selection
AI_PROVIDER=gemini  # Options: gemini, claude, openai

# Provider API Keys
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key

# AI Service Configuration
AI_CACHE_TTL=86400  # Cache TTL in seconds (default: 24 hours)
AI_MAX_RETRIES=3    # Maximum retry attempts
AI_TIMEOUT=30       # Request timeout in seconds
```

#### Enabling AI Features
```python
# Initialize coordinator with AI enabled
coordinator = PRCoordinator(github_token="your-token", ai_enabled=True)

# Analyze PR with AI summaries
results = coordinator.analyze_pr_with_ai(
    "https://github.com/owner/repo/pull/123"
)

# Access AI summaries
print(results["ai_summaries"]["executive_summary"])
print(results["ai_summaries"]["product_summary"])
print(results["ai_summaries"]["developer_summary"])
```

### Summary Personas

#### 1. Executive Summary (150 tokens)
- **Focus**: Business impact and scope
- **Length**: 1-2 sentences
- **Example**: "Sevio Bid Adapter added to Prebid.js and supports banner and native media types."

#### 2. Product Manager Summary (300 tokens)
- **Focus**: Features and capabilities
- **Length**: 2-4 sentences
- **Example**: "Sevio Bid Adapter added to Prebid.js with comprehensive support for banner (300x250, 728x90) and native ad formats. Features include Ethereum and Solana digital wallet detection for Web3 targeting, GDPR/CCPA compliance handling, and real-time bid adjustment based on user engagement metrics. Implements standard adapter callbacks (onBidWon, onBidderError, onTimeout) plus custom user sync with configurable pixel and iframe endpoints supporting up to 5 concurrent syncs."

#### 3. Developer Summary (500 tokens)
- **Focus**: Technical implementation details
- **Length**: 4-6 sentences
- **Example**: "Sevio Bid Adapter (modules/sevioBidAdapter.js) and CryptoUtils library (libraries/cryptoUtils/index.js) added to Prebid.js. The CryptoUtils library implements SHA-256 hashing and AES-GCM encryption using the Web Crypto API for secure bid request signing, with fallback to CryptoJS for older browsers. The Sevio adapter extends the Prebid BaseAdapter class, implementing interpretResponse() with custom bid parsing logic that handles nested JSON responses, buildRequests() with dynamic endpoint selection based on datacenter location, and isBidRequestValid() with strict schema validation using Joi. Adds three new dependencies: crypto-js@4.1.1 for legacy support, joi@17.9.0 for validation, and ethers@6.7.0 for Web3 wallet detection. Test coverage includes 47 unit tests (93% line coverage) using Sinon for mocking external API calls and Chai for assertions. Performance optimization through request batching reduces API calls by 60% for multi-slot pages. Implements OWASP-compliant input sanitization and rate limiting (100 req/min) to prevent abuse."

### Prompt Engineering

#### Repository Context
The system enriches prompts with repository-specific context:
- Repository type and description
- Module patterns and structure
- Programming languages detected
- File organization

#### Dynamic Prompt Construction
```python
# Example prompt structure for executive persona
prompt = f"""
You are summarizing code changes for an executive audience.
Repository: {repo_name} ({repo_type})

PR Title: {pr_title}
Files Changed: {file_count}
Lines Added: {additions}
Lines Deleted: {deletions}

Repository Context:
{repo_context}

Provide a 1-2 sentence executive summary...
"""
```

### Caching Strategy

#### Cache Key Generation
Cache keys are generated based on:
- Repository name and type
- Change magnitude (small/medium/large)
- File patterns (e.g., "*BidAdapter.js")
- Primary directories affected

#### Benefits
- Consistent summaries for similar changes
- Reduced API costs
- Lower latency for common patterns
- 24-hour default TTL

### Error Handling

#### Graceful Degradation
- Provider failures return error summaries
- Automatic retry with exponential backoff
- Fallback to cached results when available

#### Error Summary Format
```python
PersonaSummary(
    persona="executive",
    summary="Error generating summary: API timeout",
    confidence=0.0
)
```

### Testing Strategy

#### Unit Tests
- Mock provider implementations
- Prompt builder validation
- Cache functionality
- Error handling scenarios

#### Integration Tests
- Full pipeline with mocked LLM responses
- Caching behavior verification
- Output format validation

### Performance Considerations

#### Concurrent Processing
- All three personas generated in parallel
- Async/await for non-blocking operations
- Total generation time typically 2-3 seconds

#### API Key Management
- Environment variable storage only
- No hardcoded credentials
- Secure key rotation support

#### Data Privacy
- No sensitive code in prompts
- Sanitized repository context
- No PII in summaries
