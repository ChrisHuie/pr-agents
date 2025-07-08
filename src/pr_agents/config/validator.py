"""
Configuration validator for repository structures.
"""

import json
from pathlib import Path

from jsonschema import Draft7Validator
from loguru import logger


class ConfigurationValidator:
    """Validates repository configuration against schema."""

    def __init__(self, schema_path: str = "config/schema/repository.schema.json"):
        """
        Initialize the configuration validator.

        Args:
            schema_path: Path to the JSON schema file
        """
        self.schema_path = Path(schema_path)
        self.schema: dict | None = None
        self.validator: Draft7Validator | None = None
        self._load_schema()

    def _load_schema(self):
        """Load the JSON schema for validation."""
        if self.schema_path.exists():
            with open(self.schema_path) as f:
                self.schema = json.load(f)
                self.validator = Draft7Validator(self.schema)
        else:
            logger.warning(f"Schema file not found: {self.schema_path}")

    def validate_file(self, config_file: Path) -> tuple[bool, list[str]]:
        """
        Validate a configuration file against the schema.

        Args:
            config_file: Path to the configuration file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not self.validator:
            return True, ["No schema loaded, skipping validation"]

        try:
            with open(config_file) as f:
                config_data = json.load(f)

            errors = []
            for error in self.validator.iter_errors(config_data):
                error_path = " -> ".join(str(p) for p in error.path)
                errors.append(f"{error_path}: {error.message}")

            return len(errors) == 0, errors

        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]
        except Exception as e:
            return False, [f"Validation error: {e}"]

    def validate_config(self, config_data: dict) -> tuple[bool, list[str]]:
        """
        Validate configuration data against the schema.

        Args:
            config_data: Configuration dictionary

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not self.validator:
            return True, ["No schema loaded, skipping validation"]

        errors = []
        for error in self.validator.iter_errors(config_data):
            error_path = " -> ".join(str(p) for p in error.path)
            errors.append(f"{error_path}: {error.message}")

        return len(errors) == 0, errors

    def validate_directory(self, directory: Path) -> dict[str, tuple[bool, list[str]]]:
        """
        Validate all configuration files in a directory.

        Args:
            directory: Directory containing configuration files

        Returns:
            Dictionary mapping file paths to validation results
        """
        results = {}

        for json_file in directory.rglob("*.json"):
            # Skip schema files
            if "schema" in str(json_file):
                continue

            is_valid, errors = self.validate_file(json_file)
            results[str(json_file)] = (is_valid, errors)

            if not is_valid:
                logger.error(f"Validation failed for {json_file}: {errors}")
            else:
                logger.info(f"Validation passed for {json_file}")

        return results

    def check_required_fields(self, config_data: dict) -> list[str]:
        """
        Check for required fields in configuration.

        Args:
            config_data: Configuration dictionary

        Returns:
            List of missing required fields
        """
        required_fields = ["repo_name", "repo_type", "module_categories"]
        missing = []

        for field in required_fields:
            if field not in config_data:
                missing.append(field)

        return missing

    def check_pattern_consistency(self, config_data: dict) -> list[str]:
        """
        Check for pattern consistency in module categories.

        Args:
            config_data: Configuration dictionary

        Returns:
            List of consistency issues
        """
        issues = []

        if "module_categories" not in config_data:
            return issues

        for cat_name, category in config_data["module_categories"].items():
            if "patterns" not in category or not category["patterns"]:
                issues.append(f"Module category '{cat_name}' has no patterns defined")
                continue

            # Check for duplicate patterns
            patterns = [p.get("pattern", "") for p in category["patterns"]]
            duplicates = [p for p in patterns if patterns.count(p) > 1]
            if duplicates:
                issues.append(f"Duplicate patterns in '{cat_name}': {set(duplicates)}")

            # Check pattern type consistency
            for pattern in category["patterns"]:
                pattern_type = pattern.get("type", "glob")
                pattern_value = pattern.get("pattern", "")

                # Basic pattern validation
                if pattern_type == "suffix" and not pattern_value.startswith("*"):
                    issues.append(
                        f"Suffix pattern in '{cat_name}' should start with '*': {pattern_value}"
                    )
                elif pattern_type == "prefix" and not pattern_value.endswith("*"):
                    issues.append(
                        f"Prefix pattern in '{cat_name}' should end with '*': {pattern_value}"
                    )

        return issues

    def validate_inheritance(self, config_file: Path) -> tuple[bool, list[str]]:
        """
        Validate inheritance chain for a configuration file.

        Args:
            config_file: Path to the configuration file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        visited = set()

        def check_extends(file_path: Path) -> bool:
            if str(file_path) in visited:
                errors.append(f"Circular inheritance detected: {file_path}")
                return False

            visited.add(str(file_path))

            try:
                with open(file_path) as f:
                    data = json.load(f)

                if "extends" in data:
                    base_path = file_path.parent / data["extends"]
                    if not base_path.exists():
                        errors.append(f"Base config not found: {base_path}")
                        return False
                    return check_extends(base_path)

                return True

            except Exception as e:
                errors.append(f"Error reading {file_path}: {e}")
                return False

        is_valid = check_extends(config_file)
        return is_valid, errors
