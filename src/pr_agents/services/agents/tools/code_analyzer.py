"""Code analysis tool for ADK agents."""

from typing import Any

from google.adk.tools import BaseTool


class CodeAnalyzerTool(BaseTool):
    """Tool for analyzing code changes and extracting insights."""

    def __init__(self):
        super().__init__(
            name="analyze_code_changes",
            description="Analyzes code changes to extract patterns, complexity, and impact",
        )

    async def run(
        self, file_diffs: list[dict[str, Any]], analysis_type: str = "all"
    ) -> dict[str, Any]:
        """Analyze code changes.

        Args:
            file_diffs: List of file diff dictionaries
            analysis_type: Type of analysis to perform

        Returns:
            Analysis results
        """
        results = {}

        if analysis_type in ["complexity", "all"]:
            results["complexity"] = self._analyze_complexity(file_diffs)

        if analysis_type in ["patterns", "all"]:
            results["patterns"] = self._detect_patterns(file_diffs)

        if analysis_type in ["impact", "all"]:
            results["impact"] = self._assess_impact(file_diffs)

        return results

    def _analyze_complexity(self, file_diffs: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze code complexity based on changes."""
        total_changes = sum(
            d.get("additions", 0) + d.get("deletions", 0) for d in file_diffs
        )
        total_additions = sum(d.get("additions", 0) for d in file_diffs)
        total_deletions = sum(d.get("deletions", 0) for d in file_diffs)

        # Determine complexity level
        if total_changes > 1000:
            complexity_level = "very_high"
            risk_assessment = "Extensive changes require thorough testing"
        elif total_changes > 500:
            complexity_level = "high"
            risk_assessment = "Significant changes with moderate risk"
        elif total_changes > 100:
            complexity_level = "medium"
            risk_assessment = "Standard changes with manageable risk"
        else:
            complexity_level = "low"
            risk_assessment = "Minor changes with minimal risk"

        return {
            "level": complexity_level,
            "total_changes": total_changes,
            "additions": total_additions,
            "deletions": total_deletions,
            "net_change": total_additions - total_deletions,
            "risk_assessment": risk_assessment,
            "files_affected": len(file_diffs),
        }

    def _detect_patterns(self, file_diffs: list[dict[str, Any]]) -> dict[str, Any]:
        """Detect common code patterns."""
        patterns = {
            "new_features": False,
            "refactoring": False,
            "bug_fixes": False,
            "test_updates": False,
            "documentation": False,
            "configuration": False,
        }

        for diff in file_diffs:
            filename = diff.get("filename", "").lower()
            additions = diff.get("additions", 0)
            deletions = diff.get("deletions", 0)

            # Pattern detection logic
            if additions > deletions * 2 and additions > 50:
                patterns["new_features"] = True

            if deletions > additions and deletions > 20:
                patterns["refactoring"] = True

            if "test" in filename or "spec" in filename:
                patterns["test_updates"] = True

            if filename.endswith((".md", ".rst", ".txt")):
                patterns["documentation"] = True

            if filename.endswith((".json", ".yaml", ".yml", ".config")):
                patterns["configuration"] = True

            if 5 < additions < 50 and 5 < deletions < 50:
                patterns["bug_fixes"] = True

        # Determine primary pattern
        active_patterns = [k for k, v in patterns.items() if v]
        primary_pattern = active_patterns[0] if active_patterns else "unknown"

        return {
            "detected_patterns": patterns,
            "active_patterns": active_patterns,
            "primary_pattern": primary_pattern,
            "pattern_count": len(active_patterns),
        }

    def _assess_impact(self, file_diffs: list[dict[str, Any]]) -> dict[str, Any]:
        """Assess the impact of changes."""
        critical_files = 0
        test_coverage = False
        core_changes = False

        for diff in file_diffs:
            filename = diff.get("filename", "").lower()

            # Check for critical files
            if any(
                critical in filename
                for critical in ["core", "auth", "security", "config"]
            ):
                critical_files += 1
                core_changes = True

            # Check for test coverage
            if "test" in filename or "spec" in filename:
                test_coverage = True

        # Determine impact level
        if critical_files > 2 or (core_changes and not test_coverage):
            impact_level = "critical"
            recommendation = "Requires careful review and extensive testing"
        elif critical_files > 0:
            impact_level = "high"
            recommendation = "Important changes requiring thorough review"
        elif len(file_diffs) > 10:
            impact_level = "medium"
            recommendation = "Moderate scope changes, standard review process"
        else:
            impact_level = "low"
            recommendation = "Minor changes, standard review sufficient"

        return {
            "level": impact_level,
            "critical_files": critical_files,
            "has_test_coverage": test_coverage,
            "affects_core": core_changes,
            "recommendation": recommendation,
        }
