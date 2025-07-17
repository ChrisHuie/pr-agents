"""Main orchestrator for agent-based summary generation."""

import asyncio
from typing import Any, Dict, Optional
from datetime import datetime
from loguru import logger

from .context import RepositoryContextProvider, PrebidContextEnricher
from .personas import ExecutiveSummaryAgent, ProductSummaryAgent, DeveloperSummaryAgent
from ...pr_processing.analysis_models import AISummaries, PersonaSummary


class SummaryAgentOrchestrator:
    """Orchestrates multiple persona agents for summary generation."""
    
    def __init__(self, model: str = "gemini-2.0-flash"):
        """Initialize the orchestrator.
        
        Args:
            model: The LLM model to use for all agents
        """
        self.model = model
        self.context_provider = RepositoryContextProvider()
        self.prebid_enricher = PrebidContextEnricher()
        
        # Initialize persona agents
        self.agents = {
            "executive": ExecutiveSummaryAgent(model=model),
            "product": ProductSummaryAgent(model=model),
            "developer": DeveloperSummaryAgent(model=model)
        }
        
        logger.info(f"Initialized agent orchestrator with model: {model}")
    
    async def generate_summaries(
        self,
        code_changes: Dict[str, Any],
        repo_name: str,
        repo_type: Optional[str] = None
    ) -> AISummaries:
        """Generate summaries for all personas using agents.
        
        Args:
            code_changes: Dictionary containing file diffs and statistics
            repo_name: Repository name (e.g., "prebid/Prebid.js")
            repo_type: Optional repository type
            
        Returns:
            AISummaries object with all persona summaries
        """
        start_time = datetime.now()
        
        # Get base repository context
        repo_context = self.context_provider.get_context(repo_name, repo_type)
        
        # Enrich context based on actual files
        file_list = [diff.get("filename", "") for diff in code_changes.get("file_diffs", [])]
        enriched_context = self.context_provider.enrich_with_file_analysis(
            repo_context, file_list
        )
        
        # Additional enrichment for Prebid repositories
        if repo_type == "prebid" or "prebid" in repo_name.lower():
            # Detect adapter changes
            adapter_files = [
                f for f in file_list 
                if "bidadapter" in f.lower() and f.endswith(".js") and "test" not in f.lower()
            ]
            
            if adapter_files:
                adapter_name = adapter_files[0].split("/")[-1].replace("BidAdapter.js", "")
                adapter_context = self.prebid_enricher.enrich_adapter_context(
                    adapter_name, code_changes
                )
                enriched_context["adapter_context"] = adapter_context
            
            # Analyze bid patterns
            bid_patterns = self.prebid_enricher.analyze_bid_patterns(
                code_changes.get("file_diffs", [])
            )
            enriched_context["bid_patterns"] = bid_patterns
        
        logger.info(f"Generating summaries for repository: {repo_name} (type: {repo_type})")
        
        # Generate summaries concurrently
        summary_tasks = []
        for persona_name, agent in self.agents.items():
            task = self._generate_persona_summary(
                agent, persona_name, code_changes, enriched_context
            )
            summary_tasks.append(task)
        
        # Wait for all summaries
        persona_summaries = await asyncio.gather(*summary_tasks)
        
        # Calculate total generation time
        generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Create AISummaries object
        summaries = AISummaries(
            executive_summary=next(s for s in persona_summaries if s.persona == "executive"),
            product_summary=next(s for s in persona_summaries if s.persona == "product"),
            developer_summary=next(s for s in persona_summaries if s.persona == "developer"),
            model_used=f"adk-{self.model}",
            generation_timestamp=datetime.now(),
            cached=False,
            total_tokens=sum(s.confidence for s in persona_summaries),  # Using confidence as token placeholder
            generation_time_ms=generation_time_ms
        )
        
        logger.info(f"Generated all summaries in {generation_time_ms}ms")
        
        return summaries
    
    async def _generate_persona_summary(
        self,
        agent: Any,
        persona: str,
        code_changes: Dict[str, Any],
        repo_context: Dict[str, Any]
    ) -> PersonaSummary:
        """Generate summary for a specific persona.
        
        Args:
            agent: The persona agent
            persona: Persona name
            code_changes: Code change data
            repo_context: Enriched repository context
            
        Returns:
            PersonaSummary object
        """
        try:
            logger.debug(f"Generating {persona} summary")
            
            # Generate summary using the agent
            summary_text = agent.generate_summary(code_changes, repo_context)
            
            # Calculate confidence based on context richness
            confidence = self._calculate_confidence(repo_context, code_changes)
            
            return PersonaSummary(
                persona=persona,
                summary=summary_text,
                confidence=confidence
            )
        
        except Exception as e:
            logger.error(f"Error generating {persona} summary: {str(e)}")
            return PersonaSummary(
                persona=persona,
                summary=f"Error generating summary: {str(e)}",
                confidence=0.0
            )
    
    def _calculate_confidence(
        self,
        repo_context: Dict[str, Any],
        code_changes: Dict[str, Any]
    ) -> float:
        """Calculate confidence score based on available context.
        
        Args:
            repo_context: Repository context
            code_changes: Code changes
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence
        
        # Boost for rich repository context
        if repo_context.get("module_patterns"):
            confidence += 0.1
        if repo_context.get("business_context"):
            confidence += 0.1
        if repo_context.get("technical_context"):
            confidence += 0.1
        
        # Boost for file analysis
        if repo_context.get("file_analysis", {}).get("detected_modules"):
            confidence += 0.1
        
        # Boost for test coverage
        if any("test" in d.get("filename", "").lower() for d in code_changes.get("file_diffs", [])):
            confidence += 0.1
        
        return min(confidence, 0.95)  # Cap at 0.95