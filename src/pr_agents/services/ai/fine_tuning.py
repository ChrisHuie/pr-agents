"""Fine-tuning support for AI models."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class ModelVersion:
    """Represents a fine-tuned model version."""

    model_id: str
    base_model: str
    version: str
    training_date: str
    metrics: dict[str, float]
    description: str
    is_active: bool = False


@dataclass
class FineTuneConfig:
    """Configuration for fine-tuning."""

    base_model: str
    training_data_path: Path
    validation_split: float = 0.2
    epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 2e-5
    repository_type: str | None = None
    custom_prompts: dict[str, str] | None = None


class FineTuningManager:
    """Manages fine-tuned models and configurations."""

    def __init__(self, config_path: Path | None = None):
        """Initialize fine-tuning manager.

        Args:
            config_path: Path to store model configurations
        """
        self.config_path = config_path or Path("config/fine_tuned_models.json")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.models: dict[str, ModelVersion] = {}
        self.custom_prompts: dict[str, dict[str, str]] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """Load model configurations from disk."""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = json.load(f)

                # Load model versions
                for model_data in data.get("models", []):
                    model = ModelVersion(**model_data)
                    self.models[model.model_id] = model

                # Load custom prompts
                self.custom_prompts = data.get("custom_prompts", {})

                logger.info(f"Loaded {len(self.models)} fine-tuned models")
            except Exception as e:
                logger.error(f"Error loading fine-tuning configs: {e}")

    def _save_configs(self) -> None:
        """Save model configurations to disk."""
        try:
            data = {
                "models": [
                    {
                        "model_id": m.model_id,
                        "base_model": m.base_model,
                        "version": m.version,
                        "training_date": m.training_date,
                        "metrics": m.metrics,
                        "description": m.description,
                        "is_active": m.is_active,
                    }
                    for m in self.models.values()
                ],
                "custom_prompts": self.custom_prompts,
            }
            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving fine-tuning configs: {e}")

    def register_model(
        self,
        model_id: str,
        base_model: str,
        version: str,
        training_date: str,
        metrics: dict[str, float],
        description: str,
    ) -> ModelVersion:
        """Register a new fine-tuned model.

        Args:
            model_id: Unique model identifier
            base_model: Base model used for fine-tuning
            version: Model version
            training_date: When model was trained
            metrics: Training/evaluation metrics
            description: Model description

        Returns:
            Registered ModelVersion
        """
        model = ModelVersion(
            model_id=model_id,
            base_model=base_model,
            version=version,
            training_date=training_date,
            metrics=metrics,
            description=description,
            is_active=False,
        )

        self.models[model_id] = model
        self._save_configs()

        logger.info(f"Registered fine-tuned model: {model_id}")
        return model

    def activate_model(self, model_id: str, persona: str | None = None) -> None:
        """Activate a fine-tuned model.

        Args:
            model_id: Model to activate
            persona: Optional persona to activate for
        """
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")

        # Deactivate other models for the same base model
        model = self.models[model_id]
        for other_model in self.models.values():
            if other_model.base_model == model.base_model:
                other_model.is_active = False

        # Activate the selected model
        model.is_active = True
        self._save_configs()

        logger.info(f"Activated model {model_id}")

    def get_active_model(self, base_model: str) -> ModelVersion | None:
        """Get active model for a base model.

        Args:
            base_model: Base model name

        Returns:
            Active ModelVersion or None
        """
        for model in self.models.values():
            if model.base_model == base_model and model.is_active:
                return model
        return None

    def add_custom_prompt(
        self,
        repository_type: str,
        persona: str,
        prompt_template: str,
    ) -> None:
        """Add custom prompt for a repository type and persona.

        Args:
            repository_type: Type of repository (e.g., "prebid", "android")
            persona: Persona type
            prompt_template: Custom prompt template
        """
        if repository_type not in self.custom_prompts:
            self.custom_prompts[repository_type] = {}

        self.custom_prompts[repository_type][persona] = prompt_template
        self._save_configs()

        logger.info(f"Added custom prompt for {repository_type}/{persona}")

    def get_custom_prompt(
        self,
        repository_type: str,
        persona: str,
    ) -> str | None:
        """Get custom prompt for a repository type and persona.

        Args:
            repository_type: Type of repository
            persona: Persona type

        Returns:
            Custom prompt template or None
        """
        return self.custom_prompts.get(repository_type, {}).get(persona)

    def prepare_training_data(
        self,
        feedback_store: Any,
        output_path: Path,
        min_rating: int = 4,
    ) -> dict[str, Any]:
        """Prepare training data from feedback.

        Args:
            feedback_store: Feedback store instance
            output_path: Path to save training data
            min_rating: Minimum rating for positive examples

        Returns:
            Training data statistics
        """
        training_data = {
            "examples": [],
            "stats": {
                "total": 0,
                "by_persona": {},
                "by_rating": {},
            },
        }

        # Get all feedback entries
        for entry in feedback_store.feedback_entries:
            if entry.feedback_type == "rating":
                rating = int(entry.feedback_value)

                # Create training example
                example = {
                    "prompt": f"Generate a {entry.persona} summary for this PR",
                    "completion": entry.summary_text,
                    "rating": rating,
                    "persona": entry.persona,
                }

                # Only include good examples for training
                if rating >= min_rating:
                    training_data["examples"].append(example)

                # Update stats
                training_data["stats"]["total"] += 1
                if entry.persona not in training_data["stats"]["by_persona"]:
                    training_data["stats"]["by_persona"][entry.persona] = 0
                training_data["stats"]["by_persona"][entry.persona] += 1

                if str(rating) not in training_data["stats"]["by_rating"]:
                    training_data["stats"]["by_rating"][str(rating)] = 0
                training_data["stats"]["by_rating"][str(rating)] += 1

            elif entry.feedback_type == "correction":
                # Use corrections as training examples
                example = {
                    "prompt": f"Generate a {entry.persona} summary for this PR",
                    "completion": entry.feedback_value,  # The corrected version
                    "rating": 5,  # Corrections are considered perfect
                    "persona": entry.persona,
                }
                training_data["examples"].append(example)

        # Save training data
        with open(output_path, "w") as f:
            json.dump(training_data, f, indent=2)

        logger.info(
            f"Prepared {len(training_data['examples'])} training examples "
            f"from {training_data['stats']['total']} feedback entries"
        )

        return training_data["stats"]

    def get_model_comparison(self) -> list[dict[str, Any]]:
        """Get comparison of all registered models.

        Returns:
            List of model comparisons
        """
        comparisons = []

        # Group by base model
        by_base_model: dict[str, list[ModelVersion]] = {}
        for model in self.models.values():
            if model.base_model not in by_base_model:
                by_base_model[model.base_model] = []
            by_base_model[model.base_model].append(model)

        # Create comparisons
        for base_model, versions in by_base_model.items():
            comparison = {
                "base_model": base_model,
                "versions": [
                    {
                        "model_id": v.model_id,
                        "version": v.version,
                        "is_active": v.is_active,
                        "metrics": v.metrics,
                        "training_date": v.training_date,
                    }
                    for v in sorted(versions, key=lambda x: x.version, reverse=True)
                ],
            }
            comparisons.append(comparison)

        return comparisons


class PromptOptimizer:
    """Optimizes prompts based on feedback and performance."""

    def __init__(self, fine_tuning_manager: FineTuningManager):
        """Initialize prompt optimizer.

        Args:
            fine_tuning_manager: Manager for fine-tuned models
        """
        self.manager = fine_tuning_manager

    def optimize_prompt(
        self,
        base_prompt: str,
        persona: str,
        repository_type: str,
        feedback_data: dict[str, Any],
    ) -> str:
        """Optimize prompt based on feedback and repository type.

        Args:
            base_prompt: Original prompt
            persona: Persona type
            repository_type: Type of repository
            feedback_data: Feedback statistics

        Returns:
            Optimized prompt
        """
        # Check for custom prompt
        custom_prompt = self.manager.get_custom_prompt(repository_type, persona)
        if custom_prompt:
            return custom_prompt

        # Apply optimizations based on feedback
        optimized = base_prompt

        # If feedback suggests shorter summaries
        if feedback_data.get("adjust_length") == "shorter":
            optimized += (
                "\n\nIMPORTANT: Keep the summary concise and focused on key points."
            )

        # If feedback suggests more clarity
        if feedback_data.get("emphasize_clarity"):
            optimized += (
                "\n\nFocus on clarity and avoid technical jargon when possible."
            )

        # Repository-specific adjustments
        if repository_type == "prebid":
            optimized += "\n\nNote: This is a Prebid.js repository. Focus on bid adapters, modules, and advertising technology."
        elif repository_type == "android":
            optimized += "\n\nNote: This is an Android repository. Focus on Android-specific patterns and components."

        return optimized
