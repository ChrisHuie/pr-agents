"""
Module processor for analyzing extracted module data across different repository types.
"""

from typing import Any

from ..models import ProcessingResult
from .base import BaseProcessor


class ModuleProcessor(BaseProcessor):
    """
    Processes extracted module data to provide repository-specific insights.

    Handles different repository structures:
    - JavaScript (Prebid.js): Individual adapter files, RTD modules, analytics
    - Server repos (Go, Java): Package-based modules, bidder implementations
    - Mobile repos: SDK components, platform-specific modules
    """

    @property
    def component_name(self) -> str:
        """Return the component name this processor handles."""
        return "modules"

    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """
        Process module extraction data with repository-specific analysis.

        Args:
            component_data: Dictionary containing extracted module data and repo info

        Returns:
            ProcessingResult with module analysis
        """
        try:
            # Extract module data
            modules = component_data.get("modules", [])
            module_categories = component_data.get("module_categories", {})
            primary_module_type = component_data.get("primary_module_type")
            total_modules = component_data.get("total_modules", 0)
            repository = component_data.get("repository", {})

            # Determine repository type
            repo_type = self._determine_repo_type(repository)

            # Perform repository-specific analysis
            if repo_type == "prebid-js":
                module_analysis = self._analyze_js_modules(
                    modules, module_categories, primary_module_type
                )
            elif repo_type == "prebid-server":
                module_analysis = self._analyze_server_modules(
                    modules, module_categories, repository
                )
            elif repo_type == "prebid-mobile":
                module_analysis = self._analyze_mobile_modules(
                    modules, module_categories, repository
                )
            else:
                # Generic analysis for unknown repo types
                module_analysis = self._analyze_generic_modules(
                    modules, module_categories, primary_module_type
                )

            # Add common fields
            module_analysis.update(
                {
                    "total_modules": total_modules,
                    "repository_type": repo_type,
                    "primary_type": primary_module_type,
                }
            )

            return ProcessingResult(
                component=self.component_name,
                success=True,
                data=module_analysis,
            )

        except Exception as e:
            return ProcessingResult(
                component=self.component_name,
                success=False,
                errors=[f"Module processing error: {str(e)}"],
            )

    def _determine_repo_type(self, repository: dict[str, Any]) -> str:
        """Determine repository type from repository data."""
        repo_name = repository.get("name", "").lower()
        full_name = repository.get("full_name", "").lower()

        # Check for specific repository patterns
        if "prebid.js" in repo_name or "/prebid.js" in full_name:
            return "prebid-js"
        elif "prebid-server" in repo_name or "/prebid-server" in full_name:
            return "prebid-server"
        elif "prebid-mobile" in repo_name or (
            "mobile" in repo_name and "prebid" in full_name
        ):
            return "prebid-mobile"
        elif "android" in repo_name or "ios" in repo_name:
            return "prebid-mobile"

        # Check language hints
        language = repository.get("language", "").lower()
        if language in ["java", "go"] and "prebid" in full_name:
            return "prebid-server"

        return "generic"

    def _analyze_js_modules(
        self,
        modules: list[dict[str, Any]],
        categories: dict[str, list[str]],
        primary_type: str | None,
    ) -> dict[str, Any]:
        """Analyze modules for JavaScript repository (adapters, RTD, analytics)."""
        analysis = {
            "modules": self._format_js_modules(modules),
            "categories": self._analyze_categories(categories),
            "adapter_changes": self._analyze_adapter_changes(modules),
            "changes_summary": self._generate_js_changes_summary(modules, primary_type),
        }

        # Check for important JS modules
        important = self._check_important_js_modules(modules)
        if important:
            analysis["important_modules"] = important

        # Check for new adapters
        new_adapters = self._find_new_adapters(modules)
        if new_adapters:
            analysis["new_adapters"] = new_adapters

        return analysis

    def _analyze_server_modules(
        self,
        modules: list[dict[str, Any]],
        categories: dict[str, list[str]],
        repository: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze modules for server repositories (Go, Java)."""
        language = repository.get("language", "").lower()

        analysis = {
            "modules": self._format_server_modules(modules, language),
            "categories": self._analyze_categories(categories),
            "package_changes": self._analyze_package_changes(modules, language),
            "changes_summary": self._generate_server_changes_summary(modules, language),
        }

        # Check for bidder implementations
        bidder_changes = self._analyze_bidder_changes(modules, language)
        if bidder_changes:
            analysis["bidder_changes"] = bidder_changes

        return analysis

    def _analyze_mobile_modules(
        self,
        modules: list[dict[str, Any]],
        categories: dict[str, list[str]],
        repository: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze modules for mobile repositories."""
        platform = self._detect_mobile_platform(repository)

        analysis = {
            "modules": self._format_mobile_modules(modules, platform),
            "categories": self._analyze_categories(categories),
            "platform": platform,
            "component_changes": self._analyze_mobile_components(modules, platform),
            "changes_summary": self._generate_mobile_changes_summary(modules, platform),
        }

        # Check for SDK core changes
        core_changes = self._check_mobile_core_changes(modules, platform)
        if core_changes:
            analysis["core_changes"] = core_changes

        return analysis

    def _analyze_generic_modules(
        self,
        modules: list[dict[str, Any]],
        categories: dict[str, list[str]],
        primary_type: str | None,
    ) -> dict[str, Any]:
        """Generic module analysis for unknown repository types."""
        return {
            "modules": self._format_generic_modules(modules),
            "categories": self._analyze_categories(categories),
            "changes_summary": self._generate_generic_changes_summary(
                modules, primary_type
            ),
        }

    # JavaScript-specific methods
    def _format_js_modules(self, modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format JavaScript modules with adapter-specific information."""
        formatted = []

        # Ensure modules is a list
        if not isinstance(modules, list):
            return formatted

        for module in modules:
            if isinstance(module, dict):
                module_info = {
                    "name": module.get("name", "Unknown"),
                    "type": module.get("type", "unknown"),
                    "file": module.get("file", ""),
                    "action": module.get("action", "modified"),
                }

                # Add adapter-specific info
                if module.get("type") == "bid_adapter":
                    module_info["adapter_type"] = "bidder"
                elif module.get("type") in ["rtd_provider", "rtd_module"]:
                    module_info["adapter_type"] = "real-time-data"
                elif module.get("type") == "analytics_adapter":
                    module_info["adapter_type"] = "analytics"

                formatted.append(module_info)
            else:
                formatted.append(
                    {"name": str(module), "type": "unknown", "action": "modified"}
                )

        return formatted

    def _analyze_adapter_changes(self, modules: list[dict[str, Any]]) -> dict[str, int]:
        """Analyze adapter-specific changes for JS repos."""
        adapter_counts = {
            "bid_adapters": 0,
            "rtd_providers": 0,
            "analytics_adapters": 0,
            "user_modules": 0,
            "other": 0,
        }

        for module in modules:
            if isinstance(module, dict):
                module_type = module.get("type", "")
                if module_type == "bid_adapter":
                    adapter_counts["bid_adapters"] += 1
                elif module_type in ["rtd_provider", "rtd_module"]:
                    adapter_counts["rtd_providers"] += 1
                elif module_type == "analytics_adapter":
                    adapter_counts["analytics_adapters"] += 1
                elif module_type == "user_module":
                    adapter_counts["user_modules"] += 1
                else:
                    adapter_counts["other"] += 1

        return {k: v for k, v in adapter_counts.items() if v > 0}

    def _check_important_js_modules(self, modules: list[dict[str, Any]]) -> list[str]:
        """Check for important/core JavaScript modules."""
        important = []
        core_modules = {
            "prebidCore": "Core auction logic",
            "adapterManager": "Adapter management system",
            "auctionManager": "Auction orchestration",
            "userSync": "User synchronization",
            "config": "Configuration management",
            "gdprEnforcement": "GDPR compliance",
            "consentManagement": "Consent handling",
            "currency": "Currency conversion",
            "sizeMapping": "Responsive ad sizing",
            "priceFloors": "Price floor management",
        }

        for module in modules:
            module_name = ""
            if isinstance(module, dict):
                module_name = module.get("name", "")
                file_path = module.get("file", "")
            else:
                module_name = str(module)
                file_path = ""

            # Check module name and file path
            for core_name, description in core_modules.items():
                if (
                    core_name.lower() in module_name.lower()
                    or core_name.lower() in file_path.lower()
                ):
                    important.append(f"{core_name} - {description}")
                    break

        return important

    def _find_new_adapters(self, modules: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Find newly added adapters."""
        new_adapters = []

        for module in modules:
            if isinstance(module, dict):
                if module.get("action") == "added" and module.get("type") in [
                    "bid_adapter",
                    "rtd_provider",
                    "rtd_module",
                    "analytics_adapter",
                ]:
                    new_adapters.append(
                        {
                            "name": module.get("name", "Unknown"),
                            "type": module.get("type", "unknown"),
                            "file": module.get("file", ""),
                        }
                    )

        return new_adapters

    def _generate_js_changes_summary(
        self, modules: list[dict[str, Any]], primary_type: str | None
    ) -> str:
        """Generate JavaScript-specific change summary."""
        if not modules:
            return "No module changes detected"

        # Count different types
        adapter_changes = self._analyze_adapter_changes(modules)

        parts = []
        if adapter_changes.get("bid_adapters", 0) > 0:
            count = adapter_changes["bid_adapters"]
            parts.append(f"{count} bid adapter{'s' if count > 1 else ''}")

        if adapter_changes.get("rtd_providers", 0) > 0:
            count = adapter_changes["rtd_providers"]
            parts.append(f"{count} RTD provider{'s' if count > 1 else ''}")

        if adapter_changes.get("analytics_adapters", 0) > 0:
            count = adapter_changes["analytics_adapters"]
            parts.append(f"{count} analytics adapter{'s' if count > 1 else ''}")

        if not parts:
            return f"Modified {len(modules)} module{'s' if len(modules) > 1 else ''}"

        return f"Modified {', '.join(parts)}"

    # Server-specific methods
    def _format_server_modules(
        self, modules: list[dict[str, Any]], language: str
    ) -> list[dict[str, Any]]:
        """Format server modules with language-specific information."""
        formatted = []

        for module in modules:
            if isinstance(module, dict):
                module_info = {
                    "name": module.get("name", "Unknown"),
                    "type": module.get("type", "unknown"),
                    "file": module.get("file", ""),
                    "action": module.get("action", "modified"),
                    "language": language,
                }

                # Add package information for Go/Java
                if language in ["go", "java"]:
                    file_path = module.get("file", "")
                    module_info["package"] = self._extract_package_from_path(
                        file_path, language
                    )

                formatted.append(module_info)
            else:
                formatted.append(
                    {"name": str(module), "type": "unknown", "action": "modified"}
                )

        return formatted

    def _analyze_package_changes(
        self, modules: list[dict[str, Any]], language: str
    ) -> dict[str, list[str]]:
        """Analyze package-level changes for server repos."""
        packages = {}

        for module in modules:
            if isinstance(module, dict):
                file_path = module.get("file", "")
                package = self._extract_package_from_path(file_path, language)

                if package:
                    if package not in packages:
                        packages[package] = []
                    packages[package].append(module.get("name", file_path))

        return packages

    def _analyze_bidder_changes(
        self, modules: list[dict[str, Any]], language: str
    ) -> list[dict[str, str]]:
        """Analyze bidder-specific changes in server repos."""
        bidder_changes = []

        # Patterns for different languages
        bidder_patterns = {
            "go": ["adapters/", "openrtb_ext/"],
            "java": ["bidders/", "adapter/"],
        }

        patterns = bidder_patterns.get(language, [])

        for module in modules:
            if isinstance(module, dict):
                file_path = module.get("file", "")

                for pattern in patterns:
                    if pattern in file_path:
                        bidder_name = self._extract_bidder_name(file_path, pattern)
                        if bidder_name:
                            bidder_changes.append(
                                {
                                    "name": bidder_name,
                                    "file": file_path,
                                    "action": module.get("action", "modified"),
                                }
                            )
                        break

        return bidder_changes

    def _extract_package_from_path(self, file_path: str, language: str) -> str:
        """Extract package name from file path."""
        if not file_path:
            return ""

        if language == "go":
            # For Go, extract package from path like "adapters/appnexus/appnexus.go"
            parts = file_path.split("/")
            if len(parts) > 1:
                return "/".join(parts[:-1])
        elif language == "java":
            # For Java, extract package from path like "src/main/java/org/prebid/server/bidder/appnexus/AppnexusBidder.java"
            if "src/main/java/" in file_path:
                package_path = file_path.split("src/main/java/")[1]
                parts = package_path.split("/")[:-1]
                return ".".join(parts)

        return ""

    def _extract_bidder_name(self, file_path: str, pattern: str) -> str:
        """Extract bidder name from file path."""
        parts = file_path.split(pattern)
        if len(parts) > 1:
            remaining = parts[1].split("/")[0]
            return remaining
        return ""

    def _generate_server_changes_summary(
        self, modules: list[dict[str, Any]], language: str
    ) -> str:
        """Generate server-specific change summary."""
        if not modules:
            return "No module changes detected"

        bidder_changes = self._analyze_bidder_changes(modules, language)

        if bidder_changes:
            bidder_names = list({change["name"] for change in bidder_changes})
            if len(bidder_names) == 1:
                return f"Modified {bidder_names[0]} bidder"
            else:
                return f"Modified {len(bidder_names)} bidders: {', '.join(bidder_names[:3])}"

        return f"Modified {len(modules)} {language} module{'s' if len(modules) > 1 else ''}"

    # Mobile-specific methods
    def _detect_mobile_platform(self, repository: dict[str, Any]) -> str:
        """Detect mobile platform from repository information."""
        repo_name = repository.get("name", "").lower()
        languages = repository.get("languages", {})

        if "android" in repo_name or "kotlin" in languages or "java" in languages:
            return "android"
        elif "ios" in repo_name or "swift" in languages or "objective-c" in languages:
            return "ios"

        return "unknown"

    def _format_mobile_modules(
        self, modules: list[dict[str, Any]], platform: str
    ) -> list[dict[str, Any]]:
        """Format mobile modules with platform-specific information."""
        formatted = []

        for module in modules:
            if isinstance(module, dict):
                module_info = {
                    "name": module.get("name", "Unknown"),
                    "type": module.get("type", "unknown"),
                    "file": module.get("file", ""),
                    "action": module.get("action", "modified"),
                    "platform": platform,
                }

                # Detect component type from file path
                file_path = module.get("file", "")
                module_info["component"] = self._detect_mobile_component(
                    file_path, platform
                )

                formatted.append(module_info)
            else:
                formatted.append(
                    {"name": str(module), "type": "unknown", "action": "modified"}
                )

        return formatted

    def _analyze_mobile_components(
        self, modules: list[dict[str, Any]], platform: str
    ) -> dict[str, int]:
        """Analyze mobile component changes."""
        components = {
            "core": 0,
            "rendering": 0,
            "networking": 0,
            "cache": 0,
            "utilities": 0,
            "tests": 0,
            "other": 0,
        }

        for module in modules:
            if isinstance(module, dict):
                file_path = module.get("file", "")
                component = self._detect_mobile_component(file_path, platform)

                if component in components:
                    components[component] += 1
                else:
                    components["other"] += 1

        return {k: v for k, v in components.items() if v > 0}

    def _detect_mobile_component(self, file_path: str, platform: str) -> str:
        """Detect mobile component type from file path."""
        path_lower = file_path.lower()

        # Common patterns across platforms
        if any(pattern in path_lower for pattern in ["core/", "prebidmobile", "sdk/"]):
            return "core"
        elif any(
            pattern in path_lower for pattern in ["render", "creative", "webview"]
        ):
            return "rendering"
        elif any(pattern in path_lower for pattern in ["network", "request", "http"]):
            return "networking"
        elif any(pattern in path_lower for pattern in ["cache", "storage"]):
            return "cache"
        elif any(pattern in path_lower for pattern in ["util", "helper", "common"]):
            return "utilities"
        elif any(pattern in path_lower for pattern in ["test", "spec", "mock"]):
            return "tests"

        return "other"

    def _check_mobile_core_changes(
        self, modules: list[dict[str, Any]], platform: str
    ) -> list[str]:
        """Check for core mobile SDK changes."""
        core_changes = []

        core_patterns = {
            "android": [
                "PrebidMobile",
                "BidManager",
                "AdUnit",
                "TargetingParams",
                "PrebidServerAdapter",
            ],
            "ios": [
                "PrebidMobile",
                "BidManager",
                "AdUnit",
                "Targeting",
                "PrebidServerAdapter",
            ],
        }

        patterns = core_patterns.get(platform, [])

        for module in modules:
            if isinstance(module, dict):
                name = module.get("name", "")
                file_path = module.get("file", "")

                for pattern in patterns:
                    if pattern in name or pattern in file_path:
                        core_changes.append(f"{pattern} - Core SDK component")
                        break

        return core_changes

    def _generate_mobile_changes_summary(
        self, modules: list[dict[str, Any]], platform: str
    ) -> str:
        """Generate mobile-specific change summary."""
        if not modules:
            return "No module changes detected"

        component_changes = self._analyze_mobile_components(modules, platform)

        parts = []
        for component, count in component_changes.items():
            if count > 0 and component != "other":
                parts.append(f"{count} {component}")

        if parts:
            platform_name = platform.capitalize() if platform != "unknown" else "Mobile"
            return f"{platform_name}: Modified {', '.join(parts[:3])} component{'s' if sum(component_changes.values()) > 1 else ''}"
        else:
            return f"Modified {len(modules)} {platform} module{'s' if len(modules) > 1 else ''}"

    # Generic methods
    def _format_generic_modules(
        self, modules: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Format modules for generic/unknown repositories."""
        formatted = []
        for module in modules:
            if isinstance(module, dict):
                formatted.append(
                    {
                        "name": module.get("name", "Unknown"),
                        "type": module.get("type", "unknown"),
                        "file": module.get("file", ""),
                        "action": module.get("action", "modified"),
                    }
                )
            else:
                formatted.append(
                    {"name": str(module), "type": "unknown", "action": "modified"}
                )
        return formatted

    def _generate_generic_changes_summary(
        self, modules: list[dict[str, Any]], primary_type: str | None
    ) -> str:
        """Generate generic change summary."""
        if not modules:
            return "No module changes detected"

        count = len(modules)
        if count == 1:
            module = modules[0]
            name = (
                module.get("name", "module")
                if isinstance(module, dict)
                else str(module)
            )
            return f"Modified {name}"

        if primary_type:
            return f"Modified {count} modules (primarily {primary_type})"

        return f"Modified {count} modules"

    def _analyze_categories(self, categories: dict[str, list[str]]) -> dict[str, int]:
        """Analyze module categories and return counts."""
        result = {}
        if not isinstance(categories, dict):
            return result

        for category, modules in categories.items():
            if isinstance(modules, list):
                result[category] = len(modules)
            elif isinstance(modules, int):
                # If already a count, use it directly
                result[category] = modules
            else:
                # For other types, try to convert or skip
                try:
                    result[category] = int(modules)
                except (TypeError, ValueError):
                    continue

        return result
