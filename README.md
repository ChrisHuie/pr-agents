# PR Agents

A modular Python library for analyzing GitHub Pull Requests with strict component isolation and type safety.

## 🎯 Project Philosophy

**Separation of Concerns**: Each component operates in complete isolation, preventing context bleeding between different aspects of PR analysis (metadata, code changes, repository info, reviews).

**Type Safety First**: Uses Pydantic models for external API boundaries and dataclasses for internal processing results, ensuring robust type safety throughout the analysis pipeline.

**Testability**: Every component can be tested independently, making the codebase maintainable and reliable.

## 🏗️ Architecture Overview

```
External API (GitHub) → Pydantic Models → Extractors → Dataclass Results → Processors → Analysis
```

### Design Principles

1. **Strict Isolation**: Extractors only see their specific component data
2. **No Context Bleeding**: PR title/description never influences code analysis
3. **Dependency Injection**: Components are injected rather than hard-coded
4. **Interface-Based**: Easy to mock and extend
5. **Immutable Processing**: Results are immutable dataclass instances

## 📁 Project Structure

```
pr-agents/
├── src/pr_agents/pr_processing/           # Core processing module
│   ├── __init__.py                        # Public API exports
│   ├── models.py                          # Pydantic models (external boundaries)
│   ├── analysis_models.py                 # Dataclass models (internal results)
│   ├── coordinator.py                     # Orchestrates processing pipeline
│   │
│   ├── extractors/                        # Component extraction (GitHub API → Python)
│   │   ├── __init__.py
│   │   ├── base.py                        # Base extractor interface
│   │   ├── metadata.py                    # PR title, description, labels
│   │   ├── code_changes.py                # Diffs, file modifications
│   │   ├── repository.py                  # Repo info, branches, languages
│   │   └── reviews.py                     # Comments, reviews, approvals
│   │
│   └── processors/                        # Analysis logic (Python → Insights)
│       ├── __init__.py
│       ├── base.py                        # Base processor interface
│       ├── metadata_processor.py          # Quality scoring, pattern detection
│       ├── code_processor.py              # Risk assessment, pattern analysis
│       └── repo_processor.py              # Health scoring, language analysis
│
├── tests/pr_processing/                   # Comprehensive test suite
│   ├── __init__.py
│   └── test_processors.py                 # Isolated component tests
│
├── examples/                              # Usage examples
│   └── pr_analysis_example.py             # Complete workflow demonstration
│
├── .env                                   # Environment variables (not committed)
├── .gitignore                             # Includes .env protection
├── CLAUDE.md                              # Development workflow & standards
├── pyproject.toml                         # Dependencies & tool configuration
└── README.md                              # This file
```

## 🔧 Component Breakdown

### **Models Layer**

#### **Pydantic Models (`models.py`)**
- **Purpose**: Handle external API data with validation and serialization
- **Used for**: GitHub API responses, data persistence, API boundaries
- **Examples**: `PRMetadata`, `CodeChanges`, `RepositoryInfo`, `ReviewData`

#### **Dataclass Models (`analysis_models.py`)**
- **Purpose**: Internal processing results with better performance
- **Used for**: Analysis outputs, processor results, structured data
- **Examples**: `TitleAnalysis`, `RiskAssessment`, `RepoHealth`

### **Extractors Layer**

**Responsibility**: Convert GitHub API data into structured Python objects

- **`MetadataExtractor`**: Extracts PR title, description, labels, author info
- **`CodeChangesExtractor`**: Extracts file diffs, additions/deletions, patches  
- **`RepositoryExtractor`**: Extracts repo info, languages, branches, topics
- **`ReviewsExtractor`**: Extracts reviews, comments, approval status

**Key Feature**: Each extractor operates in complete isolation - no cross-contamination.

### **Processors Layer**

**Responsibility**: Analyze extracted data and generate insights

- **`MetadataProcessor`**: Quality scoring, title analysis, label categorization
- **`CodeProcessor`**: Risk assessment, pattern detection, file analysis
- **`RepoProcessor`**: Health scoring, language analysis, branch patterns

**Key Feature**: Processors receive only their specific component data, ensuring unbiased analysis.

### **Coordinator Layer**

**Responsibility**: Orchestrate the entire pipeline with controlled data flow

```python
coordinator = PRCoordinator(github_token)

# Extract only specific components
pr_data = coordinator.extract_pr_components(pr_url, {"metadata", "code_changes"})

# Process in isolation  
results = coordinator.process_components(pr_data, ["metadata"])

# Complete analysis
analysis = coordinator.analyze_pr(pr_url)
```

## 🚀 Quick Start

### Installation

```bash
git clone <repository-url>
cd pr-agents
uv install  # or pip install -e .
```

### Environment Setup

```bash
# Create .env file
echo "GITHUB_TOKEN=your_github_token_here" > .env
```

### Logging Configuration

Control logging behavior with environment variables:

```bash
# Development (default) - Verbose logging with function details
python main.py

# Production - Minimal logging for performance
PR_AGENTS_ENV=production python main.py

# Custom configuration
export LOG_LEVEL=DEBUG
export LOG_SHOW_FUNCTIONS=false
export LOG_FILE=/tmp/pr-agents.log
python main.py
```

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `PR_AGENTS_ENV` | `development` | `development`, `staging`, `production` | Environment type |
| `LOG_LEVEL` | Environment-dependent | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Logging level |
| `LOG_SHOW_FUNCTIONS` | Environment-dependent | `true`, `false` | Show function names |
| `LOG_SHOW_DATA_FLOW` | Environment-dependent | `true`, `false` | Show data flow details |
| `LOG_FILE` | None | Any file path | Optional log file output |

