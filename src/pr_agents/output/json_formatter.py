"""
JSON formatter for PR analysis output.
"""

import json
from typing import Any

from .base import BaseFormatter


class JSONFormatter(BaseFormatter):
    """Formats PR analysis results as JSON."""

    def __init__(self, indent: int = 2, sort_keys: bool = True):
        """
        Initialize JSON formatter.

        Args:
            indent: Number of spaces for indentation
            sort_keys: Whether to sort dictionary keys
        """
        self.indent = indent
        self.sort_keys = sort_keys

    def format(self, data: dict[str, Any]) -> str:
        """
        Format PR analysis data as JSON.

        Args:
            data: PR analysis results dictionary

        Returns:
            JSON formatted string
        """
        # Clean up any non-serializable objects
        cleaned_data = self._clean_data(data)

        return json.dumps(
            cleaned_data,
            indent=self.indent,
            sort_keys=self.sort_keys,
            ensure_ascii=False,
            default=str,
        )

    def _clean_data(self, obj: Any) -> Any:
        """
        Recursively clean data to ensure JSON serializability.

        Args:
            obj: Object to clean

        Returns:
            Cleaned object
        """
        if isinstance(obj, dict):
            return {k: self._clean_data(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [self._clean_data(item) for item in obj if item is not None]
        elif isinstance(obj, str | int | float | bool) or obj is None:
            return obj
        else:
            # Convert other types to string
            return str(obj)

    def get_file_extension(self) -> str:
        """Return JSON file extension."""
        return ".json"

    def validate_data(self, data: dict[str, Any]) -> bool:
        """
        Validate that the data can be serialized to JSON.

        Args:
            data: PR analysis results dictionary

        Returns:
            True if data can be serialized, False otherwise
        """
        try:
            json.dumps(data, default=str)
            return True
        except (TypeError, ValueError):
            return False
