"""
Filename generator for creating descriptive output filenames.
"""

import re
from typing import Any


class FilenameGenerator:
    """Generate descriptive filenames based on PR/analysis data."""

    @staticmethod
    def generate_pr_filename(data: dict[str, Any], base_name: str | None = None) -> str:
        """
        Generate a descriptive filename for PR analysis.

        Args:
            data: Analysis data containing PR information
            base_name: Optional base name to use if provided

        Returns:
            Descriptive filename (without extension)
        """
        # If user provided a specific base name, check if it's generic
        if base_name and not FilenameGenerator._is_generic_name(base_name):
            return base_name

        # Extract PR number
        pr_number = data.get("pr_number", "")
        if isinstance(pr_number, int):
            pr_number = str(pr_number)
        elif isinstance(pr_number, str) and pr_number.startswith("#"):
            pr_number = pr_number[1:]

        # If we have a PR number, return just "pr{number}"
        if pr_number:
            return f"pr{pr_number}"

        # If we have no PR number, use a fallback
        return "analysis"

    @staticmethod
    def generate_release_filename(
        repo_name: str, release_tag: str, base_name: str | None = None
    ) -> str:
        """
        Generate filename for release analysis.

        Args:
            repo_name: Repository name
            release_tag: Release tag/version
            base_name: Optional base name

        Returns:
            Descriptive filename
        """
        if base_name and not FilenameGenerator._is_generic_name(base_name):
            return base_name

        # Clean release tag
        clean_tag = re.sub(r"[^\w\.\-]", "", release_tag)
        return f"release-{clean_tag}"

    @staticmethod
    def generate_batch_filename(
        batch_type: str,
        identifier: str | None = None,
        base_name: str | None = None,
    ) -> str:
        """
        Generate filename for batch analysis.

        Args:
            batch_type: Type of batch (e.g., "unreleased", "date-range")
            identifier: Optional identifier (e.g., date, branch)
            base_name: Optional base name

        Returns:
            Descriptive filename
        """
        if base_name and not FilenameGenerator._is_generic_name(base_name):
            return base_name

        parts = [batch_type]
        if identifier:
            clean_id = re.sub(r"[^\w\.\-]", "", identifier)
            parts.append(clean_id)

        return "-".join(parts)

    @staticmethod
    def _is_generic_name(name: str) -> bool:
        """Check if a filename is too generic."""
        generic_names = {
            "analysis",
            "report",
            "output",
            "result",
            "summary",
            "pr_analysis",
            "pr_report",
            "full_analysis",
            "data",
        }
        # Remove extension if present
        base = name.rsplit(".", 1)[0].lower()
        return base in generic_names

    @staticmethod
    def _identify_main_module(data: dict[str, Any]) -> str | None:
        """Identify the main module/adapter from PR data using extracted module information."""
        # First check if we have modules data (already extracted by ModuleExtractor)
        if "modules" in data:
            modules_data = data["modules"]
            if isinstance(modules_data, dict):
                modules_list = modules_data.get("modules", [])

                # If single module PR, use that module name
                if len(modules_list) == 1:
                    module = modules_list[0]
                    if isinstance(module, dict):
                        return module.get("name", "")
                    return str(module)

                # If multiple modules, check if we should use "multiple"
                elif len(modules_list) > 1:
                    # If more than 2 modules, use "multiple-modules"
                    if len(modules_list) > 2:
                        return "multiple-modules"

                    # For exactly 2 modules, try to use both names
                    if len(modules_list) == 2:
                        names = []
                        for module in modules_list[:2]:
                            if isinstance(module, dict):
                                names.append(module.get("name", ""))
                            else:
                                names.append(str(module))
                        if all(names):
                            # Clean the names and join them
                            clean_names = [re.sub(r"[^\w\-]", "", n) for n in names]
                            return "-".join(clean_names)

                    # Fallback to first module
                    module = modules_list[0]
                    if isinstance(module, dict):
                        return module.get("name", "")
                    return str(module)

        return None
