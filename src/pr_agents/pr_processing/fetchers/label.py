"""
Label-based PR fetcher implementation.
"""

from typing import Any

from loguru import logger

from ...logging_config import log_api_call, log_processing_step
from .base import BasePRFetcher


class LabelPRFetcher(BasePRFetcher):
    """
    Fetches PRs based on labels.

    Handles:
    - PRs with specific labels
    - PRs with multiple labels (AND/OR logic)
    - PRs without specific labels
    - Label combinations
    """

    def fetch(self, **kwargs) -> list[dict[str, Any]]:
        """
        Fetch PRs based on label criteria.

        Supported kwargs:
        - repo_name: Repository name (required)
        - labels: Single label or list of labels
        - labels_all: List of labels (PR must have ALL)
        - labels_any: List of labels (PR must have ANY)
        - labels_none: List of labels (PR must have NONE)
        - state: PR state filter (open, closed, merged, all)

        Returns:
            List of PR data dictionaries
        """
        repo_name = kwargs.get("repo_name")
        if not repo_name:
            raise ValueError("repo_name is required")

        state = kwargs.get("state", "all")

        if kwargs.get("labels"):
            # Single label or simple list (ANY logic)
            labels = kwargs["labels"]
            if isinstance(labels, str):
                labels = [labels]
            return self.get_prs_by_labels_any(repo_name, labels, state)
        elif kwargs.get("labels_all"):
            # Must have ALL labels
            return self.get_prs_by_labels_all(repo_name, kwargs["labels_all"], state)
        elif kwargs.get("labels_any"):
            # Must have ANY of the labels
            return self.get_prs_by_labels_any(repo_name, kwargs["labels_any"], state)
        elif kwargs.get("labels_none"):
            # Must NOT have any of these labels
            return self.get_prs_without_labels(repo_name, kwargs["labels_none"], state)
        else:
            raise ValueError(
                "Must specify either labels, labels_all, labels_any, or labels_none"
            )

    def get_prs_by_labels_any(
        self, repo_name: str, labels: list[str], state: str = "all"
    ) -> list[dict[str, Any]]:
        """
        Get PRs that have ANY of the specified labels.

        Args:
            repo_name: Repository name
            labels: List of labels (OR logic)
            state: PR state filter

        Returns:
            List of PR data dictionaries
        """
        try:
            log_processing_step(f"Fetching PRs with any of labels: {labels}")

            # GitHub search doesn't support OR for labels directly,
            # so we need to make multiple queries and deduplicate
            all_prs = {}  # Use dict to deduplicate by PR number

            for label in labels:
                query = f'repo:{repo_name} type:pr label:"{label}"'

                if state != "all":
                    if state == "merged":
                        query += " is:merged"
                    elif state == "closed":
                        query += " is:closed"
                    elif state == "open":
                        query += " is:open"

                log_api_call("search_issues", {"query": query})

                for pr in self.github_client.search_issues(query=query):
                    pr_data = self._build_pr_data(pr)
                    pr_data["repository"] = repo_name
                    # Use PR number as key to avoid duplicates
                    all_prs[pr.number] = pr_data

            prs = list(all_prs.values())
            logger.info(f"Found {len(prs)} PRs with any of labels: {labels}")
            return prs

        except Exception as e:
            logger.error(f"Error fetching PRs by labels: {e}")
            raise

    def get_prs_by_labels_all(
        self, repo_name: str, labels: list[str], state: str = "all"
    ) -> list[dict[str, Any]]:
        """
        Get PRs that have ALL of the specified labels.

        Args:
            repo_name: Repository name
            labels: List of labels (AND logic)
            state: PR state filter

        Returns:
            List of PR data dictionaries
        """
        try:
            log_processing_step(f"Fetching PRs with all labels: {labels}")

            # Build query with all labels (AND logic)
            query = f"repo:{repo_name} type:pr"

            for label in labels:
                query += f' label:"{label}"'

            if state != "all":
                if state == "merged":
                    query += " is:merged"
                elif state == "closed":
                    query += " is:closed"
                elif state == "open":
                    query += " is:open"

            log_api_call("search_issues", {"query": query})

            prs = []
            for pr in self.github_client.search_issues(query=query):
                pr_data = self._build_pr_data(pr)
                pr_data["repository"] = repo_name
                prs.append(pr_data)

            logger.info(f"Found {len(prs)} PRs with all labels: {labels}")
            return prs

        except Exception as e:
            logger.error(f"Error fetching PRs by labels: {e}")
            raise

    def get_prs_without_labels(
        self, repo_name: str, labels: list[str], state: str = "all"
    ) -> list[dict[str, Any]]:
        """
        Get PRs that do NOT have any of the specified labels.

        Args:
            repo_name: Repository name
            labels: List of labels to exclude
            state: PR state filter

        Returns:
            List of PR data dictionaries
        """
        try:
            log_processing_step(f"Fetching PRs without labels: {labels}")

            # Build query with negative labels
            query = f"repo:{repo_name} type:pr"

            for label in labels:
                query += f' -label:"{label}"'

            if state != "all":
                if state == "merged":
                    query += " is:merged"
                elif state == "closed":
                    query += " is:closed"
                elif state == "open":
                    query += " is:open"

            log_api_call("search_issues", {"query": query})

            prs = []
            for pr in self.github_client.search_issues(query=query):
                pr_data = self._build_pr_data(pr)
                pr_data["repository"] = repo_name
                prs.append(pr_data)

            logger.info(f"Found {len(prs)} PRs without labels: {labels}")
            return prs

        except Exception as e:
            logger.error(f"Error fetching PRs without labels: {e}")
            raise

    def get_prs_by_label_pattern(
        self, repo_name: str, label_pattern: str, state: str = "all"
    ) -> list[dict[str, Any]]:
        """
        Get PRs with labels matching a pattern.

        Note: GitHub search doesn't support wildcards in labels,
        so this fetches all PRs and filters client-side.

        Args:
            repo_name: Repository name
            label_pattern: Label pattern (e.g., "bug-*", "priority-*")
            state: PR state filter

        Returns:
            List of PR data dictionaries
        """
        try:
            import re

            log_processing_step(f"Fetching PRs with label pattern: {label_pattern}")

            # Convert pattern to regex
            regex_pattern = label_pattern.replace("*", ".*")
            label_regex = re.compile(f"^{regex_pattern}$")

            # Fetch all PRs and filter by label pattern
            query = f"repo:{repo_name} type:pr"

            if state != "all":
                if state == "merged":
                    query += " is:merged"
                elif state == "closed":
                    query += " is:closed"
                elif state == "open":
                    query += " is:open"

            log_api_call("search_issues", {"query": query})

            prs = []
            for pr in self.github_client.search_issues(query=query):
                # Check if any label matches the pattern
                pr_labels = [label.name for label in pr.labels]
                if any(label_regex.match(label) for label in pr_labels):
                    pr_data = self._build_pr_data(pr)
                    pr_data["repository"] = repo_name
                    prs.append(pr_data)

            logger.info(f"Found {len(prs)} PRs with label pattern: {label_pattern}")
            return prs

        except Exception as e:
            logger.error(f"Error fetching PRs by label pattern: {e}")
            raise
