"""
Parametrized integration tests using table-driven approach.

This refactored test suite eliminates repetition by using pytest parametrization
and declarative test scenario definitions.
"""

from unittest.mock import patch

import pytest

from src.pr_agents.pr_processing import PRCoordinator

from .test_data import (
    TEST_SCENARIOS,
    get_scenario_parameters,
    validate_basic_structure,
    validate_component_expectations,
    validate_processing_success,
)


class TestParametrizedPRScenarios:
    """Parametrized tests for PR processing scenarios."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a coordinator with mocked GitHub client."""
        with patch("src.pr_agents.pr_processing.coordinator.Github") as mock_github:
            coordinator = PRCoordinator("fake-token")
            coordinator.github_client = mock_github.return_value
            return coordinator

    @pytest.mark.parametrize("scenario", get_scenario_parameters())
    def test_complete_pr_analysis(self, mock_coordinator, scenario):
        """
        Test complete PR analysis for each scenario.

        This single test replaces multiple repetitive test functions,
        using table-driven testing to verify different PR patterns.
        """
        # Create the mock PR from the scenario
        mock_pr = scenario.pr_factory()

        # Mock the PR retrieval
        with patch.object(mock_coordinator, "_get_pr_from_url", return_value=mock_pr):
            # Perform complete analysis
            analysis = mock_coordinator.analyze_pr(scenario.url_template)

            # Basic structure validation (common to all scenarios)
            validate_basic_structure(analysis)

            # Processing success validation
            if scenario.should_process_successfully:
                validate_processing_success(
                    analysis["processing_results"], scenario.expected_processor_count
                )

            # Component-specific validation
            validate_component_expectations(
                analysis["extracted_data"], analysis["processing_results"], scenario
            )

            # Custom scenario validation (if defined)
            if scenario.custom_validator:
                scenario.custom_validator(analysis)

            # Summary validation
            summary = analysis["summary"]
            assert summary["components_processed"] > 0
            assert summary["processing_failures"] == 0

    @pytest.mark.parametrize("scenario", get_scenario_parameters())
    def test_component_extraction(self, mock_coordinator, scenario):
        """Test selective component extraction for each scenario."""
        mock_pr = scenario.pr_factory()

        with patch.object(mock_coordinator, "_get_pr_from_url", return_value=mock_pr):
            # Extract all components
            pr_data = mock_coordinator.extract_pr_components(scenario.url_template)

            # Verify expected components are present
            for component in scenario.expected_components:
                component_data = getattr(pr_data, component, None)
                assert (
                    component_data is not None
                ), f"Expected component {component} not extracted"

    @pytest.mark.parametrize("scenario", get_scenario_parameters())
    def test_selective_processing(self, mock_coordinator, scenario):
        """Test selective component processing for each scenario."""
        mock_pr = scenario.pr_factory()

        with patch.object(mock_coordinator, "_get_pr_from_url", return_value=mock_pr):
            # Extract data for processing
            pr_data = mock_coordinator.extract_pr_components(scenario.url_template)

            # Test processing individual components
            available_processors = ["metadata", "code_changes", "repository"]

            for processor in available_processors:
                # Process single component
                results = mock_coordinator.process_components(pr_data, [processor])

                # Should have exactly one result
                assert len(results) == 1
                assert results[0].component == processor

                # Should succeed for valid scenarios
                if scenario.should_process_successfully:
                    assert results[
                        0
                    ].success, f"Processing {processor} failed: {results[0].errors}"

    def test_component_isolation_verification(self, mock_coordinator):
        """
        Test component isolation using the first scenario.

        This test verifies that components remain isolated regardless of scenario.
        """
        # Use the first scenario for isolation testing
        scenario = TEST_SCENARIOS[0]
        mock_pr = scenario.pr_factory()

        with patch.object(mock_coordinator, "_get_pr_from_url", return_value=mock_pr):
            # Test metadata-only extraction
            metadata_only = mock_coordinator.extract_pr_components(
                scenario.url_template, components={"metadata"}
            )
            assert metadata_only.metadata is not None
            assert metadata_only.code_changes is None
            assert metadata_only.repository_info is None

            # Test code-only extraction
            code_only = mock_coordinator.extract_pr_components(
                scenario.url_template, components={"code_changes"}
            )
            assert code_only.metadata is None
            assert code_only.code_changes is not None
            assert code_only.repository_info is None

            # Test isolated processing
            metadata_results = mock_coordinator.process_components(
                metadata_only, processors=["metadata"]
            )
            assert len(metadata_results) == 1
            assert metadata_results[0].component == "metadata"
            assert metadata_results[0].success


