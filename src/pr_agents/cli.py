#!/usr/bin/env python3
"""Command-line interface for PR Agents."""

import argparse
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from github import Github
from loguru import logger

from .output import OutputManager
from .pr_processing.coordinator import PRCoordinator

# Load environment variables
load_dotenv()


def setup_environment():
    """Setup environment variables and API keys."""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    # Set up AI provider keys
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        os.environ["GOOGLE_GENAI_API_KEY"] = gemini_key

    return github_token


def setup_ai_and_personas(args):
    """Setup AI provider and personas from args."""
    if args.ai_provider:
        os.environ["AI_PROVIDER"] = args.ai_provider
        logger.info(f"Using AI provider: {args.ai_provider}")

        # Configure personas if specified
        if hasattr(args, "personas") and args.personas:
            personas = [p.strip() for p in args.personas.split(",")]
            valid_personas = {"executive", "product", "developer", "reviewer"}
            invalid = set(personas) - valid_personas
            if invalid:
                logger.error(f"Invalid personas: {', '.join(invalid)}")
                logger.info(f"Valid personas: {', '.join(valid_personas)}")
                sys.exit(1)
            os.environ["AI_PERSONAS"] = ",".join(personas)
            logger.info(f"Using personas: {', '.join(personas)}")


def analyze_pr(args):
    """Analyze a single PR."""
    github_token = setup_environment()

    # Configure AI and personas
    setup_ai_and_personas(args)

    # Initialize coordinator
    coordinator = PRCoordinator(
        github_token=github_token, ai_enabled=args.ai_provider is not None
    )

    # Analyze PR
    logger.info(f"Analyzing PR: {args.pr_url}")
    start_time = datetime.now()

    if args.output:
        # Analyze and save
        output_path, saved_file = coordinator.analyze_pr_and_save(
            args.pr_url, args.output, output_format=args.format
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.success(f"Analysis completed in {elapsed:.2f}s")
        logger.info(f"Results saved to: {saved_file}")
    else:
        # Just analyze
        results = coordinator.analyze_pr(args.pr_url)
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.success(f"Analysis completed in {elapsed:.2f}s")

        # Display results based on format
        output_mgr = OutputManager()
        formatter = output_mgr._get_formatter(args.format)
        formatted = formatter.format(results)
        print(formatted)


def analyze_release(args):
    """Analyze PRs in a release."""
    github_token = setup_environment()

    # Configure AI and personas
    setup_ai_and_personas(args)

    coordinator = PRCoordinator(
        github_token=github_token, ai_enabled=args.ai_provider is not None
    )

    logger.info(f"Analyzing release {args.release_tag} for {args.repo}")
    results = coordinator.analyze_release_prs(args.repo, args.release_tag)

    # Save or display results
    if args.output:
        output_mgr = OutputManager()
        output_path = output_mgr.save(results, args.output, args.format)
        logger.info(f"Results saved to: {output_path}")
    else:
        # Display summary
        print(
            f"\nAnalyzed {len(results.get('prs', []))} PRs in release {args.release_tag}"
        )


def analyze_unreleased(args):
    """Analyze unreleased PRs."""
    github_token = setup_environment()

    # Configure AI and personas
    setup_ai_and_personas(args)

    coordinator = PRCoordinator(
        github_token=github_token, ai_enabled=args.ai_provider is not None
    )

    logger.info(f"Analyzing unreleased PRs for {args.repo} (branch: {args.branch})")
    results = coordinator.analyze_unreleased_prs(args.repo, args.branch)

    # Save or display results
    if args.output:
        output_mgr = OutputManager()
        output_path = output_mgr.save(results, args.output, args.format)
        logger.info(f"Results saved to: {output_path}")
    else:
        # Display summary
        pr_count = len(results.get("pr_results", {}))
        batch_summary = results.get("batch_summary", {})

        print(f"\nAnalyzed {pr_count} unreleased PRs from {args.repo}")
        print(f"Branch: {args.branch}")

        if pr_count > 0:
            print("\nSummary:")
            print(
                f"- Successful analyses: {batch_summary.get('successful_analyses', 0)}"
            )
            print(f"- Failed analyses: {batch_summary.get('failed_analyses', 0)}")

            # Show risk breakdown if available
            risk_levels = batch_summary.get("by_risk_level", {})
            if risk_levels:
                print("\nRisk Levels:")
                for level, count in risk_levels.items():
                    if count > 0:
                        print(f"- {level}: {count}")
        else:
            print("No unreleased PRs found.")


def analyze_batch(args):
    """Analyze multiple PRs."""
    github_token = setup_environment()

    # Configure AI and personas
    setup_ai_and_personas(args)

    coordinator = PRCoordinator(
        github_token=github_token, ai_enabled=args.ai_provider is not None
    )

    # Get PRs based on input method
    pr_urls = []

    if args.file:
        # Read from file
        with open(args.file) as f:
            pr_urls = [line.strip() for line in f if line.strip()]
    elif args.repo and args.count:
        # Get recent PRs from repo
        g = Github(github_token)
        repo = g.get_repo(args.repo)

        prs = []
        for pr in repo.get_pulls(state="closed", sort="created", direction="desc"):
            if pr.merged:
                prs.append(f"https://github.com/{args.repo}/pull/{pr.number}")
                if len(prs) >= args.count:
                    break
        pr_urls = prs
    else:
        # Use provided URLs
        pr_urls = args.pr_urls

    logger.info(f"Analyzing {len(pr_urls)} PRs")

    # Analyze each PR
    results = []
    for i, pr_url in enumerate(pr_urls, 1):
        logger.info(f"[{i}/{len(pr_urls)}] Analyzing {pr_url}")
        try:
            if args.output:
                # Generate individual output files
                output_name = f"{args.output}_pr_{pr_url.split('/')[-1]}"
                _, saved_file = coordinator.analyze_pr_and_save(
                    pr_url, output_name, args.format
                )
                results.append({"pr_url": pr_url, "output": saved_file})
            else:
                result = coordinator.analyze_pr(pr_url)
                results.append({"pr_url": pr_url, "result": result})
        except Exception as e:
            logger.error(f"Error analyzing {pr_url}: {e}")
            results.append({"pr_url": pr_url, "error": str(e)})

    # Summary
    success_count = sum(1 for r in results if "error" not in r)
    logger.info(f"\nBatch complete: {success_count}/{len(results)} successful")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PR Agents - Analyze GitHub Pull Requests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single PR
  pr-agents analyze https://github.com/owner/repo/pull/123

  # Analyze with AI summaries
  pr-agents analyze https://github.com/owner/repo/pull/123 --ai google-adk

  # Analyze with only specific personas
  pr-agents analyze https://github.com/owner/repo/pull/123 --ai google-adk --personas reviewer
  pr-agents analyze https://github.com/owner/repo/pull/123 --ai google-adk --personas executive,reviewer

  # Save to file
  pr-agents analyze https://github.com/owner/repo/pull/123 -o analysis.md

  # Analyze a release
  pr-agents release owner/repo v1.2.3

  # Analyze unreleased PRs (merged but not in any release)
  pr-agents unreleased owner/repo --ai google-adk

  # Analyze unreleased PRs with only code review
  pr-agents unreleased owner/repo --ai google-adk --personas reviewer

  # Analyze unreleased PRs from a different branch
  pr-agents unreleased owner/repo --branch develop

  # Analyze last 5 PRs from a repo
  pr-agents batch --repo owner/repo --count 5 --ai google-adk
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Analyze single PR
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a single PR")
    analyze_parser.add_argument("pr_url", help="PR URL to analyze")
    analyze_parser.add_argument("-o", "--output", help="Output file path")
    analyze_parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "md", "json", "text", "txt"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    analyze_parser.add_argument(
        "--ai",
        dest="ai_provider",
        choices=["google-adk", "claude-adk", "gemini", "claude", "openai"],
        help="Enable AI summaries with specified provider",
    )
    analyze_parser.add_argument(
        "--personas",
        help="Comma-separated list of personas to include (default: all). Options: executive,product,developer,reviewer",
        default=None,
    )
    analyze_parser.set_defaults(func=analyze_pr)

    # Analyze release
    release_parser = subparsers.add_parser("release", help="Analyze PRs in a release")
    release_parser.add_argument("repo", help="Repository (owner/name)")
    release_parser.add_argument("release_tag", help="Release tag")
    release_parser.add_argument("-o", "--output", help="Output file path")
    release_parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "md", "json", "text", "txt"],
        default="markdown",
        help="Output format",
    )
    release_parser.add_argument("--ai", dest="ai_provider", help="Enable AI summaries")
    release_parser.add_argument(
        "--personas",
        help="Comma-separated list of personas to include (default: all)",
        default=None,
    )
    release_parser.set_defaults(func=analyze_release)

    # Analyze unreleased PRs
    unreleased_parser = subparsers.add_parser(
        "unreleased", help="Analyze PRs merged but not yet released"
    )
    unreleased_parser.add_argument("repo", help="Repository (owner/name)")
    unreleased_parser.add_argument(
        "--branch", default="main", help="Base branch to check (default: main)"
    )
    unreleased_parser.add_argument("-o", "--output", help="Output file path")
    unreleased_parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "md", "json", "text", "txt"],
        default="markdown",
        help="Output format",
    )
    unreleased_parser.add_argument(
        "--ai", dest="ai_provider", help="Enable AI summaries"
    )
    unreleased_parser.add_argument(
        "--personas",
        help="Comma-separated list of personas to include (default: all)",
        default=None,
    )
    unreleased_parser.set_defaults(func=analyze_unreleased)

    # Batch analyze
    batch_parser = subparsers.add_parser("batch", help="Analyze multiple PRs")
    batch_parser.add_argument("pr_urls", nargs="*", help="PR URLs to analyze")
    batch_parser.add_argument("--file", help="File containing PR URLs (one per line)")
    batch_parser.add_argument("--repo", help="Repository to get PRs from")
    batch_parser.add_argument(
        "--count", type=int, help="Number of recent PRs to analyze"
    )
    batch_parser.add_argument("-o", "--output", help="Output file prefix")
    batch_parser.add_argument(
        "-f", "--format", default="markdown", help="Output format"
    )
    batch_parser.add_argument("--ai", dest="ai_provider", help="Enable AI summaries")
    batch_parser.add_argument(
        "--personas",
        help="Comma-separated list of personas to include (default: all)",
        default=None,
    )
    batch_parser.set_defaults(func=analyze_batch)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
