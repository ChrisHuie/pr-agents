"""
Module detection strategies for different module types.
"""

from abc import ABC, abstractmethod
from typing import Any


class ModuleDetector(ABC):
    """Base class for module type detection strategies."""

    @abstractmethod
    def detect(self, module_name: str, file_path: str) -> tuple[str | None, str | None]:
        """
        Detect if the given module matches this detector's pattern.

        Args:
            module_name: Name of the module
            file_path: Full file path

        Returns:
            Tuple of (module_type, category) or (None, None) if no match
        """
        pass


class BidAdapterDetector(ModuleDetector):
    """Detects bid adapter modules."""

    def detect(self, module_name: str, file_path: str) -> tuple[str | None, str | None]:
        if module_name.endswith("BidAdapter"):
            return "bid_adapter", "adapter"
        return None, None


class RtdModuleDetector(ModuleDetector):
    """Detects real-time data modules."""

    def detect(self, module_name: str, file_path: str) -> tuple[str | None, str | None]:
        if module_name.endswith("RtdModule") or module_name.endswith("RtdProvider"):
            return "rtd_module", "rtd"
        return None, None


class AnalyticsAdapterDetector(ModuleDetector):
    """Detects analytics adapter modules."""

    def detect(self, module_name: str, file_path: str) -> tuple[str | None, str | None]:
        if module_name.endswith("AnalyticsAdapter"):
            return "analytics_adapter", "analytics"
        return None, None


class IdSystemDetector(ModuleDetector):
    """Detects ID system modules."""

    def detect(self, module_name: str, file_path: str) -> tuple[str | None, str | None]:
        if module_name.endswith("IdSystem"):
            return "id_system", "identity"
        return None, None


class UserModuleDetector(ModuleDetector):
    """Detects user modules."""

    def detect(self, module_name: str, file_path: str) -> tuple[str | None, str | None]:
        if module_name.endswith("UserModule"):
            return "user_module", "user"
        return None, None


class VideoModuleDetector(ModuleDetector):
    """Detects video modules."""

    def detect(self, module_name: str, file_path: str) -> tuple[str | None, str | None]:
        if module_name.endswith("VideoModule"):
            return "video_module", "video"
        return None, None


class ConfigBasedDetector(ModuleDetector):
    """Detects modules based on repository configuration patterns."""

    def __init__(self, module_type: str, config: dict[str, Any]):
        self.module_type = module_type
        self.config = config
        self.paths = config.get("paths", [])
        self.naming_pattern = config.get("naming_pattern", "")
        self.category = config.get("category", self._determine_category(module_type))

    def detect(self, module_name: str, file_path: str) -> tuple[str | None, str | None]:
        # Check if file matches configured paths
        for path_pattern in self.paths:
            if self._matches_pattern(file_path, path_pattern):
                # Check naming pattern if specified
                if self.naming_pattern:
                    if self._matches_naming_pattern(module_name):
                        return self.module_type, self.category
                else:
                    # No naming pattern, just path match is enough
                    return self.module_type, self.category
        return None, None

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches a pattern."""
        import fnmatch

        return fnmatch.fnmatch(file_path, pattern)

    def _matches_naming_pattern(self, module_name: str) -> bool:
        """Check if module name matches naming pattern."""
        if "endsWith" in self.naming_pattern:
            suffix = self.naming_pattern.split("'")[1]
            return module_name.endswith(suffix)
        elif "startsWith" in self.naming_pattern:
            prefix = self.naming_pattern.split("'")[1]
            return module_name.startswith(prefix)
        return True

    def _determine_category(self, module_type: str) -> str:
        """Determine category from module type."""
        category_map = {
            "bid_adapter": "adapter",
            "analytics_adapter": "analytics",
            "rtd_provider": "rtd",
            "rtd_module": "rtd",
            "id_system": "identity",
            "user_module": "user",
            "video_module": "video",
            "core": "core",
            "library": "utility",
            "generic": "utility",
        }
        return category_map.get(module_type, "other")


class ModuleDetectorRegistry:
    """Registry for module detectors."""

    def __init__(self):
        # Default detectors for common patterns
        self.default_detectors: list[ModuleDetector] = [
            BidAdapterDetector(),
            RtdModuleDetector(),
            AnalyticsAdapterDetector(),
            IdSystemDetector(),
            UserModuleDetector(),
            VideoModuleDetector(),
        ]
        self.config_detectors: list[ModuleDetector] = []

    def load_repository_config(self, config: dict[str, Any]) -> None:
        """
        Load repository-specific module detection configuration.

        Args:
            config: Repository configuration with module_locations
        """
        self.config_detectors.clear()

        module_locations = config.get("module_locations", {})
        for module_type, type_config in module_locations.items():
            detector = ConfigBasedDetector(module_type, type_config)
            self.config_detectors.append(detector)

    def detect_module_type(self, module_name: str, file_path: str) -> dict[str, Any]:
        """
        Detect module type using registered detectors.

        Config-based detectors are checked first, then default detectors.

        Args:
            module_name: Name of the module
            file_path: Full file path

        Returns:
            Dictionary with type and category
        """
        # Check config-based detectors first (more specific)
        for detector in self.config_detectors:
            module_type, category = detector.detect(module_name, file_path)
            if module_type:
                return {"type": module_type, "category": category}

        # Fall back to default detectors
        for detector in self.default_detectors:
            module_type, category = detector.detect(module_name, file_path)
            if module_type:
                return {"type": module_type, "category": category}

        # Default to generic if no detector matches
        return {"type": "generic", "category": "utility"}

    def register_detector(
        self, detector: ModuleDetector, use_config: bool = False
    ) -> None:
        """
        Register a new module detector.

        Args:
            detector: Module detector instance
            use_config: If True, add to config detectors, else to default
        """
        if use_config:
            self.config_detectors.append(detector)
        else:
            self.default_detectors.append(detector)
