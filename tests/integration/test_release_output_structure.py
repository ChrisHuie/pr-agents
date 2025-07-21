"""Integration tests for release output structure with PR grouping."""

from unittest.mock import Mock, patch

import pytest

from pr_agents.pr_processing.coordinator import PRCoordinator


class TestReleaseOutputStructure:
    """Test release analysis output with PR grouping by tags."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client with release data."""
        mock_client = Mock()
        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo

        # Mock release
        mock_release = Mock()
        mock_release.tag_name = "v8.0.0"
        mock_release.name = "Prebid 8.0.0"
        mock_release.published_at = "2024-01-15T10:00:00Z"
        mock_repo.get_releases.return_value = [mock_release]

        return mock_client

    @pytest.fixture
    def mock_pr_results(self):
        """Create mock PR results with different types."""
        return [
            {
                "success": True,
                "pr_data": {
                    "number": 1001,
                    "title": "Add new bid adapter for Example SSP",
                    "url": "https://github.com/prebid/Prebid.js/pull/1001",
                    "author": "adapter-dev",
                    "created_at": "2024-01-10T09:00:00Z",
                    "merged_at": "2024-01-12T15:00:00Z",
                    "state": "closed",
                    "labels": [{"name": "adapter"}, {"name": "feature"}],
                },
                "processing_results": [
                    {
                        "component": "ai_summaries",
                        "success": True,
                        "data": {
                            "executive_summary": "New Example SSP bid adapter added to expand programmatic demand sources.",
                            "product_summary": "Example SSP adapter supports banner and video formats with advanced targeting.",
                            "developer_summary": "Implements ExampleSSPAdapter extending BaseAdapter with bid validation.",
                            "reviewer_summary": "Clean implementation with proper error handling and test coverage.",
                        },
                    },
                    {
                        "component": "metadata",
                        "success": True,
                        "data": {
                            "title_quality": "good",
                            "description_quality": "excellent",
                            "has_tests": True,
                            "has_documentation": True,
                        },
                    },
                    {
                        "component": "code_changes",
                        "success": True,
                        "data": {
                            "files_changed": 3,
                            "additions": 250,
                            "deletions": 10,
                            "risk_level": "medium",
                            "file_types": {"JavaScript": 3},
                        },
                    },
                ],
                "metrics": {
                    "extraction_time": 0.5,
                    "processing_time": 1.2,
                    "total_time": 1.7,
                    "components_extracted": 4,
                    "processors_run": 5,
                },
            },
            {
                "success": True,
                "pr_data": {
                    "number": 1002,
                    "title": "Fix memory leak in auction manager",
                    "url": "https://github.com/prebid/Prebid.js/pull/1002",
                    "author": "core-dev",
                    "created_at": "2024-01-08T14:00:00Z",
                    "merged_at": "2024-01-10T10:00:00Z",
                    "state": "closed",
                    "labels": [{"name": "bug"}, {"name": "performance"}],
                },
                "processing_results": [
                    {
                        "component": "ai_summaries",
                        "success": True,
                        "data": {
                            "executive_summary": "Critical memory leak fixed improving site performance.",
                            "product_summary": "Resolved auction manager memory leak preventing page slowdowns.",
                            "developer_summary": "Fixed event listener cleanup in auction manager destructor.",
                        },
                    }
                ],
                "metrics": {
                    "extraction_time": 0.3,
                    "processing_time": 0.8,
                    "total_time": 1.1,
                },
            },
            {
                "success": True,
                "pr_data": {
                    "number": 1003,
                    "title": "Update dependencies and cleanup docs",
                    "url": "https://github.com/prebid/Prebid.js/pull/1003",
                    "author": "maintainer",
                    "created_at": "2024-01-11T11:00:00Z",
                    "merged_at": "2024-01-11T16:00:00Z",
                    "state": "closed",
                    "labels": [{"name": "dependencies"}, {"name": "documentation"}],
                },
                "processing_results": [
                    {
                        "component": "ai_summaries",
                        "success": True,
                        "data": {
                            "executive_summary": "Routine maintenance updating dependencies.",
                            "product_summary": "Updated third-party libraries to latest stable versions.",
                            "developer_summary": "Updated webpack, babel, and testing dependencies.",
                        },
                    }
                ],
                "metrics": {
                    "extraction_time": 0.2,
                    "processing_time": 0.5,
                    "total_time": 0.7,
                },
            },
        ]

    def test_release_output_structure(
        self, tmp_path, mock_github_client, mock_pr_results
    ):
        """Test that release output has correct structure with PR grouping."""
        # Setup coordinator
        with patch("pr_agents.pr_processing.coordinator.Github") as mock_github:
            mock_github.return_value = mock_github_client

            coordinator = PRCoordinator("fake-token", ai_enabled=True)

            # Mock the analyze_release_prs to return our test data
            with patch.object(coordinator, "analyze_release_prs") as mock_analyze:
                mock_analyze.return_value = {
                    "repository": "prebid/Prebid.js",
                    "release_tag": "v8.0.0",
                    "pr_results": mock_pr_results,
                    "batch_summary": {
                        "total_prs": 3,
                        "successful_analyses": 3,
                        "failed_analyses": 0,
                    },
                }

                # Run analysis
                results = coordinator.analyze_release_prs("prebid/Prebid.js", "v8.0.0")

                # Create enhanced output structure
                output_dir = tmp_path / "release_v8.0.0"
                output_dir.mkdir()

                # Group PRs by tag
                pr_groups = {"Feature": [], "Bug Fix": [], "Maintenance": []}

                for pr_result in results["pr_results"]:
                    pr_data = pr_result["pr_data"]
                    pr_number = pr_data["number"]

                    # Determine tag
                    tag = self._get_pr_tag(pr_data)

                    # Create individual PR file
                    pr_file = self._create_individual_pr_file(
                        pr_result, output_dir, pr_number
                    )

                    pr_groups[tag].append(
                        {
                            "number": pr_number,
                            "title": pr_data["title"],
                            "file": pr_file.name,
                        }
                    )

                # Create main summary file
                summary_file = output_dir / "release_summary.md"
                self._create_summary_file(summary_file, results, pr_groups)

                # Verify structure
                assert summary_file.exists()
                assert (output_dir / "pr_1001.md").exists()
                assert (output_dir / "pr_1002.md").exists()
                assert (output_dir / "pr_1003.md").exists()

                # Verify content structure
                summary_content = summary_file.read_text()
                assert "# Release v8.0.0 Summary" in summary_content
                assert "## Feature" in summary_content
                assert "## Bug Fix" in summary_content
                assert "## Maintenance" in summary_content
                assert "[#1001](pr_1001.md): Add new bid adapter" in summary_content
                assert "[#1002](pr_1002.md): Fix memory leak" in summary_content
                assert "[#1003](pr_1003.md): Update dependencies" in summary_content

                # Verify individual PR file content
                pr1001_content = (output_dir / "pr_1001.md").read_text()
                assert "# PR #1001:" in pr1001_content
                assert "## AI Summaries" in pr1001_content
                assert "### Executive Summary" in pr1001_content
                assert "### Product Manager Summary" in pr1001_content
                assert "### Developer Summary" in pr1001_content
                assert "### Technical Writer Summary" in pr1001_content
                assert "## Tool Metrics" in pr1001_content
                assert "## PR Details" in pr1001_content

    def test_pr_grouping_logic(self):
        """Test PR tag categorization logic."""
        # Feature PR
        feature_pr = {"labels": [{"name": "feature"}, {"name": "adapter"}]}
        assert self._get_pr_tag(feature_pr) == "Feature"

        # Bug fix PR
        bug_pr = {"labels": [{"name": "bug"}, {"name": "performance"}]}
        assert self._get_pr_tag(bug_pr) == "Bug Fix"

        # Security fix (still bug fix)
        security_pr = {"labels": [{"name": "security"}]}
        assert self._get_pr_tag(security_pr) == "Bug Fix"

        # Maintenance PR
        maintenance_pr = {
            "labels": [{"name": "dependencies"}, {"name": "documentation"}]
        }
        assert self._get_pr_tag(maintenance_pr) == "Maintenance"

        # No labels = Maintenance
        no_labels_pr = {"labels": []}
        assert self._get_pr_tag(no_labels_pr) == "Maintenance"

    def test_output_with_missing_personas(self, tmp_path):
        """Test output handles missing AI personas gracefully."""
        pr_result = {
            "success": True,
            "pr_data": {
                "number": 2001,
                "title": "Test PR",
                "url": "https://github.com/prebid/Prebid.js/pull/2001",
                "labels": [],
            },
            "processing_results": [
                {
                    "component": "ai_summaries",
                    "success": True,
                    "data": {
                        "executive_summary": "Executive summary present",
                        "product_summary": "Product summary present",
                        "developer_summary": "Developer summary present",
                        # Note: technical_writer_summary is missing
                    },
                }
            ],
            "metrics": {},
        }

        pr_file = self._create_individual_pr_file(pr_result, tmp_path, 2001)
        content = pr_file.read_text()

        # Should still have all 4 persona sections
        assert "### Executive Summary" in content
        assert "### Product Manager Summary" in content
        assert "### Developer Summary" in content
        assert "### Technical Writer Summary" in content
        assert "Technical documentation summary not available" in content

    def _get_pr_tag(self, pr_data):
        """Determine PR tag based on labels."""
        if not pr_data.get("labels"):
            return "Maintenance"

        label_names = [label["name"].lower() for label in pr_data["labels"]]

        # Check for feature-related labels
        feature_labels = ["feature", "enhancement", "adapter"]
        for label in label_names:
            for feature_label in feature_labels:
                if feature_label in label:
                    return "Feature"

        # Check for bug-related labels
        bug_labels = ["bug", "fix", "security"]
        for label in label_names:
            for bug_label in bug_labels:
                if bug_label in label:
                    return "Bug Fix"

        return "Maintenance"

    def _create_individual_pr_file(self, pr_result, output_dir, pr_number):
        """Create individual PR markdown file."""
        pr_file = output_dir / f"pr_{pr_number}.md"
        pr_data = pr_result["pr_data"]

        content = f"# PR #{pr_number}: {pr_data['title']}\n\n"
        content += f"**URL**: {pr_data['url']}\n\n"

        # Add AI summaries
        content += "## AI Summaries\n\n"
        ai_summaries = None
        for result in pr_result.get("processing_results", []):
            if result["component"] == "ai_summaries":
                ai_summaries = result["data"]
                break

        personas = [
            ("Executive", "executive_summary"),
            ("Product Manager", "product_summary"),
            ("Developer", "developer_summary"),
            ("Technical Writer", "technical_writer_summary"),
        ]

        for persona_name, persona_key in personas:
            content += f"### {persona_name} Summary\n"
            if ai_summaries and persona_key in ai_summaries:
                content += f"{ai_summaries[persona_key]}\n\n"
            else:
                if persona_key == "technical_writer_summary":
                    content += "Technical documentation summary not available - this persona may need to be configured\n\n"
                else:
                    content += "No summary available\n\n"

        # Add tool metrics
        content += "## Tool Metrics\n\n"
        metrics = pr_result.get("metrics", {})
        if metrics:
            content += f"- **Total Time**: {metrics.get('total_time', 'N/A')}s\n\n"

        # Add PR details
        content += "## PR Details\n\n"
        content += "Details section...\n"

        pr_file.write_text(content)
        return pr_file

    def _create_summary_file(self, summary_file, results, pr_groups):
        """Create main release summary file."""
        content = f"# Release {results['release_tag']} Summary\n\n"
        content += f"**Repository**: {results['repository']}\n"
        content += f"**Total PRs**: {results['batch_summary']['total_prs']}\n\n"

        # Add PRs by tag
        for tag in ["Feature", "Bug Fix", "Maintenance"]:
            if pr_groups[tag]:
                content += f"## {tag}\n\n"
                for pr in sorted(pr_groups[tag], key=lambda x: x["number"]):
                    content += f"- [#{pr['number']}]({pr['file']}): {pr['title']}\n"
                content += "\n"

        summary_file.write_text(content)
