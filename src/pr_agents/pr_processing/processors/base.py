"""
Base processor interface for analyzing extracted PR components.
"""

from abc import ABC, abstractmethod
from typing import Any

from ..models import ProcessingResult


class BaseProcessor(ABC):
    """Base class for all PR component processors."""

    @abstractmethod
    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """
        Process extracted component data in isolation.

        Args:
            component_data: Dictionary containing component-specific data

        Returns:
            ProcessingResult with analysis results
        """
        pass

    @property
    @abstractmethod
    def component_name(self) -> str:
        """Name of the component this processor handles."""
        pass
