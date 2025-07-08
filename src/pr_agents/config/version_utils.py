"""
Version parsing and comparison utilities.
"""

from functools import lru_cache

from packaging.version import InvalidVersion, Version

from .exceptions import VersionParseError


@lru_cache(maxsize=128)
def parse_version(version_str: str) -> Version:
    """
    Parse a version string into a Version object.

    Args:
        version_str: Version string (e.g., "v10.0", "10.0.1")

    Returns:
        Parsed Version object

    Raises:
        VersionParseError: If version cannot be parsed
    """
    # Remove common prefixes
    cleaned = version_str.lstrip("v")

    try:
        return Version(cleaned)
    except InvalidVersion as e:
        raise VersionParseError(f"Invalid version string: {version_str}") from e


def version_matches_range(version: str, version_range: str) -> bool:
    """
    Check if a version matches a version range specification.

    Args:
        version: Version to check
        version_range: Range specification (e.g., ">=10.0", ">=9.0,<10.0")

    Returns:
        True if version matches the range
    """
    try:
        parsed_version = parse_version(version)

        # Handle compound ranges
        if "," in version_range:
            # All parts must match
            for part in version_range.split(","):
                if not _check_single_range(parsed_version, part.strip()):
                    return False
            return True
        else:
            # Single range
            return _check_single_range(parsed_version, version_range)

    except (VersionParseError, ValueError):
        return False


def _check_single_range(version: Version, range_spec: str) -> bool:
    """Check if version matches a single range specification."""
    if range_spec.startswith(">="):
        min_version = parse_version(range_spec[2:].strip())
        return version >= min_version
    elif range_spec.startswith(">"):
        min_version = parse_version(range_spec[1:].strip())
        return version > min_version
    elif range_spec.startswith("<="):
        max_version = parse_version(range_spec[2:].strip())
        return version <= max_version
    elif range_spec.startswith("<"):
        max_version = parse_version(range_spec[1:].strip())
        return version < max_version
    elif range_spec.startswith("=="):
        exact_version = parse_version(range_spec[2:].strip())
        return version == exact_version
    else:
        # Assume exact match
        exact_version = parse_version(range_spec)
        return version == exact_version


def extract_version_and_range(version_key: str) -> tuple[str, str | None]:
    """
    Extract version and range from a version key.

    Args:
        version_key: Version key (e.g., "v10.0+", "v9.0")

    Returns:
        Tuple of (version, range_spec)
    """
    if version_key.endswith("+"):
        version = version_key[:-1]
        # Convert + suffix to >= range
        range_spec = f">={version.lstrip('v')}"
        return version, range_spec
    else:
        return version_key, None
