"""
Agent-specific context loader for enhanced AI understanding.
"""

from pathlib import Path

from loguru import logger


class AgentContextLoader:
    """Loads agent-specific context files for enhanced AI understanding."""

    def __init__(self, config_dir: Path | str | None = None):
        """
        Initialize context loader.

        Args:
            config_dir: Configuration directory (defaults to "config")
        """
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.project_root = Path.cwd()

        # Map of AI providers to their context files
        self.provider_context_files = {
            "claude": ["claude.md"],
            "claude-adk": ["claude.md", "agents.md"],
            "gemini": ["gemini.md"],
            "google-adk": ["gemini.md", "agents.md"],
            "adk": ["agents.md"],
            "openai": ["openai.md"],
        }

    def load_context_for_pr(self, ai_provider: str, repo_full_name: str) -> str:
        """
        Load all relevant context for analyzing a PR.

        Priority order:
        1. Repository-specific agent context (highest priority)
        2. Repository knowledge base
        3. Project-level agent context
        4. Project-level CLAUDE.md

        Args:
            ai_provider: AI provider name (claude, gemini, etc.)
            repo_full_name: Full repository name (e.g., "prebid/Prebid.js")

        Returns:
            Combined context string
        """
        context_parts = []

        # 1. Load project-level CLAUDE.md (general project context)
        project_context = self._read_file(self.project_root / "CLAUDE.md")
        if project_context:
            context_parts.append("# Project Context (CLAUDE.md)\n\n" + project_context)

        # 2. Load project-level agent context
        project_agent_context = self._load_project_agent_context(ai_provider)
        if project_agent_context:
            context_parts.append(project_agent_context)

        # 3. Load repository-specific knowledge
        repo_knowledge = self._load_repository_knowledge(repo_full_name)
        if repo_knowledge:
            context_parts.append(repo_knowledge)

        # 4. Load repository-specific agent context (highest priority)
        repo_agent_context = self._load_repository_agent_context(
            ai_provider, repo_full_name
        )
        if repo_agent_context:
            context_parts.append(repo_agent_context)

        return "\n\n---\n\n".join(context_parts)

    def _load_project_agent_context(self, ai_provider: str) -> str | None:
        """Load project-level agent context files."""
        provider_key = ai_provider.lower()

        if provider_key not in self.provider_context_files:
            return None

        context_parts = []
        for filename in self.provider_context_files[provider_key]:
            content = self._read_file(self.project_root / filename.upper())
            if not content:
                content = self._read_file(self.project_root / filename)

            if content:
                context_parts.append(
                    f"# Project Agent Context ({filename})\n\n{content}"
                )

        return "\n\n".join(context_parts) if context_parts else None

    def _load_repository_knowledge(self, repo_full_name: str) -> str | None:
        """Load repository knowledge from YAML (already processed)."""
        # This would integrate with the existing knowledge loader
        # For now, we'll just note this is where it would plug in
        return None  # Will be provided by RepositoryKnowledgeLoader

    def _load_repository_agent_context(
        self, ai_provider: str, repo_full_name: str
    ) -> str | None:
        """
        Load repository-specific agent context.

        Structure:
        config/
        ├── agent-context/
        │   ├── repositories/
        │   │   ├── prebid-js/
        │   │   │   ├── claude.md      # Claude-specific context for Prebid.js
        │   │   │   ├── gemini.md      # Gemini-specific context for Prebid.js
        │   │   │   └── agents.md      # ADK agent context for Prebid.js
        """
        provider_key = ai_provider.lower()

        if provider_key not in self.provider_context_files:
            return None

        # Extract just repo name from full name (e.g., "prebid/Prebid.js" -> "prebid-js")
        repo_name = self._extract_repo_name(repo_full_name)
        repo_agent_dir = self.config_dir / "agent-context" / "repositories" / repo_name

        context_parts = []
        for filename in self.provider_context_files[provider_key]:
            filepath = repo_agent_dir / filename
            content = self._read_file(filepath)

            if content:
                context_parts.append(
                    f"# Repository Agent Context ({repo_full_name} - {filename})\n\n{content}"
                )

        return "\n\n".join(context_parts) if context_parts else None

    def _read_file(self, filepath: Path) -> str | None:
        """
        Read a context file.

        Args:
            filepath: Path to file

        Returns:
            File content or None if not found
        """
        if filepath.exists():
            try:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read().strip()
                    logger.debug(f"Loaded context from {filepath}")
                    return content
            except Exception as e:
                logger.error(f"Error reading context file {filepath}: {e}")

        return None

    def create_repository_context_structure(self, repo_full_name: str) -> Path:
        """
        Create directory structure for repository-specific agent context.

        Args:
            repo_full_name: Full repository name

        Returns:
            Path to repository context directory
        """
        repo_name = self._extract_repo_name(repo_full_name)
        repo_agent_dir = self.config_dir / "agent-context" / "repositories" / repo_name
        repo_agent_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created agent context directory: {repo_agent_dir}")
        return repo_agent_dir

    def _extract_repo_name(self, repo_full_name: str) -> str:
        """
        Extract repository name and convert to directory format.

        Examples:
            "prebid/Prebid.js" -> "prebid-js"
            "prebid/prebid-server" -> "prebid-server"

        Args:
            repo_full_name: Full repository name

        Returns:
            Directory-friendly repo name
        """
        # Handle owner/repo format
        if "/" in repo_full_name:
            repo_name = repo_full_name.split("/")[-1]
        else:
            repo_name = repo_full_name

        # Convert to lowercase and replace dots with hyphens
        return repo_name.lower().replace(".", "-")
