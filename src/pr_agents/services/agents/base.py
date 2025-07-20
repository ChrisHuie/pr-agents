"""Base classes for ADK-based summary agents."""

import asyncio
import os
from abc import ABC, abstractmethod
from typing import Any

from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import BaseTool
from loguru import logger

from .context.enhanced_repository import EnhancedRepositoryContextProvider


class BaseSummaryAgent(ABC):
    """Base class for all persona-specific summary agents."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        """Initialize the base agent.

        Args:
            model: The LLM model to use for this agent
        """
        self.model = model
        self._agent = None
        self._runner = None
        self._session_id = None
        self._context_provider = EnhancedRepositoryContextProvider()

    @property
    def agent(self) -> Agent:
        """Get or create the ADK agent instance."""
        if self._agent is None:
            self._agent = self.create_agent()
        return self._agent

    @property
    def runner(self) -> InMemoryRunner:
        """Get or create the runner instance."""
        if self._runner is None:
            self._runner = InMemoryRunner(self.agent)
        return self._runner

    @abstractmethod
    def create_agent(self) -> Agent:
        """Create and configure the ADK agent instance."""
        pass

    @abstractmethod
    def get_instructions(self) -> str:
        """Get persona-specific instructions for the agent."""
        pass

    @abstractmethod
    def get_tools(self) -> list[BaseTool]:
        """Get the tools this agent should have access to."""
        pass

    async def generate_summary_async(
        self, code_changes: dict[str, Any], repo_context: dict[str, Any]
    ) -> str:
        """Generate a summary using ADK runner (async version).

        Args:
            code_changes: Dictionary containing file diffs, additions, deletions
            repo_context: Repository-specific context (patterns, conventions, etc.)

        Returns:
            Generated summary text
        """
        try:
            # Prepare the input for the agent
            agent_input = self._prepare_input(code_changes, repo_context)

            # Create session if needed
            if self._session_id is None:
                session_service = self.runner._in_memory_session_service
                session = await session_service.create_session(
                    user_id="pr_analyzer", app_name="pr_agents"
                )
                self._session_id = session.id

            # Collect response from event stream
            response_parts = []
            event_count = 0

            async for event in self.runner.run_async(
                user_id="pr_analyzer",
                session_id=self._session_id,
                new_message=agent_input,
            ):
                event_count += 1
                if hasattr(event, "text") and event.text:
                    response_parts.append(event.text)
                    logger.debug(f"ADK event {event_count}: received text chunk")

            final_response = "".join(response_parts).strip()
            logger.debug(f"ADK generated summary: {len(final_response)} chars")

            return final_response if final_response else "Unable to generate summary"

        except Exception as e:
            logger.error(f"Error in ADK agent async generation: {str(e)}")
            # Fallback to direct Gemini API
            return self._generate_with_gemini_api(code_changes, repo_context)

    def generate_summary(
        self, code_changes: dict[str, Any], repo_context: dict[str, Any]
    ) -> str:
        """Generate a summary based on code changes and repository context.

        Args:
            code_changes: Dictionary containing file diffs, additions, deletions
            repo_context: Repository-specific context (patterns, conventions, etc.)

        Returns:
            Generated summary text
        """
        try:
            # Try to use asyncio.run
            return asyncio.run(self.generate_summary_async(code_changes, repo_context))
        except RuntimeError:
            # If already in an event loop, use the fallback
            logger.warning("Already in event loop, using Gemini API directly")
            return self._generate_with_gemini_api(code_changes, repo_context)

    def _generate_with_gemini_api(
        self, code_changes: dict[str, Any], repo_context: dict[str, Any]
    ) -> str:
        """Fallback method using direct Gemini API instead of ADK.

        Args:
            code_changes: Dictionary containing file diffs, additions, deletions
            repo_context: Repository-specific context

        Returns:
            Generated summary text
        """
        try:
            import google.generativeai as genai

            # Configure Gemini
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
            if not api_key:
                return "Error: No Gemini API key found"

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.model)

            # Prepare prompt with instructions
            prompt = f"{self.get_instructions()}\n\n{self._prepare_input(code_changes, repo_context)}"

            # Generate response
            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Error using Gemini API: {str(e)}")
            return f"Error generating summary: {str(e)}"

    def _prepare_input(
        self, code_changes: dict[str, Any], repo_context: dict[str, Any]
    ) -> str:
        """Prepare input prompt for the agent.

        Args:
            code_changes: Code change data
            repo_context: Repository context

        Returns:
            Formatted input string for the agent
        """
        # Format code changes
        files_changed = code_changes.get("changed_files", 0)
        additions = code_changes.get("total_additions", 0)
        deletions = code_changes.get("total_deletions", 0)

        file_list = []
        code_patches = []
        file_names = []

        for diff in code_changes.get("file_diffs", []):
            file_list.append(
                f"- {diff['filename']} (+{diff['additions']}, -{diff['deletions']})"
            )
            file_names.append(diff["filename"])

            # Add the actual code patch if available
            if diff.get("patch"):
                code_patches.append(f"\n### {diff['filename']}")
                code_patches.append("```diff")
                code_patches.append(diff["patch"])
                code_patches.append("```")

        # Get enhanced context if available
        enhanced_context = None
        repo_url = repo_context.get("url", "")
        logger.debug(
            f"Base agent repo_url: {repo_url}, has context provider: {hasattr(self, '_context_provider')}"
        )
        if hasattr(self, "_context_provider") and repo_url:
            enhanced_context = self._context_provider.get_context(repo_url, file_names)

        # Build the prompt
        prompt_parts = [
            "Analyze the following code changes and provide a summary:",
        ]

        # Add PR title if available (Level 3 context)
        pr_title = code_changes.get("pr_title", "")
        if pr_title:
            prompt_parts.append(f"\nPR Title: {pr_title}")

        # Use enhanced context if available
        if enhanced_context:
            prompt_parts.extend(
                [
                    f"\nRepository: {enhanced_context.get('repository', 'unknown')}",
                    f"Type: {enhanced_context.get('type', 'unknown')}",
                    f"Description: {enhanced_context.get('description', '')}",
                    f"Primary Language: {enhanced_context.get('primary_language', '')}",
                    f"Ecosystem: {enhanced_context.get('ecosystem', '')}",
                ]
            )
        else:
            prompt_parts.extend(
                [
                    f"\nRepository Type: {repo_context.get('type', 'unknown')}",
                    f"Repository: {repo_context.get('name', 'unknown')}",
                ]
            )

        prompt_parts.extend(
            [
                "\nCode Statistics:",
                f"- Files Changed: {files_changed}",
                f"- Lines Added: {additions}",
                f"- Lines Deleted: {deletions}",
                "\nModified Files:",
            ]
        )
        prompt_parts.extend(file_list)

        # Add actual code diffs
        if code_patches:
            prompt_parts.append("\n## Actual Code Changes:")
            prompt_parts.extend(code_patches)

        # Add enhanced context elements
        if enhanced_context:
            # Add relevant examples
            if enhanced_context.get("relevant_examples"):
                prompt_parts.append("\n## Relevant Code Examples from Repository:")
                for example in enhanced_context["relevant_examples"][:2]:  # Limit to 2
                    prompt_parts.append(f"\n### {example['description']}")
                    prompt_parts.append("```")
                    prompt_parts.append(
                        example["code"][:500] + "..."
                        if len(example["code"]) > 500
                        else example["code"]
                    )
                    prompt_parts.append("```")

            # Add quality checklist
            if enhanced_context.get("quality_checklist"):
                prompt_parts.append("\n## Quality Considerations for this Repository:")
                for item in enhanced_context["quality_checklist"][:5]:  # Limit to 5
                    prompt_parts.append(f"- {item}")

            # Add file-specific guidance
            if enhanced_context.get("file_guidance"):
                prompt_parts.append("\n## File-Specific Guidelines:")
                for file_type, guidance in enhanced_context["file_guidance"].items():
                    prompt_parts.append(f"\n{file_type.title()}:")
                    if isinstance(guidance, dict):
                        for key, value in guidance.items():
                            if isinstance(value, list):
                                prompt_parts.append(f"- {key}: {', '.join(value[:3])}")
                            else:
                                prompt_parts.append(f"- {key}: {value}")

        # Add repository context if available
        elif "module_patterns" in repo_context:
            prompt_parts.append("\nRepository Module Patterns:")
            for module_type, info in repo_context["module_patterns"].items():
                prompt_parts.append(f"- {module_type}: {info.get('purpose', 'N/A')}")

        prompt_parts.append("\nGenerate a summary based on these code changes.")

        return "\n".join(prompt_parts)
