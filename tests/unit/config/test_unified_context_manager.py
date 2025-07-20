"""Tests for unified repository context manager."""

from unittest.mock import Mock, patch

import pytest

from src.pr_agents.config.context_models import (
    RepositoryKnowledge,
    UnifiedRepositoryContext,
)
from src.pr_agents.config.unified_manager import UnifiedRepositoryContextManager


class TestUnifiedRepositoryContextManager:
    """Test unified context manager functionality."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a manager with test config directory."""
        return UnifiedRepositoryContextManager(
            config_path=str(tmp_path), enable_hot_reload=False, cache_contexts=True
        )

    def test_initialization(self, manager):
        """Test manager initializes correctly."""
        assert manager.structure_manager is not None
        assert manager.knowledge_loader is not None
        assert manager.agent_context_loader is not None
        assert manager.cache_contexts is True
        assert len(manager._context_cache) == 0

    @patch("src.pr_agents.config.unified_manager.RepositoryStructureManager")
    @patch("src.pr_agents.config.unified_manager.RepositoryKnowledgeLoader")
    @patch("src.pr_agents.config.unified_manager.AgentContextLoader")
    def test_get_full_context_no_config(
        self, mock_agent_loader, mock_knowledge_loader, mock_structure_manager, tmp_path
    ):
        """Test getting context when no configuration exists."""
        # Setup mocks
        mock_structure_manager.return_value.get_repository.return_value = None
        mock_knowledge_loader.return_value.load_repository_config.return_value = {}
        mock_agent_loader.return_value.load_agent_context.return_value = {}

        manager = UnifiedRepositoryContextManager(str(tmp_path))

        # Get context for unknown repo
        context = manager.get_full_context("https://github.com/unknown/repo")

        assert isinstance(context, UnifiedRepositoryContext)
        assert context.repo_name == "unknown/repo"
        assert context.repo_url == "https://github.com/unknown/repo"
        assert context.structure is None
        assert context.knowledge.purpose == ""
        assert len(context.agent_context.pr_patterns) == 0

    def test_get_context_for_ai(self, manager):
        """Test getting AI-optimized context."""
        # Create a mock full context
        mock_context = UnifiedRepositoryContext(
            repo_name="test/repo",
            repo_url="https://github.com/test/repo",
            primary_language="JavaScript",
        )
        mock_context.knowledge = RepositoryKnowledge(
            purpose="Test repository",
            key_features=["Feature 1", "Feature 2"],
            architecture={"core": "test"},
        )

        with patch.object(manager, "get_full_context", return_value=mock_context):
            ai_context = manager.get_context_for_ai("https://github.com/test/repo")

            assert ai_context["name"] == "test/repo"
            assert ai_context["url"] == "https://github.com/test/repo"
            assert ai_context["type"] == "unknown"  # No structure set
            assert ai_context["primary_language"] == "JavaScript"
            assert ai_context["description"] == "Test repository"
            assert ai_context["key_features"] == ["Feature 1", "Feature 2"]
            assert ai_context["architecture"] == {"core": "test"}

    def test_context_caching(self, manager):
        """Test that contexts are cached properly."""
        repo_url = "https://github.com/test/repo"

        # Create mock context
        mock_context = UnifiedRepositoryContext(
            repo_name="test/repo", repo_url=repo_url
        )

        # Mock the loading methods
        with patch.object(
            manager.structure_manager, "get_repository", return_value=None
        ):
            with patch.object(
                manager.knowledge_loader, "load_repository_config", return_value={}
            ):
                with patch.object(
                    manager.agent_context_loader, "load_agent_context", return_value={}
                ):
                    # First call should create and cache
                    context1 = manager.get_full_context(repo_url)
                    assert len(manager._context_cache) == 1

                    # Second call should return cached
                    context2 = manager.get_full_context(repo_url)
                    assert context1 is context2  # Same object
                    assert len(manager._context_cache) == 1

    def test_cache_clearing(self, manager):
        """Test cache clearing functionality."""
        repo_url = "https://github.com/test/repo"

        # Add to cache
        manager._context_cache[repo_url] = UnifiedRepositoryContext()
        assert len(manager._context_cache) == 1

        # Clear cache
        manager.clear_cache()
        assert len(manager._context_cache) == 0

    def test_extract_repo_name_github(self, manager):
        """Test extracting repository name from GitHub URLs."""
        test_cases = [
            ("https://github.com/owner/repo", "owner/repo"),
            ("https://github.com/owner/repo/", "owner/repo"),
            ("https://github.com/owner/repo/pull/123", "owner/repo"),
            ("https://github.com/owner/repo.git", "owner/repo.git"),
            (
                "git@github.com:owner/repo",
                "git@github.com:owner/repo",
            ),  # Not GitHub format
            ("https://example.com/repo", "https://example.com/repo"),  # Not GitHub
        ]

        for url, expected in test_cases:
            assert manager._extract_repo_name(url) == expected

    def test_parse_knowledge(self, manager):
        """Test parsing knowledge dictionary."""
        # Test with repository_context format
        knowledge_dict = {
            "repository_context": {
                "purpose": "Test purpose",
                "key_features": ["Feature 1"],
                "architecture": {"core": "test"},
            },
            "code_patterns": {"pattern1": "test"},
            "testing_requirements": {"unit": "required"},
        }

        knowledge = manager._parse_knowledge(knowledge_dict)
        assert knowledge.purpose == "Test purpose"
        assert knowledge.key_features == ["Feature 1"]
        assert knowledge.architecture == {"core": "test"}
        assert knowledge.code_patterns == {"pattern1": "test"}
        assert knowledge.testing_requirements == {"unit": "required"}

        # Test with overview format
        knowledge_dict2 = {
            "overview": {
                "purpose": "Overview purpose",
                "key_features": ["Feature 2"],
                "architecture": {"overview": "test"},
            },
            "patterns": {"pattern2": "test2"},
            "testing": {"integration": "optional"},
        }

        knowledge2 = manager._parse_knowledge(knowledge_dict2)
        assert knowledge2.purpose == "Overview purpose"
        assert knowledge2.key_features == ["Feature 2"]
        assert knowledge2.code_patterns == {"pattern2": "test2"}
        assert knowledge2.testing_requirements == {"integration": "optional"}

    def test_parse_agent_context(self, manager):
        """Test parsing agent context dictionary."""
        agent_dict = {
            "pr_analysis": {
                "common_patterns": [
                    {
                        "pattern": "Test pattern",
                        "indicators": ["indicator1"],
                        "review_focus": ["focus1"],
                        "validation_rules": ["rule1"],
                    }
                ],
                "quality_indicators": {
                    "good_pr": ["Good indicator"],
                    "red_flags": ["Red flag"],
                },
                "module_relationships": {"module1": {"requires": ["dep1"]}},
            },
            "code_review_guidelines": {
                "required_checks": ["check1"],
                "performance_considerations": ["perf1"],
                "security_considerations": ["sec1"],
                "module_specific_rules": {"module1": ["rule1"]},
            },
            "common_issues": ["issue1", "issue2"],
        }

        context = manager._parse_agent_context(agent_dict)

        assert len(context.pr_patterns) == 1
        assert context.pr_patterns[0].pattern == "Test pattern"
        assert context.pr_patterns[0].indicators == ["indicator1"]

        assert context.quality_indicators.good_pr == ["Good indicator"]
        assert context.quality_indicators.red_flags == ["Red flag"]

        assert context.code_review_guidelines.required_checks == ["check1"]
        assert context.code_review_guidelines.module_specific_rules == {
            "module1": ["rule1"]
        }

        assert context.common_issues == ["issue1", "issue2"]
        assert context.module_relationships == {"module1": {"requires": ["dep1"]}}

    def test_detect_primary_language(self, manager):
        """Test primary language detection."""
        # Mock structure with explicit language
        mock_structure = Mock()
        mock_structure.primary_language = "Python"
        assert manager._detect_primary_language(mock_structure) == "Python"

        # Mock structure with repo type
        mock_structure2 = Mock()
        mock_structure2.primary_language = None
        mock_structure2.repo_type = "prebid-js"
        assert manager._detect_primary_language(mock_structure2) == "JavaScript"

        # Unknown repo type
        mock_structure3 = Mock()
        mock_structure3.primary_language = None
        mock_structure3.repo_type = "unknown-type"
        assert manager._detect_primary_language(mock_structure3) == "Unknown"
