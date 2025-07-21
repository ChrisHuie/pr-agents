"""
Markdown context loader for repository-specific knowledge.
"""

from pathlib import Path

from loguru import logger


class MarkdownContextLoader:
    """Loads markdown context files for repositories."""

    def __init__(self, config_dir: Path | str):
        """
        Initialize the markdown context loader.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir)
        self.context_dirs = [
            self.config_dir / "prebid-context",  # Prebid-specific contexts
            self.config_dir / "repository-context",  # General repository contexts
        ]

    def load_markdown_context(self, repo_full_name: str) -> str | None:
        """
        Load markdown context for a repository.

        Args:
            repo_full_name: Full repository name (e.g., "prebid/Prebid.js")

        Returns:
            Markdown content or None if not found
        """
        # Extract repo name and normalize
        repo_name = self._normalize_repo_name(repo_full_name)

        # Look for context files in priority order
        for context_dir in self.context_dirs:
            if not context_dir.exists():
                continue

            # Try different naming conventions
            possible_files = [
                context_dir / f"{repo_name}.md",
                context_dir / f"{repo_name.lower()}.md",
                context_dir / f"{repo_name.replace('-', '_')}.md",
            ]

            for file_path in possible_files:
                if file_path.exists():
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read().strip()
                            logger.info(f"Loaded markdown context from {file_path}")
                            return content
                    except Exception as e:
                        logger.error(f"Error reading markdown context {file_path}: {e}")

        logger.debug(f"No markdown context found for {repo_full_name}")
        return None

    def _normalize_repo_name(self, repo_full_name: str) -> str:
        """
        Normalize repository name for file lookup.

        Examples:
            "prebid/Prebid.js" -> "prebid-js"
            "prebid/prebid-server" -> "prebid-server"
            "prebid/prebid-mobile-android" -> "prebid-mobile-android"

        Args:
            repo_full_name: Full repository name

        Returns:
            Normalized name for file lookup
        """
        # Handle owner/repo format
        if "/" in repo_full_name:
            _, repo_name = repo_full_name.split("/", 1)
        else:
            repo_name = repo_full_name

        # Convert dots to hyphens and lowercase
        normalized = repo_name.lower().replace(".", "-")

        return normalized

    def list_available_contexts(self) -> dict[str, list[str]]:
        """
        List all available markdown context files.

        Returns:
            Dictionary mapping context directory to list of available contexts
        """
        available = {}

        for context_dir in self.context_dirs:
            if not context_dir.exists():
                continue

            contexts = []
            for file_path in context_dir.glob("*.md"):
                contexts.append(file_path.stem)

            if contexts:
                available[context_dir.name] = sorted(contexts)

        return available
