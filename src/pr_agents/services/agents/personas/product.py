"""Product manager summary agent using Google ADK."""

from typing import List
from google.adk import Agent
from google.adk.tools import BaseTool

from ..base import BaseSummaryAgent
from ..tools import CodeAnalyzerTool, PatternDetectorTool


class ProductSummaryAgent(BaseSummaryAgent):
    """Agent specialized in generating product manager summaries."""
    
    def get_instructions(self) -> str:
        """Get product manager-specific instructions."""
        return """You are a product summary specialist analyzing code changes for product managers.

CRITICAL RULES:
1. ONLY analyze the provided code changes - NEVER reference PR titles or descriptions
2. Focus on features, capabilities, and user benefits
3. Explain technical changes in product terms
4. Keep summaries detailed (2-4 sentences) but accessible

ANALYSIS FRAMEWORK:
- Feature Impact: What new capabilities or improvements?
- User Experience: How do changes affect end users?
- Publisher Benefits: What value for publishers/customers?
- Adoption Requirements: What's needed for implementation?

For Prebid.js changes specifically:
- Adapter changes = publisher monetization options
- Performance improvements = page speed and user experience
- New modules = additional capabilities and flexibility
- Test coverage = reliability and quality assurance

OUTPUT FORMAT:
Provide a 2-4 sentence product summary that explains:
1. What changed from a feature perspective
2. Who benefits and how
3. Any implementation considerations
4. Quality/reliability aspects if tests are included"""
    
    def get_tools(self) -> List[BaseTool]:
        """Get tools for product analysis."""
        return [
            CodeAnalyzerTool(),
            PatternDetectorTool()
        ]
    
    def create_agent(self) -> Agent:
        """Create the product summary agent."""
        return Agent(
            name="product_summary_agent",
            model=self.model,
            instruction=self.get_instructions(),
            description="Generates product-focused summaries emphasizing features and benefits",
            tools=self.get_tools()
        )
    
    def _prepare_input(self, code_changes: dict, repo_context: dict) -> str:
        """Prepare product-focused input."""
        # Extract technical context
        tech_context = repo_context.get("technical_context", {})
        
        prompt_parts = [
            "Analyze these code changes for product impact:",
            f"\nRepository: {repo_context.get('name', 'Unknown')} (Type: {repo_context.get('type', 'generic')})",
        ]
        
        # Add repository description if available
        if "description" in repo_context:
            prompt_parts.append(f"Description: {repo_context['description']}")
        
        # Add technical context relevant to products
        if tech_context:
            if "performance_targets" in tech_context:
                targets = tech_context["performance_targets"]
                prompt_parts.append(f"\nPerformance Context:")
                for metric, value in targets.items():
                    prompt_parts.append(f"- {metric}: {value}")
        
        # Add code change details
        prompt_parts.extend([
            f"\nChange Statistics:",
            f"- Files Modified: {code_changes.get('changed_files', 0)}",
            f"- Code Added: {code_changes.get('total_additions', 0)} lines",
            f"- Code Removed: {code_changes.get('total_deletions', 0)} lines"
        ])
        
        # Analyze patterns for product relevance
        file_diffs = code_changes.get("file_diffs", [])
        
        # Check for specific patterns
        has_tests = any("test" in d.get("filename", "").lower() for d in file_diffs)
        has_docs = any(d.get("filename", "").endswith(".md") for d in file_diffs)
        has_config = any("config" in d.get("filename", "").lower() for d in file_diffs)
        
        prompt_parts.append("\nDetected Patterns:")
        if has_tests:
            prompt_parts.append("- Includes test coverage for quality assurance")
        if has_docs:
            prompt_parts.append("- Documentation updates for easier adoption")
        if has_config:
            prompt_parts.append("- Configuration changes affecting deployment")
        
        # Module patterns if available
        if "module_patterns" in repo_context:
            modules = repo_context["module_patterns"]
            affected_modules = []
            
            for module_type, info in modules.items():
                # Check if any files match this module pattern
                locations = info.get("location", [])
                if isinstance(locations, str):
                    locations = [locations]
                
                for location in locations:
                    pattern = location.replace("*", "")
                    if any(pattern in d.get("filename", "") for d in file_diffs):
                        affected_modules.append({
                            "type": module_type,
                            "purpose": info.get("purpose", ""),
                            "impact": info.get("revenue_impact", "")
                        })
            
            if affected_modules:
                prompt_parts.append("\nAffected Components:")
                for module in affected_modules:
                    prompt_parts.append(f"- {module['type']}: {module['purpose']}")
        
        # List significant files
        prompt_parts.append("\nModified Files:")
        for diff in file_diffs[:5]:  # First 5 files
            prompt_parts.append(f"- {diff['filename']} (+{diff['additions']}, -{diff['deletions']})")
        if len(file_diffs) > 5:
            prompt_parts.append(f"- ... and {len(file_diffs) - 5} more files")
        
        prompt_parts.append("\nProvide a product summary focusing on features, user benefits, and implementation considerations.")
        
        return "\n".join(prompt_parts)