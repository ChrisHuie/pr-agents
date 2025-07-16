"""
Dataclass models for internal analysis results.

These are separate from Pydantic models which handle external API data.
Dataclasses provide better performance and less boilerplate for internal processing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# Metadata Analysis Results
@dataclass
class TitleAnalysis:
    """Analysis of PR title characteristics."""

    length: int
    word_count: int
    has_emoji: bool
    has_prefix: bool
    has_ticket_reference: bool
    is_question: bool
    is_wip: bool


@dataclass
class DescriptionAnalysis:
    """Analysis of PR description characteristics."""

    has_description: bool
    length: int
    line_count: int = 0
    sections: list[str] = field(default_factory=list)
    has_checklist: bool = False
    has_links: bool = False
    has_code_blocks: bool = False


@dataclass
class LabelAnalysis:
    """Analysis of PR labels."""

    total_count: int
    categorized: dict[str, list[str]] = field(default_factory=dict)
    uncategorized: list[str] = field(default_factory=list)
    has_type_label: bool = False
    has_priority_label: bool = False


@dataclass
class TitleQuality:
    """Title quality assessment on 1-100 scale."""

    score: int
    quality_level: str
    issues: list[str] = field(default_factory=list)


@dataclass
class DescriptionQuality:
    """Description quality assessment on 1-100 scale."""

    score: int
    quality_level: str
    issues: list[str] = field(default_factory=list)


@dataclass
class MetadataAnalysisResult:
    """Complete metadata analysis result."""

    title_analysis: TitleAnalysis
    description_analysis: DescriptionAnalysis
    label_analysis: LabelAnalysis
    title_quality: TitleQuality
    description_quality: DescriptionQuality


# Code Analysis Results
@dataclass
class ChangeStats:
    """Basic change statistics."""

    total_additions: int
    total_deletions: int
    total_changes: int
    changed_files: int
    net_lines: int
    change_ratio: float


@dataclass
class FileAnalysis:
    """File-level change analysis."""

    file_types: dict[str, int] = field(default_factory=dict)
    file_sizes: dict[str, int] = field(default_factory=dict)
    file_statuses: dict[str, int] = field(default_factory=dict)
    largest_file_changes: int = 0


@dataclass
class PatternAnalysis:
    """Code pattern analysis."""

    has_tests: bool = False
    has_config_changes: bool = False
    has_documentation: bool = False
    has_migrations: bool = False
    has_dependencies: bool = False
    test_file_ratio: float = 0.0
    config_files: list[str] = field(default_factory=list)
    potential_breaking_changes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """Risk assessment of code changes."""

    risk_score: int
    risk_level: str
    risk_factors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class CodeAnalysisResult:
    """Complete code analysis result."""

    change_stats: ChangeStats
    file_analysis: FileAnalysis
    pattern_analysis: PatternAnalysis
    risk_assessment: RiskAssessment


# Repository Analysis Results
@dataclass
class RepoInfo:
    """Basic repository information."""

    name: str | None
    full_name: str | None
    owner: str | None
    is_private: bool
    is_fork: bool
    has_description: bool
    description_length: int
    topics_count: int
    topics: list[str] = field(default_factory=list)


@dataclass
class LanguageAnalysis:
    """Repository language composition analysis."""

    primary_language: str | None
    language_count: int
    language_distribution: dict[str, float] = field(default_factory=dict)
    total_bytes: int = 0
    languages_list: list[str] = field(default_factory=list)
    repo_categories: list[str] = field(default_factory=list)
    is_polyglot: bool = False


@dataclass
class BranchAnalysis:
    """Branch information analysis."""

    base_branch: str
    head_branch: str
    default_branch: str
    base_branch_type: str
    head_branch_type: str
    is_to_main: bool
    is_cross_fork: bool
    follows_naming_convention: bool


@dataclass
class RepoHealth:
    """Repository health assessment."""

    health_score: int
    health_level: str
    health_factors: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    max_possible_score: int = 70
    recommendations: list[str] = field(default_factory=list)


@dataclass
class RepoAnalysisResult:
    """Complete repository analysis result."""

    repo_info: RepoInfo
    language_analysis: LanguageAnalysis
    branch_analysis: BranchAnalysis
    repo_health: RepoHealth


# AI Analysis Results
@dataclass
class PersonaSummary:
    """Summary for a specific persona."""

    persona: str  # "executive", "product", "developer"
    summary: str
    confidence: float


@dataclass
class AISummaries:
    """AI-generated summaries for code changes."""

    executive_summary: PersonaSummary
    product_summary: PersonaSummary
    developer_summary: PersonaSummary
    model_used: str
    generation_timestamp: datetime
    cached: bool = False
    total_tokens: int = 0
    generation_time_ms: int = 0
