"""
Tests for PR processors - demonstrates component isolation.
"""

import pytest

from src.pr_agents.pr_processing.constants import (
    BRANCH_ANALYSIS_KEY,
    CHANGE_STATS_KEY,
    CODE_CHANGES_COMPONENT,
    DESCRIPTION_ANALYSIS_KEY,
    DESCRIPTION_QUALITY_KEY,
    FILE_ANALYSIS_KEY,
    LANGUAGE_ANALYSIS_KEY,
    METADATA_COMPONENT,
    PATTERN_ANALYSIS_KEY,
    REPO_HEALTH_KEY,
    REPO_INFO_KEY,
    REPOSITORY_COMPONENT,
    RISK_ASSESSMENT_KEY,
    TITLE_ANALYSIS_KEY,
    TITLE_QUALITY_KEY,
)
from src.pr_agents.pr_processing.processors import (
    CodeProcessor,
    MetadataProcessor,
    RepoProcessor,
)


@pytest.fixture
def metadata_processor():
    """Create a MetadataProcessor instance for testing."""
    return MetadataProcessor()


@pytest.fixture
def code_processor():
    """Create a CodeProcessor instance for testing."""
    return CodeProcessor()


@pytest.fixture
def repo_processor():
    """Create a RepoProcessor instance for testing."""
    return RepoProcessor()


class TestMetadataProcessor:
    """Test metadata processor in isolation."""

    def test_metadata_processor_basic(self, metadata_processor):
        processor = metadata_processor

        # Test with minimal metadata
        metadata = {
            "title": "Fix bug in authentication",
            "description": "This fixes a critical authentication bug",
            "labels": ["bug", "critical"],
            "author": "test_user",
        }

        result = processor.process(metadata)

        assert result.success is True
        assert result.component == METADATA_COMPONENT
        assert TITLE_ANALYSIS_KEY in result.data
        assert DESCRIPTION_ANALYSIS_KEY in result.data
        assert TITLE_QUALITY_KEY in result.data
        assert DESCRIPTION_QUALITY_KEY in result.data

        # Check title quality scoring
        title_quality = result.data[TITLE_QUALITY_KEY]
        assert 0 <= title_quality["score"] <= 100
        assert title_quality["quality_level"] in ["poor", "fair", "good", "excellent"]

        # Check description quality scoring
        desc_quality = result.data[DESCRIPTION_QUALITY_KEY]
        assert 0 <= desc_quality["score"] <= 100
        assert desc_quality["quality_level"] in ["poor", "fair", "good", "excellent"]

    def test_metadata_processor_empty_description(self, metadata_processor):
        processor = metadata_processor

        metadata = {
            "title": "Update README",
            "description": None,
            "labels": [],
            "author": "test_user",
        }

        result = processor.process(metadata)

        assert result.success is True
        assert result.data[DESCRIPTION_ANALYSIS_KEY]["has_description"] is False
        # Description quality should be 0 for missing description
        assert result.data[DESCRIPTION_QUALITY_KEY]["score"] == 0
        assert result.data[DESCRIPTION_QUALITY_KEY]["quality_level"] == "poor"

    def test_metadata_processor_missing_keys(self, metadata_processor):
        """Test processor handles missing optional keys gracefully."""
        processor = metadata_processor

        # Test with minimal metadata - missing optional keys entirely
        metadata = {
            "title": "Minimal PR",
            "author": "test_user",
            # Missing: description, labels, milestone, etc.
        }

        result = processor.process(metadata)

        assert result.success is True
        assert result.component == METADATA_COMPONENT
        assert TITLE_ANALYSIS_KEY in result.data
        assert DESCRIPTION_ANALYSIS_KEY in result.data
        assert TITLE_QUALITY_KEY in result.data
        assert DESCRIPTION_QUALITY_KEY in result.data
        # Should handle missing description gracefully
        assert result.data[DESCRIPTION_ANALYSIS_KEY]["has_description"] is False


