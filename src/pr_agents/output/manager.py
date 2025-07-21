"""
Output manager for coordinating different formatters.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from loguru import logger

from .base import BaseFormatter
from .filename_generator import FilenameGenerator
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
        repo_structure: bool = True,
        auto_name: bool = True,
    ) -> Path:
        """
        Save formatted data to a file.

        Args:
            data: PR analysis results dictionary
            filepath: Path to save the file (can be with or without extension)
            format_type: Output format type (if None, inferred from filepath)
            repo_structure: If True and data contains repo info, organize in repo subdirectory
            auto_name: If True, generate descriptive filename for generic names

        Returns:
            Path to the saved file

        Raises:
            ValueError: If format cannot be determined
        """
        filepath = Path(filepath)

        # Generate descriptive filename if enabled and name is generic
        if auto_name and filepath.name:
            base_name = filepath.stem  # filename without extension
            descriptive_name = FilenameGenerator.generate_pr_filename(data, base_name)
            if descriptive_name != base_name:
                # Replace the filename with the descriptive one
                filepath = filepath.parent / descriptive_name
                if filepath.suffix == "":  # Preserve original extension if it had one
                    filepath = filepath.with_suffix(Path(str(filepath)).suffix)

        # Apply repository-based directory structure if requested
        if repo_structure and "repository" in data:
            repo_info = data["repository"]
            if "full_name" in repo_info:
                # Extract just the repo name from full_name (e.g., "owner/repo" -> "repo")
                repo_name = repo_info["full_name"].split("/")[-1]
                repo_path = Path("output") / repo_name
                # If filepath is relative, prepend the repo path
                if not filepath.is_absolute():
                    filepath = repo_path / filepath

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
        self,
        data: dict[str, Any],
        base_path: Path | str,
        formats: list[OutputFormat],
        repo_structure: bool = True,
        auto_name: bool = True,
    ) -> list[Path]:
        """
        Save data in multiple formats.

        Args:
            data: PR analysis results dictionary
            base_path: Base path for files (without extension)
            formats: List of output formats
            repo_structure: If True and data contains repo info, organize in repo subdirectory
            auto_name: If True, generate descriptive filename for generic names

        Returns:
            List of paths to saved files
        """
        base_path = Path(base_path)
        saved_files = []

        for format_type in formats:
            try:
                filepath = self.save(
                    data, base_path, format_type, repo_structure, auto_name
                )
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

    def save_release_with_individual_prs(
        self,
        data: dict[str, Any],
        output_dir: Path | str,
        format_type: OutputFormat = "markdown",
        batch_size: int = 5,
        progress_callback: Callable | None = None,
    ) -> dict[str, Path]:
        """
        Save release analysis with individual PR files.

        Creates:
        - Main file: {repo}_{release}.md with PRs grouped by tag
        - Individual files: PR_{number}.md with all AI personas

        Args:
            data: Release analysis results with pr_results
            output_dir: Directory to save files
            format_type: Output format (currently only markdown supported)

        Returns:
            Dictionary with paths to main file and PR files
        """
        if format_type not in ["markdown", "md"]:
            raise ValueError(
                "Multi-file output currently only supports markdown format"
            )

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Check if this is release data
        if "pr_results" not in data or "batch_summary" not in data:
            raise ValueError("Data does not appear to be release analysis results")

        # Get repository and release info
        repo_name = data.get("repository", "unknown_repo").replace("/", "_")
        release_tag = data.get("release_tag", data.get("release_version", "unknown"))

        # Create main release file with grouped format
        from .formatters.base import FormatterConfig

        main_config = FormatterConfig(grouped_by_tag=True)
        main_formatter = MarkdownFormatter(config=main_config)

        main_filename = f"{repo_name}_{release_tag}.md"
        main_filepath = output_dir / main_filename

        # Format and save main file
        main_content = main_formatter.format(data)

        # Enhance main content with links to individual PR files
        enhanced_lines = []
        for line in main_content.split("\n"):
            # Look for PR entries and add link to individual file
            if line.startswith("### PR #") and ": " in line:
                # Extract PR number
                pr_num_start = line.find("#") + 1
                pr_num_end = line.find(":", pr_num_start)
                pr_number = line[pr_num_start:pr_num_end]

                # Add link to individual file
                line += f" - [Full Details](./PR_{pr_number}.md)"
            enhanced_lines.append(line)

        # Save main file
        with open(main_filepath, "w") as f:
            f.write("\n".join(enhanced_lines))

        logger.info(f"Saved main release file: {main_filepath}")

        # Create individual PR files with AI personas focus
        saved_files = {"main": main_filepath, "prs": []}

        pr_config = FormatterConfig(
            sections=["header", "ai_summaries", "code_changes", "metadata"],
            include_metrics=False,
        )
        pr_formatter = MarkdownFormatter(config=pr_config)

        # Process each PR
        for pr_url, pr_data in data.get("pr_results", {}).items():
            if pr_data.get("error"):
                continue

            # Get PR number
            pr_number = pr_data.get("pr_number", "unknown")

            # Create individual PR data structure
            individual_pr_data = {
                "pr_url": pr_url,
                "pr_number": pr_number,
                "repository": data.get("repository"),
                "release_version": release_tag,
            }

            # Copy relevant sections from PR data
            for key in [
                "metadata",
                "code_changes",
                "ai_summaries",
                "modules",
                "reviews",
            ]:
                if key in pr_data:
                    individual_pr_data[key] = pr_data[key]

            # Format and save individual PR file
            pr_filename = f"PR_{pr_number}.md"
            pr_filepath = output_dir / pr_filename

            pr_formatter.save_to_file(individual_pr_data, pr_filepath)

            saved_files["prs"].append(pr_filepath)

        logger.info(f"Saved {len(saved_files['prs'])} individual PR files")

        return saved_files
