# PR Agents Project

## Project Overview
PR Agents is a modular Python library for analyzing GitHub Pull Requests with strict component isolation. The project emphasizes type safety, preventing "context bleeding" between different analysis components, and provides comprehensive PR insights through a structured pipeline architecture.

### Architecture
```
GitHub API → Pydantic Models → Extractors → Dataclass Results → Processors → Analysis
```

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

2. **Extractors** (`src/pr_agents/pr_processing/extractors/`)
   - `metadata.py`: Extracts PR title, description, labels, author
   - `code_changes.py`: Extracts diffs, additions/deletions, patches
   - `repository.py`: Extracts repo info, languages, branches, topics
   - `reviews.py`: Extracts reviews, comments, approval status

3. **Processors** (`src/pr_agents/pr_processing/processors/`)
   - `metadata_processor.py`: Quality scoring, title analysis, label categorization
   - `code_processor.py`: Risk assessment, pattern detection, file analysis
   - `repo_processor.py`: Health scoring, language analysis, branch patterns

4. **Coordinator** (`coordinator.py`): Orchestrates the extraction and processing pipeline

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
- 100-point scale:
  - Title: 30 points (length, formatting, prefix)
  - Description: 40 points (content, sections, formatting)
  - Labels: 30 points (presence, categorization)
- Quality levels: poor (<40), fair (40-59), good (60-79), excellent (80+)

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
GITHUB_TOKEN=your_github_token  # Required for GitHub API access
OPENAI_API_KEY=your_openai_key  # Optional: For OpenAI integration
GEMINI_API_KEY=your_gemini_key  # Optional: For Google Gemini
ANTHROPIC_API_KEY=your_anthropic_key  # Optional: For Claude/Anthropic
GITHUB_COPILOT_API_KEY=your_copilot_key  # Optional: For GitHub Copilot
```

### Test Configuration
- Test markers defined in pytest.ini
- Use appropriate markers: unit, integration, parametrized, matrix, live, slow
- Run specific test sets: `uv run pytest -m unit`

## Code Documentation Standards
All code must be consistently documented inline:

### Required for All Functions/Classes
- **Docstrings**: Follow existing project style with clear purpose, Args, Returns
- **Type hints**: Complete type annotations for all function parameters and returns
- **Consistent style**: Match existing docstring format in the codebase

### README Updates
Update README.md only when changes affect:
- Installation, setup, or environment configuration
- User-facing features or API usage
- New environment variables or configuration options
- Core functionality that users need to understand

### Documentation Consistency
- Follow existing patterns and style in the codebase
- Keep docstrings concise but complete
- Include practical examples only when they clarify complex usage

## Usage Patterns

### Basic PR Analysis
```python
from src.pr_agents.pr_processing.coordinator import PRCoordinator

coordinator = PRCoordinator()
results = coordinator.process_pr(pr_data, components=["metadata", "code"])
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

### Usage Example
```python
# In coordinator.py - Modified to support validation phase
class PRCoordinator:
    def process_pr(self, pr_url: str, components: list[str], 
                   validate_accuracy: bool = False) -> dict:
        # Existing extraction and processing
        extracted_data = self.extract_pr_components(pr_url, components)
        processed_results = self.process_components(extracted_data, components)
        
        # Optional validation phase
        if validate_accuracy:
            # Prepare data for validator
            validation_input = {
                "metadata_results": processed_results.get("metadata"),
                "code_results": processed_results.get("code")
            }
            
            # Run accuracy validation
            validator = AccuracyValidator()
            validation_result = validator.process(validation_input)
            
            processed_results["accuracy_validation"] = validation_result.data
        
        return processed_results
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

## PR Analysis Enhancement Components

### Overview
Two separate components enhance PR analysis with repository-specific understanding:
1. **PR Tagging Processor** - Uses YAML registry to tag and categorize PRs
2. **Repository Structure Configuration** - JSON-based module location mapping

### Component 1: PR Tagging Processor

#### Purpose
Analyzes PR files and adds repository-specific tags, impact analysis, and categorization based on YAML registry rules.

#### Architecture
- **Type**: Processor (operates on extracted PR data)
- **Location**: `src/pr_agents/pr_processing/processors/pr_tagger.py`
- **Input**: File changes + YAML registry definitions
- **Output**: Tags, impact levels, module categories, rule matches

#### Key Features
- File-level tagging based on patterns
- Overall PR tag generation
- Impact analysis (high/medium/low)
- Module categorization
- Rule matching from YAML definitions

#### YAML Registry Structure
Located in `registry/prebid/`, each YAML file defines:
```yaml
repo: "https://github.com/prebid/Prebid.js"
structure:
  modules:
    "Bid Adapter": 
      - modules/++ endsWith('BidAdapter', file)
    "Analytics Adapter":
      - modules/++ endsWith('AnalyticsAdapter', file)
definitions:
  - name: "rule_name"
    description: "Rule description"
    rules_class: "class_name"
    scope: "per_file"
    tags: ["tag1", "tag2"]
```

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

### Implementation Plan

#### Phase 1: PR Tagging Processor
1. Create data models for tagging results
2. Implement YAML registry loader
3. Build pattern evaluation system
4. Create PR tagger processor
5. Add unit tests

#### Phase 2: Repository Structure Configuration
1. Design JSON schema for repo structures
2. Implement configuration loader
3. Create structure query API
4. Add configuration for all Prebid repos
5. Add validation and tests

#### Phase 3: Integration
1. Update Module Extractor to use repo structure config
2. Enhance Accuracy Validator with tagging data
3. Update coordinator to include new components
4. Add integration tests

### Key Design Decisions
- **Separation of Concerns**: Tagging (analysis) vs Structure (configuration)
- **Isolation Maintained**: Each component operates independently
- **Extensibility**: Easy to add new repos by adding YAML/JSON files
- **Composability**: Components can be used together or separately