class TestCodeProcessor:
    """Test code processor in isolation."""

    def test_code_processor_basic(self, code_processor):
        processor = code_processor

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
        assert result.component == CODE_CHANGES_COMPONENT
        assert CHANGE_STATS_KEY in result.data
        assert FILE_ANALYSIS_KEY in result.data
        assert RISK_ASSESSMENT_KEY in result.data
        assert result.data[PATTERN_ANALYSIS_KEY]["has_tests"] is True

    def test_code_processor_high_risk(self, code_processor):
        processor = code_processor

        # Test high-risk changes
        # Risk calculation: 3 (>1000 changes) + 2 (>20 files) + 1 (main.py) = 6 points = "high"
        code_data = {
            "total_additions": 2000,
            "total_deletions": 500,
            "total_changes": 2500,  # This will be calculated as total_changes
            "changed_files": 25,
            "file_diffs": [
                {
                    "filename": "main.py",  # Critical file (+1 point)
                    "status": "modified",
                    "additions": 1000,
                    "deletions": 200,
                    "changes": 1200,
                }
            ],
        }

        result = processor.process(code_data)

        assert result.success is True
        risk_assessment = result.data[RISK_ASSESSMENT_KEY]
        # With this input, we should get exactly 6 risk points = "high" level
        assert risk_assessment["risk_level"] == "high"
        assert risk_assessment["risk_score"] == 6
        assert "Very large changeset" in risk_assessment["risk_factors"]
        assert "Many files changed" in risk_assessment["risk_factors"]
        assert "Critical file modified: main.py" in risk_assessment["risk_factors"]

    def test_code_processor_missing_keys(self, code_processor):
        """Test processor handles missing optional keys gracefully."""
        processor = code_processor

        # Test with minimal code data - missing optional keys
        code_data = {
            "total_additions": 10,
            "total_deletions": 5,
            # Missing: total_changes, changed_files, file_diffs
        }

        result = processor.process(code_data)

        assert result.success is True
        assert result.component == CODE_CHANGES_COMPONENT
        assert CHANGE_STATS_KEY in result.data
        assert RISK_ASSESSMENT_KEY in result.data
        # Should handle missing data gracefully
        assert (
            result.data[CHANGE_STATS_KEY]["total_changes"] == 0
        )  # Default when missing
        assert (
            result.data[RISK_ASSESSMENT_KEY]["risk_level"] == "minimal"
        )  # Low risk for minimal data

    def test_code_processor_edge_case_risk_levels(self, code_processor):
        """Test exact risk level boundaries."""
        processor = code_processor

        # Test exact boundary for "medium" risk (3 points)
        code_data = {
            "total_additions": 600,  # 2 points (large changeset)
            "total_deletions": 100,
            "total_changes": 700,
            "changed_files": 12,  # 1 point (several files)
            "file_diffs": [],
        }

        result = processor.process(code_data)
        assert result.data[RISK_ASSESSMENT_KEY]["risk_level"] == "medium"
        assert result.data[RISK_ASSESSMENT_KEY]["risk_score"] == 3

        # Test exact boundary for "low" risk (1 point)
        code_data_low = {
            "total_additions": 150,  # 1 point (medium changeset)
            "total_deletions": 50,
            "total_changes": 200,
            "changed_files": 5,  # 0 points
            "file_diffs": [],
        }

        result_low = processor.process(code_data_low)
        assert result_low.data[RISK_ASSESSMENT_KEY]["risk_level"] == "low"
        assert result_low.data[RISK_ASSESSMENT_KEY]["risk_score"] == 1


class TestRepoProcessor:
    """Test repository processor in isolation."""

    def test_repo_processor_basic(self, repo_processor):
        processor = repo_processor

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
        assert result.component == REPOSITORY_COMPONENT
        assert REPO_INFO_KEY in result.data
        assert LANGUAGE_ANALYSIS_KEY in result.data
        assert BRANCH_ANALYSIS_KEY in result.data
        assert result.data[LANGUAGE_ANALYSIS_KEY]["primary_language"] == "Python"

    def test_repo_processor_health_assessment(self, repo_processor):
        processor = repo_processor

        # Test well-maintained repo
        # Health calculation: 10 (description) + 10 (>=3 topics) + 15 (multi-language) + 10 (public) + 10 (main branch) = 55 points = "excellent"
        repo_data = {
            "name": "awesome-project",
            "description": "An awesome project that does amazing things",  # +10 points
            "languages": {
                "Python": 5000,
                "TypeScript": 3000,
                "CSS": 1000,
            },  # +15 points (multi-language)
            "topics": [
                "python",
                "typescript",
                "web-development",
                "api",
                "modern",
            ],  # +10 points (>=3 topics)
            "is_private": False,  # +10 points (public)
            "base_branch": "main",  # +10 points (standard branch)
        }

        result = processor.process(repo_data)

        assert result.success is True
        health = result.data[REPO_HEALTH_KEY]
        # With this input, we should get exactly 55 points = "excellent" level
        assert health["health_level"] == "excellent"
        assert health["health_score"] == 55
        assert health["max_possible_score"] == 70
        assert "Has description" in health["health_factors"]
        assert "Well-tagged with topics" in health["health_factors"]
        assert "Multi-language repository" in health["health_factors"]
        assert "Public repository" in health["health_factors"]
        assert "Standard base branch" in health["health_factors"]

    def test_repo_processor_missing_keys(self, repo_processor):
        """Test processor handles missing optional keys gracefully."""
        processor = repo_processor

        # Test with minimal repo data - missing most optional keys
        repo_data = {
            "name": "minimal-repo",
            # Missing: description, languages, topics, is_private, base_branch, etc.
        }

        result = processor.process(repo_data)

        assert result.success is True
        assert result.component == REPOSITORY_COMPONENT
        assert REPO_INFO_KEY in result.data
        assert REPO_HEALTH_KEY in result.data
        # Should handle missing data gracefully with poor health score
        health = result.data[REPO_HEALTH_KEY]
        assert (
            health["health_level"] == "needs_improvement"
        )  # Very low score due to missing data
        assert health["health_score"] < 20  # Should be low due to missing fields
        assert len(health["issues"]) > 0  # Should identify missing elements as issues
