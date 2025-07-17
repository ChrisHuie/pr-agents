"""Base classes for ADK-based summary agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from google.adk import Agent
from google.adk.tools import BaseTool


class BaseSummaryAgent(ABC):
    """Base class for all persona-specific summary agents."""
    
    def __init__(self, model: str = "gemini-2.0-flash"):
        """Initialize the base agent.
        
        Args:
            model: The LLM model to use for this agent
        """
        self.model = model
        self._agent = None
    
    @property
    def agent(self) -> Agent:
        """Get or create the ADK agent instance."""
        if self._agent is None:
            self._agent = self.create_agent()
        return self._agent
    
    @abstractmethod
    def create_agent(self) -> Agent:
        """Create and configure the ADK agent instance."""
        pass
    
    @abstractmethod
    def get_instructions(self) -> str:
        """Get persona-specific instructions for the agent."""
        pass
    
    @abstractmethod
    def get_tools(self) -> List[BaseTool]:
        """Get the tools this agent should have access to."""
        pass
    
    def generate_summary(self, code_changes: Dict[str, Any], 
                        repo_context: Dict[str, Any]) -> str:
        """Generate a summary based on code changes and repository context.
        
        Args:
            code_changes: Dictionary containing file diffs, additions, deletions
            repo_context: Repository-specific context (patterns, conventions, etc.)
            
        Returns:
            Generated summary text
        """
        # Prepare the input for the agent
        agent_input = self._prepare_input(code_changes, repo_context)
        
        # Run the agent
        response = self.agent.run(agent_input)
        
        return response.output
    
    def _prepare_input(self, code_changes: Dict[str, Any], 
                      repo_context: Dict[str, Any]) -> str:
        """Prepare input prompt for the agent.
        
        Args:
            code_changes: Code change data
            repo_context: Repository context
            
        Returns:
            Formatted input string for the agent
        """
        # Format code changes
        files_changed = code_changes.get("changed_files", 0)
        additions = code_changes.get("total_additions", 0)
        deletions = code_changes.get("total_deletions", 0)
        
        file_list = []
        for diff in code_changes.get("file_diffs", []):
            file_list.append(f"- {diff['filename']} (+{diff['additions']}, -{diff['deletions']})")
        
        # Build the prompt
        prompt_parts = [
            "Analyze the following code changes and provide a summary:",
            f"\nRepository Type: {repo_context.get('type', 'unknown')}",
            f"Repository: {repo_context.get('name', 'unknown')}",
            f"\nCode Statistics:",
            f"- Files Changed: {files_changed}",
            f"- Lines Added: {additions}",
            f"- Lines Deleted: {deletions}",
            f"\nModified Files:",
        ]
        prompt_parts.extend(file_list)
        
        # Add repository context if available
        if "module_patterns" in repo_context:
            prompt_parts.append("\nRepository Module Patterns:")
            for module_type, info in repo_context["module_patterns"].items():
                prompt_parts.append(f"- {module_type}: {info.get('purpose', 'N/A')}")
        
        prompt_parts.append("\nGenerate a summary based on these code changes.")
        
        return "\n".join(prompt_parts)