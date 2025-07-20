"""Enhanced repository context provider using knowledge bases."""

import re
from pathlib import Path
from typing import Any

import yaml
from loguru import logger


class EnhancedRepositoryContextProvider:
    """Provides rich repository context from knowledge bases.

    Implemented as a singleton to prevent multiple instances from loading
    all knowledge bases repeatedly.
    """

    _instance = None
    _initialized = False

    def __new__(cls, knowledge_base_path: Path | None = None):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, knowledge_base_path: Path | None = None):
        """Initialize the enhanced context provider.

        Args:
            knowledge_base_path: Path to repository knowledge files
        """
        # Only initialize once
        if EnhancedRepositoryContextProvider._initialized:
            return

        if knowledge_base_path is None:
            # Default to config/repository-knowledge in project root
            # __file__ is in src/pr_agents/services/agents/context/
            # Go up 5 levels to reach project root
            knowledge_base_path = (
                Path(__file__).parent.parent.parent.parent.parent.parent
                / "config"
                / "repository-knowledge"
            )

        self.knowledge_base_path = knowledge_base_path
        self._knowledge_cache = {}
        # Don't load all knowledge bases on init - load on demand
        EnhancedRepositoryContextProvider._initialized = True
        logger.info("Initialized EnhancedRepositoryContextProvider (singleton)")

    def _load_knowledge_base(self, repo_type: str) -> dict | None:
        """Load a specific repository knowledge base on demand.

        Args:
            repo_type: Repository type to load

        Returns:
            Knowledge base dictionary or None if not found
        """
        # Check if already cached
        if repo_type in self._knowledge_cache:
            return self._knowledge_cache[repo_type]

        if not self.knowledge_base_path.exists():
            logger.warning(
                f"Knowledge base path does not exist: {self.knowledge_base_path}"
            )
            return None

        # Try to load the specific YAML file
        yaml_file = self.knowledge_base_path / f"{repo_type}.yaml"
        if yaml_file.exists():
            try:
                with open(yaml_file) as f:
                    knowledge = yaml.safe_load(f)
                    self._knowledge_cache[repo_type] = knowledge
                    logger.info(f"Loaded knowledge base for {repo_type}")
                    return knowledge
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")
        else:
            logger.debug(f"No knowledge base found for {repo_type}")

        return None

    def get_context(self, repo_url: str, files_changed: list[str]) -> dict[str, Any]:
        """Get enhanced repository context based on URL and changed files.

        Args:
            repo_url: Repository URL
            files_changed: List of files being changed in the PR

        Returns:
            Enhanced repository context with examples and patterns
        """
        # Determine repository type
        repo_type = self._determine_repo_type(repo_url)
        logger.debug(f"Determined repo type: {repo_type} for URL: {repo_url}")

        # Load knowledge base on demand
        base_knowledge = self._load_knowledge_base(repo_type)

        if not base_knowledge:
            logger.debug(
                f"No knowledge base found for repo type: {repo_type}, using generic context"
            )
            return self._get_generic_context(repo_url)

        # Build context based on changed files
        context = {
            "repository": base_knowledge.get("repository", repo_url),
            "type": repo_type,
            "description": base_knowledge.get("description", ""),
            "primary_language": base_knowledge.get("primary_language", ""),
            "ecosystem": base_knowledge.get("ecosystem", ""),
        }

        # Add relevant examples based on file types
        context["relevant_examples"] = self._get_relevant_examples(
            base_knowledge, files_changed
        )

        # Add patterns and conventions
        context["patterns"] = self._get_relevant_patterns(base_knowledge, files_changed)

        # Add quality checklist
        context["quality_checklist"] = self._get_quality_checklist(
            base_knowledge, files_changed
        )

        # Add common issues
        context["common_issues"] = self._get_common_issues(
            base_knowledge, files_changed
        )

        # Add file-specific guidance
        context["file_guidance"] = self._get_file_guidance(
            base_knowledge, files_changed
        )

        return context

    def _determine_repo_type(self, repo_url: str) -> str:
        """Determine repository type from URL."""
        repo_lower = repo_url.lower()

        # Prebid.js
        if "prebid.js" in repo_lower or "prebid/prebid.js" in repo_lower:
            return "prebid-js"

        # Prebid Server
        if "prebid-server" in repo_lower:
            if "java" in repo_lower:
                return "prebid-server-java"
            else:
                return "prebid-server-go"

        # Prebid Mobile
        if "prebid-mobile" in repo_lower:
            if "ios" in repo_lower:
                return "prebid-mobile-ios"
            elif "android" in repo_lower:
                return "prebid-mobile-android"

        return "generic"

    def _get_relevant_examples(
        self, knowledge: dict, files_changed: list[str]
    ) -> list[dict]:
        """Get code examples relevant to the changed files."""
        examples = []
        code_examples = knowledge.get("code_examples", {})

        # Analyze file patterns
        for file in files_changed:
            # Bid adapter pattern
            if re.search(r"BidAdapter\.(js|java|go|swift|kt)$", file):
                if "bid_adapter" in code_examples:
                    examples.append(
                        {
                            "type": "bid_adapter",
                            "description": "Reference bid adapter implementation",
                            "code": code_examples["bid_adapter"]
                            .get("complete_example", {})
                            .get("code", ""),
                        }
                    )
                    break

            # Analytics adapter
            elif re.search(r"AnalyticsAdapter\.(js|java|go|swift|kt)$", file):
                if "analytics_adapter" in code_examples:
                    examples.append(
                        {
                            "type": "analytics_adapter",
                            "description": "Analytics adapter reference",
                            "code": code_examples["analytics_adapter"].get("code", ""),
                        }
                    )
                    break

            # Test files
            elif re.search(
                r"_spec\.(js|java|go|swift|kt)$|Test\.(java|swift|kt)$", file
            ):
                test_key = (
                    "test_patterns"
                    if "test_patterns" in code_examples
                    else "adapter_test"
                )
                if test_key in code_examples:
                    examples.append(
                        {
                            "type": "test",
                            "description": "Test structure reference",
                            "code": (
                                code_examples[test_key]
                                .get("adapter_test", {})
                                .get("code", "")
                                if test_key == "test_patterns"
                                else code_examples[test_key].get("code", "")
                            ),
                        }
                    )

        return examples[:3]  # Limit to 3 most relevant examples

    def _get_relevant_patterns(self, knowledge: dict, files_changed: list[str]) -> dict:
        """Get patterns relevant to the changed files."""
        patterns = knowledge.get("patterns", {})
        relevant_patterns = {}

        # Determine which patterns are relevant
        for file in files_changed:
            if "adapter" in file.lower():
                if "adapter_structure" in patterns:
                    relevant_patterns["adapter_structure"] = patterns[
                        "adapter_structure"
                    ]
                if "error_handling" in patterns:
                    relevant_patterns["error_handling"] = patterns["error_handling"]
                break

        # Always include common patterns
        if "imports" in patterns:
            relevant_patterns["imports"] = patterns["imports"]

        return relevant_patterns

    def _get_quality_checklist(
        self, knowledge: dict, files_changed: list[str]
    ) -> list[str]:
        """Get quality checklist items relevant to the PR."""
        checklist = []
        quality_section = knowledge.get("quality_checklist", {})

        # Determine what type of change this is
        is_adapter = any("adapter" in f.lower() for f in files_changed)
        has_tests = any(re.search(r"_spec\.|_test\.|Test\.", f) for f in files_changed)

        if is_adapter and "must_have" in quality_section:
            checklist.extend(quality_section["must_have"])

        if not has_tests:
            checklist.append("⚠️ No test files detected - ensure test coverage")

        return checklist[:10]  # Limit checklist size

    def _get_common_issues(
        self, knowledge: dict, files_changed: list[str]
    ) -> list[dict]:
        """Get common issues that might apply to this PR."""
        issues = []
        troubleshooting = knowledge.get("troubleshooting", {}).get("common_errors", {})

        # Check for patterns that might indicate certain issues
        for file in files_changed:
            if "adapter" in file.lower() and "timeout" in troubleshooting:
                issues.append(
                    {
                        "issue": troubleshooting["timeout"].get("issue", ""),
                        "solution": troubleshooting["timeout"].get("solution", ""),
                    }
                )
                break

        return issues[:3]  # Limit to top 3 issues

    def _get_file_guidance(self, knowledge: dict, files_changed: list[str]) -> dict:
        """Get specific guidance for the types of files being changed."""
        guidance = {}

        for file in files_changed:
            if re.search(r"BidAdapter\.(js|java|go|swift|kt)$", file):
                guidance["adapter"] = {
                    "required_methods": knowledge.get("patterns", {})
                    .get("adapter_structure", {})
                    .get("required_methods", []),
                    "optional_methods": knowledge.get("patterns", {})
                    .get("adapter_structure", {})
                    .get("optional_methods", []),
                    "common_imports": knowledge.get("patterns", {})
                    .get("imports", {})
                    .get("required", []),
                }

            elif re.search(r"_spec\.|Test\.", file):
                guidance["tests"] = {
                    "structure": "Follow existing test patterns",
                    "coverage": "Aim for >80% coverage",
                    "edge_cases": "Include error scenarios",
                }

        return guidance

    def _get_generic_context(self, repo_url: str) -> dict:
        """Get generic context when no specific knowledge base exists."""
        return {
            "repository": repo_url,
            "type": "generic",
            "description": "Generic repository",
            "relevant_examples": [],
            "patterns": {},
            "quality_checklist": [
                "Code follows project conventions",
                "Includes appropriate tests",
                "No hardcoded values",
                "Proper error handling",
            ],
            "common_issues": [],
            "file_guidance": {},
        }
