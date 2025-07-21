"""
Repository knowledge loader for loading JSON configs from prebid directory.
"""

import json
from pathlib import Path
from typing import Any

from loguru import logger


class RepositoryKnowledgeLoader:
    """Loads repository configuration from JSON files in config/prebid/."""

    def __init__(self, config_dir: Path | str):
        """
        Initialize the knowledge loader.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir)
        self.prebid_dir = self.config_dir / "prebid"

    def load_repository_config(self, repo_full_name: str) -> dict[str, Any]:
        """
        Load repository configuration from JSON files.

        Args:
            repo_full_name: Full repository name (e.g., "prebid/Prebid.js")

        Returns:
            Repository configuration from JSON
        """
        # Handle different repo name formats
        if "/" in repo_full_name:
            owner, repo = repo_full_name.split("/", 1)
        else:
            # If no owner provided, assume prebid
            owner = "prebid"
            repo = repo_full_name

        # Try different paths based on repo name
        possible_paths = self._get_possible_config_paths(owner, repo)

        for path in possible_paths:
            if path.exists():
                config = self._load_json_config(path)
                if config:
                    logger.debug(f"Loaded config for {repo_full_name} from {path}")
                    return config

        logger.debug(f"No config found for {repo_full_name}")
        return {}

    def _get_possible_config_paths(self, owner: str, repo: str) -> list[Path]:
        """Get possible paths for a repository config."""
        paths = []

        # Normalize repo name
        normalized = repo.lower().replace(".", "-")

        # Direct path: prebid/prebid-js/config.json
        paths.append(self.prebid_dir / normalized / "config.json")

        # Server variants: prebid/prebid-server/config-go.json
        if "server" in normalized:
            base_dir = self.prebid_dir / "prebid-server"
            if "go" in normalized:
                paths.append(base_dir / "config-go.json")
            elif "java" in normalized:
                paths.append(base_dir / "config-java.json")

        # Mobile variants: prebid/prebid-mobile-ios/config.json
        if "mobile" in normalized:
            paths.append(self.prebid_dir / normalized / "config.json")

        # Docs variant: prebid/prebid-docs/config.json
        if "docs" in normalized:
            paths.append(self.prebid_dir / "prebid-docs" / "config.json")

        return paths

    def _load_json_config(self, path: Path) -> dict[str, Any]:
        """Load JSON configuration file."""
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error loading JSON config {path}: {e}")
            return {}
