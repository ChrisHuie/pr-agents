# Testing Guide

This document explains the testing strategy and how to run different types of tests.

## Test Structure

```
tests/
├── pr_processing/               # Unit tests for individual components
│   └── test_processors.py     # Original unit tests
├── integration/                # Integration tests
│   ├── test_prebid_scenarios.py        # Original repetitive tests (deprecated)
│   ├── test_parametrized_scenarios.py  # NEW: Table-driven tests
│   ├── test_live_integration.py        # Live API tests
│   └── test_data.py                    # Test scenario definitions
└── fixtures/                   # Test data and mocks
    ├── mock_github.py          # Mock GitHub objects
    └── prebid_scenarios.py     # Realistic PR scenarios
```

## Test Types

### 1. Unit Tests
Fast, isolated tests for individual components:
```bash
# Run all unit tests
pytest tests/pr_processing/ -m unit

# Run specific component tests
pytest tests/pr_processing/test_processors.py -v
```

### 2. Parametrized Integration Tests (NEW!)
Table-driven tests that eliminate repetition:
```bash
# Run all parametrized tests
pytest tests/integration/test_parametrized_scenarios.py -m parametrized -v

# Run specific scenario
pytest tests/integration/test_parametrized_scenarios.py::TestParametrizedPRScenarios::test_complete_pr_analysis[js_adapter] -v

# Run matrix tests
pytest tests/integration/test_parametrized_scenarios.py::TestScenarioMatrix -v
```

### 3. Live Integration Tests
Tests against real GitHub API (requires GITHUB_TOKEN):
```bash
# Run live tests
GITHUB_TOKEN=your_token pytest tests/integration/test_live_integration.py -m live -v

# Skip if no token
pytest tests/integration/test_live_integration.py -m live --tb=short
```

## Table-Driven Testing Benefits

### Before (Repetitive)
```python
def test_prebid_js_adapter_analysis(self, mock_coordinator):
    mock_pr = PrebidPRScenarios.prebid_js_adapter_pr()
    with patch.object(mock_coordinator, '_get_pr_from_url', return_value=mock_pr):
        pr_data = mock_coordinator.extract_pr_components("url")
        assert pr_data.metadata is not None
        assert pr_data.code_changes is not None
        # ... 50 lines of repetitive assertions

def test_prebid_server_infrastructure_analysis(self, mock_coordinator):
    mock_pr = PrebidPRScenarios.prebid_server_go_infrastructure()
    with patch.object(mock_coordinator, '_get_pr_from_url', return_value=mock_pr):
        pr_data = mock_coordinator.extract_pr_components("url")
        assert pr_data.metadata is not None  
        assert pr_data.code_changes is not None
        # ... 50 lines of similar repetitive assertions
        
# ... 5 more similar functions
```

### After (Table-Driven)
```python
@pytest.mark.parametrize("scenario", get_scenario_parameters())
def test_complete_pr_analysis(self, mock_coordinator, scenario):
    mock_pr = scenario.pr_factory()
    with patch.object(mock_coordinator, '_get_pr_from_url', return_value=mock_pr):
        analysis = mock_coordinator.analyze_pr(scenario.url_template)
        
        # Common validation for all scenarios
        validate_basic_structure(analysis)
        validate_processing_success(analysis["processing_results"])
        validate_component_expectations(analysis, scenario)
        
        # Scenario-specific validation
        if scenario.custom_validator:
            scenario.custom_validator(analysis)
```

## Adding New Test Scenarios

To add a new test scenario, simply add to `test_data.py`:

```python
TEST_SCENARIOS.append(
    PRTestScenario(
        id="my_new_scenario",
        name="My New PR Type",
        pr_factory=MyNewPRScenarios.my_new_pr,
        url_template="https://github.com/org/repo/pull/123",
        expected_components={"metadata", "code_changes"},
        custom_validator=validate_my_new_pr,
    )
)
```

No need to write new test functions!

## Running Specific Test Categories

```bash
# All tests
pytest

# Only unit tests (fast)
pytest tests/pr_processing/

# Only parametrized integration tests
pytest tests/integration/test_parametrized_scenarios.py

# Only live tests (slow, requires token)
pytest tests/integration/test_live_integration.py -m live

# All integration tests (no live)
pytest tests/integration/ -m "not live"

# Matrix tests for thorough coverage
pytest tests/integration/test_parametrized_scenarios.py::TestScenarioMatrix

# Specific scenario across all test types
pytest -k "js_adapter"
```

## Test Performance

| Test Type | Count | Time | Network |
|-----------|-------|------|---------|
| Unit | 6 tests | ~0.2s | No |
| Parametrized | 15+ tests | ~1.0s | No |
| Matrix | 35+ tests | ~2.0s | No |
| Live | 4 tests | ~10s | Yes |

## Quality Assurance

Always run the full test suite before committing:
```bash
# Full quality check
uv run black . && uv run ruff check . && uv run pytest
```