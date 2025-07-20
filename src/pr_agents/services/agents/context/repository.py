"""Repository context provider for agents."""

from pathlib import Path
from typing import Any

from loguru import logger


class RepositoryContextProvider:
    """Provides repository-specific context to agents without exposing PR metadata."""

    def __init__(self, config_path: Path | None = None):
        """Initialize the context provider.

        Args:
            config_path: Path to repository configurations
        """
        if config_path is None:
            # Default to config directory in project root
            config_path = Path(__file__).parent.parent.parent.parent.parent / "config"

        self.config_path = config_path
        self._context_cache = {}
        self._load_base_contexts()

    def _load_base_contexts(self):
        """Load base repository contexts from configuration."""
        # Load Prebid context as an example
        self._context_cache["prebid"] = {
            "type": "prebid",
            "name": "Prebid.js",
            "description": "Header bidding library for programmatic advertising",
            "module_patterns": {
                "bid_adapters": {
                    "location": "modules/*BidAdapter.js",
                    "purpose": "Integrate demand sources for programmatic advertising",
                    "revenue_impact": "direct",
                    "typical_size": "200-500 lines for new adapters",
                },
                "analytics": {
                    "location": "modules/analytics/*",
                    "purpose": "Track performance metrics and revenue analytics",
                    "revenue_impact": "indirect",
                },
                "user_modules": {
                    "location": "modules/userId/*",
                    "purpose": "User identification for targeted advertising",
                    "revenue_impact": "enabling",
                },
                "core": {
                    "location": ["src/", "libraries/"],
                    "purpose": "Core auction and bidding logic",
                    "revenue_impact": "foundational",
                },
            },
            "code_patterns": {
                "new_adapter_indicators": {
                    "min_additions": 200,
                    "max_deletions": 50,
                    "typical_files": ["*BidAdapter.js", "test/spec/*_spec.js"],
                },
                "optimization_indicators": {
                    "deletion_ratio": 2.0,  # deletions > additions * 2
                    "typical_patterns": ["refactor", "optimize", "simplify"],
                },
            },
            "business_context": {
                "ecosystem_size": "150+ integrated demand partners",
                "revenue_per_adapter": "$10-50M annually per major adapter",
                "critical_metrics": ["latency", "timeout", "bid_density", "win_rate"],
                "compliance_requirements": ["GDPR", "CCPA", "TCF 2.0"],
            },
            "technical_context": {
                "architecture": "Plugin-based adapter system",
                "key_apis": [
                    "buildRequests",
                    "interpretResponse",
                    "isBidRequestValid",
                    "getUserSyncs",
                ],
                "performance_targets": {
                    "auction_timeout": "1000ms default",
                    "adapter_timeout": "300-500ms typical",
                    "page_impact": "<100ms added latency",
                },
            },
        }

        # Add more repository contexts as needed
        logger.info(f"Loaded {len(self._context_cache)} repository contexts")

    def get_context(
        self, repo_name: str, repo_type: str | None = None
    ) -> dict[str, Any]:
        """Get repository context for agents.

        Args:
            repo_name: Repository name (e.g., "prebid/Prebid.js")
            repo_type: Optional repository type override

        Returns:
            Repository context dictionary
        """
        # Normalize repo name
        repo_key = repo_name.lower().replace("/", "_")

        # Check cache first
        if repo_type and repo_type in self._context_cache:
            context = self._context_cache[repo_type].copy()
            context["name"] = repo_name
            return context

        # Try to match by repo name patterns
        if "prebid" in repo_key:
            context = self._context_cache.get("prebid", {}).copy()
            context["name"] = repo_name
            return context

        # Return generic context if no specific match
        return {
            "name": repo_name,
            "type": repo_type or "generic",
            "description": "Generic repository",
            "module_patterns": {},
            "code_patterns": {},
            "business_context": {},
            "technical_context": {},
        }

    def enrich_with_file_analysis(
        self, base_context: dict[str, Any], file_list: list[str]
    ) -> dict[str, Any]:
        """Enrich context based on actual files being changed.

        Args:
            base_context: Base repository context
            file_list: List of files being changed

        Returns:
            Enriched context with file-specific insights
        """
        enriched = base_context.copy()

        # Analyze file patterns
        file_analysis = {
            "detected_modules": [],
            "affected_components": [],
            "change_category": "unknown",
        }

        # Check against module patterns
        for module_type, pattern_info in base_context.get(
            "module_patterns", {}
        ).items():
            locations = pattern_info.get("location", [])
            if isinstance(locations, str):
                locations = [locations]

            for location in locations:
                # Simple pattern matching (could be enhanced)
                pattern = location.replace("*", "")
                if any(pattern in f for f in file_list):
                    file_analysis["detected_modules"].append(module_type)
                    file_analysis["affected_components"].append(
                        {
                            "type": module_type,
                            "purpose": pattern_info.get("purpose", ""),
                            "impact": pattern_info.get("revenue_impact", ""),
                        }
                    )

        # Determine change category
        if any("test" in f.lower() for f in file_list):
            file_analysis["has_tests"] = True

        if any(f.endswith("BidAdapter.js") for f in file_list):
            file_analysis["change_category"] = "adapter_change"
        elif any("core" in f or "src/" in f for f in file_list):
            file_analysis["change_category"] = "core_change"
        elif any("util" in f.lower() for f in file_list):
            file_analysis["change_category"] = "utility_change"

        enriched["file_analysis"] = file_analysis
        return enriched
