"""
Metadata processor - analyzes PR title, description, labels in isolation.
"""

import re
from dataclasses import asdict
from typing import Any

from ..analysis_models import (
    DescriptionAnalysis,
    DescriptionQuality,
    LabelAnalysis,
    MetadataAnalysisResult,
    TitleAnalysis,
    TitleQuality,
)
from ..models import ProcessingResult
from .base import BaseProcessor


class MetadataProcessor(BaseProcessor):
    """Processes PR metadata without any code or review context."""

    @property
    def component_name(self) -> str:
        return "metadata"

    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """Analyze PR metadata in isolation."""
        try:
            # Extract data
            title = component_data.get("title", "")
            description = component_data.get("description") or ""
            labels = component_data.get("labels", [])

            # Create analysis result using dataclasses
            title_analysis = self._analyze_title(title)
            description_analysis = self._analyze_description(description)

            analysis_result = MetadataAnalysisResult(
                title_analysis=title_analysis,
                description_analysis=description_analysis,
                label_analysis=self._analyze_labels(labels),
                title_quality=self._assess_title_quality(title, title_analysis),
                description_quality=self._assess_description_quality(
                    description, description_analysis
                ),
            )

            return ProcessingResult(
                component="metadata",
                success=True,
                data=asdict(analysis_result),
            )

        except Exception as e:
            return ProcessingResult(
                component="metadata",
                success=False,
                errors=[str(e)],
            )

    def _analyze_title(self, title: str) -> TitleAnalysis:
        """Analyze PR title characteristics."""
        return TitleAnalysis(
            length=len(title),
            word_count=len(title.split()),
            has_emoji=bool(
                re.search(
                    r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]",
                    title,
                )
            ),
            has_prefix=bool(
                re.match(r"^(feat|fix|docs|style|refactor|test|chore):", title.lower())
            ),
            has_ticket_reference=bool(re.search(r"#\d+|\b[A-Z]+-\d+\b", title)),
            is_question=title.strip().endswith("?"),
            is_wip="wip" in title.lower() or "work in progress" in title.lower(),
        )

    def _analyze_description(self, description: str) -> DescriptionAnalysis:
        """Analyze PR description characteristics."""
        if not description:
            return DescriptionAnalysis(
                has_description=False,
                length=0,
                sections=[],
            )

        # Look for common sections
        sections = []
        section_patterns = {
            "summary": r"## ?summary|## ?description|## ?what",
            "changes": r"## ?changes|## ?what changed",
            "testing": r"## ?test|## ?testing|## ?test plan",
            "checklist": r"## ?checklist|## ?todo",
            "breaking": r"## ?breaking|## ?breaking change",
            "links": r"## ?link|## ?related|## ?reference",
        }

        for section, pattern in section_patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                sections.append(section)

        return DescriptionAnalysis(
            has_description=True,
            length=len(description),
            line_count=len(description.split("\n")),
            sections=sections,
            has_checklist="- [ ]" in description or "- [x]" in description,
            has_links=bool(re.search(r"https?://", description)),
            has_code_blocks="```" in description,
        )

    def _analyze_labels(self, labels: list) -> LabelAnalysis:
        """Analyze PR labels."""
        label_categories = {
            "type": ["bug", "feature", "enhancement", "refactor", "docs", "test"],
            "priority": ["critical", "high", "medium", "low", "urgent"],
            "size": ["small", "medium", "large", "xl", "xs"],
            "status": ["wip", "ready", "blocked", "needs-review"],
            "area": ["frontend", "backend", "api", "ui", "database", "security"],
        }

        categorized = {category: [] for category in label_categories}
        uncategorized = []

        for label in labels:
            categorized_label = False
            for category, keywords in label_categories.items():
                if any(keyword in label.lower() for keyword in keywords):
                    categorized[category].append(label)
                    categorized_label = True
                    break

            if not categorized_label:
                uncategorized.append(label)

        return LabelAnalysis(
            total_count=len(labels),
            categorized=categorized,
            uncategorized=uncategorized,
            has_type_label=bool(categorized["type"]),
            has_priority_label=bool(categorized["priority"]),
        )

    def _assess_title_quality(
        self, title: str, title_analysis: TitleAnalysis
    ) -> TitleQuality:
        """Assess title quality on a 1-100 scale."""
        score = 0
        issues = []

        # Length assessment (25 points)
        if 15 <= title_analysis.length <= 80:
            score += 25
        elif 10 <= title_analysis.length < 15:
            score += 15
            issues.append("Title is a bit short")
        elif 80 < title_analysis.length <= 100:
            score += 15
            issues.append("Title is a bit long")
        elif title_analysis.length < 10:
            score += 5
            issues.append("Title too short")
        else:
            score += 5
            issues.append("Title too long")

        # Word count assessment (15 points)
        if 3 <= title_analysis.word_count <= 12:
            score += 15
        elif 2 <= title_analysis.word_count < 3:
            score += 10
            issues.append("Title could be more descriptive")
        elif 12 < title_analysis.word_count <= 15:
            score += 10
            issues.append("Title is wordy")
        else:
            score += 5
            issues.append("Title word count not optimal")

        # Prefix/Convention assessment (20 points)
        if title_analysis.has_prefix:
            score += 20
        else:
            score += 10
            issues.append("No conventional prefix (feat/fix/docs/etc)")

        # Ticket reference assessment (15 points)
        if title_analysis.has_ticket_reference:
            score += 15

        # Clarity indicators (25 points)
        if not title_analysis.is_wip:
            score += 10
        else:
            issues.append("Work in progress")

        if not title_analysis.is_question:
            score += 10
        else:
            score += 5
            issues.append("Title is phrased as a question")

        # Basic grammar check - starts with capital letter
        if title and title[0].isupper():
            score += 5

        quality_level = (
            "excellent"
            if score >= 85
            else "good" if score >= 70 else "fair" if score >= 50 else "poor"
        )

        return TitleQuality(
            score=score,
            quality_level=quality_level,
            issues=issues,
        )

    def _assess_description_quality(
        self, description: str, description_analysis: DescriptionAnalysis
    ) -> DescriptionQuality:
        """Assess description quality on a 1-100 scale."""
        score = 0
        issues = []

        # Has description at all (20 points)
        if not description_analysis.has_description:
            issues.append("No description provided")
            return DescriptionQuality(
                score=0,
                quality_level="poor",
                issues=issues,
            )

        score += 20

        # Length assessment (20 points)
        if description_analysis.length >= 100:
            score += 20
        elif description_analysis.length >= 50:
            score += 15
            issues.append("Description could be more detailed")
        else:
            score += 5
            issues.append("Description too brief")

        # Structure assessment (25 points)
        if len(description_analysis.sections) >= 3:
            score += 25
        elif len(description_analysis.sections) >= 2:
            score += 20
        elif len(description_analysis.sections) >= 1:
            score += 15
            issues.append("Consider adding more sections")
        else:
            score += 5
            issues.append("No structured sections found")

        # Content richness (35 points)
        if description_analysis.has_checklist:
            score += 10

        if description_analysis.has_links:
            score += 10

        if description_analysis.has_code_blocks:
            score += 10

        # Line count as a proxy for detail
        if description_analysis.line_count >= 5:
            score += 5

        quality_level = (
            "excellent"
            if score >= 85
            else "good" if score >= 70 else "fair" if score >= 50 else "poor"
        )

        return DescriptionQuality(
            score=score,
            quality_level=quality_level,
            issues=issues,
        )
