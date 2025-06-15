"""
Test scenario definitions for parametrized testing.

This module defines test scenarios in a table-driven approach to eliminate
repetition and make tests easier to maintain and extend.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from ..fixtures import PrebidPRScenarios
from ..fixtures.mock_github import MockPullRequest


@dataclass
class ComponentExpectation:
    """Expected results for a specific component analysis."""

    should_exist: bool = True
    expected_fields: set[str] | None = None
    assertions: dict[str, Any] | None = None


@dataclass
class PRTestScenario:
    """
    Complete test scenario definition for parametrized testing.

    This structure eliminates repetition by defining expected outcomes
    for each PR scenario in a declarative way.
    """

    id: str  # Test ID for pytest
    name: str  # Human readable name
    pr_factory: Callable[[], MockPullRequest]  # Function to create the PR
    url_template: str  # URL template for the test

    # Expected extraction results
    expected_components: set[str]  # Which components should be extracted

    # Component-specific expectations
    metadata_expectations: ComponentExpectation | None = None
    code_expectations: ComponentExpectation | None = None
    repo_expectations: ComponentExpectation | None = None

    # Processing expectations
    should_process_successfully: bool = True
    expected_processor_count: int = 3  # metadata, code_changes, repository

    # Custom validation function (optional)
    custom_validator: Callable[[dict[str, Any]], None] | None = None


# Define validation helper functions
def validate_javascript_adapter(analysis_result: dict[str, Any]) -> None:
    """Validate JavaScript adapter PR analysis."""
    # Check that JavaScript files are detected
    code_result = next(
        r
        for r in analysis_result["processing_results"]
        if r["component"] == "code_changes"
    )
    file_analysis = code_result["data"]["file_analysis"]
    assert file_analysis["file_types"].get("js", 0) > 0

    # Should detect tests
    pattern_analysis = code_result["data"]["pattern_analysis"]
    assert pattern_analysis["has_tests"]


def validate_go_infrastructure(analysis_result: dict[str, Any]) -> None:
    """Validate Go infrastructure PR analysis."""
    # Check Go files detected
    code_result = next(
        r
        for r in analysis_result["processing_results"]
        if r["component"] == "code_changes"
    )
    file_analysis = code_result["data"]["file_analysis"]
    assert file_analysis["file_types"].get("go", 0) > 0

    # Should detect config changes
    pattern_analysis = code_result["data"]["pattern_analysis"]
    assert pattern_analysis["has_config_changes"]

    # Repository should be categorized as backend
    repo_result = next(
        r
        for r in analysis_result["processing_results"]
        if r["component"] == "repository"
    )
    language_analysis = repo_result["data"]["language_analysis"]
    assert "backend" in language_analysis["repo_categories"]


def validate_mobile_ios(analysis_result: dict[str, Any]) -> None:
    """Validate iOS mobile PR analysis."""
    # Check Swift files
    code_result = next(
        r
        for r in analysis_result["processing_results"]
        if r["component"] == "code_changes"
    )
    file_analysis = code_result["data"]["file_analysis"]
    assert file_analysis["file_types"].get("swift", 0) > 0

    # Repository should be mobile
    repo_result = next(
        r
        for r in analysis_result["processing_results"]
        if r["component"] == "repository"
    )
    language_analysis = repo_result["data"]["language_analysis"]
    assert "mobile" in language_analysis["repo_categories"]


def validate_documentation(analysis_result: dict[str, Any]) -> None:
    """Validate documentation PR analysis."""
    # Should have markdown files
    code_result = next(
        r
        for r in analysis_result["processing_results"]
        if r["component"] == "code_changes"
    )
    file_analysis = code_result["data"]["file_analysis"]
    assert file_analysis["file_types"].get("md", 0) > 0

    # Risk should be low
    risk_assessment = code_result["data"]["risk_assessment"]
    assert risk_assessment["risk_level"] in ["minimal", "low"]


def validate_security_update(analysis_result: dict[str, Any]) -> None:
    """Validate security PR analysis."""
    # Should detect dependencies
    code_result = next(
        r
        for r in analysis_result["processing_results"]
        if r["component"] == "code_changes"
    )
    pattern_analysis = code_result["data"]["pattern_analysis"]
    assert pattern_analysis["has_dependencies"]

    # Should have security labels
    metadata_result = next(
        r for r in analysis_result["processing_results"] if r["component"] == "metadata"
    )
    label_analysis = metadata_result["data"]["label_analysis"]
    has_security_label = any(
        "security" in label.lower()
        for category_labels in label_analysis["categorized"].values()
        for label in category_labels
    )
    assert has_security_label


# Define test scenarios
TEST_SCENARIOS = [
    PRTestScenario(
        id="js_adapter",
        name="JavaScript Adapter PR",
        pr_factory=PrebidPRScenarios.prebid_js_adapter_pr,
        url_template="https://github.com/prebid/Prebid.js/pull/123",
        expected_components={
            "metadata",
            "code_changes",
            "repository_info",
            "review_data",
        },
        metadata_expectations=ComponentExpectation(
            expected_fields={"title", "author", "labels"},
            assertions={
                "title": "Zeta SSP Adapter: add GPP support",
                "author": "adapter-developer",
                "has_adapter_label": True,
            },
        ),
        code_expectations=ComponentExpectation(
            expected_fields={"changed_files", "total_additions", "file_diffs"},
            assertions={
                "changed_files": 2,
                "total_additions": 70,
                "has_js_files": True,
            },
        ),
        custom_validator=validate_javascript_adapter,
    ),
    PRTestScenario(
        id="go_infrastructure",
        name="Go Infrastructure PR",
        pr_factory=PrebidPRScenarios.prebid_server_go_infrastructure,
        url_template="https://github.com/prebid/prebid-server/pull/456",
        expected_components={"metadata", "code_changes", "repository_info"},
        metadata_expectations=ComponentExpectation(
            assertions={
                "has_security_label": True,
                "has_enhancement_label": True,
            }
        ),
        code_expectations=ComponentExpectation(
            assertions={
                "has_go_files": True,
                "has_config_changes": True,
            }
        ),
        custom_validator=validate_go_infrastructure,
    ),
    PRTestScenario(
        id="ios_mobile",
        name="iOS Mobile Feature PR",
        pr_factory=PrebidPRScenarios.prebid_mobile_ios_feature,
        url_template="https://github.com/prebid/prebid-mobile-ios/pull/789",
        expected_components={"metadata", "code_changes", "repository_info"},
        metadata_expectations=ComponentExpectation(
            assertions={
                "has_mobile_theme": True,
                "has_enhancement_label": True,
            }
        ),
        code_expectations=ComponentExpectation(
            assertions={
                "has_swift_files": True,
                "has_tests": True,
            }
        ),
        custom_validator=validate_mobile_ios,
    ),
    PRTestScenario(
        id="documentation",
        name="Documentation Update PR",
        pr_factory=PrebidPRScenarios.documentation_update,
        url_template="https://github.com/prebid/prebid.github.io/pull/101",
        expected_components={"metadata", "code_changes", "repository_info"},
        metadata_expectations=ComponentExpectation(
            assertions={
                "has_doc_label": True,
            }
        ),
        code_expectations=ComponentExpectation(
            assertions={
                "has_markdown_files": True,
                "low_risk": True,
            }
        ),
        custom_validator=validate_documentation,
    ),
    PRTestScenario(
        id="security_update",
        name="Security Update PR",
        pr_factory=PrebidPRScenarios.universal_creative_security,
        url_template="https://github.com/prebid/prebid-universal-creative/pull/55",
        expected_components={"metadata", "code_changes", "repository_info"},
        metadata_expectations=ComponentExpectation(
            assertions={
                "has_security_label": True,
                "has_critical_label": True,
            }
        ),
        code_expectations=ComponentExpectation(
            assertions={
                "has_dependency_changes": True,
            }
        ),
        custom_validator=validate_security_update,
    ),
]


# Pytest parameter generator
def get_scenario_parameters():
    """Generate pytest parameters from test scenarios."""
    return [pytest.param(scenario, id=scenario.id) for scenario in TEST_SCENARIOS]


# Helper functions for common test patterns
def extract_component_result(
    processing_results: list, component: str
) -> dict[str, Any]:
    """Extract results for a specific component."""
    return next((r for r in processing_results if r["component"] == component), None)


def validate_basic_structure(analysis: dict[str, Any]) -> None:
    """Validate basic analysis structure."""
    assert "extracted_data" in analysis
    assert "processing_results" in analysis
    assert "summary" in analysis


def validate_processing_success(
    processing_results: list, expected_count: int = 3
) -> None:
    """Validate that all processing succeeded."""
    assert len(processing_results) == expected_count
    for result in processing_results:
        assert result["success"], f"Processing failed: {result.get('errors', [])}"


def validate_component_expectations(
    extracted_data: dict[str, Any], processing_results: list, scenario: PRTestScenario
) -> None:
    """Validate component-specific expectations."""
    # Validate metadata expectations
    if scenario.metadata_expectations and "metadata" in extracted_data:
        metadata = extracted_data["metadata"]
        expectations = scenario.metadata_expectations

        if expectations.expected_fields:
            for field in expectations.expected_fields:
                assert field in metadata, f"Missing expected field: {field}"

        if expectations.assertions:
            assertions = expectations.assertions
            if "title" in assertions:
                assert metadata["title"] == assertions["title"]
            if "author" in assertions:
                assert metadata["author"] == assertions["author"]
            if "has_adapter_label" in assertions:
                labels = metadata["labels"]
                assert "adapter" in labels

    # Validate code expectations
    if scenario.code_expectations:
        code_result = extract_component_result(processing_results, "code_changes")
        if code_result:
            expectations = scenario.code_expectations

            if expectations.assertions:
                assertions = expectations.assertions
                if "changed_files" in assertions:
                    extracted_code = extracted_data.get("code_changes", {})
                    assert (
                        extracted_code.get("changed_files")
                        == assertions["changed_files"]
                    )

                if "has_js_files" in assertions:
                    file_analysis = code_result["data"]["file_analysis"]
                    assert file_analysis["file_types"].get("js", 0) > 0
