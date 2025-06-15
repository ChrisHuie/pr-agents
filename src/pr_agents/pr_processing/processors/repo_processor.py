"""
Repository processor - analyzes repo information in isolation.
"""

from dataclasses import asdict
from typing import Any

from ..analysis_models import (
    BranchAnalysis,
    LanguageAnalysis,
    RepoAnalysisResult,
    RepoHealth,
    RepoInfo,
)
from ..models import ProcessingResult
from .base import BaseProcessor


class RepoProcessor(BaseProcessor):
    """Processes repository information without any PR-specific context."""

    @property
    def component_name(self) -> str:
        return "repository"

    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """Analyze repository information in isolation."""
        try:
            # Basic repo info
            repo_info = self._analyze_repo_info(component_data)

            # Language analysis
            languages = component_data.get("languages", {})
            language_analysis = self._analyze_languages(languages)

            # Branch analysis
            branch_analysis = self._analyze_branches(component_data)

            # Repository health assessment
            repo_health = self._assess_repo_health(component_data)

            # Create the analysis result dataclass
            analysis_result = RepoAnalysisResult(
                repo_info=repo_info,
                language_analysis=language_analysis,
                branch_analysis=branch_analysis,
                repo_health=repo_health,
            )

            return ProcessingResult(
                component="repository",
                success=True,
                data=asdict(analysis_result),
            )

        except Exception as e:
            return ProcessingResult(
                component="repository",
                success=False,
                errors=[str(e)],
            )

    def _analyze_repo_info(self, data: dict[str, Any]) -> RepoInfo:
        """Analyze basic repository information."""
        return RepoInfo(
            name=data.get("name"),
            full_name=data.get("full_name"),
            owner=data.get("owner"),
            is_private=data.get("is_private", False),
            is_fork=data.get("fork_info") is not None,
            has_description=bool(data.get("description")),
            description_length=len(data.get("description", "")),
            topics_count=len(data.get("topics", [])),
            topics=data.get("topics", []),
        )

    def _analyze_languages(self, languages: dict[str, int]) -> LanguageAnalysis:
        """Analyze repository language composition."""
        if not languages:
            return LanguageAnalysis(
                primary_language=None,
                language_count=0,
                language_distribution={},
                total_bytes=0,
            )

        total_bytes = sum(languages.values())
        language_percentages = {
            lang: (bytes_count / total_bytes) * 100
            for lang, bytes_count in languages.items()
        }

        primary_language = max(languages.items(), key=lambda x: x[1])[0]

        # Categorize languages
        language_categories = {
            "web": ["JavaScript", "TypeScript", "HTML", "CSS", "PHP", "Vue", "React"],
            "backend": ["Python", "Java", "C#", "Go", "Rust", "Ruby", "Node.js"],
            "mobile": ["Swift", "Kotlin", "Dart", "Objective-C", "Java"],
            "data": ["Python", "R", "Julia", "Scala", "SQL"],
            "systems": ["C", "C++", "Rust", "Go", "Assembly"],
            "functional": ["Haskell", "Clojure", "F#", "Erlang", "Elixir"],
        }

        repo_categories = []
        for category, category_languages in language_categories.items():
            if any(lang in languages for lang in category_languages):
                repo_categories.append(category)

        return LanguageAnalysis(
            primary_language=primary_language,
            language_count=len(languages),
            language_distribution=language_percentages,
            total_bytes=total_bytes,
            languages_list=list(languages.keys()),
            repo_categories=repo_categories,
            is_polyglot=len(languages) > 3,
        )

    def _analyze_branches(self, data: dict[str, Any]) -> BranchAnalysis:
        """Analyze branch information."""
        base_branch = data.get("base_branch", "")
        head_branch = data.get("head_branch", "")
        default_branch = data.get("default_branch", "main")

        # Common branch naming patterns
        branch_patterns = {
            "feature": ["feature/", "feat/", "add/", "implement/"],
            "bugfix": ["fix/", "bug/", "hotfix/", "patch/"],
            "release": ["release/", "rel/", "version/"],
            "develop": ["develop", "dev", "development"],
            "main": ["main", "master"],
            "experimental": ["experiment/", "test/", "try/", "poc/"],
        }

        def categorize_branch(branch_name: str) -> str:
            branch_lower = branch_name.lower()
            for category, patterns in branch_patterns.items():
                if any(pattern in branch_lower for pattern in patterns):
                    return category
            return "other"

        return BranchAnalysis(
            base_branch=base_branch,
            head_branch=head_branch,
            default_branch=default_branch,
            base_branch_type=categorize_branch(base_branch),
            head_branch_type=categorize_branch(head_branch),
            is_to_main=base_branch in ["main", "master"],
            is_cross_fork=data.get("fork_info") is not None,
            follows_naming_convention=categorize_branch(head_branch) != "other",
        )

    def _assess_repo_health(self, data: dict[str, Any]) -> RepoHealth:
        """Assess overall repository health indicators."""
        health_score = 0
        health_factors = []
        issues = []

        # Description (10 points)
        if data.get("description"):
            health_score += 10
            health_factors.append("Has description")
        else:
            issues.append("No repository description")

        # Topics (10 points)
        topics_count = len(data.get("topics", []))
        if topics_count >= 3:
            health_score += 10
            health_factors.append("Well-tagged with topics")
        elif topics_count > 0:
            health_score += 5
            health_factors.append("Has some topics")
        else:
            issues.append("No topics assigned")

        # Language diversity (15 points)
        languages = data.get("languages", {})
        if len(languages) > 1:
            health_score += 15
            health_factors.append("Multi-language repository")
        elif len(languages) == 1:
            health_score += 10
            health_factors.append("Single language repository")
        else:
            issues.append("No primary language detected")

        # Privacy and accessibility (10 points)
        if not data.get("is_private", True):
            health_score += 10
            health_factors.append("Public repository")
        else:
            health_score += 5
            health_factors.append("Private repository")

        # Fork information (5 points)
        if data.get("fork_info"):
            health_score += 5
            health_factors.append("Active fork with clear parent")

        # Branch naming (10 points)
        base_branch = data.get("base_branch", "")
        if base_branch in ["main", "master", "develop"]:
            health_score += 10
            health_factors.append("Standard base branch")

        # Calculate health level
        if health_score >= 50:
            health_level = "excellent"
        elif health_score >= 35:
            health_level = "good"
        elif health_score >= 20:
            health_level = "fair"
        else:
            health_level = "needs_improvement"

        return RepoHealth(
            health_score=health_score,
            health_level=health_level,
            health_factors=health_factors,
            issues=issues,
            max_possible_score=70,
            recommendations=self._get_health_recommendations(health_level, issues),
        )

    def _get_health_recommendations(self, health_level: str, issues: list) -> list[str]:
        """Get recommendations for improving repository health."""
        recommendations = []

        if "No repository description" in issues:
            recommendations.append("Add a clear repository description")

        if "No topics assigned" in issues:
            recommendations.append("Add relevant topics to improve discoverability")

        if "No primary language detected" in issues:
            recommendations.append("Ensure repository contains actual code files")

        if health_level in ["fair", "needs_improvement"]:
            recommendations.extend(
                [
                    "Consider adding more documentation",
                    "Review repository organization and structure",
                    "Ensure consistent naming conventions",
                ]
            )

        return recommendations
