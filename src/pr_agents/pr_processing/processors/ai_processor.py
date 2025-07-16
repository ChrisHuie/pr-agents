"""AI-powered processor for generating code summaries."""

import asyncio
from dataclasses import asdict
from typing import Any

from loguru import logger

from src.pr_agents.config.manager import RepositoryStructureManager
from src.pr_agents.pr_processing.processors.base import BaseProcessor, ProcessingResult
from src.pr_agents.services.ai import AIService, BaseAIService


class AIProcessor(BaseProcessor):
    """Generates AI-powered summaries of code changes using LLMs."""

    def __init__(
        self,
        ai_service: BaseAIService | None = None,
        repo_config_manager: RepositoryStructureManager | None = None,
    ):
        """Initialize AI processor.

        Args:
            ai_service: AI service instance (creates default if None)
            repo_config_manager: Repository configuration manager
        """
        self.ai_service = ai_service or AIService()
        # Repository config manager is optional - will be None if not provided
        self.repo_config_manager = repo_config_manager

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

            if not code_data:
                return ProcessingResult(
                    component=self.component_name,
                    success=False,
                    data={},
                    errors=["No code data provided for AI analysis"],
                )

            # Build repository context
            repo_context = self._build_repo_context(repo_url, code_data)

            # Prepare PR metadata
            pr_metadata = {
                "title": metadata.get("title", ""),
                "description": metadata.get("description", ""),
                "base_branch": metadata.get("base", {}).get("ref", "main"),
                "head_branch": metadata.get("head", {}).get("ref", "feature"),
            }

            # Convert dict to CodeChanges object if needed
            from ..models import CodeChanges

            if isinstance(code_data, dict):
                code_data_obj = CodeChanges(**code_data)
            else:
                code_data_obj = code_data

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
        import threading
        
        async_coroutine = self.ai_service.generate_summaries(
            code_changes=code_changes,
            repo_context=repo_context,
            pr_metadata=pr_metadata,
        )
        
        try:
            # Check if we're in an event loop
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop, safe to use asyncio.run
            return asyncio.run(async_coroutine)
        
        # We're in an event loop, use a thread to avoid blocking
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, async_coroutine)
            return future.result()

    def _build_repo_context(
        self, repo_url: str, code_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Build repository context for AI prompts.

        Args:
            repo_url: Repository URL
            code_data: Code change data

        Returns:
            Repository context dictionary
        """
        context = {
            "name": self._extract_repo_name(repo_url),
            "url": repo_url,
        }

        # Try to get repository configuration
        if self.repo_config_manager and repo_url:
            try:
                repo_config = self.repo_config_manager.get_config_for_url(repo_url)
                if repo_config:
                    context.update(
                        {
                            "type": repo_config.get("repo_type", "unknown"),
                            "description": repo_config.get("description", ""),
                            "module_patterns": repo_config.get("module_locations", {}),
                            "structure": {
                                "core_paths": repo_config.get("core_paths", []),
                                "test_paths": repo_config.get("test_paths", []),
                                "doc_paths": repo_config.get("doc_paths", []),
                            },
                        }
                    )
            except Exception as e:
                logger.warning(f"Could not load repo config: {str(e)}")

        # Add language information if available
        if "file_diffs" in code_data:
            languages = self._detect_languages(code_data["file_diffs"])
            if languages:
                context["primary_language"] = languages[0]
                context["languages"] = languages

        return context

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
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 2:
                return f"{parts[-2]}/{parts[-1]}"

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
