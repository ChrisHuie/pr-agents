# Google ADK Integration Plan for PR Agents

## Overview
Integrate Google's Agent Development Kit (ADK) to enhance AI summary generation while maintaining strict separation of concerns and component isolation.

## Architecture Design

### 1. Core Components

#### Agent Service Layer (`src/pr_agents/services/agents/`)
```
agents/
├── __init__.py
├── base.py              # Base agent interfaces
├── orchestrator.py      # Main agent orchestrator
├── context/
│   ├── __init__.py
│   ├── repository.py    # Repository context provider
│   └── prebid.py       # Prebid-specific context
├── personas/
│   ├── __init__.py
│   ├── executive.py     # Executive summary agent
│   ├── product.py       # Product manager agent
│   └── developer.py     # Developer summary agent
└── tools/
    ├── __init__.py
    ├── code_analyzer.py # Code analysis tools
    └── pattern_detector.py # Pattern detection tools
```

### 2. Key Design Principles

1. **Strict Isolation**: Each agent only receives code changes, never metadata
2. **Context Injection**: Repository context provided separately from PR data
3. **Modular Agents**: Each persona is a separate agent with specific instructions
4. **Tool-Based Analysis**: Code analysis logic extracted into reusable tools

### 3. Implementation Steps

#### Step 1: Install and Configure ADK
```bash
# Add to pyproject.toml
google-adk = "^0.1.0"  # Or latest version
```

#### Step 2: Create Base Agent Infrastructure
```python
# src/pr_agents/services/agents/base.py
from abc import ABC, abstractmethod
from google.adk.agents import Agent
from typing import Any, Dict

class BaseSummaryAgent(ABC):
    """Base class for all summary agents."""
    
    @abstractmethod
    def create_agent(self) -> Agent:
        """Create the ADK agent instance."""
        pass
    
    @abstractmethod
    def get_instructions(self) -> str:
        """Get agent-specific instructions."""
        pass
```

#### Step 3: Repository Context Provider
```python
# src/pr_agents/services/agents/context/repository.py
class RepositoryContextProvider:
    """Provides repository-specific context to agents."""
    
    def get_context(self, repo_name: str, repo_type: str) -> Dict[str, Any]:
        """Get repository context without exposing PR metadata."""
        # Load from configuration
        # Return structure, patterns, conventions
        pass
```

#### Step 4: Agent Orchestrator
```python
# src/pr_agents/services/agents/orchestrator.py
from google.adk.agents import Agent, SequentialAgent
from typing import Dict, Any

class SummaryAgentOrchestrator:
    """Orchestrates multiple persona agents for summary generation."""
    
    def __init__(self, repo_context_provider):
        self.context_provider = repo_context_provider
        self.agents = self._initialize_agents()
    
    def generate_summaries(self, code_changes: Dict[str, Any], 
                         repo_name: str, repo_type: str) -> Dict[str, str]:
        """Generate summaries for all personas."""
        # Get repository context
        repo_context = self.context_provider.get_context(repo_name, repo_type)
        
        # Run agents in parallel
        # Return persona-keyed summaries
        pass
```

#### Step 5: Persona-Specific Agents
```python
# src/pr_agents/services/agents/personas/executive.py
from google.adk.agents import Agent
from ..base import BaseSummaryAgent

class ExecutiveSummaryAgent(BaseSummaryAgent):
    """Agent for generating executive summaries."""
    
    def create_agent(self) -> Agent:
        return Agent(
            name="executive_summary_agent",
            model="gemini-2.0-flash",
            instruction=self.get_instructions(),
            description="Generates executive summaries from code changes",
            tools=[self.code_impact_tool, self.business_value_tool]
        )
    
    def get_instructions(self) -> str:
        return """
        You are an executive summary specialist. Analyze ONLY the provided code changes.
        Focus on:
        - Business impact and revenue implications
        - Operational efficiency gains
        - Strategic positioning
        - Risk mitigation
        
        Never reference PR titles or descriptions. Base analysis solely on code patterns.
        """
```

### 4. Integration with Existing System

#### Modified AI Processor
```python
# src/pr_agents/pr_processing/processors/ai_processor.py
class AIProcessor(BaseProcessor):
    """AI processor using ADK agents."""
    
    def __init__(self, orchestrator: SummaryAgentOrchestrator):
        self.orchestrator = orchestrator
    
    def process(self, component_data: Dict[str, Any]) -> ProcessingResult:
        # Extract code changes
        code_changes = component_data.get("code_changes", {})
        repo_info = component_data.get("repo_info", {})
        
        # Generate summaries using agents
        summaries = self.orchestrator.generate_summaries(
            code_changes, 
            repo_info.get("name"),
            repo_info.get("type")
        )
        
        return ProcessingResult(
            component="ai_summaries",
            success=True,
            data=summaries
        )
```

### 5. Configuration System

#### Repository Configuration (`config/repositories/prebid/context.yaml`)
```yaml
prebid:
  type: "advertising_platform"
  description: "Header bidding library for programmatic advertising"
  
  module_patterns:
    bid_adapters:
      location: "modules/*BidAdapter.js"
      purpose: "Integrate demand sources"
      revenue_impact: "direct"
    
    analytics:
      location: "modules/analytics/*"
      purpose: "Track performance metrics"
      revenue_impact: "indirect"
    
    user_modules:
      location: "modules/userId/*"
      purpose: "User identification"
      revenue_impact: "enabling"
  
  code_patterns:
    new_adapter_threshold: 200  # Lines to consider "new"
    optimization_ratio: 2.0     # Deletion/addition ratio
  
  business_context:
    revenue_per_adapter: "10-50M annually"
    ecosystem_size: "150+ adapters"
    critical_components: ["auction", "bidding", "consent"]
```

### 6. Benefits of ADK Approach

1. **Better Context Management**: Repository context separate from PR data
2. **Scalable Architecture**: Easy to add new personas or analysis types
3. **Tool Reusability**: Analysis tools can be shared across agents
4. **Testing**: Each agent can be tested independently
5. **Observability**: ADK provides built-in debugging and monitoring

### 7. Migration Path

1. Keep existing ClaudeDirectProvider as fallback
2. Implement ADK agents incrementally
3. A/B test summaries between old and new systems
4. Gradually migrate all summary generation to ADK

### 8. Next Steps

1. Install google-adk package
2. Create base agent infrastructure
3. Implement repository context system
4. Build persona agents with specific tools
5. Integrate with existing processor architecture
6. Add comprehensive tests
7. Document agent behavior and configuration