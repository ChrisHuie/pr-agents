"""
Metadata processor - analyzes PR title, description, labels in isolation.
"""

import re
from dataclasses import asdict
from typing import Any

from ..analysis_models import (
    DescriptionAnalysis,
    LabelAnalysis,
    MetadataAnalysisResult,
    MetadataQuality,
    TitleAnalysis,
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
            analysis_result = MetadataAnalysisResult(
                title_analysis=self._analyze_title(title),
                description_analysis=self._analyze_description(description),
                label_analysis=self._analyze_labels(labels),
                metadata_quality=self._assess_metadata_quality(
                    title, description, labels
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

    def _assess_metadata_quality(
        self, title: str, description: str, labels: list
    ) -> MetadataQuality:
        """Assess overall metadata quality."""
        score = 0
        issues = []

        # Title quality (30 points)
        if len(title) > 10:
            score += 10
        else:
            issues.append("Title too short")

        if len(title) < 100:
            score += 10
        else:
            issues.append("Title too long")

        if not title.lower().startswith(("fix", "add", "remove", "update")):
            score += 10

        # Description quality (40 points)
        if description and len(description) > 50:
            score += 20
        else:
            issues.append("Description missing or too short")

        if description and ("## " in description or "# " in description):
            score += 20
        elif description:
            score += 10

        # Labels quality (30 points)
        if len(labels) > 0:
            score += 15
        else:
            issues.append("No labels assigned")

        if len(labels) >= 2:
            score += 15

        quality_level = (
            "excellent"
            if score >= 80
            else "good" if score >= 60 else "fair" if score >= 40 else "poor"
        )

        return MetadataQuality(
            score=score,
            quality_level=quality_level,
            issues=issues,
        )
