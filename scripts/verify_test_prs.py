#!/usr/bin/env python3
"""
Script to verify that test PR URLs are still valid and accessible.

This script uses the test utilities to check if the GitHub PRs used in
live integration tests are still accessible via the GitHub API.

Usage:
    python scripts/verify_test_prs.py
"""

from tests.utils import get_prebid_test_prs, verify_pr_urls

if __name__ == "__main__":
    print("🔍 Verifying test PR URLs...")
    print("=" * 50)

    test_prs = get_prebid_test_prs()
    verify_pr_urls(test_prs)

    print("=" * 50)
    print("✅ Verification complete!")
    print("\nTo update test PR URLs, modify tests/utils.py:get_prebid_test_prs()")
    print("Use these commands to find suitable PRs:")
    print("  gh pr list --repo prebid/Prebid.js --state merged --limit 10")
    print("  gh pr list --repo prebid/prebid-server --state merged --limit 10")
    print("  gh pr list --repo prebid/prebid.github.io --state merged --limit 10")
