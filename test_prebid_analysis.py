#!/usr/bin/env python3
"""Test PR Agents on recent Prebid.js PRs using actual AI summaries."""

import os
import asyncio
from datetime import datetime
from pathlib import Path

from src.pr_agents.pr_processing.coordinator import PRCoordinator


async def main():
    """Test the full PR analysis pipeline on Prebid.js."""
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("Error: GITHUB_TOKEN not set")
        return
    
    # Check which AI provider is configured
    ai_provider = os.getenv('AI_PROVIDER', 'gemini')
    print(f"Testing PR Agents with {ai_provider.upper()} AI provider...")
    
    # Initialize coordinator with AI enabled
    print("\nInitializing PR Coordinator with AI summaries...")
    coordinator = PRCoordinator(github_token=github_token, ai_enabled=True)
    
    # Show current AI configuration
    model_info = coordinator.get_ai_model_info()
    print(f"\nAI Configuration:")
    print(f"  AI Enabled: {model_info.get('ai_enabled', False)}")
    
    if model_info.get('ai_enabled'):
        print(f"  Provider: {model_info.get('provider', 'Unknown')}")
        print(f"  Model: {model_info.get('model', 'Unknown')}")
        print(f"  Has API Key: {model_info.get('has_api_key', False)}")
    else:
        print(f"  Status: {model_info.get('message', 'AI not initialized')}")
    
    if model_info.get('ai_enabled') and not model_info.get('has_api_key') and model_info.get('provider') not in ['basic', 'gemini-free']:
        print(f"\n⚠️  Warning: No API key found for {model_info['provider']}")
        print("Set one of these environment variables:")
        print("  export GEMINI_API_KEY=your-key")
        print("  export ANTHROPIC_API_KEY=your-key")
        print("  export OPENAI_API_KEY=your-key")
    
    # Get recent PRs from Prebid.js
    print("\nFetching recent merged PRs from prebid/Prebid.js...")
    
    from github import Github
    g = Github(github_token)
    repo = g.get_repo("prebid/Prebid.js")
    
    # Get last 5 merged PRs
    pr_urls = []
    pr_info = []
    for pr in repo.get_pulls(state="closed", sort="updated", direction="desc"):
        if pr.merged and len(pr_urls) < 5:
            pr_urls.append(pr.html_url)
            pr_info.append({
                'number': pr.number,
                'title': pr.title,
                'author': pr.user.login,
                'merged_at': pr.merged_at
            })
            print(f"  PR #{pr.number}: {pr.title}")
        if len(pr_urls) >= 5:
            break
    
    # Analyze PRs in batch
    print(f"\n🔬 Analyzing {len(pr_urls)} PRs with full pipeline...")
    print("This may take a moment as AI generates summaries...\n")
    
    start_time = datetime.now()
    
    # Run batch analysis
    results = coordinator.analyze_prs_batch(
        pr_urls,
        extract_components={'metadata', 'code_changes', 'repository', 'reviews'},
        run_processors=['metadata', 'code_changes', 'repository', 'ai_summaries']
    )
    
    analysis_time = (datetime.now() - start_time).total_seconds()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = f"output/prebid_test_{timestamp}"
    
    print(f"\n💾 Saving results...")
    
    # Save as both markdown and JSON
    md_path = coordinator.output_manager.save(results, output_base, 'markdown')
    json_path = coordinator.output_manager.save(results, output_base, 'json')
    
    print(f"  ✓ Markdown: {md_path}")
    print(f"  ✓ JSON: {json_path}")
    
    # Display summary of results
    print(f"\n📊 Analysis Summary:")
    print(f"  Total PRs analyzed: {len(results.get('pr_analyses', []))}")
    print(f"  Total analysis time: {analysis_time:.2f} seconds")
    print(f"  Average per PR: {analysis_time/len(pr_urls):.2f} seconds")
    
    # Show example AI summaries from first PR
    if 'pr_analyses' in results and results['pr_analyses']:
        first_pr = results['pr_analyses'][0]
        
        print(f"\n📝 Example AI Summaries for PR #{pr_info[0]['number']}:")
        print(f"   Title: {pr_info[0]['title']}")
        
        # Find AI summaries in processing results
        for proc_result in first_pr.get('processing_results', []):
            if proc_result.get('component') == 'ai_summaries' and proc_result.get('success'):
                ai_data = proc_result.get('data', {})
                
                # Executive summary
                exec_summary = ai_data.get('executive_summary', {})
                print(f"\n🎯 Executive Summary:")
                print(f"   {exec_summary.get('summary', 'Not generated')}")
                
                # Product summary
                prod_summary = ai_data.get('product_summary', {})
                print(f"\n📦 Product Summary:")
                print(f"   {prod_summary.get('summary', 'Not generated')}")
                
                # Developer summary (truncated for display)
                dev_summary = ai_data.get('developer_summary', {})
                dev_text = dev_summary.get('summary', 'Not generated')
                if len(dev_text) > 200:
                    dev_text = dev_text[:200] + "..."
                print(f"\n💻 Developer Summary (truncated):")
                print(f"   {dev_text}")
                
                # Metadata
                print(f"\n⚙️  Generation Details:")
                print(f"   Model: {ai_data.get('model_used', 'Unknown')}")
                print(f"   Cached: {ai_data.get('cached', False)}")
                print(f"   Generation time: {ai_data.get('generation_time_ms', 0)}ms")
                break
    
    # Check processing statistics
    if 'statistics' in results:
        stats = results['statistics']
        print(f"\n📈 Processing Statistics:")
        print(f"   Successful: {stats.get('successful_analyses', 0)}")
        print(f"   Failed: {stats.get('failed_analyses', 0)}")
        
        if 'component_stats' in stats:
            print(f"\n   Component Success Rates:")
            for comp, comp_stats in stats['component_stats'].items():
                success_rate = (comp_stats['successful'] / comp_stats['total'] * 100) if comp_stats['total'] > 0 else 0
                print(f"     {comp}: {success_rate:.1f}% ({comp_stats['successful']}/{comp_stats['total']})")
    
    print(f"\n✅ Test complete! Check the output files for detailed results.")
    print(f"\n💡 To test with different AI providers, set:")
    print("   export AI_PROVIDER=gemini    # Google Gemini")
    print("   export AI_PROVIDER=claude    # Anthropic Claude")
    print("   export AI_PROVIDER=openai    # OpenAI GPT")


if __name__ == "__main__":
    asyncio.run(main())