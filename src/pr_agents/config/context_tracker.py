"""
Context tracking for repository analysis.
Tracks which contexts are loaded and used for each PR analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger


class ContextSource(Enum):
    """Source of context data."""

    JSON_CONFIG = "json_config"
    MARKDOWN = "markdown"
    AGENT_CONTEXT = "agent_context"
    DEFAULT = "default"
    CACHED = "cached"


@dataclass
class ContextUsage:
    """Tracks usage of a specific context."""

    source: ContextSource
    loaded: bool
    is_default: bool = False
    file_path: str | None = None
    size_bytes: int = 0
    load_time_ms: float = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PRContextTracking:
    """Complete context tracking for a PR analysis."""

    pr_url: str
    repo_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    contexts: dict[str, ContextUsage] = field(default_factory=dict)

    def add_context(self, name: str, usage: ContextUsage):
        """Add a context usage record."""
        self.contexts[name] = usage

    def get_summary(self) -> dict[str, Any]:
        """Get summary of context usage."""
        return {
            "pr_url": self.pr_url,
            "repo_name": self.repo_name,
            "timestamp": self.timestamp.isoformat(),
            "contexts_loaded": {
                name: {
                    "source": usage.source.value,
                    "loaded": usage.loaded,
                    "is_default": usage.is_default,
                    "file_path": usage.file_path,
                    "size_bytes": usage.size_bytes,
                    "load_time_ms": usage.load_time_ms,
                    "error": usage.error,
                }
                for name, usage in self.contexts.items()
            },
            "summary": {
                "total_contexts": len(self.contexts),
                "loaded_count": sum(1 for c in self.contexts.values() if c.loaded),
                "default_count": sum(1 for c in self.contexts.values() if c.is_default),
                "error_count": sum(1 for c in self.contexts.values() if c.error),
                "total_size_bytes": sum(c.size_bytes for c in self.contexts.values()),
                "total_load_time_ms": sum(
                    c.load_time_ms for c in self.contexts.values()
                ),
            },
        }


class ContextTracker:
    """Singleton tracker for context usage across the application."""

    _instance = None
    _tracking_data: dict[str, PRContextTracking] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tracking_data = {}
        return cls._instance

    def start_pr_tracking(self, pr_url: str, repo_name: str) -> PRContextTracking:
        """Start tracking context for a PR."""
        tracking = PRContextTracking(pr_url=pr_url, repo_name=repo_name)
        self._tracking_data[pr_url] = tracking
        logger.debug(f"Started context tracking for PR: {pr_url}")
        return tracking

    def get_pr_tracking(self, pr_url: str) -> PRContextTracking | None:
        """Get tracking data for a PR."""
        return self._tracking_data.get(pr_url)

    def record_context_usage(
        self,
        pr_url: str,
        context_name: str,
        source: ContextSource,
        loaded: bool,
        is_default: bool = False,
        file_path: str | None = None,
        size_bytes: int = 0,
        load_time_ms: float = 0,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Record usage of a context."""
        tracking = self._tracking_data.get(pr_url)
        if not tracking:
            logger.warning(f"No tracking found for PR: {pr_url}")
            return

        usage = ContextUsage(
            source=source,
            loaded=loaded,
            is_default=is_default,
            file_path=file_path,
            size_bytes=size_bytes,
            load_time_ms=load_time_ms,
            error=error,
            metadata=metadata or {},
        )

        tracking.add_context(context_name, usage)

        # Log the usage
        if loaded:
            if is_default:
                logger.info(
                    f"Loaded DEFAULT {context_name} context for {tracking.repo_name} "
                    f"(source: {source.value})"
                )
            else:
                logger.info(
                    f"Loaded {context_name} context for {tracking.repo_name} "
                    f"from {file_path or 'memory'} ({size_bytes} bytes, {load_time_ms:.1f}ms)"
                )
        else:
            logger.debug(
                f"Failed to load {context_name} context for {tracking.repo_name}: {error or 'Not found'}"
            )

    def get_summary(self, pr_url: str) -> dict[str, Any] | None:
        """Get summary of context usage for a PR."""
        tracking = self._tracking_data.get(pr_url)
        if not tracking:
            return None
        return tracking.get_summary()

    def get_all_summaries(self) -> dict[str, dict[str, Any]]:
        """Get summaries for all tracked PRs."""
        return {
            url: tracking.get_summary() for url, tracking in self._tracking_data.items()
        }

    def clear_tracking(self, pr_url: str | None = None):
        """Clear tracking data."""
        if pr_url:
            self._tracking_data.pop(pr_url, None)
            logger.debug(f"Cleared context tracking for PR: {pr_url}")
        else:
            self._tracking_data.clear()
            logger.debug("Cleared all context tracking data")

    def log_summary(self, pr_url: str):
        """Log a summary of context usage for a PR."""
        summary = self.get_summary(pr_url)
        if not summary:
            return

        logger.info(f"Context usage summary for {summary['repo_name']}:")
        logger.info(f"  Total contexts: {summary['summary']['total_contexts']}")
        logger.info(f"  Successfully loaded: {summary['summary']['loaded_count']}")
        logger.info(f"  Using defaults: {summary['summary']['default_count']}")
        logger.info(f"  Errors: {summary['summary']['error_count']}")
        logger.info(
            f"  Total load time: {summary['summary']['total_load_time_ms']:.1f}ms"
        )

        # Log details for each context
        for name, details in summary["contexts_loaded"].items():
            if details["is_default"]:
                logger.info(f"  - {name}: DEFAULT ({details['source']})")
            elif details["loaded"]:
                logger.info(
                    f"  - {name}: LOADED from {details['file_path']} "
                    f"({details['size_bytes']} bytes)"
                )
            else:
                logger.info(f"  - {name}: FAILED ({details['error']})")
