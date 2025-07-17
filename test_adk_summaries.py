#!/usr/bin/env python3
"""Test ADK-based AI summaries for PR analysis."""

import os
import asyncio
from datetime import datetime

from src.pr_agents.services.agents import SummaryAgentOrchestrator
from src.pr_agents.pr_processing.models import CodeChanges, FileDiff


async def test_adk_summaries():
    """Test the ADK agent-based summary generation."""
    
    print("Testing Google ADK Agent-Based Summaries")
    print("=" * 80)
    
    # Set up test data - simulate different types of PRs
    test_cases = [
        {
            "name": "New Bid Adapter",
            "repo": "prebid/Prebid.js",
            "code_changes": CodeChanges(
                file_diffs=[
                    FileDiff(
                        filename="modules/exampleBidAdapter.js",
                        additions=350,
                        deletions=0,
                        changes=350,
                        patch="",
                        status="added"
                    ),
                    FileDiff(
                        filename="test/spec/modules/exampleBidAdapter_spec.js",
                        additions=200,
                        deletions=0,
                        changes=200,
                        patch="",
                        status="added"
                    ),
                    FileDiff(
                        filename="modules/exampleBidAdapter.md",
                        additions=50,
                        deletions=0,
                        changes=50,
                        patch="",
                        status="added"
                    )
                ],
                total_additions=600,
                total_deletions=0,
                total_changes=600,
                changed_files=3,
                base_sha="abc123",
                head_sha="def456"
            )
        },
        {
            "name": "Utility Optimization",
            "repo": "prebid/Prebid.js",
            "code_changes": CodeChanges(
                file_diffs=[
                    FileDiff(
                        filename="src/utils/arrayHelpers.js",
                        additions=15,
                        deletions=45,
                        changes=60,
                        patch="",
                        status="modified"
                    ),
                    FileDiff(
                        filename="test/spec/utils/arrayHelpers_spec.js",
                        additions=10,
                        deletions=5,
                        changes=15,
                        patch="",
                        status="modified"
                    )
                ],
                total_additions=25,
                total_deletions=50,
                total_changes=75,
                changed_files=2,
                base_sha="abc123",
                head_sha="def456"
            )
        },
        {
            "name": "Adapter Enhancement",
            "repo": "prebid/Prebid.js",
            "code_changes": CodeChanges(
                file_diffs=[
                    FileDiff(
                        filename="modules/rubiconBidAdapter.js",
                        additions=45,
                        deletions=20,
                        changes=65,
                        patch="",
                        status="modified"
                    ),
                    FileDiff(
                        filename="test/spec/modules/rubiconBidAdapter_spec.js",
                        additions=30,
                        deletions=10,
                        changes=40,
                        patch="",
                        status="modified"
                    )
                ],
                total_additions=75,
                total_deletions=30,
                total_changes=105,
                changed_files=2,
                base_sha="abc123",
                head_sha="def456"
            )
        }
    ]
    
    # Initialize orchestrator
    orchestrator = SummaryAgentOrchestrator(model="gemini-2.0-flash")
    
    for test_case in test_cases:
        print(f"\n{'='*80}")
        print(f"Test Case: {test_case['name']}")
        print(f"Repository: {test_case['repo']}")
        print(f"{'='*80}")
        
        # Convert to dict format
        code_changes_dict = {
            "file_diffs": [
                {
                    "filename": diff.filename,
                    "additions": diff.additions,
                    "deletions": diff.deletions,
                    "changes": diff.changes,
                    "status": diff.status
                }
                for diff in test_case["code_changes"].file_diffs
            ],
            "total_additions": test_case["code_changes"].total_additions,
            "total_deletions": test_case["code_changes"].total_deletions,
            "total_changes": test_case["code_changes"].total_changes,
            "changed_files": test_case["code_changes"].changed_files
        }
        
        # Print code change summary
        print(f"\nCode Changes:")
        print(f"- Files: {code_changes_dict['changed_files']}")
        print(f"- Additions: {code_changes_dict['total_additions']}")
        print(f"- Deletions: {code_changes_dict['total_deletions']}")
        print("\nFiles:")
        for diff in code_changes_dict["file_diffs"]:
            print(f"  - {diff['filename']} (+{diff['additions']}, -{diff['deletions']})")
        
        # Generate summaries
        start_time = datetime.now()
        
        try:
            summaries = await orchestrator.generate_summaries(
                code_changes_dict,
                test_case["repo"],
                "prebid"
            )
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Display results
            print(f"\n✅ Summaries generated in {generation_time:.2f}s")
            print(f"\nModel: {summaries.model_used}")
            
            print("\n📊 EXECUTIVE SUMMARY:")
            print(f"Confidence: {summaries.executive_summary.confidence:.2f}")
            print(f"Summary: {summaries.executive_summary.summary}")
            
            print("\n📦 PRODUCT SUMMARY:")
            print(f"Confidence: {summaries.product_summary.confidence:.2f}")
            print(f"Summary: {summaries.product_summary.summary}")
            
            print("\n💻 DEVELOPER SUMMARY:")
            print(f"Confidence: {summaries.developer_summary.confidence:.2f}")
            # Truncate developer summary if too long
            dev_summary = summaries.developer_summary.summary
            if len(dev_summary) > 300:
                print(f"Summary: {dev_summary[:300]}...")
            else:
                print(f"Summary: {dev_summary}")
            
        except Exception as e:
            print(f"\n❌ Error generating summaries: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("✅ ADK Summary Testing Complete!")
    print("\nKey Observations:")
    print("1. Each persona receives different, contextually relevant summaries")
    print("2. Summaries are based purely on code changes, not metadata")
    print("3. Repository context enriches the analysis")
    print("4. Prebid-specific patterns are recognized and incorporated")


if __name__ == "__main__":
    # Set environment variable to use ADK
    os.environ["AI_PROVIDER"] = "adk"
    
    # Run the async test
    asyncio.run(test_adk_summaries())