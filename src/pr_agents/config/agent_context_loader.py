"""
Agent context loader for AI-specific repository understanding.
"""

from pathlib import Path
from typing import Any

import yaml
from loguru import logger


class AgentContextLoader:
    """Loads agent-specific context for repositories."""

    def __init__(self, config_dir: Path | str):
        """
        Initialize the agent context loader.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir)
        self.agent_context_dir = self.config_dir / "agent-contexts"

        # Create directory if it doesn't exist
        self.agent_context_dir.mkdir(parents=True, exist_ok=True)

    def load_agent_context(self, repo_full_name: str) -> dict[str, Any]:
        """
        Load agent-specific context for a repository.

        Args:
            repo_full_name: Full repository name (e.g., "prebid/Prebid.js")

        Returns:
            Agent context dictionary
        """
        # Normalize repo name for file path
        _, repo = repo_full_name.split("/", 1)
        filename = f"{repo.lower().replace('.', '-')}-agent.yaml"
        context_path = self.agent_context_dir / filename

        if not context_path.exists():
            logger.debug(f"No agent context found for {repo_full_name}")
            return self._get_default_agent_context()

        try:
            with open(context_path) as f:
                context = yaml.safe_load(f)
                logger.info(f"Loaded agent context for {repo_full_name}")
                return context or {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing agent context {context_path}: {e}")
            return self._get_default_agent_context()

    def _get_default_agent_context(self) -> dict[str, Any]:
        """Return default agent context structure."""
        return {
            "pr_analysis": {
                "common_patterns": [],
                "quality_indicators": {
                    "good_pr": [
                        "Includes tests for new functionality",
                        "Updates documentation when needed",
                        "Follows project conventions",
                    ],
                    "red_flags": [
                        "Large changes without tests",
                        "Breaking changes without documentation",
                        "Inconsistent code style",
                    ],
                },
                "review_focus": [],
            },
            "code_review_guidelines": {
                "required_checks": [],
                "performance_considerations": [],
                "security_considerations": [],
            },
        }

    def save_agent_context(self, repo_full_name: str, context: dict[str, Any]) -> Path:
        """
        Save agent context for a repository.

        Args:
            repo_full_name: Full repository name
            context: Agent context to save

        Returns:
            Path to saved context file
        """
        _, repo = repo_full_name.split("/", 1)
        filename = f"{repo.lower().replace('.', '-')}-agent.yaml"
        context_path = self.agent_context_dir / filename

        with open(context_path, "w") as f:
            yaml.safe_dump(context, f, sort_keys=False, default_flow_style=False)

        logger.info(f"Saved agent context for {repo_full_name} to {context_path}")
        return context_path
