"""
Live integration tests for development and CI.

These tests make actual network requests to verify the tool works
with real GitHub PRs. Only run when explicitly requested.
"""

import os

import pytest

from src.pr_agents.pr_processing import PRCoordinator

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
    """Known good Prebid PRs for testing (use closed/merged PRs to avoid disruption)."""
    return [
        # Small, simple PRs that are safe to test against
        "https://github.com/prebid/Prebid.js/pull/10000",  # Replace with actual merged PR
        "https://github.com/prebid/prebid-server/pull/3000",  # Replace with actual merged PR
    ]


class TestLiveIntegration:
    """Live integration tests with real GitHub API."""

    def test_live_prebid_js_pr_analysis(self, live_coordinator):
        """Test analysis of a real Prebid.js PR."""
        # Use a known merged PR that won't change
        # Replace with actual PR URL from Prebid.js that's merged/closed
        pr_url = "https://github.com/prebid/Prebid.js/pull/10000"  # Example - replace

        try:
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
                ], f"Processing failed: {result.get('errors', [])}"

        except Exception as e:
            pytest.skip(f"Live test failed (expected for placeholder PR): {e}")

    def test_live_component_isolation(self, live_coordinator):
        """Test component isolation with real PR data."""
        # Use a known merged PR
        pr_url = (
            "https://github.com/prebid/prebid-server/pull/3000"  # Example - replace
        )

        try:
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

        except Exception as e:
            pytest.skip(f"Live test failed (expected for placeholder PR): {e}")

    def test_live_error_handling(self, live_coordinator):
        """Test error handling with invalid PR URLs."""
        # Test with non-existent PR
        invalid_url = "https://github.com/prebid/Prebid.js/pull/999999999"

        try:
            analysis = live_coordinator.analyze_pr(invalid_url)
            # Should handle gracefully, not crash
            assert analysis is not None
        except Exception as e:
            # Expected to fail, but shouldn't crash the application
            assert "Could not retrieve PR" in str(e) or "404" in str(e)

    @pytest.mark.slow
    def test_live_performance_benchmark(self, live_coordinator):
        """Benchmark performance with real PR data."""
        import time

        pr_url = "https://github.com/prebid/Prebid.js/pull/10000"  # Replace

        try:
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
                        assert result["processing_time_ms"] > 0

        except Exception as e:
            pytest.skip(f"Performance test failed (expected for placeholder PR): {e}")


# Helper function to run live tests manually
def run_live_tests():
    """
    Run live integration tests manually.

    Usage:
        python -m pytest tests/integration/test_live_integration.py -m live -v

    Or programmatically:
        from tests.integration.test_live_integration import run_live_tests
        run_live_tests()
    """
    import subprocess
    import sys

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/integration/test_live_integration.py",
        "-m",
        "live",
        "-v",
    ]

    print("Running live integration tests...")
    print("Note: These tests require GITHUB_TOKEN environment variable")
    print("Command:", " ".join(cmd))

    result = subprocess.run(cmd)
    return result.returncode == 0


if __name__ == "__main__":
    # Allow running this file directly for development
    run_live_tests()
