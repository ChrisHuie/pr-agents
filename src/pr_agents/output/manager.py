"""
Output manager for coordinating different formatters.
"""

from pathlib import Path
from typing import Any, Literal

from loguru import logger

from .base import BaseFormatter
from .json_formatter import JSONFormatter
from .markdown import MarkdownFormatter
from .text import TextFormatter

OutputFormat = Literal["markdown", "md", "text", "txt", "json"]


class OutputManager:
    """
    Manages different output formatters and handles file writing.

    Provides a unified interface for formatting and saving PR analysis results
    in various formats.
    """

    def __init__(self):
        """Initialize output manager with available formatters."""
        self.formatters = {
            "markdown": MarkdownFormatter(),
            "md": MarkdownFormatter(),
            "text": TextFormatter(),
            "txt": TextFormatter(),
            "json": JSONFormatter(),
        }
        logger.info(
            "Output manager initialized with formatters: {}",
            list(self.formatters.keys()),
        )

    def format(self, data: dict[str, Any], format_type: OutputFormat) -> str:
        """
        Format data using the specified formatter.

        Args:
            data: PR analysis results dictionary
            format_type: Output format type

        Returns:
            Formatted string

        Raises:
            ValueError: If format_type is not supported
        """
        formatter = self._get_formatter(format_type)

        if not formatter.validate_data(data):
            logger.warning("Data validation failed for format: {}", format_type)

        return formatter.format(data)

    def save(
        self,
        data: dict[str, Any],
        filepath: Path | str,
        format_type: OutputFormat | None = None,
    ) -> Path:
        """
        Save formatted data to a file.

        Args:
            data: PR analysis results dictionary
            filepath: Path to save the file (can be with or without extension)
            format_type: Output format type (if None, inferred from filepath)

        Returns:
            Path to the saved file

        Raises:
            ValueError: If format cannot be determined
        """
        filepath = Path(filepath)

        # Determine format from file extension if not specified
        if format_type is None:
            if filepath.suffix:
                format_type = self._infer_format_from_extension(filepath.suffix)
            else:
                raise ValueError(
                    "Cannot determine output format: no format specified and no file extension"
                )

        formatter = self._get_formatter(format_type)

        # Add extension if not present
        if not filepath.suffix:
            filepath = filepath.with_suffix(formatter.get_file_extension())

        # Create parent directories if needed
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Save the file
        formatter.save_to_file(data, filepath)
        logger.info("Saved PR analysis to: {}", filepath)

        return filepath

    def save_multiple_formats(
        self, data: dict[str, Any], base_path: Path | str, formats: list[OutputFormat]
    ) -> list[Path]:
        """
        Save data in multiple formats.

        Args:
            data: PR analysis results dictionary
            base_path: Base path for files (without extension)
            formats: List of output formats

        Returns:
            List of paths to saved files
        """
        base_path = Path(base_path)
        saved_files = []

        for format_type in formats:
            try:
                filepath = self.save(data, base_path, format_type)
                saved_files.append(filepath)
            except Exception as e:
                logger.error("Failed to save {} format: {}", format_type, e)

        return saved_files

    def _get_formatter(self, format_type: OutputFormat) -> BaseFormatter:
        """
        Get formatter for the specified format type.

        Args:
            format_type: Output format type

        Returns:
            Formatter instance

        Raises:
            ValueError: If format_type is not supported
        """
        if format_type not in self.formatters:
            raise ValueError(
                f"Unsupported format: {format_type}. "
                f"Available formats: {list(self.formatters.keys())}"
            )

        return self.formatters[format_type]

    def _infer_format_from_extension(self, extension: str) -> OutputFormat:
        """
        Infer format type from file extension.

        Args:
            extension: File extension (with or without dot)

        Returns:
            Format type

        Raises:
            ValueError: If extension is not recognized
        """
        # Remove dot if present
        ext = extension.lstrip(".")

        extension_map = {
            "md": "markdown",
            "markdown": "markdown",
            "txt": "text",
            "text": "text",
            "json": "json",
        }

        if ext not in extension_map:
            raise ValueError(f"Unknown file extension: {extension}")

        return extension_map[ext]

    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported output formats.

        Returns:
            List of format names
        """
        # Return unique format names (excluding aliases)
        unique_formats = []
        seen_formatters = set()

        for format_name, formatter in self.formatters.items():
            formatter_type = type(formatter)
            if formatter_type not in seen_formatters:
                unique_formats.append(format_name)
                seen_formatters.add(formatter_type)

        return unique_formats
