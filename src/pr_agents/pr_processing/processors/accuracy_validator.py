"""PR Metadata-Code Accuracy Validator processor."""

import re
from dataclasses import asdict
from typing import Any

from loguru import logger

from src.pr_agents.logging_config import log_function_entry, log_function_exit
from src.pr_agents.pr_processing.analysis_models import (
    AccuracyComponents,
    AccuracyRecommendation,
    AccuracyScore,
)
from src.pr_agents.pr_processing.models import ProcessingResult
from src.pr_agents.pr_processing.processors.base import BaseProcessor


class AccuracyValidator(BaseProcessor):
    """Validates that PR metadata accurately reflects code changes.

    This processor works with pre-processed results from metadata and code
    processors to calculate accuracy scores without making any API calls.
    """

    @property
    def component_name(self) -> str:
        """Name of the component this processor handles."""
        return "accuracy_validation"

    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """Process accuracy validation between metadata and code.

        Args:
            component_data: Dictionary containing:
                - metadata_results: Results from metadata processor
                - code_results: Results from code processor
                - modules_results: Optional results from module extractor

        Returns:
            ProcessingResult with accuracy scores and recommendations
        """
        log_function_entry("process", component="accuracy_validation")

        try:
            # Extract pre-processed results
            metadata_results = component_data.get("metadata_results", {})
            code_results = component_data.get("code_results", {})
            modules_results = component_data.get("modules_results", {})

            if not metadata_results or not code_results:
                logger.warning("Missing required results for accuracy validation")
                return ProcessingResult(
                    component=self.component_name,
                    success=False,
                    errors=["Missing metadata or code results"],
                )

            # Calculate accuracy score
            accuracy_score = self._calculate_accuracy(
                metadata_results, code_results, modules_results
            )

            log_function_exit(
                "process", result=f"accuracy={accuracy_score.total_score:.1f}"
            )

            return ProcessingResult(
                component=self.component_name, success=True, data=asdict(accuracy_score)
            )

        except Exception as e:
            logger.error(f"Error in accuracy validation: {e}")
            return ProcessingResult(
                component=self.component_name, success=False, errors=[str(e)]
            )

    def _calculate_accuracy(
        self, metadata: dict[str, Any], code: dict[str, Any], modules: dict[str, Any]
    ) -> AccuracyScore:
        """Calculate accuracy score between metadata and code.

        Args:
            metadata: Metadata processor results
            code: Code processor results
            modules: Module extractor results (optional)

        Returns:
            AccuracyScore with components and recommendations
        """
        # Extract relevant data
        title_analysis = metadata.get("title_analysis", {})
        description_analysis = metadata.get("description_analysis", {})
        file_analysis = code.get("file_analysis", {})
        pattern_analysis = code.get("pattern_analysis", {})

        # Calculate component scores
        title_accuracy = self._score_title_accuracy(
            title_analysis, file_analysis, modules
        )
        description_accuracy = self._score_description_accuracy(
            description_analysis, file_analysis, pattern_analysis
        )
        completeness = self._score_completeness(metadata, code, modules)
        specificity = self._score_specificity(title_analysis, description_analysis)

        # Create component scores
        components = AccuracyComponents(
            title_accuracy=title_accuracy,
            description_accuracy=description_accuracy,
            completeness=completeness,
            specificity=specificity,
        )

        # Calculate weighted total (30% title, 40% description, 20% completeness, 10% specificity)
        total_score = (
            title_accuracy * 0.3
            + description_accuracy * 0.4
            + completeness * 0.2
            + specificity * 0.1
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(components, metadata, code)

        # Determine accuracy level
        accuracy_level = self._get_accuracy_level(total_score)

        # Calculate mention ratios
        files_mentioned_ratio = self._calculate_files_mentioned_ratio(
            title_analysis, description_analysis, file_analysis
        )
        modules_mentioned_ratio = self._calculate_modules_mentioned_ratio(
            title_analysis, description_analysis, modules
        )

        return AccuracyScore(
            total_score=total_score,
            component_scores=components,
            recommendations=recommendations,
            accuracy_level=accuracy_level,
            files_mentioned_ratio=files_mentioned_ratio,
            modules_mentioned_ratio=modules_mentioned_ratio,
        )

    def _score_title_accuracy(
        self,
        title_analysis: dict[str, Any],
        file_analysis: dict[str, Any],
        modules: dict[str, Any],
    ) -> float:
        """Score how well the title reflects the changes.

        Args:
            title_analysis: Title analysis data
            file_analysis: File analysis data
            modules: Module data

        Returns:
            Score 0-100
        """
        score = 0.0
        title = title_analysis.get("title", "").lower()

        # Check if title mentions key files or modules (40 points)
        files_changed = file_analysis.get("files_changed", [])
        if files_changed:
            mentioned_files = sum(
                1
                for f in files_changed
                if self._fuzzy_match_in_text(
                    self._extract_filename(f["filename"]), title
                )
            )
            score += min(40, (mentioned_files / len(files_changed)) * 40)

        # Check if title mentions modules (20 points)
        if modules:
            module_list = modules.get("modules", [])
            if module_list:
                mentioned_modules = sum(
                    1
                    for m in module_list
                    if self._fuzzy_match_in_text(m["name"], title)
                )
                score += min(20, (mentioned_modules / len(module_list)) * 20)

        # Check for action verb accuracy (20 points)
        action_verbs = ["add", "fix", "update", "remove", "refactor", "implement"]
        has_action = any(verb in title for verb in action_verbs)
        if has_action:
            score += 20

        # Check scope precision (20 points)
        # Does the title scope match the actual scope?
        total_changes = file_analysis.get("total_changes", 0)
        if total_changes > 0:
            if total_changes > 500 and "major" not in title and "large" not in title:
                score += 0  # Large change not indicated
            elif total_changes < 50 and ("major" in title or "large" in title):
                score += 0  # Small change over-scoped
            else:
                score += 20  # Scope matches

        return min(100, score)

    def _score_description_accuracy(
        self,
        description_analysis: dict[str, Any],
        file_analysis: dict[str, Any],
        pattern_analysis: dict[str, Any],
    ) -> float:
        """Score how well the description covers the changes.

        Args:
            description_analysis: Description analysis data
            file_analysis: File analysis data
            pattern_analysis: Pattern analysis data

        Returns:
            Score 0-100
        """
        score = 0.0

        # No description = 0 score
        if not description_analysis.get("has_description", False):
            return 0.0

        description = description_analysis.get("description", "").lower()

        # File coverage (30 points)
        files_changed = file_analysis.get("files_changed", [])
        if files_changed:
            mentioned_files = sum(
                1
                for f in files_changed
                if self._fuzzy_match_in_text(
                    self._extract_filename(f["filename"]), description
                )
            )
            coverage_ratio = mentioned_files / len(files_changed)
            score += coverage_ratio * 30

        # Technical detail alignment (30 points)
        patterns = pattern_analysis.get("patterns_detected", [])
        if patterns:
            mentioned_patterns = sum(1 for p in patterns if p.lower() in description)
            pattern_ratio = mentioned_patterns / len(patterns)
            score += pattern_ratio * 30

        # Change type matching (20 points)
        change_types = self._extract_change_types(file_analysis)
        mentioned_types = sum(1 for ct in change_types if ct in description)
        if change_types:
            type_ratio = mentioned_types / len(change_types)
            score += type_ratio * 20

        # Has structured sections (20 points)
        sections = description_analysis.get("sections", [])
        if len(sections) >= 2:
            score += 20
        elif sections:
            score += 10

        return min(100, score)

    def _score_completeness(
        self, metadata: dict[str, Any], code: dict[str, Any], modules: dict[str, Any]
    ) -> float:
        """Score how complete the metadata is relative to changes.

        Args:
            metadata: All metadata results
            code: All code results
            modules: Module results

        Returns:
            Score 0-100
        """
        score = 100.0  # Start at 100 and deduct for missing info

        # Check for unmentioned significant files
        file_analysis = code.get("file_analysis", {})
        significant_files = [
            f
            for f in file_analysis.get("files_changed", [])
            if f.get("changes", 0) > 100  # Significant = >100 line changes
        ]

        title = metadata.get("title_analysis", {}).get("title", "").lower()
        description = (
            metadata.get("description_analysis", {}).get("description", "").lower()
        )
        combined_text = title + " " + description

        unmentioned_significant = sum(
            1
            for f in significant_files
            if not self._fuzzy_match_in_text(
                self._extract_filename(f["filename"]), combined_text
            )
        )

        if significant_files:
            score -= (unmentioned_significant / len(significant_files)) * 30

        # Check for unmentioned modules (20 points)
        if modules:
            module_list = modules.get("modules", [])
            if module_list:
                unmentioned_modules = sum(
                    1
                    for m in module_list
                    if not self._fuzzy_match_in_text(m["name"], combined_text)
                )
                score -= (unmentioned_modules / len(module_list)) * 20

        # Check if risk level is communicated (20 points)
        risk_assessment = code.get("risk_assessment", {})
        risk_level = risk_assessment.get("risk_level", "").lower()
        if risk_level in ["high", "medium"] and risk_level not in combined_text:
            if "risk" not in combined_text and "careful" not in combined_text:
                score -= 20

        return max(0, score)

    def _score_specificity(
        self, title_analysis: dict[str, Any], description_analysis: dict[str, Any]
    ) -> float:
        """Score the technical specificity of the metadata.

        Args:
            title_analysis: Title analysis
            description_analysis: Description analysis

        Returns:
            Score 0-100
        """
        score = 0.0

        title = title_analysis.get("title", "").lower()
        description = description_analysis.get("description", "").lower()

        # Technical terms in title (40 points)
        technical_terms = [
            "api",
            "endpoint",
            "adapter",
            "module",
            "component",
            "function",
            "method",
            "class",
            "interface",
            "implementation",
            "algorithm",
            "optimization",
            "refactor",
            "deprecate",
            "migrate",
        ]

        title_technical_count = sum(1 for term in technical_terms if term in title)
        score += min(40, title_technical_count * 10)

        # Technical terms in description (40 points)
        if description:
            desc_technical_count = sum(
                1 for term in technical_terms if term in description
            )
            score += min(40, desc_technical_count * 5)

        # Concrete vs vague language (20 points)
        vague_terms = ["fix", "update", "change", "modify", "improve", "enhance"]
        concrete_terms = [
            "implement",
            "remove",
            "add",
            "replace",
            "migrate",
            "deprecate",
        ]

        vague_count = sum(1 for term in vague_terms if term in title)
        concrete_count = sum(1 for term in concrete_terms if term in title)

        if concrete_count > vague_count:
            score += 20
        elif concrete_count == vague_count and concrete_count > 0:
            score += 10

        return min(100, score)

    def _generate_recommendations(
        self,
        components: AccuracyComponents,
        metadata: dict[str, Any],
        code: dict[str, Any],
    ) -> list[AccuracyRecommendation]:
        """Generate recommendations for improving accuracy.

        Args:
            components: Component scores
            metadata: Metadata results
            code: Code results

        Returns:
            List of recommendations
        """
        recommendations = []

        # Title recommendations
        if components.title_accuracy < 70:
            files_changed = code.get("file_analysis", {}).get("files_changed", [])
            if files_changed:
                key_file = max(files_changed, key=lambda f: f.get("changes", 0))
                recommendations.append(
                    AccuracyRecommendation(
                        component="title",
                        issue="Title doesn't mention key files or modules changed",
                        suggestion=f"Consider mentioning '{self._extract_filename(key_file['filename'])}' in the title",
                        priority="high",
                    )
                )

        # Description recommendations
        if components.description_accuracy < 70:
            if not metadata.get("description_analysis", {}).get(
                "has_description", False
            ):
                recommendations.append(
                    AccuracyRecommendation(
                        component="description",
                        issue="No description provided",
                        suggestion="Add a description explaining what changed and why",
                        priority="high",
                    )
                )
            else:
                recommendations.append(
                    AccuracyRecommendation(
                        component="description",
                        issue="Description doesn't cover all significant changes",
                        suggestion="List all modified files and explain the changes made",
                        priority="medium",
                    )
                )

        # Completeness recommendations
        if components.completeness < 70:
            recommendations.append(
                AccuracyRecommendation(
                    component="completeness",
                    issue="Significant changes not mentioned in metadata",
                    suggestion="Review all changed files and ensure major changes are documented",
                    priority="high",
                )
            )

        # Specificity recommendations
        if components.specificity < 50:
            recommendations.append(
                AccuracyRecommendation(
                    component="specificity",
                    issue="Metadata uses vague language",
                    suggestion="Use specific technical terms and concrete action verbs",
                    priority="medium",
                )
            )

        return recommendations

    def _get_accuracy_level(self, score: float) -> str:
        """Get accuracy level from score.

        Args:
            score: Total accuracy score

        Returns:
            Level string
        """
        if score >= 85:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 50:
            return "fair"
        else:
            return "poor"

    def _fuzzy_match_in_text(self, needle: str, haystack: str) -> bool:
        """Check if needle appears in haystack with fuzzy matching.

        Args:
            needle: Text to find
            haystack: Text to search in

        Returns:
            True if found with reasonable similarity
        """
        needle = needle.lower().strip()
        haystack = haystack.lower()

        # Direct substring match
        if needle in haystack:
            return True

        # Try without common suffixes
        for suffix in [
            "bidadapter",
            "adapter",
            "module",
            "component",
            ".js",
            ".py",
            ".java",
        ]:
            if needle.endswith(suffix):
                base = needle[: -len(suffix)]
                if base in haystack:
                    return True

        # Check if the base name (without camelCase) is present
        # Convert camelCase to words: exampleBidAdapter -> example bid adapter

        words = re.sub(
            "([A-Z][a-z]+)", r" \1", re.sub("([A-Z]+)", r" \1", needle)
        ).split()
        base_word = words[0].lower() if words else needle
        if len(base_word) > 3 and base_word in haystack:
            return True

        # Check for partial matches of significant length
        if len(needle) > 5:
            # Check if a significant portion of needle is in haystack
            for i in range(len(haystack) - len(needle) + 3):
                substring = haystack[i : i + len(needle) - 2]
                if needle.startswith(substring) or substring in needle:
                    if len(substring) >= len(needle) * 0.7:
                        return True

        return False

    def _extract_filename(self, filepath: str) -> str:
        """Extract filename from filepath.

        Args:
            filepath: Full file path

        Returns:
            Filename without extension
        """
        import os

        filename = os.path.basename(filepath)
        name_without_ext = os.path.splitext(filename)[0]
        return name_without_ext

    def _extract_change_types(self, file_analysis: dict[str, Any]) -> set[str]:
        """Extract types of changes made.

        Args:
            file_analysis: File analysis data

        Returns:
            Set of change types
        """
        change_types = set()

        for file_info in file_analysis.get("files_changed", []):
            if file_info.get("status") == "added":
                change_types.add("added")
            elif file_info.get("status") == "removed":
                change_types.add("removed")
            elif file_info.get("status") == "modified":
                change_types.add("modified")
            elif file_info.get("status") == "renamed":
                change_types.add("renamed")

        return change_types

    def _calculate_files_mentioned_ratio(
        self,
        title_analysis: dict[str, Any],
        description_analysis: dict[str, Any],
        file_analysis: dict[str, Any],
    ) -> float:
        """Calculate ratio of files mentioned in metadata.

        Args:
            title_analysis: Title data
            description_analysis: Description data
            file_analysis: File data

        Returns:
            Ratio 0-1
        """
        files_changed = file_analysis.get("files_changed", [])
        if not files_changed:
            return 1.0

        title = title_analysis.get("title", "").lower()
        description = description_analysis.get("description", "").lower()
        combined_text = title + " " + description

        mentioned_count = sum(
            1
            for f in files_changed
            if self._fuzzy_match_in_text(
                self._extract_filename(f["filename"]), combined_text
            )
        )

        return mentioned_count / len(files_changed)

    def _calculate_modules_mentioned_ratio(
        self,
        title_analysis: dict[str, Any],
        description_analysis: dict[str, Any],
        modules: dict[str, Any],
    ) -> float:
        """Calculate ratio of modules mentioned in metadata.

        Args:
            title_analysis: Title data
            description_analysis: Description data
            modules: Module data

        Returns:
            Ratio 0-1
        """
        module_list = modules.get("modules", [])
        if not module_list:
            return 1.0

        title = title_analysis.get("title", "").lower()
        description = description_analysis.get("description", "").lower()
        combined_text = title + " " + description

        mentioned_count = sum(
            1
            for m in module_list
            if self._fuzzy_match_in_text(m["name"], combined_text)
        )

        return mentioned_count / len(module_list)
