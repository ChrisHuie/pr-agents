"""
Base formatter interface for output formatting.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseFormatter(ABC):
    """
    Abstract base class for output formatters.

    Handles formatting of PR analysis results into different output formats.
    """

    @abstractmethod
    def format(self, data: dict[str, Any]) -> str:
        """
        Format the analysis data into a string representation.

        Args:
            data: PR analysis results dictionary

        Returns:
            Formatted string representation
        """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """
        Get the appropriate file extension for this format.

        Returns:
            File extension with dot (e.g., '.md', '.json', '.txt')
        """
        pass

    def save_to_file(self, data: dict[str, Any], filepath: Path) -> None:
        """
        Save formatted data to a file.

        Args:
            data: PR analysis results dictionary
            filepath: Path to save the file
        """
        formatted_content = self.format(data)
        filepath.write_text(formatted_content, encoding="utf-8")

    def validate_data(self, data: dict[str, Any]) -> bool:
        """
        Validate that the data contains required fields.

        Args:
            data: PR analysis results dictionary

        Returns:
            True if data is valid, False otherwise
        """
        # Basic validation - can be overridden by subclasses
        return isinstance(data, dict) and len(data) > 0
