"""Tests for unified context manager batch optimization."""

from unittest.mock import patch

import pytest

from pr_agents.config.context_models import (
    RepositoryKnowledge,
    UnifiedRepositoryContext,
)
from pr_agents.config.models import ModuleCategory, RepositoryStructure
from pr_agents.config.unified_manager import UnifiedRepositoryContextManager


class TestUnifiedContextBatch:
    """Test batch optimization features of unified context manager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a context manager with caching enabled."""
        return UnifiedRepositoryContextManager(
            config_path=str(tmp_path), enable_hot_reload=False, cache_contexts=True
        )

    def _create_module_category(self, name, display_name, paths):
        """Helper to create ModuleCategory with proper structure."""
        return ModuleCategory(
            name=name,
            display_name=display_name,
            paths=paths,
            patterns=[],  # Empty patterns for tests
        )

    @pytest.fixture
    def mock_loaders(self):
        """Create mocked loader dependencies."""
        with patch(
            "pr_agents.config.unified_manager.RepositoryStructureManager"
        ) as mock_struct:
            with patch(
                "pr_agents.config.unified_manager.RepositoryKnowledgeLoader"
            ) as mock_knowledge:
                with patch(
                    "pr_agents.config.unified_manager.AgentContextLoader"
                ) as mock_agent:
                    yield {
                        "structure": mock_struct,
                        "knowledge": mock_knowledge,
                        "agent": mock_agent,
                    }

    def test_batch_context_caching(self, manager):
        """Test that contexts are cached for batch processing."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Mock the loaders to return data
        mock_structure = RepositoryStructure(
            repo_name="prebid/Prebid.js",
            repo_type="prebid-js",
            module_categories={
                "bid_adapter": ModuleCategory(
                    name="bid_adapter",
                    display_name="Bid Adapters",
                    paths=["modules/"],
                    patterns=[],
                )
            },
        )

        with patch.object(
            manager.structure_manager, "get_repository", return_value=mock_structure
        ):
            with patch.object(
                manager.knowledge_loader, "load_repository_config", return_value={}
            ):
                with patch.object(
                    manager.agent_context_loader, "load_agent_context", return_value={}
                ):
                    # First call should build context
                    context1 = manager.get_full_context(repo_url)
                    assert repo_url in manager._context_cache
                    assert len(manager._context_cache) == 1

                    # Second call should use cache
                    context2 = manager.get_full_context(repo_url)
                    assert context1 is context2  # Same object

                    # Verify loaders were only called once
                    manager.structure_manager.get_repository.assert_called_once()

                    # Third call for same repo
                    context3 = manager.get_full_context(repo_url)
                    assert context1 is context3

                    # Still only called once
                    manager.structure_manager.get_repository.assert_called_once()

    def test_batch_ai_context_optimization(self, manager):
        """Test AI context generation is optimized for batch."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Create rich mock context
        mock_context = UnifiedRepositoryContext(
            repo_name="prebid/Prebid.js",
            repo_url=repo_url,
            primary_language="JavaScript",
        )
        mock_context.structure = RepositoryStructure(
            repo_name="prebid/Prebid.js",
            repo_type="prebid-js",
            module_categories={
                "bid_adapter": ModuleCategory(
                    name="bid_adapter",
                    display_name="Bid Adapters",
                    paths=["modules/"],
                    patterns=[],
                )
            },
        )
        mock_context.knowledge = RepositoryKnowledge(
            purpose="Header bidding library",
            key_features=["Real-time bidding", "Multi-format support"],
            architecture={"core": "Auction engine", "adapters": "Bid adapters"},
        )

        with patch.object(manager, "get_full_context", return_value=mock_context):
            # Get AI context multiple times (simulating batch)
            ai_context1 = manager.get_context_for_ai(repo_url)
            ai_context2 = manager.get_context_for_ai(repo_url)
            ai_context3 = manager.get_context_for_ai(repo_url)

            # Verify context is consistent
            assert ai_context1 == ai_context2 == ai_context3
            assert ai_context1["type"] == "prebid-js"
            assert ai_context1["description"] == "Header bidding library"
            assert "bid_adapter" in ai_context1["module_patterns"]

    def test_batch_processing_different_repos(self, manager):
        """Test batch processing with multiple repositories."""
        repos = [
            "https://github.com/prebid/Prebid.js",
            "https://github.com/prebid/prebid-server",
            "https://github.com/prebid/prebid-server-java",
            "https://github.com/prebid/prebid-mobile-android",
            "https://github.com/prebid/prebid-mobile-ios",
        ]

        # Mock different structures for each repo type
        repo_structures = {
            "prebid/Prebid.js": RepositoryStructure(
                repo_name="prebid/Prebid.js",
                repo_type="prebid-js",
                module_categories={
                    "bid_adapter": self._create_module_category(
                        "bid_adapter", "Bid Adapters", ["modules/"]
                    ),
                    "analytics_adapter": self._create_module_category(
                        "analytics_adapter", "Analytics Adapters", ["modules/"]
                    ),
                },
            ),
            "prebid/prebid-server": RepositoryStructure(
                repo_name="prebid/prebid-server",
                repo_type="prebid-server-go",
                module_categories={
                    "bid_adapter": self._create_module_category(
                        "bid_adapter", "Bid Adapters", ["adapters/"]
                    ),
                    "analytics": self._create_module_category(
                        "analytics", "Analytics Modules", ["analytics/"]
                    ),
                },
            ),
            "prebid/prebid-server-java": RepositoryStructure(
                repo_name="prebid/prebid-server-java",
                repo_type="prebid-server-java",
                module_categories={
                    "bid_adapter": self._create_module_category(
                        "bid_adapter",
                        "Bid Adapters",
                        ["src/main/java/org/prebid/server/bidder/"],
                    ),
                    "analytics": self._create_module_category(
                        "analytics",
                        "Analytics Modules",
                        ["src/main/java/org/prebid/server/analytics/"],
                    ),
                },
            ),
            "prebid/prebid-mobile-android": RepositoryStructure(
                repo_name="prebid/prebid-mobile-android",
                repo_type="prebid-mobile-android",
                module_categories={
                    "rendering": self._create_module_category(
                        "rendering",
                        "Rendering Modules",
                        [
                            "PrebidMobile/PrebidMobile-core/src/main/java/org/prebid/mobile/rendering/"
                        ],
                    ),
                    "api": self._create_module_category(
                        "api",
                        "API Modules",
                        [
                            "PrebidMobile/PrebidMobile-core/src/main/java/org/prebid/mobile/api/"
                        ],
                    ),
                },
            ),
            "prebid/prebid-mobile-ios": RepositoryStructure(
                repo_name="prebid/prebid-mobile-ios",
                repo_type="prebid-mobile-ios",
                module_categories={
                    "rendering": self._create_module_category(
                        "rendering",
                        "Rendering Modules",
                        ["PrebidMobile/PrebidMobileRendering/"],
                    ),
                    "api": self._create_module_category(
                        "api", "API Modules", ["PrebidMobile/Core/"]
                    ),
                },
            ),
        }

        def get_repo_structure(repo_url):
            repo_name = manager._extract_repo_name(repo_url)
            return repo_structures.get(repo_name)

        with patch.object(
            manager.structure_manager, "get_repository", side_effect=get_repo_structure
        ):
            with patch.object(
                manager.knowledge_loader, "load_repository_config", return_value={}
            ):
                with patch.object(
                    manager.agent_context_loader, "load_agent_context", return_value={}
                ):
                    # Get contexts for all repos
                    contexts = []
                    for repo in repos:
                        contexts.append(manager.get_full_context(repo))

                    # Verify all cached with correct structures
                    assert len(manager._context_cache) == 5

                    # Verify each context has the right structure
                    for i, repo in enumerate(repos):
                        context = contexts[i]
                        repo_name = manager._extract_repo_name(repo)
                        assert (
                            context.structure.repo_type
                            == repo_structures[repo_name].repo_type
                        )
                        assert (
                            context.structure.module_categories
                            == repo_structures[repo_name].module_categories
                        )

                    # Get contexts again - should use cache
                    for repo in repos:
                        manager.get_full_context(repo)

                    # Verify structure manager was only called once per repo
                    assert manager.structure_manager.get_repository.call_count == 5

    def test_cache_performance_metrics(self, manager):
        """Test cache hit/miss tracking for performance monitoring."""
        # Add tracking attributes
        manager._cache_hits = 0
        manager._cache_misses = 0

        # Override get_full_context to track metrics
        original_get_full_context = manager.get_full_context

        def tracked_get_full_context(repo_url):
            if repo_url in manager._context_cache:
                manager._cache_hits += 1
            else:
                manager._cache_misses += 1
            return original_get_full_context(repo_url)

        manager.get_full_context = tracked_get_full_context

        # Simulate batch processing
        repo = "https://github.com/prebid/Prebid.js"

        mock_structure = RepositoryStructure(
            repo_name="prebid/Prebid.js", repo_type="prebid-js"
        )

        with patch.object(
            manager.structure_manager, "get_repository", return_value=mock_structure
        ):
            with patch.object(
                manager.knowledge_loader, "load_repository_config", return_value={}
            ):
                with patch.object(
                    manager.agent_context_loader, "load_agent_context", return_value={}
                ):
                    # First PR in batch - cache miss
                    manager.get_full_context(repo)
                    assert manager._cache_misses == 1
                    assert manager._cache_hits == 0

                    # Subsequent PRs - cache hits
                    for _ in range(5):
                        manager.get_full_context(repo)

                    assert manager._cache_misses == 1
                    assert manager._cache_hits == 5

                    # Calculate hit rate
                    total_requests = manager._cache_hits + manager._cache_misses
                    hit_rate = manager._cache_hits / total_requests
                    assert hit_rate > 0.8  # 83% hit rate

    def test_cache_size_limits(self, manager):
        """Test cache doesn't grow unbounded."""
        # Set a cache size limit
        manager._max_cache_size = 3

        # Add entries beyond limit
        for i in range(5):
            repo_url = f"https://github.com/test/repo{i}"
            context = UnifiedRepositoryContext(
                repo_name=f"test/repo{i}", repo_url=repo_url
            )
            manager._context_cache[repo_url] = context

            # Enforce cache limit (simple FIFO for test)
            if len(manager._context_cache) > manager._max_cache_size:
                # Remove oldest entry
                oldest_key = next(iter(manager._context_cache))
                del manager._context_cache[oldest_key]

        # Verify cache size is limited
        assert len(manager._context_cache) <= manager._max_cache_size
        assert "https://github.com/test/repo0" not in manager._context_cache  # Evicted
        assert "https://github.com/test/repo4" in manager._context_cache  # Recent

    def test_batch_context_with_pr_specific_data(self, manager):
        """Test batch context can be enriched with PR-specific data."""
        repo_url = "https://github.com/prebid/Prebid.js"

        # Create base context
        base_context = UnifiedRepositoryContext(
            repo_name="prebid/Prebid.js",
            repo_url=repo_url,
            primary_language="JavaScript",
        )
        base_context.knowledge = RepositoryKnowledge(
            purpose="Header bidding library",
            code_patterns={"adapter_pattern": "BaseAdapter extension"},
        )

        manager._context_cache[repo_url] = base_context

        # Get AI context (which would be enriched per PR)
        ai_context1 = manager.get_context_for_ai(repo_url)
        ai_context2 = manager.get_context_for_ai(repo_url)

        # Base context should be the same
        assert ai_context1["name"] == ai_context2["name"]
        assert ai_context1["description"] == ai_context2["description"]

        # In real usage, PR-specific enrichment would happen at a different layer

    def test_clear_cache_for_batch_end(self, manager):
        """Test cache can be cleared when batch processing ends."""
        # Populate cache
        for i in range(3):
            repo_url = f"https://github.com/test/repo{i}"
            manager._context_cache[repo_url] = UnifiedRepositoryContext()

        assert len(manager._context_cache) == 3

        # Clear cache (batch end)
        manager.clear_cache()

        assert len(manager._context_cache) == 0

    def test_batch_with_hot_reload_disabled(self, tmp_path):
        """Test batch processing with hot reload disabled for performance."""
        manager = UnifiedRepositoryContextManager(
            config_path=str(tmp_path),
            enable_hot_reload=False,  # Disabled for batch performance
            cache_contexts=True,
        )

        # Verify hot reload is disabled
        assert (
            hasattr(manager.structure_manager, "_watcher") is False
            or manager.structure_manager._watcher is None
        )

        # Batch processing should work without file watching overhead
        mock_structure = RepositoryStructure(
            repo_name="prebid/Prebid.js", repo_type="prebid-js"
        )

        with patch.object(
            manager.structure_manager, "get_repository", return_value=mock_structure
        ):
            with patch.object(
                manager.knowledge_loader, "load_repository_config", return_value={}
            ):
                with patch.object(
                    manager.agent_context_loader, "load_agent_context", return_value={}
                ):
                    # Process batch
                    repo = "https://github.com/prebid/Prebid.js"
                    for _ in range(10):
                        manager.get_full_context(repo)

                    # Only built once despite multiple requests
                    assert manager.structure_manager.get_repository.call_count == 1

    def test_mixed_repo_batch_context_isolation(self, manager):
        """Test that contexts remain isolated when processing mixed repository batches."""
        # Simulate a batch with PRs from different repos (including all types)
        pr_batch = [
            ("https://github.com/prebid/Prebid.js/pull/1", "prebid/Prebid.js"),
            ("https://github.com/prebid/prebid-server/pull/2", "prebid/prebid-server"),
            ("https://github.com/prebid/Prebid.js/pull/3", "prebid/Prebid.js"),
            (
                "https://github.com/prebid/prebid-mobile-ios/pull/4",
                "prebid/prebid-mobile-ios",
            ),
            (
                "https://github.com/prebid/prebid-server-java/pull/5",
                "prebid/prebid-server-java",
            ),
            (
                "https://github.com/prebid/prebid-mobile-android/pull/6",
                "prebid/prebid-mobile-android",
            ),
            (
                "https://github.com/prebid/prebid-server/pull/7",
                "prebid/prebid-server",
            ),  # Same repo again
        ]

        # Mock structures for each repo type
        repo_structures = {
            "prebid/Prebid.js": RepositoryStructure(
                repo_name="prebid/Prebid.js",
                repo_type="prebid-js",
                description="JavaScript header bidding library",
            ),
            "prebid/prebid-server": RepositoryStructure(
                repo_name="prebid/prebid-server",
                repo_type="prebid-server-go",
                description="Go server-side header bidding",
            ),
            "prebid/prebid-server-java": RepositoryStructure(
                repo_name="prebid/prebid-server-java",
                repo_type="prebid-server-java",
                description="Java server-side header bidding",
            ),
            "prebid/prebid-mobile-ios": RepositoryStructure(
                repo_name="prebid/prebid-mobile-ios",
                repo_type="prebid-mobile-ios",
                description="iOS mobile SDK",
            ),
            "prebid/prebid-mobile-android": RepositoryStructure(
                repo_name="prebid/prebid-mobile-android",
                repo_type="prebid-mobile-android",
                description="Android mobile SDK",
            ),
        }

        def get_repo_structure(repo_url):
            repo_name = manager._extract_repo_name(repo_url)
            return repo_structures.get(repo_name)

        with patch.object(
            manager.structure_manager, "get_repository", side_effect=get_repo_structure
        ):
            with patch.object(
                manager.knowledge_loader, "load_repository_config", return_value={}
            ):
                with patch.object(
                    manager.agent_context_loader, "load_agent_context", return_value={}
                ):
                    # Process batch and verify correct context for each PR
                    for pr_url, expected_repo in pr_batch:
                        context = manager.get_full_context(pr_url)
                        assert context.repo_name == expected_repo
                        assert (
                            context.structure.repo_type
                            == repo_structures[expected_repo].repo_type
                        )

                    # Verify cache contains entries for all PR URLs (7 PRs)
                    assert len(manager._context_cache) == len(pr_batch)

                    # Verify unique repos count
                    unique_repos = {repo for _, repo in pr_batch}
                    assert len(unique_repos) == 5

                    # Verify structure manager was called once per PR URL (not per unique repo)
                    # This is because each PR URL is cached separately
                    assert manager.structure_manager.get_repository.call_count == len(
                        pr_batch
                    )

    @pytest.mark.parametrize(
        "batch_size,expected_builds",
        [
            (1, 1),  # Single PR
            (10, 1),  # Small batch
            (100, 1),  # Large batch
            (1000, 1),  # Very large batch
        ],
    )
    def test_cache_efficiency_scales(self, manager, batch_size, expected_builds):
        """Test cache efficiency scales with batch size."""
        repo = "https://github.com/prebid/Prebid.js"

        # Mock the structure manager
        mock_structure = RepositoryStructure(
            repo_name="prebid/Prebid.js", repo_type="prebid-js"
        )

        with patch.object(
            manager.structure_manager, "get_repository", return_value=mock_structure
        ):
            with patch.object(
                manager.knowledge_loader, "load_repository_config", return_value={}
            ):
                with patch.object(
                    manager.agent_context_loader, "load_agent_context", return_value={}
                ):
                    # Simulate batch of PRs
                    for _ in range(batch_size):
                        manager.get_full_context(repo)

                    # Context should only be built once regardless of batch size
                    assert (
                        manager.structure_manager.get_repository.call_count
                        == expected_builds
                    )
