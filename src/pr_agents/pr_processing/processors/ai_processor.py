"""AI-powered processor for generating code summaries."""

import asyncio
from dataclasses import asdict
from typing import Any

from loguru import logger

from src.pr_agents.config.unified_manager import UnifiedRepositoryContextManager
from src.pr_agents.pr_processing.processors.base import BaseProcessor, ProcessingResult
from src.pr_agents.services.ai import AIService, BaseAIService


class AIProcessor(BaseProcessor):
    """Generates AI-powered summaries of code changes using LLMs."""

    def __init__(
        self,
        ai_service: BaseAIService | None = None,
        context_manager: UnifiedRepositoryContextManager | None = None,
    ):
        """Initialize AI processor.

        Args:
            ai_service: AI service instance (creates default if None)
            context_manager: Unified repository context manager
        """
        self.ai_service = ai_service or AIService()
        # Context manager provides rich repository understanding
        self.context_manager = context_manager or UnifiedRepositoryContextManager()

    @property
    def component_name(self) -> str:
        """Return the component name."""
        return "ai_summaries"

    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """Process code changes to generate AI summaries.

        This processor expects:
        - code: Extracted code change data
        - metadata: PR metadata (title, description, etc.)
        - repo_url: Repository URL for context
        - pr_url: PR URL for tracking

        Args:
            component_data: Dictionary containing extracted component data

        Returns:
            ProcessingResult with AI-generated summaries
        """
        try:
            # Extract required data
            code_data = component_data.get("code")
            metadata = component_data.get("metadata", {})
            repo_url = component_data.get("repo_url", "")
            pr_url = component_data.get("pr_url", "")
            logger.debug(
                f"AI Processor received repo_url: {repo_url}, pr_url: {pr_url}"
            )

            if not code_data:
                return ProcessingResult(
                    component=self.component_name,
                    success=False,
                    data={},
                    errors=["No code data provided for AI analysis"],
                )

            # Convert dict to CodeChanges object if needed
            from ..models import CodeChanges

            if isinstance(code_data, dict):
                code_data_obj = CodeChanges(**code_data)
            else:
                code_data_obj = code_data

            # Get enriched repository context using unified manager
            repo_context = self._get_enriched_repo_context(
                repo_url, code_data_obj, pr_url
            )

            # Prepare PR metadata
            pr_metadata = {
                "title": metadata.get("title", ""),
                "description": metadata.get("description", ""),
                "base_branch": metadata.get("base", {}).get("ref", "main"),
                "head_branch": metadata.get("head", {}).get("ref", "feature"),
            }

            # Generate summaries (run async in sync context)
            logger.info(f"Generating AI summaries for PR: {pr_metadata.get('title')}")

            # Generate summaries using sync wrapper
            summaries = self._generate_summaries_sync(
                code_data_obj, repo_context, pr_metadata
            )

            logger.info(
                f"Successfully generated AI summaries using {summaries.model_used} "
                f"(cached: {summaries.cached}, tokens: {summaries.total_tokens})"
            )

            return ProcessingResult(
                component=self.component_name,
                success=True,
                data=asdict(summaries),
            )

        except Exception as e:
            logger.error(f"Error in AI processor: {str(e)}")
            return ProcessingResult(
                component=self.component_name,
                success=False,
                data={},
                errors=[f"AI processing error: {str(e)}"],
            )

    def _generate_summaries_sync(self, code_changes, repo_context, pr_metadata):
        """Synchronous wrapper for async generate_summaries.

        Handles both sync and async contexts gracefully without external dependencies.
        """
        import concurrent.futures

        async_coroutine = self.ai_service.generate_summaries(
            code_changes=code_changes,
            repo_context=repo_context,
            pr_metadata=pr_metadata,
        )

        try:
            # Check if we're in an event loop
            asyncio.get_running_loop()
        except RuntimeError:
            # No event loop, safe to use asyncio.run
            return asyncio.run(async_coroutine)

        # We're in an event loop, use a thread to avoid blocking
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, async_coroutine)
            return future.result()

    def _get_enriched_repo_context(
        self, repo_url: str, code_data: Any, pr_url: str = ""
    ) -> dict[str, Any]:
        """Get enriched repository context using unified context manager.

        Args:
            repo_url: Repository URL
            code_data: Code change data
            pr_url: PR URL for tracking

        Returns:
            Repository context dictionary optimized for AI
        """
        # Get AI-optimized context from unified manager with tracking
        context = self.context_manager.get_context_for_ai(repo_url, pr_url or None)

        # Add detected languages from actual file changes
        if hasattr(code_data, "file_diffs"):
            languages = self._detect_languages(code_data.file_diffs)
            if languages:
                # Override with detected languages as they're more accurate
                context["primary_language"] = languages[0]
                context["languages"] = languages

        # Add code change context
        context["change_context"] = self._analyze_change_context(code_data, context)

        logger.debug(
            f"Built enriched context for {repo_url}: {context.get('type', 'unknown')} repository"
        )

        return context

    def _analyze_change_context(
        self, code_data: Any, repo_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze the change context based on repository knowledge.

        Args:
            code_data: Code change data
            repo_context: Repository context

        Returns:
            Change-specific context
        """
        change_context = {
            "change_patterns": [],
            "affected_components": [],
            "review_focus_areas": [],
        }

        # Analyze files to detect patterns
        if hasattr(code_data, "file_diffs"):
            for file_diff in code_data.file_diffs:
                filename = file_diff.filename

                # Check against module patterns if available
                if "module_patterns" in repo_context:
                    for pattern_name, pattern_info in repo_context[
                        "module_patterns"
                    ].items():
                        if self._matches_module_pattern(filename, pattern_info):
                            change_context["affected_components"].append(
                                {
                                    "type": pattern_name,
                                    "name": pattern_info.get(
                                        "display_name", pattern_name
                                    ),
                                    "file": filename,
                                }
                            )

                # Detect common change patterns
                if filename.endswith("_spec.js") or filename.endswith("_test.js"):
                    change_context["change_patterns"].append("test_modification")
                elif filename.endswith(".md"):
                    change_context["change_patterns"].append("documentation_update")

        # Add PR-specific patterns from agent context
        if "pr_patterns" in repo_context:
            # This would match against the patterns defined in agent context
            # For now, we'll note that patterns are available
            change_context["has_pr_patterns"] = True

        # Deduplicate
        change_context["affected_components"] = list(
            {
                (comp["type"], comp["file"]): comp
                for comp in change_context["affected_components"]
            }.values()
        )
        change_context["change_patterns"] = list(set(change_context["change_patterns"]))

        return change_context

    def _matches_module_pattern(
        self, filename: str, pattern_info: dict[str, Any]
    ) -> bool:
        """Check if filename matches a module pattern.

        Args:
            filename: File path to check
            pattern_info: Pattern information dict

        Returns:
            True if matches
        """
        # Check if file is in specified paths
        for path in pattern_info.get("paths", []):
            if filename.startswith(path):
                return True

        # Could be extended to check actual patterns
        return False

    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL.

        Args:
            repo_url: Repository URL

        Returns:
            Repository name (owner/repo format)
        """
        if not repo_url:
            return "unknown"

        # Handle GitHub URLs
        if "github.com" in repo_url:
            # Extract owner/repo from URL like https://github.com/owner/repo
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 5 and parts[2] == "github.com":
                return f"{parts[3]}/{parts[4]}"

        return repo_url

    def _detect_languages(self, file_diffs: list[dict[str, Any]]) -> list[str]:
        """Detect programming languages from file extensions.

        Args:
            file_diffs: List of file diff data

        Returns:
            List of detected languages (most common first)
        """
        language_map = {
            # JavaScript ecosystem (Prebid.js)
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".mjs": "JavaScript",
            ".cjs": "JavaScript",
            # Java ecosystem (Prebid Server Java)
            ".java": "Java",
            ".scala": "Scala",
            ".kt": "Kotlin",
            ".groovy": "Groovy",
            # Go ecosystem (Prebid Server Go)
            ".go": "Go",
            # Mobile ecosystems
            ".swift": "Swift",  # iOS
            ".m": "Objective-C",  # iOS
            ".mm": "Objective-C++",  # iOS
            ".h": "C/C++ Header",  # iOS/Android
            # Web technologies
            ".html": "HTML",
            ".htm": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".sass": "Sass",
            ".less": "Less",
            # Configuration and data
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".xml": "XML",
            ".toml": "TOML",
            ".ini": "INI",
            ".properties": "Properties",
            ".gradle": "Gradle",
            ".pom": "Maven POM",
            # Documentation
            ".md": "Markdown",
            ".rst": "reStructuredText",
            ".adoc": "AsciiDoc",
            ".txt": "Text",
            # Scripts and tools
            ".sh": "Shell",
            ".bash": "Bash",
            ".zsh": "Zsh",
            ".ps1": "PowerShell",
            ".bat": "Batch",
            ".cmd": "Batch",
            # Other languages that might appear
            ".py": "Python",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".vb": "Visual Basic",
            ".fs": "F#",
            ".cpp": "C++",
            ".cc": "C++",
            ".cxx": "C++",
            ".c": "C",
            ".rs": "Rust",
            ".r": "R",
            ".lua": "Lua",
            ".pl": "Perl",
            ".sql": "SQL",
            # Build and package files
            ".dockerfile": "Dockerfile",
            ".makefile": "Makefile",
            ".cmake": "CMake",
            ".bazel": "Bazel",
            ".bzl": "Bazel",
            # Prebid-specific
            ".pegjs": "PEG.js",  # Parser grammar files sometimes used
        }

        language_counts = {}

        for diff in file_diffs:
            # Handle both dict and FileDiff object
            if hasattr(diff, "filename"):
                filename = diff.filename.lower()
            else:
                filename = diff.get("filename", "").lower()

            # Special case for files without extensions
            if "/" in filename:
                basename = filename.split("/")[-1]
                if basename in [
                    "dockerfile",
                    "makefile",
                    "gemfile",
                    "rakefile",
                    "brewfile",
                ]:
                    lang = basename.capitalize()
                    language_counts[lang] = language_counts.get(lang, 0) + 1
                    continue

            # Check extensions
            for ext, lang in language_map.items():
                if filename.endswith(ext):
                    language_counts[lang] = language_counts.get(lang, 0) + 1
                    break

        # Sort by count
        sorted_languages = sorted(
            language_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return [lang for lang, _ in sorted_languages]