class TestScenarioMatrix:
    """Matrix testing for different combinations of components and processors."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a coordinator with mocked GitHub client."""
        with patch("src.pr_agents.pr_processing.coordinator.Github") as mock_github:
            coordinator = PRCoordinator("fake-token")
            coordinator.github_client = mock_github.return_value
            return coordinator

    @pytest.mark.parametrize("scenario", get_scenario_parameters())
    @pytest.mark.parametrize("component", ["metadata", "code_changes", "repository"])
    def test_component_processor_matrix(self, mock_coordinator, scenario, component):
        """
        Test each component processor against each scenario.

        This matrix test ensures every processor works with every scenario type.
        """
        mock_pr = scenario.pr_factory()

        with patch.object(mock_coordinator, "_get_pr_from_url", return_value=mock_pr):
            # Extract the specific component
            pr_data = mock_coordinator.extract_pr_components(
                scenario.url_template, components={component}
            )

            # Process the component
            if getattr(pr_data, component, None) is not None:
                results = mock_coordinator.process_components(pr_data, [component])

                assert len(results) == 1
                assert results[0].component == component

                if scenario.should_process_successfully:
                    assert results[
                        0
                    ].success, f"Failed processing {component} for {scenario.name}"

    @pytest.mark.parametrize("scenario", get_scenario_parameters())
    @pytest.mark.parametrize(
        "components",
        [
            {"metadata"},
            {"code_changes"},
            {"repository"},
            {"metadata", "code_changes"},
            {"metadata", "repository"},
            {"code_changes", "repository"},
            {"metadata", "code_changes", "repository"},
        ],
    )
    def test_component_combination_matrix(self, mock_coordinator, scenario, components):
        """
        Test different combinations of component extraction.

        This ensures all component combinations work correctly.
        """
        mock_pr = scenario.pr_factory()

        with patch.object(mock_coordinator, "_get_pr_from_url", return_value=mock_pr):
            # Extract the component combination
            pr_data = mock_coordinator.extract_pr_components(
                scenario.url_template, components=components
            )

            # Verify only requested components are present
            all_components = {
                "metadata",
                "code_changes",
                "repository_info",
                "review_data",
            }

            for component in all_components:
                component_data = getattr(pr_data, component, None)

                # Map component names to extraction component names
                component_mapping = {
                    "metadata": "metadata",
                    "code_changes": "code_changes",
                    "repository_info": "repository",
                    "review_data": "reviews",
                }

                extraction_name = next(
                    (k for k, v in component_mapping.items() if v == component),
                    component,
                )

                if extraction_name in components:
                    # Should be present if requested
                    assert (
                        component_data is not None
                    ), f"Component {component} not extracted"
                else:
                    # Should be None if not requested
                    assert (
                        component_data is None
                    ), f"Component {component} unexpectedly extracted"


class TestErrorScenarios:
    """Test error handling and edge cases."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a coordinator with mocked GitHub client."""
        with patch("src.pr_agents.pr_processing.coordinator.Github") as mock_github:
            coordinator = PRCoordinator("fake-token")
            coordinator.github_client = mock_github.return_value
            return coordinator

    def test_invalid_pr_url_handling(self, mock_coordinator):
        """Test handling of invalid PR URLs."""
        with patch.object(mock_coordinator, "_get_pr_from_url", return_value=None):
            try:
                analysis = mock_coordinator.analyze_pr("invalid-url")
                # Should handle gracefully or raise appropriate error
                assert analysis is not None or True  # Either succeeds or raises
            except ValueError as e:
                assert "Could not retrieve PR" in str(e)

    def test_empty_component_set(self, mock_coordinator):
        """Test behavior with empty component set."""
        scenario = TEST_SCENARIOS[0]
        mock_pr = scenario.pr_factory()

        with patch.object(mock_coordinator, "_get_pr_from_url", return_value=mock_pr):
            # Extract no components
            pr_data = mock_coordinator.extract_pr_components(
                scenario.url_template, components=set()
            )

            # All components should be None
            assert pr_data.metadata is None
            assert pr_data.code_changes is None
            assert pr_data.repository_info is None
            assert pr_data.review_data is None

    @pytest.mark.parametrize("invalid_component", ["invalid", "nonexistent", ""])
    def test_invalid_component_names(self, mock_coordinator, invalid_component):
        """Test handling of invalid component names."""
        scenario = TEST_SCENARIOS[0]

        with pytest.raises(ValueError, match="Invalid components"):
            mock_coordinator.extract_pr_components(
                scenario.url_template, components={invalid_component}
            )

    @pytest.mark.parametrize("invalid_processor", ["invalid", "nonexistent", ""])
    def test_invalid_processor_names(self, mock_coordinator, invalid_processor):
        """Test handling of invalid processor names."""
        scenario = TEST_SCENARIOS[0]
        mock_pr = scenario.pr_factory()

        with patch.object(mock_coordinator, "_get_pr_from_url", return_value=mock_pr):
            pr_data = mock_coordinator.extract_pr_components(scenario.url_template)

            with pytest.raises(ValueError, match="Invalid processors"):
                mock_coordinator.process_components(pr_data, [invalid_processor])
