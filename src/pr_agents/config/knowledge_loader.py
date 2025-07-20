"""
Repository knowledge loader for enriching configurations.
"""

import json
from pathlib import Path
from typing import Any

import yaml
from loguru import logger


class RepositoryKnowledgeLoader:
    """Loads and merges repository knowledge from multiple sources."""

    def __init__(self, config_dir: Path | str):
        """
        Initialize the knowledge loader.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir)
        self.json_config_dir = self.config_dir / "repositories"
        self.yaml_knowledge_dir = self.config_dir / "repository-knowledge"

    def load_repository_config(self, repo_full_name: str) -> dict[str, Any]:
        """
        Load repository configuration with knowledge enrichment.

        Args:
            repo_full_name: Full repository name (e.g., "prebid/Prebid.js")

        Returns:
            Enriched repository configuration
        """
        # Normalize repo name for file paths
        owner, repo = repo_full_name.split("/", 1)

        # Load base JSON configuration
        json_path = (
            self.json_config_dir / owner / f"{repo.lower().replace('.', '-')}.json"
        )
        config = self._load_json_config(json_path)

        # Load YAML knowledge
        yaml_path = self.yaml_knowledge_dir / f"{repo.lower().replace('.', '-')}.yaml"
        knowledge = self._load_yaml_knowledge(yaml_path)

        # Merge knowledge into config
        if knowledge:
            config = self._merge_knowledge(config, knowledge)

        return config

    def _load_json_config(self, path: Path) -> dict[str, Any]:
        """Load JSON configuration file."""
        if not path.exists():
            logger.warning(f"Configuration file not found: {path}")
            return {}

        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON config {path}: {e}")
            return {}

    def _load_yaml_knowledge(self, path: Path) -> dict[str, Any]:
        """Load YAML knowledge file."""
        if not path.exists():
            logger.debug(f"Knowledge file not found: {path}")
            return {}

        try:
            with open(path) as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML knowledge {path}: {e}")
            return {}

    def _merge_knowledge(
        self, config: dict[str, Any], knowledge: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge knowledge into configuration.

        Args:
            config: Base configuration
            knowledge: Knowledge to merge

        Returns:
            Merged configuration
        """
        # Add repository context
        if "overview" in knowledge:
            config["repository_context"] = {
                "purpose": knowledge["overview"].get("purpose", ""),
                "key_features": knowledge["overview"].get("key_features", []),
                "architecture": knowledge["overview"].get("architecture", {}),
            }

        # Enhance module locations with examples and descriptions
        if (
            "directory_structure" in knowledge
            and "modules" in knowledge["directory_structure"]
        ):
            modules_info = knowledge["directory_structure"]["modules"]

            # Add pattern descriptions to module_locations
            if "patterns" in modules_info and "module_locations" in config:
                for pattern, description in modules_info["patterns"].items():
                    # Map pattern to module type
                    module_type = self._pattern_to_module_type(pattern)
                    if module_type and module_type in config["module_locations"]:
                        config["module_locations"][module_type][
                            "description"
                        ] = description

        # Add code patterns
        if "patterns" in knowledge:
            config["code_patterns"] = knowledge["patterns"]

        # Add common PR patterns
        if "code_examples" in knowledge:
            config["pr_patterns"] = self._extract_pr_patterns(
                knowledge["code_examples"]
            )

        # Add testing requirements
        if "testing" in knowledge:
            config["testing_requirements"] = knowledge["testing"]

        return config

    def _pattern_to_module_type(self, pattern: str) -> str | None:
        """Map file pattern to module type."""
        pattern_map = {
            "*BidAdapter.js": "bid_adapter",
            "*AnalyticsAdapter.js": "analytics_adapter",
            "*IdSystem.js": "id_system",
            "*RtdProvider.js": "rtd_module",
            "*UserModule.js": "user_module",
            "*VideoModule.js": "video_module",
        }
        return pattern_map.get(pattern)

    def _extract_pr_patterns(self, code_examples: dict[str, Any]) -> dict[str, Any]:
        """Extract PR patterns from code examples."""
        patterns = {}

        for module_type, example_info in code_examples.items():
            if isinstance(example_info, dict) and "description" in example_info:
                patterns[module_type] = {
                    "description": example_info["description"],
                    "common_changes": [],
                }

                # Extract common patterns from the code example
                if "code" in example_info:
                    # This is where we could analyze the code to find patterns
                    # For now, just note that we have an example
                    patterns[module_type]["has_example"] = True

        return patterns
