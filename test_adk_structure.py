#!/usr/bin/env python3
"""Test ADK structure without requiring API key."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pr_agents.services.agents.orchestrator import SummaryAgentOrchestrator
from src.pr_agents.services.agents.personas import ExecutiveSummaryAgent, ProductSummaryAgent, DeveloperSummaryAgent
from src.pr_agents.services.agents.tools import CodeAnalyzerTool, PatternDetectorTool
from src.pr_agents.services.agents.context import RepositoryContextProvider
from google.adk import Agent
from google.adk.tools import BaseTool

def test_adk_structure():
    """Test that our ADK components are properly structured."""
    
    print("Testing ADK Structure")
    print("=" * 80)
    
    # Test 1: Tools inherit from BaseTool
    print("\n1. Testing Tools...")
    try:
        analyzer = CodeAnalyzerTool()
        detector = PatternDetectorTool()
        
        assert isinstance(analyzer, BaseTool), "CodeAnalyzerTool should inherit from BaseTool"
        assert isinstance(detector, BaseTool), "PatternDetectorTool should inherit from BaseTool"
        
        print("   ✓ CodeAnalyzerTool is a BaseTool")
        print("   ✓ PatternDetectorTool is a BaseTool")
    except Exception as e:
        print(f"   ✗ Tool test failed: {e}")
    
    # Test 2: Agents can be created
    print("\n2. Testing Agent Creation...")
    try:
        # Create persona agents
        exec_agent = ExecutiveSummaryAgent(model="gemini-2.0-flash")
        prod_agent = ProductSummaryAgent(model="gemini-2.0-flash")
        dev_agent = DeveloperSummaryAgent(model="gemini-2.0-flash")
        
        # Check they have the required methods
        for agent, name in [(exec_agent, "Executive"), (prod_agent, "Product"), (dev_agent, "Developer")]:
            assert hasattr(agent, "get_instructions"), f"{name} agent missing get_instructions"
            assert hasattr(agent, "get_tools"), f"{name} agent missing get_tools"
            assert hasattr(agent, "create_agent"), f"{name} agent missing create_agent"
            print(f"   ✓ {name}SummaryAgent has required methods")
    except Exception as e:
        print(f"   ✗ Agent creation test failed: {e}")
    
    # Test 3: Agent instructions
    print("\n3. Testing Agent Instructions...")
    try:
        exec_inst = exec_agent.get_instructions()
        prod_inst = prod_agent.get_instructions()
        dev_inst = dev_agent.get_instructions()
        
        # Verify instructions are different
        assert exec_inst != prod_inst, "Executive and Product instructions should be different"
        assert prod_inst != dev_inst, "Product and Developer instructions should be different"
        assert exec_inst != dev_inst, "Executive and Developer instructions should be different"
        
        # Verify instructions contain persona-specific content
        assert "executive" in exec_inst.lower(), "Executive instructions should mention executive"
        assert "product" in prod_inst.lower(), "Product instructions should mention product"
        assert "developer" in dev_inst.lower() or "technical" in dev_inst.lower(), "Developer instructions should mention developer/technical"
        
        print("   ✓ Each persona has unique instructions")
        print("   ✓ Instructions are persona-specific")
    except Exception as e:
        print(f"   ✗ Instruction test failed: {e}")
    
    # Test 4: Context Provider
    print("\n4. Testing Context Provider...")
    try:
        context_provider = RepositoryContextProvider()
        
        # Test getting context
        context = context_provider.get_context("prebid/Prebid.js", "prebid")
        
        assert "name" in context, "Context should have name"
        assert "type" in context, "Context should have type"
        assert context["name"] == "prebid/Prebid.js", "Context name should match"
        assert context["type"] == "prebid", "Context type should match"
        
        print("   ✓ RepositoryContextProvider works correctly")
        print(f"   ✓ Context has {len(context)} fields")
    except Exception as e:
        print(f"   ✗ Context provider test failed: {e}")
    
    # Test 5: Orchestrator
    print("\n5. Testing Orchestrator...")
    try:
        orchestrator = SummaryAgentOrchestrator(model="gemini-2.0-flash")
        
        assert hasattr(orchestrator, "agents"), "Orchestrator should have agents"
        assert len(orchestrator.agents) == 3, "Orchestrator should have 3 agents"
        assert "executive" in orchestrator.agents, "Orchestrator should have executive agent"
        assert "product" in orchestrator.agents, "Orchestrator should have product agent"
        assert "developer" in orchestrator.agents, "Orchestrator should have developer agent"
        
        print("   ✓ Orchestrator initialized correctly")
        print("   ✓ All three persona agents registered")
    except Exception as e:
        print(f"   ✗ Orchestrator test failed: {e}")
    
    # Test 6: Agent Tools
    print("\n6. Testing Agent Tools...")
    try:
        exec_tools = exec_agent.get_tools()
        prod_tools = prod_agent.get_tools()
        dev_tools = dev_agent.get_tools()
        
        for tools, name in [(exec_tools, "Executive"), (prod_tools, "Product"), (dev_tools, "Developer")]:
            assert isinstance(tools, list), f"{name} tools should be a list"
            assert len(tools) > 0, f"{name} should have at least one tool"
            for tool in tools:
                assert isinstance(tool, BaseTool), f"All {name} tools should be BaseTool instances"
        
        print("   ✓ All agents have tools")
        print("   ✓ All tools are BaseTool instances")
    except Exception as e:
        print(f"   ✗ Tool test failed: {e}")
    
    print("\n" + "=" * 80)
    print("ADK Structure Tests Complete!")
    print("\nNote: This test validates the structure without making API calls.")
    print("To test actual functionality, you'll need a valid Gemini API key.")

if __name__ == "__main__":
    test_adk_structure()