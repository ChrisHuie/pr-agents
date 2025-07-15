"""
PR Tagging Processor - Tags PRs based on YAML registry and repository structure.
"""

from dataclasses import asdict
from typing import Any

from ...config.manager import RepositoryStructureManager
from ..models import ProcessingResult
from ..pattern_evaluator import PatternEvaluator
from ..registry_loader import RegistryLoader
from ..tagging_models import (
    FileTag,
    ImpactLevel,
    TaggingResult,
)
from .base import BaseProcessor


class PRTaggerProcessor(BaseProcessor):
    """
    Tags PRs based on repository-specific YAML registry rules and structure.
    Provides hierarchical tagging, impact analysis, and module categorization.
    """

    def __init__(
        self,
        registry_path: str = "registry/prebid/",
        config_file: str = "config/repository_structures.json",
    ):
        self.registry_loader = RegistryLoader(registry_path)
        self.pattern_evaluator = PatternEvaluator()
        self.repo_manager = RepositoryStructureManager(config_file)

    @property
    def component_name(self) -> str:
        return "pr_tagging"

    def process(self, component_data: dict[str, Any]) -> ProcessingResult:
        """
        Tag PR based on file changes and repository rules.

        Expected component_data:
        - repository: Repository information (from repository extractor)
        - code_changes: Code changes information (from code extractor)
        - metadata: PR metadata (optional, for context)
        """
        try:
            # Extract repository and file information
            repo_info = component_data.get("repository", {})
            repo_url = repo_info.get("clone_url", "")

            code_changes = component_data.get("code_changes", {})
            files = code_changes.get("files", [])

            # Initialize result
            result = TaggingResult(
                repo_type=repo_info.get("repo_type"),
                repo_version=self._detect_version(component_data, repo_info),
            )

            # Get YAML registry for this repo
            registry = self.registry_loader.get_repo_registry(repo_url)

            # Get repository structure configuration
            repo_structure = self.repo_manager.get_repository(repo_url)

            # Process each file
            for file_info in files:
                self._process_file(
                    file_info, result, registry, repo_structure, repo_url
                )

            # Generate PR-level tags and summary
            self._generate_pr_summary(result)

            # Calculate statistics
            self._calculate_statistics(result)

            return ProcessingResult(
                component=self.component_name,
                success=True,
                data=self._serialize_result(result),
            )

        except Exception as e:
            return ProcessingResult(
                component=self.component_name, success=False, error=str(e), data={}
            )

    def _process_file(
        self,
        file_info: dict[str, Any],
        result: TaggingResult,
        registry: Any,
        repo_structure: Any,
        repo_url: str,
    ):
        """Process a single file and add tags."""
        filepath = file_info.get("filename", "")
        status = file_info.get("status", "modified")

        # Create FileTag object
        file_tag = FileTag(filepath=filepath, is_new_file=(status == "added"))

        # Apply repository structure categorization (from JSON config)
        if repo_structure:
            # Get detailed module info including name extraction
            module_info = self.repo_manager.get_module_info(
                repo_url, filepath, result.repo_version
            )

            # Update file tag with structure info
            file_tag.module_categories = module_info.get("categories", [])
            file_tag.module_name = module_info.get("module_name")
            file_tag.is_core = module_info.get("is_core", False)
            file_tag.is_test = module_info.get("is_test", False)
            file_tag.is_doc = module_info.get("is_doc", False)

            # Add module information to result
            if file_tag.module_name and file_tag.module_categories:
                for category in file_tag.module_categories:
                    if category not in result.affected_modules:
                        result.affected_modules[category] = []
                    if file_tag.module_name not in result.affected_modules[category]:
                        result.affected_modules[category].append(file_tag.module_name)

        # Apply YAML registry patterns (hierarchical tagging)
        if registry:
            patterns = self.registry_loader.parse_structure_patterns(registry.structure)

            matches = self.pattern_evaluator.evaluate_file(filepath, patterns, status)

            for pattern, match_info in matches:
                # Add hierarchical tag
                htag = match_info["hierarchical_tag"]
                file_tag.hierarchical_tags.append(htag)
                file_tag.flat_tags.append(htag.to_string())

                # Add to result hierarchy
                result.add_file_to_hierarchy(filepath, htag.primary, htag.secondary)

                # Extract module info from pattern
                module_info = self.pattern_evaluator.extract_module_info(
                    filepath, pattern
                )
                if module_info.get("module_type") and not file_tag.module_categories:
                    file_tag.module_categories.append(module_info["module_type"])

            # Determine impact level
            impact_level = self.pattern_evaluator.determine_impact_level(
                filepath, matches, status
            )
            file_tag.impact_level = ImpactLevel(impact_level)

        # Apply any matching rules from registry
        if registry and registry.rules:
            self._apply_rules(file_tag, registry.rules, result)

        # Add file tag to result
        result.file_tags[filepath] = file_tag

    def _apply_rules(
        self, file_tag: FileTag, rules: list[dict[str, Any]], result: TaggingResult
    ):
        """Apply registry rules to a file."""
        # This is a placeholder for rule application logic
        # Rules would be evaluated based on file properties and patterns
        pass

    def _generate_pr_summary(self, result: TaggingResult):
        """Generate PR-level summary from file-level analysis."""
        # Collect all unique tags
        all_tags = set()
        all_hierarchical_tags = []
        impact_levels = []

        for file_tag in result.file_tags.values():
            all_tags.update(file_tag.flat_tags)
            all_hierarchical_tags.extend(file_tag.hierarchical_tags)
            impact_levels.append(file_tag.impact_level.value)

        result.pr_tags = all_tags
        result.pr_hierarchical_tags = all_hierarchical_tags

        # Determine overall impact level (highest among all files)
        if impact_levels:
            impact_priority = {
                "critical": 5,
                "high": 4,
                "medium": 3,
                "low": 2,
                "minimal": 1,
            }
            max_impact = max(impact_levels, key=lambda x: impact_priority.get(x, 0))
            result.pr_impact_level = ImpactLevel(max_impact)

        # Collect unique module categories
        all_categories = set()
        for file_tag in result.file_tags.values():
            all_categories.update(file_tag.module_categories)
        result.module_categories = list(all_categories)

    def _calculate_statistics(self, result: TaggingResult):
        """Calculate summary statistics."""
        result.stats = {
            "total_files": len(result.file_tags),
            "files_by_impact": {},
            "files_by_primary_tag": {},
            "new_files_count": 0,
            "core_files_count": 0,
            "test_files_count": 0,
            "doc_files_count": 0,
            "module_count": sum(
                len(modules) for modules in result.affected_modules.values()
            ),
        }

        # Count files by impact level
        for level in ImpactLevel:
            result.stats["files_by_impact"][level.value] = 0

        # Count files by primary tag
        for file_tag in result.file_tags.values():
            # Impact level
            result.stats["files_by_impact"][file_tag.impact_level.value] += 1

            # File types
            if file_tag.is_new_file:
                result.stats["new_files_count"] += 1
            if file_tag.is_core:
                result.stats["core_files_count"] += 1
            if file_tag.is_test:
                result.stats["test_files_count"] += 1
            if file_tag.is_doc:
                result.stats["doc_files_count"] += 1

            # Primary tags
            for htag in file_tag.hierarchical_tags:
                primary = htag.primary
                if primary not in result.stats["files_by_primary_tag"]:
                    result.stats["files_by_primary_tag"][primary] = 0
                result.stats["files_by_primary_tag"][primary] += 1

    def _detect_version(
        self, component_data: dict[str, Any], repo_info: dict[str, Any]
    ) -> str | None:
        """Detect repository version from component data or repo info."""
        # Check if version is provided in component data first
        if "version" in component_data:
            return component_data["version"]

        # Check if version is provided in repo info
        if "version" in repo_info:
            return repo_info["version"]

        # Fall back to default branch
        return repo_info.get("default_branch", "master")

    def _serialize_result(self, result: TaggingResult) -> dict[str, Any]:
        """Serialize TaggingResult to dictionary."""
        # Convert file tags
        file_tags_dict = {}
        for filepath, file_tag in result.file_tags.items():
            file_tags_dict[filepath] = {
                "tags": file_tag.flat_tags,
                "hierarchical_tags": [
                    {
                        "primary": ht.primary,
                        "secondary": ht.secondary,
                        "tertiary": ht.tertiary,
                    }
                    for ht in file_tag.hierarchical_tags
                ],
                "module_categories": file_tag.module_categories,
                "module_name": file_tag.module_name,
                "impact_level": file_tag.impact_level.value,
                "is_core": file_tag.is_core,
                "is_test": file_tag.is_test,
                "is_doc": file_tag.is_doc,
                "is_new_file": file_tag.is_new_file,
                "metadata": file_tag.metadata,
            }

        return {
            "file_tags": file_tags_dict,
            "pr_tags": list(result.pr_tags),
            "pr_hierarchical_tags": [
                {
                    "primary": ht.primary,
                    "secondary": ht.secondary,
                    "tertiary": ht.tertiary,
                }
                for ht in result.pr_hierarchical_tags
            ],
            "pr_impact_level": result.pr_impact_level.value,
            "tag_hierarchy": result.tag_hierarchy,
            "affected_modules": result.affected_modules,
            "module_categories": result.module_categories,
            "rule_matches": [asdict(rm) for rm in result.rule_matches],
            "stats": result.stats,
            "repo_type": result.repo_type,
            "repo_version": result.repo_version,
        }
