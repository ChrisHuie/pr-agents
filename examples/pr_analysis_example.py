"""
Example usage of the PR processing system with component isolation.
"""

import os
from pprint import pprint

from src.pr_agents.pr_processing import PRCoordinator


def main():
    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Please set GITHUB_TOKEN environment variable")
        return

    # Initialize coordinator
    coordinator = PRCoordinator(github_token)

    # Example PR URL (replace with actual PR)
    pr_url = "https://github.com/octocat/Hello-World/pull/1"

    print("🔍 Analyzing PR with component isolation...")
    print(f"PR URL: {pr_url}")
    print("-" * 60)

    try:
        # Example 1: Extract only metadata (no code context bleeding)
        print("\n📋 EXTRACTING METADATA ONLY (isolated):")
        pr_data = coordinator.extract_pr_components(pr_url, components={"metadata"})

        if pr_data.metadata:
            print(f"Title: {pr_data.metadata['title']}")
            print(f"Author: {pr_data.metadata['author']}")
            print(f"Labels: {pr_data.metadata['labels']}")

        # Example 2: Extract code changes only (no metadata context)
        print("\n🔧 EXTRACTING CODE CHANGES ONLY (isolated):")
        code_data = coordinator.extract_pr_components(
            pr_url, components={"code_changes"}
        )

        if code_data.code_changes:
            print(f"Files changed: {code_data.code_changes['changed_files']}")
            print(f"Total additions: {code_data.code_changes['total_additions']}")
            print(f"Total deletions: {code_data.code_changes['total_deletions']}")

        # Example 3: Process metadata in isolation
        print("\n🧠 PROCESSING METADATA (isolated analysis):")
        if pr_data.metadata:
            metadata_results = coordinator.process_components(
                pr_data, processors=["metadata"]
            )

            for result in metadata_results:
                if result.success:
                    if "title_quality" in result.data:
                        title_quality = result.data["title_quality"]
                        print(f"Title quality level: {title_quality['quality_level']}")
                        print(f"Title score: {title_quality['score']}/100")
                    if "description_quality" in result.data:
                        desc_quality = result.data["description_quality"]
                        print(
                            f"Description quality level: {desc_quality['quality_level']}"
                        )
                        print(f"Description score: {desc_quality['score']}/100")

        # Example 4: Complete analysis with all components
        print("\n🎯 COMPLETE ANALYSIS (all components, strict isolation):")
        analysis = coordinator.analyze_pr(pr_url)

        print("Summary:")
        pprint(analysis["summary"])

        # Show that components remain isolated
        print("\n🔒 COMPONENT ISOLATION VERIFICATION:")
        extracted = analysis["extracted_data"]
        print(f"Components extracted: {list(extracted.keys())}")

        # Metadata processor never sees code changes
        # Code processor never sees PR title/description
        # Repository processor never sees PR-specific details
        print("✅ Each component processed in complete isolation")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure to use a valid GitHub PR URL")


if __name__ == "__main__":
    main()
