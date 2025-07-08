"""
CLI tool for managing repository configurations.
"""

import argparse
import json
from pathlib import Path

from .loader import ConfigurationLoader
from .validator import ConfigurationValidator


def validate_command(args):
    """Validate configuration files."""
    validator = ConfigurationValidator(args.schema)

    if args.file:
        # Validate single file
        is_valid, errors = validator.validate_file(Path(args.file))
        if is_valid:
            print(f"✅ {args.file} is valid")
        else:
            print(f"❌ {args.file} has errors:")
            for error in errors:
                print(f"  - {error}")
    else:
        # Validate directory
        results = validator.validate_directory(Path(args.directory))

        valid_count = sum(1 for is_valid, _ in results.values() if is_valid)
        total_count = len(results)

        print(f"\nValidation Results: {valid_count}/{total_count} files valid\n")

        for file_path, (is_valid, errors) in results.items():
            if not is_valid:
                print(f"❌ {file_path}:")
                for error in errors:
                    print(f"  - {error}")


def migrate_command(args):
    """Migrate from single file to multi-file format."""
    source_file = Path(args.source)
    target_dir = Path(args.target)

    if not source_file.exists():
        print(f"Source file not found: {source_file}")
        return

    # Create target directory structure
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "repositories").mkdir(exist_ok=True)
    (target_dir / "repositories" / "prebid").mkdir(exist_ok=True)
    (target_dir / "repositories" / "shared").mkdir(exist_ok=True)
    (target_dir / "schema").mkdir(exist_ok=True)

    # Load the single file
    with open(source_file) as f:
        data = json.load(f)

    # Create base config from common patterns
    base_config = {
        "$schema": "../schema/repository.schema.json",
        "description": "Base configuration for Prebid repository modules and adapters",
        "module_categories": {},
    }

    # Extract common module categories
    common_categories = [
        "bid_adapter",
        "analytics_adapter",
        "rtd_module",
        "id_module",
        "video_module",
    ]

    # Process each repository
    repo_files = []
    for repo_name, repo_data in data.items():
        if not isinstance(repo_data, dict):
            continue

        # Create individual repo file
        repo_config = {
            "$schema": "../../schema/repository.schema.json",
            "repo_name": repo_name,
            "repo_type": repo_data.get("repo_type", ""),
            "description": repo_data.get("description", ""),
            "extends": "../shared/prebid-base.json",
        }

        # Add detection and fetch strategies
        if "default_detection_strategy" in repo_data:
            repo_config["detection_strategy"] = repo_data["default_detection_strategy"]
        if "fetch_strategy" in repo_data:
            repo_config["fetch_strategy"] = repo_data["fetch_strategy"]

        # Process module categories
        if "module_categories" in repo_data:
            repo_config["module_categories"] = {}
            for cat_name, cat_data in repo_data["module_categories"].items():
                # Add to base if it's common
                if (
                    cat_name in common_categories
                    and cat_name not in base_config["module_categories"]
                ):
                    base_patterns = cat_data.get("patterns", [])
                    if base_patterns:
                        base_config["module_categories"][cat_name] = {
                            "display_name": cat_data.get("display_name", ""),
                            "patterns": base_patterns,
                        }

                # Add repo-specific overrides
                repo_config["module_categories"][cat_name] = {
                    "paths": cat_data.get("paths", [])
                }
                if "detection_strategy" in cat_data:
                    repo_config["module_categories"][cat_name]["detection_strategy"] = (
                        cat_data["detection_strategy"]
                    )

        # Process version configs
        if "version_configs" in repo_data:
            repo_config["version_overrides"] = {}
            for ver_config in repo_data["version_configs"]:
                version_key = ver_config.get("version", "")
                if ver_config.get("version_range", "").startswith(">="):
                    version_key += "+"

                repo_config["version_overrides"][version_key] = {
                    "module_categories": ver_config.get("module_categories", {})
                }

        # Process paths
        repo_config["paths"] = {
            "core": repo_data.get("core_paths", []),
            "test": repo_data.get("test_paths", []),
            "docs": repo_data.get("doc_paths", []),
            "exclude": repo_data.get("exclude_paths", []),
        }

        # Process relationships
        if "relationships" in repo_data:
            repo_config["relationships"] = []
            for rel in repo_data["relationships"]:
                repo_config["relationships"].append(
                    {
                        "type": rel.get("relationship_type", ""),
                        "target": rel.get("target_repo", ""),
                        "description": rel.get("description", ""),
                    }
                )

        # Determine subdirectory
        if "prebid" in repo_name.lower():
            subdir = "prebid"
        else:
            subdir = "other"

        # Save repo file
        repo_filename = (
            repo_data.get("repo_type", repo_name.replace("/", "-")) + ".json"
        )
        repo_path = target_dir / "repositories" / subdir / repo_filename

        with open(repo_path, "w") as f:
            json.dump(repo_config, f, indent=2)

        repo_files.append(f"./repositories/{subdir}/{repo_filename}")
        print(f"Created: {repo_path}")

    # Save base config
    base_path = target_dir / "repositories" / "shared" / "prebid-base.json"
    with open(base_path, "w") as f:
        json.dump(base_config, f, indent=2)
    print(f"Created: {base_path}")

    # Create master repositories.json
    master_config = {
        "$schema": "./schema/repository.schema.json",
        "description": "Master configuration that imports all repository configurations",
        "repositories": sorted(repo_files),
    }

    master_path = target_dir / "repositories.json"
    with open(master_path, "w") as f:
        json.dump(master_config, f, indent=2)
    print(f"Created: {master_path}")

    print(f"\nMigration complete! Created {len(repo_files)} repository configs.")


def test_command(args):
    """Test loading configurations."""
    try:
        loader = ConfigurationLoader(args.path)
        config = loader.load_config()

        print(f"Successfully loaded {len(config.repositories)} repositories:\n")

        for repo_name, repo in config.repositories.items():
            print(f"- {repo_name} ({repo.repo_type})")
            print(f"  Module categories: {len(repo.module_categories)}")
            print(f"  Version configs: {len(repo.version_configs)}")
            if repo.relationships:
                print(f"  Relationships: {len(repo.relationships)}")
            print()

    except Exception as e:
        print(f"Error loading configuration: {e}")
        raise


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Repository configuration management tool"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate configuration files"
    )
    validate_parser.add_argument(
        "--schema",
        default="config/schema/repository.schema.json",
        help="Path to JSON schema file",
    )
    validate_parser.add_argument("--file", help="Validate a specific file")
    validate_parser.add_argument(
        "--directory", default="config", help="Directory to validate (default: config)"
    )

    # Migrate command
    migrate_parser = subparsers.add_parser(
        "migrate", help="Migrate from single to multi-file format"
    )
    migrate_parser.add_argument("source", help="Source configuration file")
    migrate_parser.add_argument("target", help="Target directory for multi-file config")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test loading configurations")
    test_parser.add_argument("--path", default="config", help="Config path to test")

    args = parser.parse_args()

    if args.command == "validate":
        validate_command(args)
    elif args.command == "migrate":
        migrate_command(args)
    elif args.command == "test":
        test_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
