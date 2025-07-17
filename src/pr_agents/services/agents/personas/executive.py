"""Executive summary agent using Google ADK."""

from typing import List
from google.adk import Agent
from google.adk.tools import BaseTool

from ..base import BaseSummaryAgent
from ..tools import CodeAnalyzerTool, PatternDetectorTool


class ExecutiveSummaryAgent(BaseSummaryAgent):
    """Agent specialized in generating executive-level summaries."""
    
    def get_instructions(self) -> str:
        """Get executive-specific instructions."""
        return """You are an executive summary specialist analyzing code changes for C-suite executives.

CRITICAL RULES:
1. ONLY analyze the provided code changes - NEVER reference PR titles or descriptions
2. Focus on business impact, revenue implications, and strategic value
3. Use metrics and percentages when discussing impact
4. Keep summaries concise (1-2 sentences) but impactful

ANALYSIS FRAMEWORK:
- Revenue Impact: How do these changes affect monetization?
- Operational Efficiency: Do changes reduce costs or improve performance?
- Strategic Position: Do changes strengthen competitive advantage?
- Risk Mitigation: Do changes address compliance or stability?

For Prebid.js changes specifically:
- New adapters = new revenue streams and partner relationships
- Optimizations = operational cost reduction and user experience
- Core changes = platform-wide impact on all revenue partners

OUTPUT FORMAT:
Provide a 1-2 sentence executive summary that quantifies business impact where possible.
Focus on outcomes, not technical details."""
    
    def get_tools(self) -> List[BaseTool]:
        """Get tools for executive analysis."""
        return [
            CodeAnalyzerTool(),
            PatternDetectorTool()
        ]
    
    def create_agent(self) -> Agent:
        """Create the executive summary agent."""
        return Agent(
            name="executive_summary_agent",
            model=self.model,
            instruction=self.get_instructions(),
            description="Generates executive-level summaries focusing on business impact",
            tools=self.get_tools()
        )
    
    def _prepare_input(self, code_changes: dict, repo_context: dict) -> str:
        """Prepare executive-focused input."""
        # Enhance with business context
        business_context = repo_context.get("business_context", {})
        
        prompt_parts = [
            "Analyze these code changes for executive impact:",
            f"\nRepository: {repo_context.get('name', 'Unknown')} (Type: {repo_context.get('type', 'generic')})",
        ]
        
        # Add business context if available
        if business_context:
            prompt_parts.append("\nBusiness Context:")
            if "ecosystem_size" in business_context:
                prompt_parts.append(f"- Ecosystem: {business_context['ecosystem_size']}")
            if "revenue_per_adapter" in business_context:
                prompt_parts.append(f"- Revenue Impact: {business_context['revenue_per_adapter']}")
        
        # Add code statistics
        prompt_parts.extend([
            f"\nCode Changes:",
            f"- Files Modified: {code_changes.get('changed_files', 0)}",
            f"- Lines Added: {code_changes.get('total_additions', 0)}",
            f"- Lines Deleted: {code_changes.get('total_deletions', 0)}"
        ])
        
        # Add file analysis if available
        if "file_analysis" in repo_context:
            analysis = repo_context["file_analysis"]
            if analysis.get("detected_modules"):
                prompt_parts.append(f"\nAffected Components: {', '.join(analysis['detected_modules'])}")
            if analysis.get("change_category"):
                prompt_parts.append(f"Change Type: {analysis['change_category']}")
        
        # List key files (limit to show pattern)
        file_diffs = code_changes.get("file_diffs", [])
        if file_diffs:
            prompt_parts.append("\nKey Files Changed:")
            for diff in file_diffs[:3]:  # First 3 files
                prompt_parts.append(f"- {diff['filename']} (+{diff['additions']}, -{diff['deletions']})")
            if len(file_diffs) > 3:
                prompt_parts.append(f"- ... and {len(file_diffs) - 3} more files")
        
        prompt_parts.append("\nProvide an executive summary focusing on business impact and strategic value.")
        
        return "\n".join(prompt_parts)