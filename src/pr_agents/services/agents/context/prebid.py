"""Prebid-specific context enrichment."""

from typing import Any, Dict, List


class PrebidContextEnricher:
    """Provides deep Prebid.js specific context for agents."""
    
    @staticmethod
    def enrich_adapter_context(adapter_name: str, file_changes: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich context with Prebid adapter-specific information.
        
        Args:
            adapter_name: Name of the adapter (e.g., "rubicon", "appnexus")
            file_changes: Dictionary of file changes
            
        Returns:
            Enriched adapter context
        """
        context = {
            "adapter_name": adapter_name,
            "adapter_type": "unknown",
            "market_position": "standard",
            "typical_cpm_range": "$1-10",
            "integration_complexity": "moderate"
        }
        
        # Determine adapter type based on changes
        additions = file_changes.get("additions", 0)
        deletions = file_changes.get("deletions", 0)
        
        if additions > 200 and deletions < 50:
            context["adapter_type"] = "new_integration"
            context["expected_impact"] = "New revenue stream, 10-20% bid density increase"
            context["rollout_recommendation"] = "Gradual rollout with A/B testing"
        elif deletions > additions * 2:
            context["adapter_type"] = "optimization"
            context["expected_impact"] = "15-30% latency reduction, improved fill rates"
            context["rollout_recommendation"] = "Immediate deployment recommended"
        else:
            context["adapter_type"] = "enhancement"
            context["expected_impact"] = "Incremental improvements to bid quality"
            context["rollout_recommendation"] = "Standard deployment process"
        
        # Add known adapter contexts
        known_adapters = {
            "rubicon": {
                "market_position": "tier_1",
                "typical_cpm_range": "$2-15",
                "specialization": "Display and video inventory"
            },
            "appnexus": {
                "market_position": "tier_1", 
                "typical_cpm_range": "$1-12",
                "specialization": "Broad inventory access"
            },
            "amazon": {
                "market_position": "premium",
                "typical_cpm_range": "$3-20",
                "specialization": "High-value retail-focused inventory"
            }
        }
        
        if adapter_name.lower() in known_adapters:
            context.update(known_adapters[adapter_name.lower()])
        
        return context
    
    @staticmethod
    def analyze_bid_patterns(file_diffs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze bidding pattern changes from code diffs.
        
        Args:
            file_diffs: List of file diff dictionaries
            
        Returns:
            Analysis of bidding pattern changes
        """
        patterns = {
            "timeout_changes": False,
            "price_floor_changes": False,
            "currency_handling": False,
            "consent_management": False,
            "video_support": False,
            "native_support": False,
            "user_sync_changes": False
        }
        
        # Analyze file names and paths
        for diff in file_diffs:
            filename = diff.get("filename", "").lower()
            
            if "timeout" in filename:
                patterns["timeout_changes"] = True
            if "floor" in filename or "price" in filename:
                patterns["price_floor_changes"] = True
            if "currency" in filename:
                patterns["currency_handling"] = True
            if "consent" in filename or "gdpr" in filename or "ccpa" in filename:
                patterns["consent_management"] = True
            if "video" in filename:
                patterns["video_support"] = True
            if "native" in filename:
                patterns["native_support"] = True
            if "sync" in filename:
                patterns["user_sync_changes"] = True
        
        # Generate impact assessment
        impact_areas = []
        if patterns["timeout_changes"]:
            impact_areas.append("Bid timeout optimization affects fill rates")
        if patterns["price_floor_changes"]:
            impact_areas.append("Price floor adjustments impact revenue yield")
        if patterns["consent_management"]:
            impact_areas.append("Privacy compliance updates required")
        if patterns["video_support"]:
            impact_areas.append("Video advertising capabilities expanded")
        
        return {
            "detected_patterns": patterns,
            "impact_areas": impact_areas,
            "risk_level": "high" if len(impact_areas) > 3 else "medium" if len(impact_areas) > 1 else "low"
        }
    
    @staticmethod
    def estimate_revenue_impact(adapter_name: str, change_type: str) -> Dict[str, Any]:
        """Estimate potential revenue impact of changes.
        
        Args:
            adapter_name: Name of the adapter
            change_type: Type of change (new, optimization, enhancement)
            
        Returns:
            Revenue impact estimation
        """
        base_impacts = {
            "new_integration": {
                "direct_impact": "$5-20M annually",
                "ecosystem_impact": "Increased competition benefits all publishers",
                "timeline": "3-6 months to full adoption"
            },
            "optimization": {
                "direct_impact": "5-15% efficiency gain",
                "ecosystem_impact": "Better user experience, higher viewability",
                "timeline": "Immediate impact upon deployment"
            },
            "enhancement": {
                "direct_impact": "2-5% incremental improvement",
                "ecosystem_impact": "Maintains competitive position",
                "timeline": "Gradual improvement over 1-2 months"
            }
        }
        
        return base_impacts.get(change_type, {
            "direct_impact": "Variable",
            "ecosystem_impact": "Depends on adoption",
            "timeline": "Monitor post-deployment"
        })