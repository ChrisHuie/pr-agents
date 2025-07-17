#!/usr/bin/env python3
"""Simple test to verify ADK setup is working."""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools import FunctionTool
from google.adk.runners import InMemoryRunner

# Load environment variables
load_dotenv()

# Set up Gemini API key
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
if not api_key or api_key == "your_gemini_api_key_here" or api_key.startswith("your_"):
    print("ERROR: No valid API key found. Please set a real GEMINI_API_KEY or GOOGLE_GENAI_API_KEY")
    print("The .env file contains a placeholder value.")
    print("\nTo fix this:")
    print("1. Get your API key from: https://makersuite.google.com/app/apikey")
    print("2. Set it with: export GEMINI_API_KEY='your-actual-api-key'")
    print("3. Or update the .env file with the real key")
    exit(1)
os.environ["GOOGLE_GENAI_API_KEY"] = api_key
print(f"Using API key: {api_key[:10]}...{api_key[-4:]}")

def analyze_code(file_list: list[str], change_type: str) -> str:
    """Simple function to analyze code changes.
    
    Args:
        file_list: List of files to analyze
        change_type: Type of change (e.g., optimization, feature, bugfix)
        
    Returns:
        Analysis result
    """
    return f"Analyzing {len(file_list)} files with change type: {change_type}"

async def test_simple_agent():
    """Test a simple ADK agent."""
    
    print("\n1. Creating tools...")
    # Create a simple tool using just the function
    analyze_tool = FunctionTool(analyze_code)
    print(f"   Tool created: {analyze_tool}")
    
    print("\n2. Creating agent...")
    # Create a simple agent
    agent = Agent(
        name="test_agent",
        model="gemini-2.0-flash",
        instruction="You are a helpful code analyzer. Analyze the provided information.",
        tools=[analyze_tool]
    )
    print(f"   Agent created: {agent.name}")
    
    print("\n3. Creating runner...")
    # Create a runner with the agent
    runner = InMemoryRunner(agent)
    print(f"   Runner created: {runner}")
    
    print("\n4. Running agent...")
    # Run the agent
    user_input = "Analyze these files: [main.py, test.py] with change type: optimization"
    
    # Try with a simple approach first
    try:
        # Use empty session_id to let it create one
        print("   Attempting to run with new session...")
        
        event_count = 0
        async for event in runner.run_async(
            user_id="test_user",
            session_id="",  # Empty string might create a new session
            new_message=user_input
        ):
            event_count += 1
            print(f"\n   Event {event_count}: {type(event).__name__}")
            
            if hasattr(event, 'text'):
                print(f"   Text: {event.text}")
            elif hasattr(event, 'content'):
                print(f"   Content: {event.content}")
            elif hasattr(event, 'data'):
                print(f"   Data: {event.data}")
            else:
                print(f"   Full event: {event}")
                
    except Exception as e:
        print(f"\n   Error: {type(e).__name__}: {e}")
        print("\n   Trying alternative approach...")
        
        # Try creating a session manually
        import uuid
        session_id = str(uuid.uuid4())
        print(f"   Using session_id: {session_id}")
        
        # Check if runner has any session-related methods
        print(f"   Runner methods: {[m for m in dir(runner) if 'session' in m.lower()]}")
        
        # Try to access the session service
        session_service = runner._in_memory_session_service
        print(f"   Session service: {session_service}")
        print(f"   Session service methods: {[m for m in dir(session_service) if not m.startswith('_')]}")
        
        # Try to create a session using the service
        print("\n   Attempting to create session via service...")
        
        # Use the create_session method
        session = await session_service.create_session(user_id="test_user")
        session_id = session.id  # Note: it's 'id' not 'session_id'
        print(f"   Session created: {session_id}")
        
        # Now try running again
        print("\n   Running with created session...")
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session_id,
            new_message=user_input
        ):
            print(f"\n   Event: {type(event).__name__}")
            if hasattr(event, 'text'):
                print(f"   Text: {event.text}")
            elif hasattr(event, 'content'):
                print(f"   Content: {event.content}")

if __name__ == "__main__":
    asyncio.run(test_simple_agent())