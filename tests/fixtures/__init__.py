"""
Test fixtures based on real Prebid organization PR patterns.

These fixtures provide realistic mock GitHub objects without network requests,
based on analysis of actual PRs from:
- Prebid.js (JavaScript/frontend)
- prebid-server (Go/backend)
- prebid-server-java (Java/enterprise)
- prebid-mobile-ios (Swift/mobile)
- prebid-mobile-android (Java/mobile)
"""

from .mock_github import MockFile, MockPullRequest, MockRepository, MockUser
from .prebid_scenarios import PrebidPRScenarios

__all__ = [
    "MockPullRequest",
    "MockRepository",
    "MockUser",
    "MockFile",
    "PrebidPRScenarios",
]
