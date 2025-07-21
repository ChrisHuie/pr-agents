"""
Unified repository context models.
"""

from dataclasses import dataclass, field
from typing import Any

from .models import RepositoryStructure


@dataclass
class PRAnalysisPattern:
    """Pattern for analyzing PRs."""

    pattern: str
    indicators: list[str] = field(default_factory=list)
    review_focus: list[str] = field(default_factory=list)
    validation_rules: list[str] = field(default_factory=list)


@dataclass
class QualityIndicators:
    """Quality indicators for PR review."""

    good_pr: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)


@dataclass
class CodeReviewGuidelines:
    """Guidelines for code review."""

    required_checks: list[str] = field(default_factory=list)
    performance_considerations: list[str] = field(default_factory=list)
    security_considerations: list[str] = field(default_factory=list)
    module_specific_rules: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Agent-specific context for repository understanding."""

    pr_patterns: list[PRAnalysisPattern] = field(default_factory=list)
    quality_indicators: QualityIndicators = field(default_factory=QualityIndicators)
    code_review_guidelines: CodeReviewGuidelines = field(
        default_factory=CodeReviewGuidelines
    )
    common_issues: list[str] = field(default_factory=list)
    module_relationships: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class RepositoryKnowledge:
    """Knowledge base information about a repository."""

    purpose: str = ""
    key_features: list[str] = field(default_factory=list)
    architecture: dict[str, Any] = field(default_factory=dict)
    code_patterns: dict[str, Any] = field(default_factory=dict)
    testing_requirements: dict[str, Any] = field(default_factory=dict)
    code_examples: dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedRepositoryContext:
    """Complete repository context combining all layers."""

    # Base structure from JSON config
    structure: RepositoryStructure | None = None

    # Knowledge from YAML knowledge base
    knowledge: RepositoryKnowledge = field(default_factory=RepositoryKnowledge)

    # Agent-specific context
    agent_context: AgentContext = field(default_factory=AgentContext)

    # Markdown context from prebid-context directory
    markdown_context: str | None = None

    # Metadata
    repo_name: str = ""
    repo_url: str = ""
    primary_language: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "repo_name": self.repo_name,
            "repo_url": self.repo_url,
            "primary_language": self.primary_language,
        }

        if self.structure:
            result["structure"] = self.structure.model_dump(exclude_none=True)

        if self.knowledge:
            result["knowledge"] = {
                "purpose": self.knowledge.purpose,
                "key_features": self.knowledge.key_features,
                "architecture": self.knowledge.architecture,
                "code_patterns": self.knowledge.code_patterns,
                "testing_requirements": self.knowledge.testing_requirements,
            }

        if self.agent_context:
            result["agent_context"] = {
                "pr_patterns": [
                    {
                        "pattern": p.pattern,
                        "indicators": p.indicators,
                        "review_focus": p.review_focus,
                        "validation_rules": p.validation_rules,
                    }
                    for p in self.agent_context.pr_patterns
                ],
                "quality_indicators": {
                    "good_pr": self.agent_context.quality_indicators.good_pr,
                    "red_flags": self.agent_context.quality_indicators.red_flags,
                },
                "code_review_guidelines": {
                    "required_checks": self.agent_context.code_review_guidelines.required_checks,
                    "performance_considerations": self.agent_context.code_review_guidelines.performance_considerations,
                    "security_considerations": self.agent_context.code_review_guidelines.security_considerations,
                    "module_specific_rules": self.agent_context.code_review_guidelines.module_specific_rules,
                },
                "common_issues": self.agent_context.common_issues,
                "module_relationships": self.agent_context.module_relationships,
            }

        if self.markdown_context:
            result["markdown_context"] = self.markdown_context

        return result

    def get_pr_review_context(self) -> dict[str, Any]:
        """Get context specifically for PR review."""
        return {
            "repo_type": self.structure.repo_type if self.structure else "unknown",
            "purpose": self.knowledge.purpose,
            "key_features": self.knowledge.key_features,
            "quality_indicators": {
                "good_pr": self.agent_context.quality_indicators.good_pr,
                "red_flags": self.agent_context.quality_indicators.red_flags,
            },
            "review_guidelines": {
                "required_checks": self.agent_context.code_review_guidelines.required_checks,
                "focus_areas": self._get_focus_areas(),
            },
            "module_patterns": self._get_module_patterns(),
        }

    def _get_focus_areas(self) -> list[str]:
        """Extract focus areas from patterns."""
        focus_areas = set()
        for pattern in self.agent_context.pr_patterns:
            focus_areas.update(pattern.review_focus)
        return list(focus_areas)

    def _get_module_patterns(self) -> dict[str, Any]:
        """Get module patterns from structure."""
        if not self.structure:
            return {}

        patterns = {}
        for name, category in self.structure.module_categories.items():
            patterns[name] = {
                "display_name": category.display_name,
                "paths": category.paths,
                "patterns": [p.pattern for p in category.patterns],
            }
        return patterns
