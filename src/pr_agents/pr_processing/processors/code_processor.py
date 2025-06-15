"""
Code processor - analyzes code changes, diffs, etc. in isolation.
"""

import re
from dataclasses import asdict
from typing import Any

from loguru import logger

from ...logging_config import log_data_flow, log_error_with_context, log_processing_step
from ..analysis_models import (
    ChangeStats,
    CodeAnalysisResult,
    FileAnalysis,
    PatternAnalysis,
    RiskAssessment,
)
from ..models import ProcessingResult
from .base import BaseProcessor


class CodeProcessor(BaseProcessor):
    """Processes code changes without any metadata or review context."""

    @property
    def component_name(self) -> str:
        return "code_changes"

    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """Analyze code changes in isolation."""
        logger.info("🔍 Starting code analysis")

        try:
            # Extract file diffs
            file_diffs = component_data.get("file_diffs", [])
            log_data_flow(
                "Code data received", f"{len(file_diffs)} file diffs", "input"
            )

            # Create analysis result using dataclasses
            log_processing_step("Analyzing change statistics")
            change_stats = self._analyze_change_stats(component_data)
            log_data_flow(
                "Change stats", f"{change_stats.total_changes} total changes", "stats"
            )

            log_processing_step("Analyzing files")
            file_analysis = self._analyze_files(file_diffs)
            log_data_flow(
                "File analysis", f"{len(file_analysis.file_types)} file types", "files"
            )

            log_processing_step("Analyzing code patterns")
            pattern_analysis = self._analyze_code_patterns(file_diffs)
            log_data_flow(
                "Patterns found",
                f"Tests: {pattern_analysis.has_tests}, Config: {pattern_analysis.has_config_changes}",
                "patterns",
            )

            log_processing_step("Assessing risk")
            risk_assessment = self._assess_risk(component_data, file_diffs)
            log_data_flow(
                "Risk assessment",
                f"Level: {risk_assessment.risk_level}, Score: {risk_assessment.risk_score}",
                "risk",
            )

            analysis_result = CodeAnalysisResult(
                change_stats=change_stats,
                file_analysis=file_analysis,
                pattern_analysis=pattern_analysis,
                risk_assessment=risk_assessment,
            )

            logger.success("✅ Code analysis complete")
            return ProcessingResult(
                component="code_changes",
                success=True,
                data=asdict(analysis_result),
            )

        except Exception as e:
            log_error_with_context(e, "code processing")
            return ProcessingResult(
                component="code_changes",
                success=False,
                errors=[str(e)],
            )

    def _analyze_change_stats(self, data: dict[str, Any]) -> ChangeStats:
        """Analyze basic change statistics."""
        return ChangeStats(
            total_additions=data.get("total_additions", 0),
            total_deletions=data.get("total_deletions", 0),
            total_changes=data.get("total_changes", 0),
            changed_files=data.get("changed_files", 0),
            net_lines=data.get("total_additions", 0) - data.get("total_deletions", 0),
            change_ratio=(
                data.get("total_deletions", 0) / max(data.get("total_additions", 1), 1)
            ),
        )

    def _analyze_files(self, file_diffs: list[dict[str, Any]]) -> FileAnalysis:
        """Analyze file-level changes."""
        file_types = {}
        file_sizes = {"small": 0, "medium": 0, "large": 0}
        statuses = {"added": 0, "modified": 0, "removed": 0, "renamed": 0}

        for file_diff in file_diffs:
            filename = file_diff.get("filename", "")
            status = file_diff.get("status", "")
            changes = file_diff.get("changes", 0)

            # File type analysis
            ext = filename.split(".")[-1].lower() if "." in filename else "no_extension"
            file_types[ext] = file_types.get(ext, 0) + 1

            # File size categorization
            if changes <= 10:
                file_sizes["small"] += 1
            elif changes <= 100:
                file_sizes["medium"] += 1
            else:
                file_sizes["large"] += 1

            # Status tracking
            statuses[status] = statuses.get(status, 0) + 1

        return FileAnalysis(
            file_types=file_types,
            file_sizes=file_sizes,
            file_statuses=statuses,
            largest_file_changes=max(
                (f.get("changes", 0) for f in file_diffs), default=0
            ),
        )

    def _analyze_code_patterns(
        self, file_diffs: list[dict[str, Any]]
    ) -> PatternAnalysis:
        """Analyze patterns in code changes."""
        has_tests = False
        has_config_changes = False
        has_documentation = False
        has_migrations = False
        has_dependencies = False
        config_files = []
        potential_breaking_changes = []

        test_files = 0
        total_files = len(file_diffs)

        for file_diff in file_diffs:
            filename = file_diff.get("filename", "").lower()
            patch = file_diff.get("patch", "") or ""

            # Test files
            if any(
                test_indicator in filename
                for test_indicator in ["test", "spec", "__test__", ".test.", "_test."]
            ):
                has_tests = True
                test_files += 1

            # Configuration files
            config_indicators = [
                "config",
                ".json",
                ".yaml",
                ".yml",
                ".toml",
                ".ini",
                "dockerfile",
                "docker-compose",
                ".env",
                "requirements.txt",
                "package.json",
                "pyproject.toml",
                "setup.py",
            ]
            if any(indicator in filename for indicator in config_indicators):
                has_config_changes = True
                config_files.append(filename)

            # Documentation
            if any(
                doc_indicator in filename
                for doc_indicator in ["readme", ".md", "doc", "docs/"]
            ):
                has_documentation = True

            # Database migrations
            if "migration" in filename or "migrate" in filename:
                has_migrations = True

            # Dependencies
            if any(
                dep_file in filename
                for dep_file in [
                    "requirements.txt",
                    "package.json",
                    "pyproject.toml",
                    "Gemfile",
                    "go.mod",
                ]
            ):
                has_dependencies = True

            # Potential breaking changes (naive detection)
            breaking_patterns = [
                r"def \w+\([^)]*\) -> [^:]+:",  # Function signature changes
                r"class \w+\([^)]*\):",  # Class inheritance changes
                r"@\w+",  # Decorator changes
                r"import \w+",  # Import changes
            ]

            for pattern in breaking_patterns:
                if re.search(pattern, patch):
                    potential_breaking_changes.append(
                        {
                            "file": filename,
                            "pattern": pattern,
                        }
                    )

        test_file_ratio = test_files / max(total_files, 1)

        return PatternAnalysis(
            has_tests=has_tests,
            has_config_changes=has_config_changes,
            has_documentation=has_documentation,
            has_migrations=has_migrations,
            has_dependencies=has_dependencies,
            test_file_ratio=test_file_ratio,
            config_files=config_files,
            potential_breaking_changes=potential_breaking_changes,
        )

    def _assess_risk(
        self, data: dict[str, Any], file_diffs: list[dict[str, Any]]
    ) -> RiskAssessment:
        """Assess risk level of the changes."""
        risk_score = 0
        risk_factors = []

        total_changes = data.get("total_changes", 0)
        changed_files = data.get("changed_files", 0)

        # Size-based risk
        if total_changes > 1000:
            risk_score += 3
            risk_factors.append("Very large changeset")
        elif total_changes > 500:
            risk_score += 2
            risk_factors.append("Large changeset")
        elif total_changes > 100:
            risk_score += 1
            risk_factors.append("Medium changeset")

        # File count risk
        if changed_files > 20:
            risk_score += 2
            risk_factors.append("Many files changed")
        elif changed_files > 10:
            risk_score += 1
            risk_factors.append("Several files changed")

        # Critical file changes
        critical_files = [
            "main.py",
            "app.py",
            "index.js",
            "main.js",
            "server.py",
            "config.py",
            "settings.py",
            "requirements.txt",
            "package.json",
        ]

        for file_diff in file_diffs:
            filename = file_diff.get("filename", "").lower()
            if any(critical in filename for critical in critical_files):
                risk_score += 1
                risk_factors.append(f"Critical file modified: {filename}")

        # Determine risk level
        if risk_score >= 5:
            risk_level = "high"
        elif risk_score >= 3:
            risk_level = "medium"
        elif risk_score >= 1:
            risk_level = "low"
        else:
            risk_level = "minimal"

        return RiskAssessment(
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendations=self._get_risk_recommendations(risk_level, risk_factors),
        )

    def _get_risk_recommendations(
        self, risk_level: str, risk_factors: list[str]
    ) -> list[str]:
        """Get recommendations based on risk assessment."""
        recommendations = []

        if risk_level == "high":
            recommendations.extend(
                [
                    "Consider breaking this PR into smaller chunks",
                    "Ensure comprehensive testing before merge",
                    "Request additional reviewers",
                    "Consider staging deployment first",
                ]
            )
        elif risk_level == "medium":
            recommendations.extend(
                [
                    "Ensure adequate test coverage",
                    "Consider additional reviewer approval",
                    "Verify deployment procedures",
                ]
            )
        elif risk_level == "low":
            recommendations.append("Standard review process should be sufficient")

        # Specific recommendations based on factors
        if any("config" in factor.lower() for factor in risk_factors):
            recommendations.append("Pay special attention to configuration changes")

        if any("many files" in factor.lower() for factor in risk_factors):
            recommendations.append("Verify all file changes are intentional")

        return recommendations
