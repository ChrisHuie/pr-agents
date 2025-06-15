"""
Mock GitHub objects that match PyGithub interfaces for testing.

These objects provide realistic data structures without making network requests,
based on real Prebid organization PR patterns.
"""

from datetime import datetime
from typing import Optional


class MockUser:
    """Mock GitHub user object."""

    def __init__(self, login: str, user_type: str = "User"):
        self.login = login
        self.type = user_type
        self.id = hash(login) % 1000000  # Fake but consistent ID


class MockLabel:
    """Mock GitHub label object."""

    def __init__(self, name: str, color: str = "0366d6"):
        self.name = name
        self.color = color


class MockMilestone:
    """Mock GitHub milestone object."""

    def __init__(self, title: str):
        self.title = title


class MockFile:
    """Mock GitHub file object for PR changes."""

    def __init__(
        self,
        filename: str,
        status: str = "modified",
        additions: int = 10,
        deletions: int = 5,
        changes: int = 15,
        patch: str | None = None,
        previous_filename: str | None = None,
    ):
        self.filename = filename
        self.status = status
        self.additions = additions
        self.deletions = deletions
        self.changes = changes
        self.patch = patch or self._generate_patch()
        self.previous_filename = previous_filename

    def _generate_patch(self) -> str:
        """Generate a realistic patch based on file type."""
        if self.filename.endswith(".js"):
            return """@@ -10,7 +10,10 @@
 function processBid(bid) {
-    return bid.cpm;
+    return {
+        cpm: bid.cpm,
+        currency: bid.currency || 'USD'
+    };
 }"""
        elif self.filename.endswith(".go"):
            return """@@ -25,3 +25,6 @@
 func (a *Adapter) MakeRequests(request *openrtb2.BidRequest) ([]*adapters.RequestData, []error) {
+    if request.Device == nil {
+        return nil, []error{errors.New("device required")}
+    }
     return a.buildRequests(request)
 }"""
        elif self.filename.endswith(".swift"):
            return """@@ -15,2 +15,5 @@
 override func viewDidLoad() {
     super.viewDidLoad()
+    if UIDevice.current.orientation.isLandscape {
+        enableLandscapeMode()
+    }
 }"""
        else:
            return f"@@ -1,3 +1,4 @@\n // {self.filename}\n+// Updated: {datetime.now().isoformat()}"


class MockReview:
    """Mock GitHub review object."""

    def __init__(
        self,
        user: MockUser,
        state: str = "APPROVED",
        body: str | None = None,
        submitted_at: datetime | None = None,
    ):
        self.user = user
        self.state = state
        self.body = body
        self.submitted_at = submitted_at or datetime.now()


class MockComment:
    """Mock GitHub review comment object."""

    def __init__(
        self,
        user: MockUser,
        body: str,
        path: str | None = None,
        position: int | None = None,
        commit_id: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.user = user
        self.body = body
        self.path = path
        self.position = position
        self.commit_id = commit_id
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or self.created_at


class MockRepository:
    """Mock GitHub repository object."""

    def __init__(
        self,
        name: str,
        full_name: str,
        owner: MockUser,
        description: str | None = None,
        private: bool = False,
        default_branch: str = "main",
        language: str | None = None,
        languages: dict[str, int] | None = None,
        topics: list[str] | None = None,
        fork: bool = False,
        parent: Optional["MockRepository"] = None,
    ):
        self.name = name
        self.full_name = full_name
        self.owner = owner
        self.description = description
        self.private = private
        self.default_branch = default_branch
        self.language = language
        self.languages = languages or {}
        self.topics = topics or []
        self.fork = fork
        self.parent = parent

    def get_languages(self) -> dict[str, int]:
        """Mock get_languages API call."""
        return self.languages

    def get_topics(self) -> list[str]:
        """Mock get_topics API call."""
        return self.topics


class MockBranch:
    """Mock GitHub branch object."""

    def __init__(self, ref: str, sha: str, repo: MockRepository):
        self.ref = ref
        self.sha = sha
        self.repo = repo


class MockPullRequest:
    """Mock GitHub PullRequest object matching PyGithub interface."""

    def __init__(
        self,
        number: int,
        title: str,
        body: str | None = None,
        user: MockUser | None = None,
        state: str = "open",
        labels: list[MockLabel] | None = None,
        milestone: MockMilestone | None = None,
        assignees: list[MockUser] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        merged_at: datetime | None = None,
        base: MockBranch | None = None,
        head: MockBranch | None = None,
        merge_commit_sha: str | None = None,
        html_url: str | None = None,
        files: list[MockFile] | None = None,
        reviews: list[MockReview] | None = None,
        review_comments: list[MockComment] | None = None,
        requested_reviewers: list[MockUser] | None = None,
    ):
        self.number = number
        self.title = title
        self.body = body
        self.user = user or MockUser("test-user")
        self.state = state
        self.labels = labels or []
        self.milestone = milestone
        self.assignees = assignees or []
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or self.created_at
        self.merged_at = merged_at
        self.merge_commit_sha = merge_commit_sha
        self.html_url = html_url or f"https://github.com/test/repo/pull/{number}"

        # Set up base and head branches
        if base is None:
            repo = MockRepository(
                "test-repo", "test-org/test-repo", MockUser("test-org")
            )
            self.base = MockBranch("main", "abc123def", repo)
        else:
            self.base = base

        if head is None:
            # Create head branch with same repo as base
            if isinstance(self.base, MockBranch):
                head_repo = self.base.repo
            else:
                # base is a MockRepository
                head_repo = self.base
            self.head = MockBranch("feature-branch", "def456ghi", head_repo)
        else:
            self.head = head

        # Internal data for mocking API calls
        self._files = files or []
        self._reviews = reviews or []
        self._review_comments = review_comments or []
        self.requested_reviewers = requested_reviewers or []

    def get_files(self) -> list[MockFile]:
        """Mock get_files API call."""
        return self._files

    def get_reviews(self) -> list[MockReview]:
        """Mock get_reviews API call."""
        return self._reviews

    def get_review_comments(self) -> list[MockComment]:
        """Mock get_review_comments API call."""
        return self._review_comments
