"""
Interface and base classes for configuration loaders.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

from .models import RepositoryConfig


class ConfigSource(Protocol):
    """Protocol for configuration sources."""

    def read(self) -> dict[str, Any]:
        """Read configuration data."""
        ...

    def exists(self) -> bool:
        """Check if source exists."""
        ...

    def get_path(self) -> str:
        """Get source path for error messages."""
        ...


class ConfigLoader(ABC):
    """Abstract base class for configuration loaders."""

    @abstractmethod
    def load(self, source: ConfigSource) -> RepositoryConfig:
        """Load configuration from source."""
        pass

    @abstractmethod
    def supports(self, source: ConfigSource) -> bool:
        """Check if loader supports this source type."""
        pass


class ConfigCache:
    """Cache for loaded configurations."""

    def __init__(self, max_size: int = 100):
        self._cache: dict[str, RepositoryConfig] = {}
        self._access_count: dict[str, int] = {}
        self.max_size = max_size

    def get(self, key: str) -> RepositoryConfig | None:
        """Get configuration from cache."""
        if key in self._cache:
            self._access_count[key] = self._access_count.get(key, 0) + 1
            return self._cache[key]
        return None

    def put(self, key: str, config: RepositoryConfig) -> None:
        """Store configuration in cache."""
        # Evict least accessed item if cache is full
        if len(self._cache) >= self.max_size:
            least_accessed = min(self._access_count.items(), key=lambda x: x[1])[0]
            del self._cache[least_accessed]
            del self._access_count[least_accessed]

        self._cache[key] = config
        self._access_count[key] = 1

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._access_count.clear()

    def invalidate(self, key: str) -> None:
        """Invalidate specific cache entry."""
        self._cache.pop(key, None)
        self._access_count.pop(key, None)


class FileConfigSource(ConfigSource):
    """Configuration source from filesystem."""

    def __init__(self, path: Path):
        self.path = path

    def read(self) -> dict[str, Any]:
        """Read JSON configuration."""
        import json

        with open(self.path) as f:
            return json.load(f)

    def exists(self) -> bool:
        """Check if file exists."""
        return self.path.exists()

    def get_path(self) -> str:
        """Get file path."""
        return str(self.path)


class DictConfigSource(ConfigSource):
    """Configuration source from dictionary (for testing)."""

    def __init__(self, data: dict[str, Any], path: str = "memory"):
        self.data = data
        self._path = path

    def read(self) -> dict[str, Any]:
        """Return dictionary data."""
        return self.data

    def exists(self) -> bool:
        """Always exists."""
        return True

    def get_path(self) -> str:
        """Get source identifier."""
        return self._path
