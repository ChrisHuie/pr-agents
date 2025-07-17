"""Tests for the Accuracy Validator processor."""

from src.pr_agents.pr_processing.processors.accuracy_validator import AccuracyValidator


class TestAccuracyValidator:
    """Test cases for AccuracyValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = AccuracyValidator()

    def test_high_accuracy_pr(self):
        """Test PR with high accuracy between metadata and code."""
        component_data = {
            "metadata_results": {
                "title_analysis": {
                    "title": "Add ExampleBidAdapter module with banner support",
                    "has_prefix": True,
                },
                "description_analysis": {
                    "has_description": True,
                    "description": "This PR adds the ExampleBidAdapter module to support banner ads. The adapter implements all required methods and includes comprehensive tests.",
                    "sections": ["Overview", "Implementation", "Testing"],
                },
            },
            "code_results": {
                "file_analysis": {
                    "files_changed": [
                        {
                            "filename": "modules/exampleBidAdapter.js",
                            "changes": 200,
                            "status": "added",
                        },
                        {
                            "filename": "test/spec/modules/exampleBidAdapter_spec.js",
                            "changes": 150,
                            "status": "added",
                        },
                    ],
                    "total_changes": 350,
                },
                "pattern_analysis": {"patterns_detected": ["adapter", "banner"]},
                "risk_assessment": {"risk_level": "low"},
            },
            "modules_results": {
                "modules": [{"name": "exampleBidAdapter", "type": "bid_adapter"}]
            },
        }

        result = self.validator.process(component_data)

        assert result.success
        assert result.component == "accuracy_validation"

        data = result.data
        assert data["total_score"] > 70  # Good accuracy
        assert data["accuracy_level"] in ["excellent", "good"]
        assert data["files_mentioned_ratio"] >= 0.5
        assert data["modules_mentioned_ratio"] == 1.0

    def test_low_accuracy_pr(self):
        """Test PR with poor accuracy between metadata and code."""
        component_data = {
            "metadata_results": {
                "title_analysis": {"title": "Fix bug", "has_prefix": False},
                "description_analysis": {
                    "has_description": False,
                    "description": "",
                    "sections": [],
                },
            },
            "code_results": {
                "file_analysis": {
                    "files_changed": [
                        {
                            "filename": "modules/importantAdapter.js",
                            "changes": 500,
                            "status": "modified",
                        },
                        {
                            "filename": "src/core.js",
                            "changes": 300,
                            "status": "modified",
                        },
                        {
                            "filename": "test/spec/core_spec.js",
                            "changes": 200,
                            "status": "modified",
                        },
                    ],
                    "total_changes": 1000,
                },
                "pattern_analysis": {
                    "patterns_detected": ["refactor", "optimization", "api_change"]
                },
                "risk_assessment": {"risk_level": "high"},
            },
            "modules_results": {
                "modules": [
                    {"name": "importantAdapter", "type": "bid_adapter"},
                    {"name": "core", "type": "core"},
                ]
            },
        }

        result = self.validator.process(component_data)

        assert result.success

        data = result.data
        assert data["total_score"] < 40  # Low accuracy
        assert data["accuracy_level"] == "poor"
        assert len(data["recommendations"]) > 0
        assert data["files_mentioned_ratio"] == 0.0
        assert data["modules_mentioned_ratio"] == 0.0

    def test_missing_data(self):
        """Test handling of missing required data."""
        component_data = {"metadata_results": {}, "code_results": {}}

        result = self.validator.process(component_data)

        assert not result.success
        assert len(result.errors) > 0

    def test_title_accuracy_scoring(self):
        """Test title accuracy scoring logic."""
        component_data = {
            "metadata_results": {
                "title_analysis": {
                    "title": "Add SevioBidAdapter for banner and native ads",
                    "has_prefix": True,
                },
                "description_analysis": {
                    "has_description": True,
                    "description": "Added new adapter",
                    "sections": [],
                },
            },
            "code_results": {
                "file_analysis": {
                    "files_changed": [
                        {
                            "filename": "modules/sevioBidAdapter.js",
                            "changes": 250,
                            "status": "added",
                        }
                    ],
                    "total_changes": 250,
                },
                "pattern_analysis": {"patterns_detected": []},
                "risk_assessment": {"risk_level": "low"},
            },
            "modules_results": {
                "modules": [{"name": "sevioBidAdapter", "type": "bid_adapter"}]
            },
        }

        result = self.validator.process(component_data)

        assert result.success
        components = result.data["component_scores"]

        # Title should have high accuracy (mentions file and module)
        assert components["title_accuracy"] > 70

    def test_recommendations_generation(self):
        """Test that recommendations are generated for low scores."""
        component_data = {
            "metadata_results": {
                "title_analysis": {"title": "Update code", "has_prefix": False},
                "description_analysis": {
                    "has_description": True,
                    "description": "Made some changes",
                    "sections": [],
                },
            },
            "code_results": {
                "file_analysis": {
                    "files_changed": [
                        {
                            "filename": "modules/criticalAdapter.js",
                            "changes": 400,
                            "status": "modified",
                        }
                    ],
                    "total_changes": 400,
                },
                "pattern_analysis": {"patterns_detected": ["api_change"]},
                "risk_assessment": {"risk_level": "medium"},
            },
        }

        result = self.validator.process(component_data)

        assert result.success
        recommendations = result.data["recommendations"]

        assert len(recommendations) > 0

        # Should have recommendations for vague title
        title_recs = [r for r in recommendations if r["component"] == "title"]
        assert len(title_recs) > 0

        # Should have recommendations for poor description
        desc_recs = [r for r in recommendations if r["component"] == "description"]
        assert len(desc_recs) > 0

    def test_fuzzy_matching(self):
        """Test fuzzy matching for file and module names."""
        component_data = {
            "metadata_results": {
                "title_analysis": {
                    "title": "Fix issues in example adapter",  # Uses "example" not "exampleBid"
                    "has_prefix": True,
                },
                "description_analysis": {
                    "has_description": True,
                    "description": "Fixed bugs in the example bid adapter module",
                    "sections": [],
                },
            },
            "code_results": {
                "file_analysis": {
                    "files_changed": [
                        {
                            "filename": "modules/exampleBidAdapter.js",
                            "changes": 100,
                            "status": "modified",
                        }
                    ],
                    "total_changes": 100,
                },
                "pattern_analysis": {"patterns_detected": []},
                "risk_assessment": {"risk_level": "low"},
            },
            "modules_results": {
                "modules": [{"name": "exampleBidAdapter", "type": "bid_adapter"}]
            },
        }

        result = self.validator.process(component_data)

        assert result.success

        # Should still recognize the match despite slight differences
        assert result.data["files_mentioned_ratio"] > 0
        assert result.data["modules_mentioned_ratio"] > 0

    def test_completeness_scoring(self):
        """Test completeness scoring for unmentioned changes."""
        component_data = {
            "metadata_results": {
                "title_analysis": {"title": "Update adapter", "has_prefix": False},
                "description_analysis": {
                    "has_description": True,
                    "description": "Updated the adapter code",
                    "sections": [],
                },
            },
            "code_results": {
                "file_analysis": {
                    "files_changed": [
                        {
                            "filename": "modules/adapter1.js",
                            "changes": 200,
                            "status": "modified",
                        },
                        {
                            "filename": "modules/adapter2.js",
                            "changes": 150,
                            "status": "modified",
                        },
                        {
                            "filename": "src/core.js",
                            "changes": 300,
                            "status": "modified",
                        },  # Significant but unmentioned
                    ],
                    "total_changes": 650,
                },
                "pattern_analysis": {"patterns_detected": []},
                "risk_assessment": {"risk_level": "medium"},
            },
        }

        result = self.validator.process(component_data)

        assert result.success
        components = result.data["component_scores"]

        # Completeness should be reduced due to unmentioned significant files
        assert components["completeness"] <= 70

    def test_specificity_scoring(self):
        """Test technical specificity scoring."""
        # Test with technical terms
        technical_data = {
            "metadata_results": {
                "title_analysis": {
                    "title": "Implement new API endpoint for adapter interface",
                    "has_prefix": True,
                },
                "description_analysis": {
                    "has_description": True,
                    "description": "Refactored the adapter module to implement the new API interface with optimized algorithm",
                    "sections": [],
                },
            },
            "code_results": {
                "file_analysis": {"files_changed": [], "total_changes": 0},
                "pattern_analysis": {"patterns_detected": []},
                "risk_assessment": {"risk_level": "low"},
            },
        }

        result = self.validator.process(technical_data)
        assert result.success
        assert result.data["component_scores"]["specificity"] > 70

        # Test with vague terms
        vague_data = {
            "metadata_results": {
                "title_analysis": {
                    "title": "Fix stuff and update things",
                    "has_prefix": False,
                },
                "description_analysis": {
                    "has_description": True,
                    "description": "Changed some code to improve it",
                    "sections": [],
                },
            },
            "code_results": {
                "file_analysis": {"files_changed": [], "total_changes": 0},
                "pattern_analysis": {"patterns_detected": []},
                "risk_assessment": {"risk_level": "low"},
            },
        }

        result = self.validator.process(vague_data)
        assert result.success
        assert result.data["component_scores"]["specificity"] < 30
