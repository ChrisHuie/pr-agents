"""JSON transformers for modular output."""

from abc import ABC, abstractmethod
from typing import Any


class JSONTransformer(ABC):
    """Base class for transforming specific sections of JSON output."""

    @abstractmethod
    def transform(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Transform a section of data for JSON output.

        Args:
            data: The data to transform
            options: Optional transformation options

        Returns:
            Transformed data dictionary
        """
        pass

    @abstractmethod
    def applies_to(self, data: dict[str, Any]) -> bool:
        """
        Check if this transformer applies to the given data.

        Args:
            data: The data to check

        Returns:
            True if this transformer should be used
        """
        pass

    @abstractmethod
    def get_field_name(self) -> str:
        """
        Get the field name for this transformed data.

        Returns:
            Field name for the JSON output
        """
        pass


class MetadataTransformer(JSONTransformer):
    """Transforms metadata for JSON output."""

    def transform(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Transform metadata section."""
        if "metadata" not in data:
            return {}

        metadata = data["metadata"]

        # Check if this is PR analysis metadata or simple metadata
        has_analysis = any(
            key in metadata
            for key in ["label_analysis", "title_quality", "description_quality"]
        )

        # If it's simple metadata, return as-is
        if not has_analysis:
            return metadata

        # Otherwise, transform PR analysis metadata
        result = {}

        # Basic info
        if "label_analysis" in metadata:
            result["title"] = metadata["label_analysis"].get("title", "")
            result["description"] = metadata["label_analysis"].get("description", "")
            result["author"] = metadata["label_analysis"].get("author", "")

        # Quality scores
        if "title_quality" in metadata:
            result["title_quality"] = metadata["title_quality"]

        if "description_quality" in metadata:
            result["description_quality"] = metadata["description_quality"]

        # Labels
        if "label_analysis" in metadata:
            result["labels"] = metadata["label_analysis"]

        return result

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if metadata is present."""
        return "metadata" in data

    def get_field_name(self) -> str:
        """Return field name."""
        return "metadata"


class CodeChangesTransformer(JSONTransformer):
    """Transforms code changes for JSON output."""

    def transform(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Transform code changes section."""
        if "code_changes" not in data:
            return {}

        options = options or {}
        compact = options.get("compact", False)

        code_changes = data["code_changes"]
        result = {}

        # Always include statistics
        if "change_stats" in code_changes:
            result["statistics"] = code_changes["change_stats"]

        # Risk assessment
        if "risk_assessment" in code_changes:
            result["risk_assessment"] = code_changes["risk_assessment"]

        # File details (unless compact)
        if not compact and "file_analysis" in code_changes:
            result["file_analysis"] = code_changes["file_analysis"]

        # Pattern analysis (unless compact)
        if not compact and "pattern_analysis" in code_changes:
            result["pattern_analysis"] = code_changes["pattern_analysis"]

        return result

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if code changes are present."""
        return "code_changes" in data

    def get_field_name(self) -> str:
        """Return field name."""
        return "code_changes"


class AISummariesTransformer(JSONTransformer):
    """Transforms AI summaries for JSON output."""

    def transform(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Transform AI summaries section."""
        if "ai_summaries" not in data:
            return {}

        options = options or {}
        personas_filter = options.get("personas")

        ai_summaries = data["ai_summaries"]
        result = {}

        # Include metadata
        result["model_used"] = ai_summaries.get("model_used", "Unknown")
        result["generation_timestamp"] = ai_summaries.get(
            "generation_timestamp", "Unknown"
        )
        result["cached"] = ai_summaries.get("cached", False)

        # Add token and timing info if available
        if "total_tokens" in ai_summaries:
            result["total_tokens"] = ai_summaries["total_tokens"]
        if "generation_time_ms" in ai_summaries:
            result["generation_time_ms"] = ai_summaries["generation_time_ms"]

        # Include personas
        result["summaries"] = {}
        personas = [
            "executive_summary",
            "product_summary",
            "developer_summary",
            "reviewer_summary",
            "technical_writer_summary",
        ]

        for persona_key in personas:
            # Apply persona filter if specified
            if (
                personas_filter
                and persona_key.replace("_summary", "") not in personas_filter
            ):
                continue

            if persona_key in ai_summaries:
                summary_data = ai_summaries[persona_key]
                if summary_data.get("summary") != "[Not requested]":
                    result["summaries"][persona_key] = {
                        "summary": summary_data.get("summary", ""),
                        "confidence": summary_data.get("confidence", 0.0),
                    }

        return result

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if AI summaries are present."""
        return "ai_summaries" in data

    def get_field_name(self) -> str:
        """Return field name."""
        return "ai_summaries"


class ModulesTransformer(JSONTransformer):
    """Transforms modules data for JSON output."""

    def transform(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Transform modules section."""
        if "modules" not in data:
            return {}

        # Return modules data as-is, it's already well structured
        return data["modules"]

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if modules data is present."""
        return "modules" in data

    def get_field_name(self) -> str:
        """Return field name."""
        return "modules"


class ReviewsTransformer(JSONTransformer):
    """Transforms reviews data for JSON output."""

    def transform(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Transform reviews section."""
        if "reviews" not in data:
            return {}

        return data["reviews"]

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if reviews data is present."""
        return "reviews" in data

    def get_field_name(self) -> str:
        """Return field name."""
        return "reviews"


class RepositoryTransformer(JSONTransformer):
    """Transforms repository info for JSON output."""

    def transform(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Transform repository section."""
        if "repository_info" not in data:
            return {}

        return data["repository_info"]

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if repository info is present."""
        return "repository_info" in data

    def get_field_name(self) -> str:
        """Return field name."""
        return "repository_info"


class MetricsTransformer(JSONTransformer):
    """Transforms processing metrics for JSON output."""

    def transform(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Transform metrics section."""
        if "processing_metrics" not in data:
            return {}

        options = options or {}
        if not options.get("include_metrics", True):
            return {}

        return data["processing_metrics"]

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if metrics are present."""
        return "processing_metrics" in data

    def get_field_name(self) -> str:
        """Return field name."""
        return "processing_metrics"


class BatchSummaryTransformer(JSONTransformer):
    """Transforms batch summary data for JSON output."""

    def transform(
        self, data: dict[str, Any], options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Transform batch summary section."""
        if "batch_summary" not in data:
            return {}

        return data["batch_summary"]

    def applies_to(self, data: dict[str, Any]) -> bool:
        """Check if batch summary is present."""
        return "batch_summary" in data

    def get_field_name(self) -> str:
        """Return field name."""
        return "batch_summary"


# Registry of all transformers
TRANSFORMER_REGISTRY = {
    "metadata": MetadataTransformer(),
    "code_changes": CodeChangesTransformer(),
    "ai_summaries": AISummariesTransformer(),
    "modules": ModulesTransformer(),
    "reviews": ReviewsTransformer(),
    "repository_info": RepositoryTransformer(),
    "processing_metrics": MetricsTransformer(),
    "batch_summary": BatchSummaryTransformer(),
}
