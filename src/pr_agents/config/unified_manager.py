"""
Unified repository context manager that combines all context layers.
"""

from pathlib import Path
from typing import Any

from loguru import logger

from .agent_context_loader import AgentContextLoader
from .context_models import (
    AgentContext,
    CodeReviewGuidelines,
    PRAnalysisPattern,
    QualityIndicators,
    RepositoryKnowledge,
    UnifiedRepositoryContext,
)
from .knowledge_loader import RepositoryKnowledgeLoader
from .manager import RepositoryStructureManager


class UnifiedRepositoryContextManager:
    """Manages unified repository context from all sources."""

    def __init__(
        self,
        config_path: str = "config",
        enable_hot_reload: bool = False,
        cache_contexts: bool = True,
    ):
        """
        Initialize the unified context manager.

        Args:
            config_path: Path to configuration directory
            enable_hot_reload: Enable automatic configuration reloading
            cache_contexts: Cache loaded contexts for performance
        """
        self.config_path = Path(config_path)
        self.cache_contexts = cache_contexts
        self._context_cache: dict[str, UnifiedRepositoryContext] = {}

        # Initialize component managers
        self.structure_manager = RepositoryStructureManager(
            config_path, enable_hot_reload
        )
        self.knowledge_loader = RepositoryKnowledgeLoader(config_path)
        self.agent_context_loader = AgentContextLoader(config_path)

        logger.info("Initialized UnifiedRepositoryContextManager")

    def get_full_context(self, repo_url: str) -> UnifiedRepositoryContext:
        """
        Get complete repository context combining all layers.

        Args:
            repo_url: Repository URL

        Returns:
            Unified repository context
        """
        # Check cache first
        if self.cache_contexts and repo_url in self._context_cache:
            logger.debug(f"Returning cached context for {repo_url}")
            return self._context_cache[repo_url]

        # Extract repository name
        repo_name = self._extract_repo_name(repo_url)

        # Create unified context
        context = UnifiedRepositoryContext(repo_name=repo_name, repo_url=repo_url)

        # Load structure
        structure = self.structure_manager.get_repository(repo_url)
        if structure:
            context.structure = structure
            logger.debug(f"Loaded structure for {repo_name}")
        else:
            logger.warning(f"No structure configuration found for {repo_name}")

        # Load knowledge
        try:
            knowledge_dict = self.knowledge_loader.load_repository_config(repo_name)
            if knowledge_dict:
                context.knowledge = self._parse_knowledge(knowledge_dict)
                logger.debug(f"Loaded knowledge for {repo_name}")
        except Exception as e:
            logger.warning(f"Could not load knowledge for {repo_name}: {e}")

        # Load agent context
        try:
            agent_dict = self.agent_context_loader.load_agent_context(repo_name)
            if agent_dict:
                context.agent_context = self._parse_agent_context(agent_dict)
                logger.debug(f"Loaded agent context for {repo_name}")
        except Exception as e:
            logger.warning(f"Could not load agent context for {repo_name}: {e}")

        # Detect primary language
        if structure:
            context.primary_language = self._detect_primary_language(structure)

        # Cache if enabled
        if self.cache_contexts:
            self._context_cache[repo_url] = context

        return context

    def get_context_for_ai(self, repo_url: str) -> dict[str, Any]:
        """
        Get repository context optimized for AI processing.

        Args:
            repo_url: Repository URL

        Returns:
            AI-optimized context dictionary
        """
        full_context = self.get_full_context(repo_url)

        # Build AI-friendly context
        ai_context = {
            "name": full_context.repo_name,
            "url": full_context.repo_url,
            "type": (
                full_context.structure.repo_type
                if full_context.structure
                else "unknown"
            ),
            "primary_language": full_context.primary_language,
        }

        # Add purpose and description
        if full_context.knowledge.purpose:
            ai_context["description"] = full_context.knowledge.purpose

        # Add key features
        if full_context.knowledge.key_features:
            ai_context["key_features"] = full_context.knowledge.key_features

        # Add architecture overview
        if full_context.knowledge.architecture:
            ai_context["architecture"] = full_context.knowledge.architecture

        # Add module patterns
        if full_context.structure:
            ai_context["module_patterns"] = {}
            for name, category in full_context.structure.module_categories.items():
                ai_context["module_patterns"][name] = {
                    "display_name": category.display_name,
                    "paths": category.paths,
                }

        # Add relevant PR patterns
        if full_context.agent_context.pr_patterns:
            ai_context["pr_patterns"] = [
                {
                    "pattern": p.pattern,
                    "indicators": p.indicators,
                }
                for p in full_context.agent_context.pr_patterns
            ]

        # Add code patterns if available
        if full_context.knowledge.code_patterns:
            ai_context["code_patterns"] = full_context.knowledge.code_patterns

        return ai_context

    def get_pr_review_context(self, repo_url: str) -> dict[str, Any]:
        """
        Get context specifically for PR review.

        Args:
            repo_url: Repository URL

        Returns:
            PR review context
        """
        full_context = self.get_full_context(repo_url)
        return full_context.get_pr_review_context()

    def clear_cache(self):
        """Clear the context cache."""
        self._context_cache.clear()
        logger.info("Cleared context cache")

    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL."""
        if "github.com" in repo_url:
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 5 and parts[2] == "github.com":
                return f"{parts[3]}/{parts[4]}"
        return repo_url

    def _parse_knowledge(self, knowledge_dict: dict[str, Any]) -> RepositoryKnowledge:
        """Parse knowledge dictionary into RepositoryKnowledge object."""
        knowledge = RepositoryKnowledge()

        # Extract repository context
        if "repository_context" in knowledge_dict:
            ctx = knowledge_dict["repository_context"]
            knowledge.purpose = ctx.get("purpose", "")
            knowledge.key_features = ctx.get("key_features", [])
            knowledge.architecture = ctx.get("architecture", {})

        # Extract overview (alternative format)
        elif "overview" in knowledge_dict:
            overview = knowledge_dict["overview"]
            knowledge.purpose = overview.get("purpose", "")
            knowledge.key_features = overview.get("key_features", [])
            knowledge.architecture = overview.get("architecture", {})

        # Extract patterns
        if "code_patterns" in knowledge_dict:
            knowledge.code_patterns = knowledge_dict["code_patterns"]
        elif "patterns" in knowledge_dict:
            knowledge.code_patterns = knowledge_dict["patterns"]

        # Extract testing requirements
        if "testing_requirements" in knowledge_dict:
            knowledge.testing_requirements = knowledge_dict["testing_requirements"]
        elif "testing" in knowledge_dict:
            knowledge.testing_requirements = knowledge_dict["testing"]

        # Extract code examples
        if "code_examples" in knowledge_dict:
            knowledge.code_examples = knowledge_dict["code_examples"]

        return knowledge

    def _parse_agent_context(self, agent_dict: dict[str, Any]) -> AgentContext:
        """Parse agent context dictionary into AgentContext object."""
        context = AgentContext()

        # Parse PR analysis patterns
        if "pr_analysis" in agent_dict:
            pr_analysis = agent_dict["pr_analysis"]

            # Parse patterns
            if "common_patterns" in pr_analysis:
                for pattern_dict in pr_analysis["common_patterns"]:
                    pattern = PRAnalysisPattern(
                        pattern=pattern_dict.get("pattern", ""),
                        indicators=pattern_dict.get("indicators", []),
                        review_focus=pattern_dict.get("review_focus", []),
                        validation_rules=pattern_dict.get("validation_rules", []),
                    )
                    context.pr_patterns.append(pattern)

            # Parse quality indicators
            if "quality_indicators" in pr_analysis:
                qi = pr_analysis["quality_indicators"]
                context.quality_indicators = QualityIndicators(
                    good_pr=qi.get("good_pr", []),
                    red_flags=qi.get("red_flags", []),
                )

            # Parse module relationships
            if "module_relationships" in pr_analysis:
                context.module_relationships = pr_analysis["module_relationships"]

        # Parse code review guidelines
        if "code_review_guidelines" in agent_dict:
            crg = agent_dict["code_review_guidelines"]
            context.code_review_guidelines = CodeReviewGuidelines(
                required_checks=crg.get("required_checks", []),
                performance_considerations=crg.get("performance_considerations", []),
                security_considerations=crg.get("security_considerations", []),
                module_specific_rules=crg.get("module_specific_rules", {}),
            )

        # Parse common issues
        if "common_issues" in agent_dict:
            context.common_issues = agent_dict["common_issues"]

        return context

    def _detect_primary_language(self, structure) -> str:
        """Detect primary language from repository structure."""
        # Check if explicitly set
        if hasattr(structure, "primary_language") and structure.primary_language:
            return structure.primary_language

        # Infer from repo type
        type_language_map = {
            "prebid-js": "JavaScript",
            "prebid-server-java": "Java",
            "prebid-server-go": "Go",
            "prebid-mobile-ios": "Swift",
            "prebid-mobile-android": "Kotlin",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "python": "Python",
            "java": "Java",
            "go": "Go",
        }

        return type_language_map.get(structure.repo_type, "Unknown")
