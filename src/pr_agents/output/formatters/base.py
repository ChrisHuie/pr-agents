"""Base classes for modular formatters."""

from abc import ABC, abstractmethod
from typing import Any


class SectionFormatter(ABC):
    """Base class for formatting individual sections of output."""

    @abstractmethod
    def format(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> list[str]:
        """
        Format a section of data.

        Args:
            data: The data to format
            options: Optional formatting options

        Returns:
            List of formatted lines
        """
        pass

    @abstractmethod
    def applies_to(self, data: dict[str, Any]) -> bool:
        """
        Check if this formatter applies to the given data.

        Args:
            data: The data to check

        Returns:
            True if this formatter should be used
        """
        pass

    def get_priority(self) -> int:
        """
        Get the priority for ordering sections.

        Lower numbers appear first.

        Returns:
            Priority value
        """
        return 100


class FormatterConfig:
    """Configuration for output formatting."""

    def __init__(
        self,
        sections: list[str] | None = None,
        personas: list[str] | None = None,
        include_metrics: bool = True,
        include_details: bool = True,
        compact: bool = False,
        grouped_by_tag: bool = False,
    ):
        """
        Initialize formatter configuration.

        Args:
            sections: List of sections to include (None = all)
            personas: List of AI personas to include (None = all)
            include_metrics: Whether to include processing metrics
            include_details: Whether to include detailed analysis
            compact: Use compact formatting
            grouped_by_tag: Group PRs by tag (for batch/release)
        """
        self.sections = sections
        self.personas = personas
        self.include_metrics = include_metrics
        self.include_details = include_details
        self.compact = compact
        self.grouped_by_tag = grouped_by_tag

    @classmethod
    def default(cls) -> "FormatterConfig":
        """Get default configuration."""
        return cls()

    @classmethod
    def compact_summary(cls) -> "FormatterConfig":
        """Get configuration for compact summary."""
        return cls(
            sections=["header", "ai_summaries", "statistics"],
            include_metrics=False,
            include_details=False,
            compact=True,
        )

    @classmethod
    def executive_only(cls) -> "FormatterConfig":
        """Get configuration for executive summary only."""
        return cls(
            sections=["header", "ai_summaries"],
            personas=["executive"],
            include_metrics=False,
            include_details=False,
        )

    @classmethod
    def developer_view(cls) -> "FormatterConfig":
        """Get configuration for developer view."""
        return cls(
            sections=["header", "code_changes", "modules", "ai_summaries", "metrics"],
            personas=["developer", "reviewer"],
            include_metrics=True,
            include_details=True,
        )

    @classmethod
    def release_summary(cls) -> "FormatterConfig":
        """Get configuration for release summary."""
        return cls(
            grouped_by_tag=True,
            include_details=False,
            sections=["header", "pr_groups", "statistics"],
        )
