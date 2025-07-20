"""Pattern detection tool for ADK agents."""

from typing import Any

from google.adk.tools import BaseTool


class PatternDetectorTool(BaseTool):
    """Tool for detecting specific patterns in code changes."""

    def __init__(self):
        super().__init__(
            name="detect_code_patterns",
            description="Detects specific patterns relevant to the repository type",
        )

    async def run(self, file_list: list[str], repo_type: str) -> dict[str, Any]:
        """Detect patterns based on repository type.

        Args:
            file_list: List of changed file paths
            repo_type: Type of repository

        Returns:
            Detected patterns and insights
        """
        if repo_type == "prebid":
            return self._detect_prebid_patterns(file_list)
        else:
            return self._detect_generic_patterns(file_list)

    def _detect_prebid_patterns(self, file_list: list[str]) -> dict[str, Any]:
        """Detect Prebid.js specific patterns."""
        patterns = {
            "adapter_changes": {"detected": False, "adapters": [], "type": None},
            "core_changes": {"detected": False, "components": []},
            "module_changes": {"detected": False, "modules": []},
            "test_coverage": {"detected": False, "test_files": []},
        }

        for filepath in file_list:
            # Adapter detection
            if "bidadapter" in filepath.lower() and filepath.endswith(".js"):
                if "test" not in filepath.lower():
                    patterns["adapter_changes"]["detected"] = True
                    adapter_name = filepath.split("/")[-1].replace("BidAdapter.js", "")
                    patterns["adapter_changes"]["adapters"].append(adapter_name)

            # Core changes
            if any(
                core in filepath.lower()
                for core in ["src/", "core/", "auction", "bidding"]
            ):
                patterns["core_changes"]["detected"] = True
                component = filepath.split("/")[-1].replace(".js", "")
                patterns["core_changes"]["components"].append(component)

            # Module detection
            if "modules/" in filepath and "bidadapter" not in filepath.lower():
                patterns["module_changes"]["detected"] = True
                module_name = filepath.split("/")[-1].replace(".js", "")
                patterns["module_changes"]["modules"].append(module_name)

            # Test coverage
            if "test" in filepath.lower() or "spec" in filepath.lower():
                patterns["test_coverage"]["detected"] = True
                patterns["test_coverage"]["test_files"].append(filepath)

        # Determine adapter change type
        if patterns["adapter_changes"]["detected"]:
            adapter_count = len(patterns["adapter_changes"]["adapters"])
            if adapter_count == 1:
                patterns["adapter_changes"]["type"] = "single_adapter"
            else:
                patterns["adapter_changes"]["type"] = "multiple_adapters"

        # Generate insights
        insights = []
        if patterns["adapter_changes"]["detected"]:
            adapters = patterns["adapter_changes"]["adapters"]
            insights.append(
                f"Modifies {len(adapters)} adapter(s): {', '.join(adapters)}"
            )

        if patterns["core_changes"]["detected"]:
            insights.append("Contains core platform changes - affects all adapters")

        if patterns["module_changes"]["detected"]:
            modules = patterns["module_changes"]["modules"]
            insights.append(
                f"Updates {len(modules)} module(s): {', '.join(modules[:3])}"
            )

        if not patterns["test_coverage"]["detected"] and (
            patterns["adapter_changes"]["detected"]
            or patterns["core_changes"]["detected"]
        ):
            insights.append("⚠️ No test coverage detected for code changes")

        return {
            "patterns": patterns,
            "insights": insights,
            "risk_indicators": self._assess_prebid_risk(patterns),
        }

    def _assess_prebid_risk(self, patterns: dict[str, Any]) -> list[str]:
        """Assess risk indicators for Prebid changes."""
        risks = []

        if patterns["core_changes"]["detected"]:
            risks.append("Core changes affect entire platform")

        if (
            patterns["adapter_changes"]["detected"]
            and not patterns["test_coverage"]["detected"]
        ):
            risks.append("Adapter changes without tests")

        if len(patterns["adapter_changes"]["adapters"]) > 3:
            risks.append("Multiple adapter changes increase complexity")

        return risks

    def _detect_generic_patterns(self, file_list: list[str]) -> dict[str, Any]:
        """Detect generic patterns for non-Prebid repositories."""
        patterns = {
            "language_types": set(),
            "change_categories": [],
            "has_tests": False,
            "has_docs": False,
            "has_config": False,
        }

        for filepath in file_list:
            # Detect language types
            if filepath.endswith(".js") or filepath.endswith(".ts"):
                patterns["language_types"].add("javascript")
            elif filepath.endswith(".py"):
                patterns["language_types"].add("python")
            elif filepath.endswith(".java"):
                patterns["language_types"].add("java")

            # Detect categories
            if "test" in filepath.lower() or "spec" in filepath.lower():
                patterns["has_tests"] = True

            if filepath.endswith((".md", ".rst", ".txt")):
                patterns["has_docs"] = True

            if any(
                config in filepath.lower()
                for config in ["config", ".json", ".yaml", ".yml"]
            ):
                patterns["has_config"] = True

        # Categorize changes
        if patterns["has_tests"] and len(patterns["language_types"]) > 0:
            patterns["change_categories"].append("code_with_tests")
        elif len(patterns["language_types"]) > 0:
            patterns["change_categories"].append("code_without_tests")

        if patterns["has_docs"]:
            patterns["change_categories"].append("documentation")

        if patterns["has_config"]:
            patterns["change_categories"].append("configuration")

        return {
            "patterns": patterns,
            "primary_language": (
                list(patterns["language_types"])[0]
                if patterns["language_types"]
                else "unknown"
            ),
            "categories": patterns["change_categories"],
        }
