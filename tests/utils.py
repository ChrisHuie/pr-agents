"""
Test utilities for the PR agents test suite.

This module contains reusable helper functions and utilities that can be
shared across different test modules to improve maintainability and reduce
code duplication.
"""

import subprocess
import sys


def verify_pr_urls(pr_urls: dict[str, str]) -> None:
    """
    Verify that test PR URLs are still valid and accessible.

    This utility function checks if the provided GitHub PR URLs are still
    accessible via the GitHub API. Useful for maintaining live integration
    tests that depend on real PRs.

    Args:
        pr_urls: Dictionary mapping PR type names to GitHub PR URLs

    Example:
        >>> test_prs = {
        ...     "small_feature": "https://github.com/owner/repo/pull/123",
        ...     "large_refactor": "https://github.com/owner/repo/pull/456"
        ... }
        >>> verify_pr_urls(test_prs)
        ✅ small_feature: https://github.com/owner/repo/pull/123 - Fix auth bug (merged)
        ✅ large_refactor: https://github.com/owner/repo/pull/456 - Refactor API (closed)
    """
    import requests

    for pr_type, url in pr_urls.items():
        # Convert GitHub URL to API URL
        api_url = url.replace("github.com", "api.github.com/repos").replace(
            "/pull/", "/pulls/"
        )

        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                pr_data = response.json()
                print(f"✅ {pr_type}: {url} - {pr_data['title']} ({pr_data['state']})")
            else:
                print(f"❌ {pr_type}: {url} - HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {pr_type}: {url} - Error: {e}")


def run_pytest_with_markers(
    *markers: str, test_path: str = ".", verbose: bool = True
) -> bool:
    """
    Run pytest with specific markers programmatically.

    Args:
        *markers: Pytest markers to include (e.g., "live", "integration")
        test_path: Path to test files/directories
        verbose: Whether to run in verbose mode

    Returns:
        True if tests passed, False otherwise

    Example:
        >>> # Run live integration tests
        >>> success = run_pytest_with_markers("live", test_path="tests/integration/")
        >>> print(f"Tests {'passed' if success else 'failed'}")
    """
    cmd = [sys.executable, "-m", "pytest"]

    if markers:
        for marker in markers:
            cmd.extend(["-m", marker])

    if verbose:
        cmd.append("-v")

    cmd.append(test_path)

    print("Running tests with command:", " ".join(cmd))
    result = subprocess.run(cmd)
    return result.returncode == 0


def get_prebid_test_prs() -> dict[str, str]:
    """
    Get the standard set of Prebid test PRs used across live integration tests.

    Returns:
        Dictionary mapping PR type to GitHub PR URL

    Note:
        These URLs should be updated periodically with real merged PRs.
        Use the GitHub CLI to find suitable PRs:

        gh pr list --repo prebid/Prebid.js --state merged --limit 10
        gh pr list --repo prebid/prebid-server --state merged --limit 10
        gh pr list --repo prebid/prebid.github.io --state merged --limit 10
    """
    return {
        "small_js_feature": "https://github.com/prebid/Prebid.js/pull/11000",
        "medium_server_fix": "https://github.com/prebid/prebid-server/pull/3200",
        "docs_update": "https://github.com/prebid/prebid.github.io/pull/4800",
    }


def run_live_integration_tests() -> bool:
    """
    Run live integration tests with proper configuration.

    This is a convenience function that runs the live integration test suite
    with the correct markers and settings.

    Returns:
        True if all tests passed, False otherwise

    Note:
        Requires GITHUB_TOKEN environment variable to be set.
    """
    print("Running live integration tests...")
    print("Note: These tests require GITHUB_TOKEN environment variable")

    return run_pytest_with_markers(
        "live", test_path="tests/integration/test_live_integration.py"
    )
