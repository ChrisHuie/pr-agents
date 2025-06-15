"""
Tests for PR processors - demonstrates component isolation.
"""

from src.pr_agents.pr_processing.processors import (
    CodeProcessor,
    MetadataProcessor,
    RepoProcessor,
)


class TestMetadataProcessor:
    """Test metadata processor in isolation."""

    def test_metadata_processor_basic(self):
        processor = MetadataProcessor()

        # Test with minimal metadata
        metadata = {
            "title": "Fix bug in authentication",
            "description": "This fixes a critical authentication bug",
            "labels": ["bug", "critical"],
            "author": "test_user",
        }

        result = processor.process(metadata)

        assert result.success is True
        assert result.component == "metadata"
        assert "title_analysis" in result.data
        assert "description_analysis" in result.data
        assert "metadata_quality" in result.data

    def test_metadata_processor_empty_description(self):
        processor = MetadataProcessor()

        metadata = {
            "title": "Update README",
            "description": None,
            "labels": [],
            "author": "test_user",
        }

        result = processor.process(metadata)

        assert result.success is True
        assert result.data["description_analysis"]["has_description"] is False


class TestCodeProcessor:
    """Test code processor in isolation."""

    def test_code_processor_basic(self):
        processor = CodeProcessor()

        # Test with sample code changes
        code_data = {
            "total_additions": 50,
            "total_deletions": 10,
            "total_changes": 60,
            "changed_files": 3,
            "file_diffs": [
                {
                    "filename": "src/auth.py",
                    "status": "modified",
                    "additions": 30,
                    "deletions": 5,
                    "changes": 35,
                    "patch": "def authenticate(user):\n    return validate_token(user.token)",
                },
                {
                    "filename": "tests/test_auth.py",
                    "status": "added",
                    "additions": 20,
                    "deletions": 0,
                    "changes": 20,
                    "patch": "def test_authenticate():\n    assert True",
                },
            ],
        }

        result = processor.process(code_data)

        assert result.success is True
        assert result.component == "code_changes"
        assert "change_stats" in result.data
        assert "file_analysis" in result.data
        assert "risk_assessment" in result.data
        assert result.data["pattern_analysis"]["has_tests"] is True

    def test_code_processor_high_risk(self):
        processor = CodeProcessor()

        # Test high-risk changes
        code_data = {
            "total_additions": 2000,
            "total_deletions": 500,
            "changed_files": 25,
            "file_diffs": [
                {
                    "filename": "main.py",
                    "status": "modified",
                    "additions": 1000,
                    "deletions": 200,
                    "changes": 1200,
                }
            ],
        }

        result = processor.process(code_data)

        assert result.success is True
        assert result.data["risk_assessment"]["risk_level"] in ["medium", "high"]


class TestRepoProcessor:
    """Test repository processor in isolation."""

    def test_repo_processor_basic(self):
        processor = RepoProcessor()

        repo_data = {
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "owner": "owner",
            "description": "A test repository for demonstration",
            "is_private": False,
            "languages": {"Python": 8000, "JavaScript": 2000},
            "topics": ["python", "web", "api"],
            "base_branch": "main",
            "head_branch": "feature/new-auth",
        }

        result = processor.process(repo_data)

        assert result.success is True
        assert result.component == "repository"
        assert "repo_info" in result.data
        assert "language_analysis" in result.data
        assert "branch_analysis" in result.data
        assert result.data["language_analysis"]["primary_language"] == "Python"

    def test_repo_processor_health_assessment(self):
        processor = RepoProcessor()

        # Test well-maintained repo
        repo_data = {
            "name": "awesome-project",
            "description": "An awesome project that does amazing things",
            "languages": {"Python": 5000, "TypeScript": 3000, "CSS": 1000},
            "topics": ["python", "typescript", "web-development", "api", "modern"],
            "is_private": False,
            "base_branch": "main",
        }

        result = processor.process(repo_data)

        assert result.success is True
        health = result.data["repo_health"]
        assert health["health_level"] in ["good", "excellent"]
        assert health["health_score"] > 40