### Basic Usage

```python
from pr_agents.pr_processing import PRCoordinator

# Initialize with GitHub token
coordinator = PRCoordinator(github_token)

# Analyze a PR with component isolation
analysis = coordinator.analyze_pr("https://github.com/owner/repo/pull/123")

# Access structured results
metadata_quality = analysis["processing_results"][0]["data"]["metadata_quality"]
print(f"PR Quality: {metadata_quality['quality_level']}")
```

### Selective Processing

```python
# Extract only metadata (no code context bleeding)
pr_data = coordinator.extract_pr_components(
    pr_url, 
    components={"metadata"}
)

# Process only code changes (no metadata influence)
results = coordinator.process_components(
    pr_data, 
    processors=["code_changes"]
)
```

## 🧪 Development Workflow

### Quality Standards

This project follows strict quality standards defined in `CLAUDE.md`:

```bash
# Code formatting
uv run black .

# Linting  
uv run ruff check .

# Testing
uv run pytest

# Complete quality check
uv run black . && uv run ruff check . && uv run pytest
```

### Adding New Components

1. **Create Extractor**: Implement `BaseExtractor` interface
2. **Create Processor**: Implement `BaseProcessor` interface  
3. **Add Models**: Create Pydantic model for external data, dataclass for results
4. **Write Tests**: Ensure complete isolation testing
5. **Update Coordinator**: Register new components

### Testing Philosophy

- **Unit Tests**: Each processor tested in complete isolation
- **Integration Tests**: End-to-end workflow testing
- **Mock Data**: No external API calls in tests
- **Component Isolation**: Verify no context bleeding between components

## 📊 Data Extraction & Analysis Capabilities

### 📋 **Metadata Details**
- **title**: PR title text and quality analysis
- **author**: Username of PR creator
- **state**: Current status (open, closed, merged)
- **pr_number**: Unique PR identifier
- **labels**: Tags/categories applied to the PR
- **assignees**: Users assigned to handle the PR
- **milestone**: Project milestone association
- **created_at/updated_at/merged_at**: Timestamp tracking
- **url**: Direct link to the PR
- **description**: Full PR description content and structure analysis

### 🔧 **Code Changes Analysis**
- **total_additions/deletions**: Line count statistics
- **total_changes**: Combined modification count
- **changed_files**: Number of files affected
- **file_diffs**: Detailed patch content for each file
- **base_sha/head_sha**: Git commit identifiers
- **file_types**: Breakdown by extension (.js, .py, etc.)
- **file_statuses**: Added, modified, deleted, or renamed files
- **change_patterns**: Detection of tests, config changes, documentation
- **risk_assessment**: Impact and complexity scoring

### 🏢 **Repository Information**
- **name/full_name**: Repository identification
- **owner**: Repository owner/organization
- **is_private**: Public or private repository status  
- **default_branch**: Main development branch
- **language**: Primary programming language
- **languages**: Complete language composition with percentages
- **topics**: Repository tags and categorization
- **base_branch/head_branch**: Source and target branch analysis
- **fork_info**: Fork relationship data

### 💬 **Review & Discussion Data**
- **reviews**: Individual review objects with approval status
- **comments**: Line-by-line review comments with file context
- **requested_reviewers**: Users asked to review
- **approved_by**: List of approving reviewers
- **changes_requested_by**: Reviewers requesting modifications
- **review_state**: APPROVED, CHANGES_REQUESTED, or COMMENTED
- **comment_position**: Line numbers and file paths for comments

### 🧠 **Computed Analysis Results**
- **metadata_quality**: Scoring for title/description completeness
- **title_analysis**: Length, word count, emoji usage, WIP status
- **description_analysis**: Structure, sections, checklists, links
- **label_analysis**: Categorization and completeness scoring
- **change_stats**: Statistical analysis of modifications
- **file_analysis**: File type distribution and size analysis
- **pattern_analysis**: Test coverage, breaking changes, dependencies
- **risk_level**: LOW/MEDIUM/HIGH based on change complexity
- **repo_health**: Repository maintenance and quality indicators
- **language_analysis**: Programming language diversity and distribution
- **branch_analysis**: Naming conventions and merge patterns

## 🔒 Security & Privacy

- **Token Protection**: `.env` files are gitignored to prevent token leakage
- **API Rate Limiting**: Respectful GitHub API usage
- **No Data Storage**: Analysis results are not persisted by default
- **Minimal Permissions**: Requires only read access to public repositories

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes following the quality standards
4. Run quality checks: `uv run black . && uv run ruff check . && uv run pytest`
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- **Python 3.13+** required
- **Type hints** for all functions  
- **Docstrings** for all public methods
- **88 character** line length
- **Double quotes** for strings

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with modern Python tooling: `uv`, `black`, `ruff`, `pytest`
- Designed for GitHub API integration with `PyGithub`
- Type safety provided by `Pydantic` and Python dataclasses
- Follows software engineering best practices for maintainability and testability