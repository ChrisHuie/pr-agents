"""
Custom exceptions for configuration system.
"""


class ConfigurationError(Exception):
    """Base exception for configuration errors."""

    pass


class ConfigurationLoadError(ConfigurationError):
    """Raised when configuration cannot be loaded."""

    pass


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration fails validation."""

    pass


class ConfigurationNotFoundError(ConfigurationError):
    """Raised when requested configuration is not found."""

    pass


class CircularInheritanceError(ConfigurationError):
    """Raised when circular inheritance is detected."""

    pass


class InvalidPatternError(ConfigurationError):
    """Raised when an invalid pattern is encountered."""

    pass


class VersionParseError(ConfigurationError):
    """Raised when version string cannot be parsed."""

    pass
