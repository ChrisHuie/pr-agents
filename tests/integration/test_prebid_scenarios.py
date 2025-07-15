"""
Integration tests using realistic Prebid organization PR patterns.

These tests verify the entire PR processing pipeline using mock PRs
based on real patterns from Prebid repositories.
"""

from unittest.mock import patch

import pytest

from src.pr_agents.pr_processing import PRCoordinator

from ..fixtures import PrebidPRScenarios


class TestPrebidPRScenarios:
    """Test PR processing with realistic Prebid scenarios."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a coordinator with mocked GitHub client."""
        with patch("src.pr_agents.pr_processing.coordinator.Github") as mock_github:
            coordinator = PRCoordinator("fake-token")
            # Mock the GitHub client to avoid network calls
            coordinator.github_client = mock_github.return_value
            return coordinator

    def test_prebid_js_adapter_analysis(self, mock_coordinator):
        """Test analysis of a typical Prebid.js adapter PR."""
        # Get realistic PR scenario
        mock_pr = PrebidPRScenarios.prebid_js_adapter_pr()

        # Mock the PR retrieval
        with patch.object(
            mock_coordinator.single_pr_coordinator,
            "_get_pr_from_url",
            return_value=mock_pr,
        ):
            # Extract and analyze the PR
            pr_data = mock_coordinator.extract_pr_components(
                "https://github.com/prebid/Prebid.js/pull/123"
            )

            # Verify extraction worked
            assert pr_data.metadata is not None
            assert pr_data.code_changes is not None
            assert pr_data.repository_info is not None

            # Check metadata extraction
            metadata = pr_data.metadata
            assert metadata["title"] == "Zeta SSP Adapter: add GPP support"
            assert metadata["author"] == "adapter-developer"
            assert "adapter" in metadata["labels"]

            # Check code changes extraction
            code_changes = pr_data.code_changes
            assert code_changes["changed_files"] == 2
            assert code_changes["total_additions"] == 70  # 45 + 25
            assert len(code_changes["file_diffs"]) == 2

            # Verify JavaScript files are detected
            js_files = [
                f for f in code_changes["file_diffs"] if f["filename"].endswith(".js")
            ]
            assert len(js_files) == 2

            # Process the extracted data
            results = mock_coordinator.process_components(pr_data)

            # Verify processing results
            assert len(results) == 3  # metadata, code_changes, repository

            # Check metadata processing
            metadata_result = next(r for r in results if r.component == "metadata")
            assert metadata_result.success

            title_analysis = metadata_result.data["title_analysis"]
            assert title_analysis["length"] > 20
            assert title_analysis["word_count"] >= 4

            # Check code processing
            code_result = next(r for r in results if r.component == "code_changes")
            assert code_result.success

            pattern_analysis = code_result.data["pattern_analysis"]
            assert pattern_analysis["has_tests"]  # Has test file

            risk_assessment = code_result.data["risk_assessment"]
            assert risk_assessment["risk_level"] in ["minimal", "low", "medium"]

    def test_prebid_server_infrastructure_analysis(self, mock_coordinator):
        """Test analysis of Go-based infrastructure changes."""
        mock_pr = PrebidPRScenarios.prebid_server_go_infrastructure()

        with patch.object(
            mock_coordinator.single_pr_coordinator,
            "_get_pr_from_url",
            return_value=mock_pr,
        ):
            # Analyze the infrastructure PR
            analysis = mock_coordinator.analyze_pr(
                "https://github.com/prebid/prebid-server/pull/456"
            )

            # Verify complete analysis structure
            assert "extracted_data" in analysis
            assert "processing_results" in analysis
            assert "summary" in analysis

            # Check repository analysis for Go project
            repo_result = next(
                (
                    r
                    for r in analysis["processing_results"]
                    if r["component"] == "repository"
                ),
                None,
            )
            assert repo_result is not None
            assert repo_result["success"]

            language_analysis = repo_result["data"]["language_analysis"]
            assert language_analysis["primary_language"] == "Go"
            assert "backend" in language_analysis["repo_categories"]

            # Check code analysis for infrastructure changes
            code_result = next(
                (
                    r
                    for r in analysis["processing_results"]
                    if r["component"] == "code_changes"
                ),
                None,
            )
            assert code_result is not None

            file_analysis = code_result["data"]["file_analysis"]
            go_files = file_analysis["file_types"].get("go", 0)
            assert go_files > 0

            # Should detect configuration changes
            pattern_analysis = code_result["data"]["pattern_analysis"]
            assert pattern_analysis["has_config_changes"]

    def test_mobile_ios_feature_analysis(self, mock_coordinator):
        """Test analysis of iOS mobile feature implementation."""
        mock_pr = PrebidPRScenarios.prebid_mobile_ios_feature()

        with patch.object(
            mock_coordinator.single_pr_coordinator,
            "_get_pr_from_url",
            return_value=mock_pr,
        ):
            pr_data = mock_coordinator.extract_pr_components(
                "https://github.com/prebid/prebid-mobile-ios/pull/789",
                components={"metadata", "code_changes", "repository"},
            )

            # Verify mobile-specific patterns
            metadata = pr_data.metadata
            assert "landscape" in metadata["title"].lower()
            assert "mobile" in metadata["labels"]

            # Check Swift file detection
            code_changes = pr_data.code_changes
            swift_files = [
                f
                for f in code_changes["file_diffs"]
                if f["filename"].endswith(".swift")
            ]
            assert len(swift_files) >= 2

            # Process and verify mobile-specific analysis
            results = mock_coordinator.process_components(pr_data)

            # Check repository categorization for mobile
            repo_result = next(r for r in results if r.component == "repository")
            language_analysis = repo_result.data["language_analysis"]
            assert language_analysis["primary_language"] == "Swift"
            assert "mobile" in language_analysis["repo_categories"]

            # Verify test file detection
            code_result = next(r for r in results if r.component == "code_changes")
            pattern_analysis = code_result.data["pattern_analysis"]
            assert pattern_analysis["has_tests"]

    def test_documentation_pr_analysis(self, mock_coordinator):
        """Test analysis of documentation-only PRs."""
        mock_pr = PrebidPRScenarios.documentation_update()

        with patch.object(
            mock_coordinator.single_pr_coordinator,
            "_get_pr_from_url",
            return_value=mock_pr,
        ):
            analysis = mock_coordinator.analyze_pr(
                "https://github.com/prebid/prebid.github.io/pull/101"
            )

            # Documentation PRs should have specific characteristics
            metadata_result = next(
                r
                for r in analysis["processing_results"]
                if r["component"] == "metadata"
            )

            # Check basic metadata processing succeeded
            assert metadata_result["success"]
            # The PR title should contain "documentation" or "doc"
            extracted_data = analysis["extracted_data"]
            if "metadata" in extracted_data and extracted_data["metadata"]:
                title = extracted_data["metadata"].get("title", "")
                assert "doc" in title.lower() or "documentation" in title.lower()

            # Code analysis should reflect documentation patterns
            code_result = next(
                r
                for r in analysis["processing_results"]
                if r["component"] == "code_changes"
            )

            file_analysis = code_result["data"]["file_analysis"]
            # Should have markdown files
            md_files = file_analysis["file_types"].get("md", 0)
            assert md_files > 0

            # Risk should be low for documentation
            risk_assessment = code_result["data"]["risk_assessment"]
            assert risk_assessment["risk_level"] in ["minimal", "low"]

    def test_security_update_analysis(self, mock_coordinator):
        """Test analysis of security-focused PRs."""
        mock_pr = PrebidPRScenarios.universal_creative_security()

        with patch.object(
            mock_coordinator.single_pr_coordinator,
            "_get_pr_from_url",
            return_value=mock_pr,
        ):
            analysis = mock_coordinator.analyze_pr(
                "https://github.com/prebid/prebid-universal-creative/pull/55"
            )

            # Security PRs should be detected appropriately
            metadata_result = next(
                r
                for r in analysis["processing_results"]
                if r["component"] == "metadata"
            )

            # Should have security-related labels
            label_analysis = metadata_result["data"]["label_analysis"]
            has_security_label = any(
                "security" in label.lower()
                for category_labels in label_analysis["categorized"].values()
                for label in category_labels
            )
            assert has_security_label

            # Code analysis should detect security patterns
            code_result = next(
                r
                for r in analysis["processing_results"]
                if r["component"] == "code_changes"
            )

            # Should detect dependency changes
            pattern_analysis = code_result["data"]["pattern_analysis"]
            assert pattern_analysis["has_dependencies"]

            # Should have appropriate risk level for security changes
            risk_assessment = code_result["data"]["risk_assessment"]
            # Security updates can be medium risk due to importance
            assert risk_assessment["risk_level"] in ["low", "medium"]

    def test_all_scenarios_complete_analysis(self, mock_coordinator):
        """Test that all scenarios can be processed without errors."""
        scenarios = PrebidPRScenarios.get_all_scenarios()

        for i, mock_pr in enumerate(scenarios):
            with patch.object(
                mock_coordinator.single_pr_coordinator,
                "_get_pr_from_url",
                return_value=mock_pr,
            ):
                # Each scenario should process successfully
                analysis = mock_coordinator.analyze_pr(
                    f"https://github.com/test/repo/pull/{i}"
                )

                # Basic structure validation
                assert "extracted_data" in analysis
                assert "processing_results" in analysis
                assert "summary" in analysis

                # All processing should succeed
                for result in analysis["processing_results"]:
                    assert result[
                        "success"
                    ], f"Processing failed for {mock_pr.title}: {result.get('errors', [])}"

                # Should have meaningful insights
                summary = analysis["summary"]
                assert summary["components_processed"] > 0
                assert summary["processing_failures"] == 0

    def test_component_isolation_verification(self, mock_coordinator):
        """Verify that component isolation is maintained across scenarios."""
        # Test with adapter PR that has both metadata and code changes
        mock_pr = PrebidPRScenarios.prebid_js_adapter_pr()

        with patch.object(
            mock_coordinator.single_pr_coordinator,
            "_get_pr_from_url",
            return_value=mock_pr,
        ):
            # Extract only metadata - should not see code changes
            metadata_only = mock_coordinator.extract_pr_components(
                "https://github.com/prebid/Prebid.js/pull/123", components={"metadata"}
            )

            assert metadata_only.metadata is not None
            assert metadata_only.code_changes is None
            assert metadata_only.repository_info is None

            # Extract only code changes - should not see metadata
            code_only = mock_coordinator.extract_pr_components(
                "https://github.com/prebid/Prebid.js/pull/123",
                components={"code_changes"},
            )

            assert code_only.metadata is None
            assert code_only.code_changes is not None
            assert code_only.repository_info is None

            # Process metadata in isolation
            metadata_results = mock_coordinator.process_components(
                metadata_only, processors=["metadata"]
            )

            # Should only have metadata processing result
            assert len(metadata_results) == 1
            assert metadata_results[0].component == "metadata"
            assert metadata_results[0].success

            # The metadata processor should never have seen code changes
            # This verifies true isolation
