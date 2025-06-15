"""
Constants for PR processing components.

These constants define the keys used in ProcessingResult.data dictionaries
to ensure consistency across processors, tests, and other consumers.
"""

# Metadata processor result keys
TITLE_ANALYSIS_KEY = "title_analysis"
DESCRIPTION_ANALYSIS_KEY = "description_analysis"
LABEL_ANALYSIS_KEY = "label_analysis"
METADATA_QUALITY_KEY = "metadata_quality"

# Code processor result keys
CHANGE_STATS_KEY = "change_stats"
FILE_ANALYSIS_KEY = "file_analysis"
PATTERN_ANALYSIS_KEY = "pattern_analysis"
RISK_ASSESSMENT_KEY = "risk_assessment"

# Repository processor result keys
REPO_INFO_KEY = "repo_info"
LANGUAGE_ANALYSIS_KEY = "language_analysis"
BRANCH_ANALYSIS_KEY = "branch_analysis"
REPO_HEALTH_KEY = "repo_health"

# Component names
METADATA_COMPONENT = "metadata"
CODE_CHANGES_COMPONENT = "code_changes"
REPOSITORY_COMPONENT = "repository"
