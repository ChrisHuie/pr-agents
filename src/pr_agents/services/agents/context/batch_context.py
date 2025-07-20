"""Batch-optimized repository context provider."""

from typing import Any

from loguru import logger

from .enhanced_repository import EnhancedRepositoryContextProvider


class BatchContextProvider:
    """Optimized context provider for batch PR processing."""

    def __init__(self):
        """Initialize the batch context provider."""
        self._base_provider = EnhancedRepositoryContextProvider()
        self._repo_context_cache = {}
        self._current_batch_repo = None
        self._batch_context = None

    def start_batch(self, repo_url: str) -> None:
        """Start a new batch for a specific repository.

        This pre-loads and caches the repository context for efficient reuse
        across multiple PRs from the same repository.

        Args:
            repo_url: Repository URL for the batch
        """
        logger.info(f"Starting batch context for repository: {repo_url}")

        # Clear previous batch if different repo
        if self._current_batch_repo != repo_url:
            self._current_batch_repo = repo_url
            self._batch_context = None

        # Pre-load repository type and knowledge base
        repo_type = self._base_provider._determine_repo_type(repo_url)

        # Load the specific knowledge base on demand
        knowledge = self._base_provider._load_knowledge_base(repo_type)

        if knowledge:
            self._batch_context = {
                "repo_url": repo_url,
                "repo_type": repo_type,
                "knowledge": knowledge,
                "repository": knowledge.get("repository", repo_url),
                "description": knowledge.get("description", ""),
                "primary_language": knowledge.get("primary_language", ""),
                "ecosystem": knowledge.get("ecosystem", ""),
            }
            logger.info(f"Loaded batch context for {repo_type} repository")
        else:
            logger.warning(f"No knowledge base found for repository type: {repo_type}")

    def get_context_for_pr(
        self, repo_url: str, files_changed: list[str]
    ) -> dict[str, Any]:
        """Get context for a specific PR within a batch.

        If processing a batch from the same repository, this reuses the cached
        repository knowledge and only computes file-specific context.

        Args:
            repo_url: Repository URL
            files_changed: List of files changed in this PR

        Returns:
            Enhanced repository context
        """
        # If we have batch context for this repo, use it
        if self._batch_context and self._current_batch_repo == repo_url:
            # Start with cached base context
            context = {
                "repository": self._batch_context["repository"],
                "type": self._batch_context["repo_type"],
                "description": self._batch_context["description"],
                "primary_language": self._batch_context["primary_language"],
                "ecosystem": self._batch_context["ecosystem"],
            }

            # Add file-specific context using cached knowledge
            knowledge = self._batch_context["knowledge"]

            # Get relevant examples based on changed files
            context["relevant_examples"] = self._base_provider._get_relevant_examples(
                knowledge, files_changed
            )

            # Get relevant patterns
            context["patterns"] = self._base_provider._get_relevant_patterns(
                knowledge, files_changed
            )

            # Get quality checklist
            context["quality_checklist"] = self._base_provider._get_quality_checklist(
                knowledge, files_changed
            )

            # Get common issues
            context["common_issues"] = self._base_provider._get_common_issues(
                knowledge, files_changed
            )

            # Get file guidance
            context["file_guidance"] = self._base_provider._get_file_guidance(
                knowledge, files_changed
            )

            return context
        else:
            # Fall back to regular context generation
            return self._base_provider.get_context(repo_url, files_changed)

    def end_batch(self) -> None:
        """End the current batch and clear batch-specific cache."""
        logger.info("Ending batch context")
        self._current_batch_repo = None
        self._batch_context = None

    def get_batch_statistics(self) -> dict[str, Any]:
        """Get statistics about the current batch context.

        Returns:
            Dictionary with batch statistics
        """
        if not self._batch_context:
            return {"active": False}

        return {
            "active": True,
            "repository": self._current_batch_repo,
            "repo_type": self._batch_context["repo_type"],
            "has_knowledge_base": bool(self._batch_context.get("knowledge")),
            "available_examples": len(
                self._batch_context.get("knowledge", {}).get("code_examples", {})
            ),
            "available_patterns": len(
                self._batch_context.get("knowledge", {}).get("patterns", {})
            ),
        }
