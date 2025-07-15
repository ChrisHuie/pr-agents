"""
Example script demonstrating output formatting capabilities.
"""

import argparse
import os
from pathlib import Path

from src.pr_agents.pr_processing.coordinator import PRCoordinator


def main():
    """Main entry point for the output example."""
    parser = argparse.ArgumentParser(
        description="Analyze a GitHub PR and save results in various formats"
    )
    parser.add_argument("pr_url", help="GitHub PR URL to analyze")
    parser.add_argument(
        "-o",
        "--output",
        default="pr_analysis",
        help="Output file path (without extension)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "json", "text"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--all-formats", action="store_true", help="Save in all available formats"
    )
    parser.add_argument(
        "--components",
        nargs="+",
        choices=["metadata", "code_changes", "repository", "reviews"],
        help="Components to extract (default: all)",
    )

    args = parser.parse_args()

    # Get GitHub token
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        return 1

    # Initialize coordinator
    print(f"Initializing PR analysis for: {args.pr_url}")
    coordinator = PRCoordinator(github_token)

    # Determine components to extract
    extract_components = None
    if args.components:
        extract_components = set(args.components)

    # Analyze and save
    try:
        if args.all_formats:
            # Save in all formats
            base_path = Path(args.output)
            formats = ["markdown", "json", "text"]

            print("Analyzing PR and saving in all formats...")
            results = coordinator.analyze_pr(args.pr_url, extract_components)
            formatted_results = coordinator._format_results_for_output(results)

            saved_files = coordinator.output_manager.save_multiple_formats(
                formatted_results, base_path, formats
            )

            print("\nSaved files:")
            for file_path in saved_files:
                print(f"  - {file_path}")

        else:
            # Save in single format
            print(f"Analyzing PR and saving as {args.format}...")
            results, saved_path = coordinator.analyze_pr_and_save(
                args.pr_url, args.output, args.format, extract_components
            )

            print(f"\nAnalysis complete! Results saved to: {saved_path}")

            # Print summary
            summary = results.get("summary", {})
            print("\nSummary:")
            print(
                f"  Components extracted: {', '.join(summary.get('components_extracted', []))}"
            )
            print(f"  Components processed: {summary.get('components_processed', 0)}")
            print(
                f"  Total processing time: {summary.get('total_processing_time_ms', 0)/1000:.2f}s"
            )

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
