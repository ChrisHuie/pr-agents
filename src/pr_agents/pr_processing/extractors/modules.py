"""Module extractor for PR analysis."""

from typing import Any

from github import PullRequest
from loguru import logger

from src.pr_agents.logging_config import (
    log_error_with_context,
    log_function_entry,
    log_function_exit,
)
from src.pr_agents.pr_processing.extractors.base import BaseExtractor


class ModuleExtractor(BaseExtractor):
    """Extracts module structure and relationships from repositories.

    This extractor identifies modules within a repository based on
    configured patterns and categorizes them by type.
    """

    def __init__(self, github_client: Any) -> None:
        """Initialize the module extractor.

        Args:
            github_client: GitHub client (not used by this extractor)
        """
        super().__init__(github_client)
        self.module_patterns: dict[str, list[str]] = {}
        self.repo_config: dict[str, Any] | None = None

    @property
    def component_name(self) -> str:
        """Name of the component this extractor handles."""
        return "modules"

    def set_repository_config(self, config: dict[str, Any]) -> None:
        """Set repository-specific configuration.

        Args:
            config: Repository configuration with module patterns
        """
        self.repo_config = config
        self.module_patterns = config.get("module_locations", {})
        logger.debug(f"Module patterns loaded: {list(self.module_patterns.keys())}")

    def extract(self, pr_data: Any) -> dict[str, Any]:
        """Extract module information from PR data.

        Args:
            pr_data: GitHub PR object or dictionary with PR data

        Returns:
            Dictionary containing:
            - modules: List of identified modules with categorization
            - module_categories: Count by category
            - primary_module_type: Most common module type
            - module_dependencies: Detected dependencies between modules
        """
        log_function_entry("extract", pr_data=type(pr_data).__name__)

        if isinstance(pr_data, dict):
            # Handle dictionary input (for testing)
            files = pr_data.get("files", [])
            repo_name = pr_data.get("repository", "unknown")
        elif isinstance(pr_data, PullRequest.PullRequest):
            # Handle actual GitHub PR object
            files = [f.filename for f in pr_data.get_files()]
            repo_name = pr_data.base.repo.full_name
        else:
            logger.error(f"Invalid PR data type: {type(pr_data)}")
            return self._empty_result()

        try:
            # Extract modules from files
            modules = self._identify_modules(files)

            # Categorize modules
            categorized = self._categorize_modules(modules)

            # Analyze dependencies (simplified for now)
            dependencies = self._extract_dependencies(modules, files)

            result = {
                "modules": modules,
                "module_categories": self._count_by_category(categorized),
                "primary_module_type": self._get_primary_type(categorized),
                "module_dependencies": dependencies,
                "total_modules": len(modules),
                "repository": repo_name,
            }

            log_function_exit("extract", result=f"{len(modules)} modules found")
            return result

        except Exception as e:
            log_error_with_context(e, f"Error extracting modules from {repo_name}")
            return self._empty_result()

    def _identify_modules(self, files: list[str]) -> list[dict[str, Any]]:
        """Identify modules from file paths.

        Args:
            files: List of file paths

        Returns:
            List of module dictionaries
        """
        modules = []
        seen_modules = set()

        for file_path in files:
            module_info = self._extract_module_from_path(file_path)
            if module_info and module_info["name"] not in seen_modules:
                modules.append(module_info)
                seen_modules.add(module_info["name"])

        return modules

    def _extract_module_from_path(self, file_path: str) -> dict[str, Any] | None:
        """Extract module information from a file path.

        Args:
            file_path: Path to the file

        Returns:
            Module information or None
        """
        # Check if it's a test file
        if self._is_test_file(file_path):
            return None

        # Try to match against configured patterns
        for module_type, config in self.module_patterns.items():
            paths = config.get("paths", [])
            naming_pattern = config.get("naming_pattern", "")

            for path_pattern in paths:
                if self._matches_pattern(file_path, path_pattern):
                    module_name = self._extract_module_name(file_path, naming_pattern)
                    if module_name:
                        return {
                            "name": module_name,
                            "type": module_type,
                            "path": file_path,
                            "category": self._determine_category(module_type),
                        }

        # Check for generic module patterns
        if "module" in file_path.lower() or "/src/" in file_path:
            parts = file_path.split("/")
            module_name = None

            # Extract module name from path
            for i, part in enumerate(parts):
                if part in ["modules", "src", "lib", "libraries"]:
                    if i + 1 < len(parts):
                        module_name = parts[i + 1].replace(".js", "").replace(".py", "")
                        break

            if module_name:
                return {
                    "name": module_name,
                    "type": "generic",
                    "path": file_path,
                    "category": "utility",
                }

        return None

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches a pattern.

        Args:
            file_path: The file path to check
            pattern: The pattern to match (supports * wildcards)

        Returns:
            True if matches
        """
        import fnmatch

        return fnmatch.fnmatch(file_path, pattern)

    def _extract_module_name(
        self, file_path: str, naming_pattern: str
    ) -> str | None:
        """Extract module name from file path based on naming pattern.

        Args:
            file_path: The file path
            naming_pattern: Pattern like "endsWith('BidAdapter')"

        Returns:
            Module name or None
        """
        import os

        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]

        # Handle endsWith pattern
        if "endsWith" in naming_pattern:
            suffix = naming_pattern.split("'")[1]
            if name_without_ext.endswith(suffix):
                return name_without_ext

        # Handle startsWith pattern
        elif "startsWith" in naming_pattern:
            prefix = naming_pattern.split("'")[1]
            if name_without_ext.startswith(prefix):
                return name_without_ext

        # Default: return filename without extension
        return name_without_ext

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file.

        Args:
            file_path: Path to check

        Returns:
            True if test file
        """
        test_indicators = ["test", "spec", "__tests__", "tests/"]
        return any(indicator in file_path.lower() for indicator in test_indicators)

    def _categorize_modules(
        self, modules: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Categorize modules by type.

        Args:
            modules: List of module dictionaries

        Returns:
            Dictionary mapping categories to module lists
        """
        categorized = {}
        for module in modules:
            category = module["category"]
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(module)
        return categorized

    def _determine_category(self, module_type: str) -> str:
        """Determine category from module type.

        Args:
            module_type: The module type

        Returns:
            Category name
        """
        # Map types to categories
        category_map = {
            "bid_adapter": "adapter",
            "analytics_adapter": "adapter",
            "rtd_provider": "provider",
            "id_system": "identity",
            "core": "core",
            "library": "utility",
            "generic": "utility",
        }
        return category_map.get(module_type, "other")

    def _count_by_category(
        self, categorized: dict[str, list[dict[str, Any]]]
    ) -> dict[str, int]:
        """Count modules by category.

        Args:
            categorized: Categorized modules

        Returns:
            Count by category
        """
        return {category: len(modules) for category, modules in categorized.items()}

    def _get_primary_type(
        self, categorized: dict[str, list[dict[str, Any]]]
    ) -> str | None:
        """Get the primary module type.

        Args:
            categorized: Categorized modules

        Returns:
            Primary type or None
        """
        if not categorized:
            return None

        # Find category with most modules
        max_category = max(categorized.items(), key=lambda x: len(x[1]))
        return max_category[0]

    def _extract_dependencies(
        self, modules: list[dict[str, Any]], files: list[str]
    ) -> dict[str, list[str]]:
        """Extract dependencies between modules (simplified).

        Args:
            modules: List of identified modules
            files: All files in the PR

        Returns:
            Dictionary mapping modules to their dependencies
        """
        # This is a simplified implementation
        # In a real implementation, you would parse import statements
        dependencies = {}

        for module in modules:
            deps = []

            # Check for common dependency patterns in the path
            if "adapter" in module["type"]:
                # Adapters often depend on core modules
                deps.append("core")

            if module["name"] not in dependencies:
                dependencies[module["name"]] = deps

        return dependencies

    def _empty_result(self) -> dict[str, Any]:
        """Return empty result structure.

        Returns:
            Empty module extraction result
        """
        return {
            "modules": [],
            "module_categories": {},
            "primary_module_type": None,
            "module_dependencies": {},
            "total_modules": 0,
            "repository": "unknown",
        }
