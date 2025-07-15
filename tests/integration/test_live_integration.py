"""
Live integration tests for development and CI.

These tests make actual network requests to verify the tool works
with real GitHub PRs. Only run when explicitly requested.

To update test PR URLs with real merged PRs, use:
    gh pr list --repo prebid/Prebid.js --state merged --limit 10
    gh pr list --repo prebid/prebid-server --state merged --limit 10
    gh pr list --repo prebid/prebid.github.io --state merged --limit 10

Run tests with:
    python -m pytest tests/integration/test_live_integration.py -m live -v
"""

import os

import pytest

from src.pr_agents.pr_processing import PRCoordinator
from tests.utils import get_prebid_test_prs, run_live_integration_tests

# Mark all tests in this module as requiring live network access
pytestmark = pytest.mark.live


@pytest.fixture
def live_coordinator():
    """Create coordinator with real GitHub token for live testing."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN not set - skipping live integration tests")

    return PRCoordinator(token)


@pytest.fixture
def prebid_test_prs():
    """
    Known good Prebid PRs for testing (use closed/merged PRs to avoid disruption).

    Returns the standard set of test PRs defined in tests.utils module.

    To update these URLs with real merged PRs, see tests.utils.get_prebid_test_prs()
    and use the GitHub CLI commands documented there.

    Choose PRs that are:
    - Merged (stable, won't change)
    - Not too large (< 1000 lines changed)
    - Have good metadata (title, description, labels)
    - Representative of different change types
    """
    return get_prebid_test_prs()


class TestLiveIntegration:
    """Live integration tests with real GitHub API."""

    @pytest.mark.parametrize(
        "pr_type,pr_url",
        [
            ("small_js_feature", "https://github.com/prebid/Prebid.js/pull/10000"),
            ("medium_server_fix", "https://github.com/prebid/prebid-server/pull/3000"),
        ],
    )
    def test_live_pr_analysis(self, live_coordinator, pr_type, pr_url):
        """Test analysis of real Prebid PRs of different types."""
        # Note: Update these URLs with actual merged PRs using:
        # gh pr list --repo prebid/Prebid.js --state merged --limit 10

        analysis = live_coordinator.analyze_pr(pr_url)

        # Basic structure validation
        assert "extracted_data" in analysis
        assert "processing_results" in analysis
        assert "summary" in analysis

        # Should successfully extract metadata
        extracted = analysis["extracted_data"]
        if "metadata" in extracted:
            metadata = extracted["metadata"]
            assert metadata["title"]
            assert metadata["author"]
            assert isinstance(metadata["pr_number"], int)

        # Processing should succeed
        for result in analysis["processing_results"]:
            assert result[
                "success"
            ], f"Processing failed for {pr_type}: {result.get('errors', [])}"

    def test_live_component_isolation(self, live_coordinator, prebid_test_prs):
        """Test component isolation with real PR data."""
        # Use a real merged PR from our test set
        pr_url = prebid_test_prs["medium_server_fix"]

        # Test selective extraction
        metadata_only = live_coordinator.extract_pr_components(
            pr_url, components={"metadata"}
        )

        assert metadata_only.metadata is not None
        assert metadata_only.code_changes is None
        assert metadata_only.repository_info is None

        # Test selective processing
        code_only = live_coordinator.extract_pr_components(
            pr_url, components={"code_changes"}
        )

        if code_only.code_changes:
            results = live_coordinator.process_components(
                code_only, processors=["code_changes"]
            )
            assert len(results) == 1
            assert results[0].component == "code_changes"

    def test_live_error_handling(self, live_coordinator):
        """Test error handling with invalid PR URLs."""
        # Test with non-existent PR
        invalid_url = "https://github.com/prebid/Prebid.js/pull/999999999"

        # Should raise a clear ValueError for invalid PRs
        with pytest.raises(ValueError, match="Could not retrieve PR"):
            live_coordinator.analyze_pr(invalid_url)

    def test_live_multiple_pr_types(self, live_coordinator, prebid_test_prs):
        """Test analysis across different types of real PRs."""
        results = {}

        for pr_type, pr_url in prebid_test_prs.items():
            try:
                analysis = live_coordinator.analyze_pr(pr_url)

                # Verify basic structure
                assert "extracted_data" in analysis
                assert "processing_results" in analysis
                assert "summary" in analysis

                # Store results for comparison
                results[pr_type] = {
                    "success": True,
                    "components_extracted": len(
                        analysis["summary"]["components_extracted"]
                    ),
                    "processing_time": analysis["summary"]["total_processing_time_ms"],
                }

            except ValueError as e:
                if "Could not retrieve PR" in str(e):
                    pytest.skip(f"PR {pr_type} no longer accessible: {pr_url}")
                raise  # Re-raise other ValueErrors

        # Verify we tested at least one PR successfully
        assert len(results) > 0, "No PRs were successfully tested"

        # All successful analyses should have extracted some components
        for pr_type, result in results.items():
            assert result["success"], f"Analysis failed for {pr_type}"
            assert (
                result["components_extracted"] > 0
            ), f"No components extracted for {pr_type}"

    @pytest.mark.slow
    def test_live_performance_benchmark(self, live_coordinator, prebid_test_prs):
        """Benchmark performance with real PR data."""
        import time

        # Use a real PR for performance testing
        pr_url = prebid_test_prs["small_js_feature"]

        start_time = time.time()
        analysis = live_coordinator.analyze_pr(pr_url)
        end_time = time.time()

        processing_time = end_time - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 30.0, f"Analysis took too long: {processing_time}s"

        # Verify timing information is captured
        if analysis["processing_results"]:
            for result in analysis["processing_results"]:
                if result["success"]:
                    assert "processing_time_ms" in result
                    assert result["processing_time_ms"] >= 0  # Allow 0ms for very fast operations


if __name__ == "__main__":
    # Allow running this file directly for development
    success = run_live_integration_tests()
    if not success:
        exit(1)
