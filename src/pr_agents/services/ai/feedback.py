"""Feedback system for AI summaries."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class FeedbackEntry:
    """A single feedback entry for a summary."""

    pr_url: str
    persona: str
    summary_text: str
    feedback_type: str  # "rating", "correction", "comment"
    feedback_value: Any  # Rating (1-5), corrected text, or comment
    timestamp: datetime
    model_used: str
    user_id: str | None = None


@dataclass
class FeedbackStats:
    """Statistics about feedback for a persona."""

    persona: str
    total_feedback: int
    average_rating: float | None
    positive_count: int
    negative_count: int
    correction_count: int


class FeedbackStore:
    """Stores and manages feedback for AI summaries."""

    def __init__(self, storage_path: Path | None = None):
        """Initialize feedback store.

        Args:
            storage_path: Path to store feedback data (JSON file)
        """
        self.storage_path = storage_path or Path("data/ai_feedback.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.feedback_entries: list[FeedbackEntry] = []
        self._load_feedback()

    def _load_feedback(self) -> None:
        """Load feedback from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self.feedback_entries = [
                        FeedbackEntry(
                            pr_url=entry["pr_url"],
                            persona=entry["persona"],
                            summary_text=entry["summary_text"],
                            feedback_type=entry["feedback_type"],
                            feedback_value=entry["feedback_value"],
                            timestamp=datetime.fromisoformat(entry["timestamp"]),
                            model_used=entry["model_used"],
                            user_id=entry.get("user_id"),
                        )
                        for entry in data
                    ]
                logger.info(f"Loaded {len(self.feedback_entries)} feedback entries")
            except Exception as e:
                logger.error(f"Error loading feedback: {e}")
                self.feedback_entries = []

    def _save_feedback(self) -> None:
        """Save feedback to storage."""
        try:
            data = [
                {
                    **asdict(entry),
                    "timestamp": entry.timestamp.isoformat(),
                }
                for entry in self.feedback_entries
            ]
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")

    def add_feedback(
        self,
        pr_url: str,
        persona: str,
        summary_text: str,
        feedback_type: str,
        feedback_value: Any,
        model_used: str,
        user_id: str | None = None,
    ) -> None:
        """Add feedback for a summary.

        Args:
            pr_url: PR URL
            persona: Persona type
            summary_text: The generated summary
            feedback_type: Type of feedback
            feedback_value: Feedback value
            model_used: Model that generated the summary
            user_id: Optional user identifier
        """
        entry = FeedbackEntry(
            pr_url=pr_url,
            persona=persona,
            summary_text=summary_text,
            feedback_type=feedback_type,
            feedback_value=feedback_value,
            timestamp=datetime.now(),
            model_used=model_used,
            user_id=user_id,
        )

        self.feedback_entries.append(entry)
        self._save_feedback()

        logger.info(
            f"Added {feedback_type} feedback for {persona} summary "
            f"(PR: {pr_url}, value: {feedback_value})"
        )

    def get_feedback_stats(self, persona: str | None = None) -> dict[str, FeedbackStats]:
        """Get feedback statistics.

        Args:
            persona: Optional persona to filter by

        Returns:
            Dictionary mapping persona to stats
        """
        stats_by_persona: dict[str, dict[str, Any]] = {}

        for entry in self.feedback_entries:
            if persona and entry.persona != persona:
                continue

            if entry.persona not in stats_by_persona:
                stats_by_persona[entry.persona] = {
                    "total": 0,
                    "ratings": [],
                    "positive": 0,
                    "negative": 0,
                    "corrections": 0,
                }

            stats = stats_by_persona[entry.persona]
            stats["total"] += 1

            if entry.feedback_type == "rating":
                rating = int(entry.feedback_value)
                stats["ratings"].append(rating)
                if rating >= 4:
                    stats["positive"] += 1
                elif rating <= 2:
                    stats["negative"] += 1
            elif entry.feedback_type == "correction":
                stats["corrections"] += 1
            elif entry.feedback_type == "comment":
                # Analyze sentiment of comment (simplified)
                comment = str(entry.feedback_value).lower()
                if any(word in comment for word in ["good", "great", "excellent", "helpful"]):
                    stats["positive"] += 1
                elif any(word in comment for word in ["bad", "poor", "wrong", "incorrect"]):
                    stats["negative"] += 1

        # Convert to FeedbackStats
        result = {}
        for persona_name, stats in stats_by_persona.items():
            avg_rating = sum(stats["ratings"]) / len(stats["ratings"]) if stats["ratings"] else None

            result[persona_name] = FeedbackStats(
                persona=persona_name,
                total_feedback=stats["total"],
                average_rating=avg_rating,
                positive_count=stats["positive"],
                negative_count=stats["negative"],
                correction_count=stats["corrections"],
            )

        return result

    def get_corrections(self, persona: str | None = None) -> list[tuple[str, str]]:
        """Get summary corrections for training.

        Args:
            persona: Optional persona to filter by

        Returns:
            List of (original, corrected) text pairs
        """
        corrections = []

        for entry in self.feedback_entries:
            if entry.feedback_type != "correction":
                continue
            if persona and entry.persona != persona:
                continue

            corrections.append((entry.summary_text, entry.feedback_value))

        return corrections

    def get_low_rated_summaries(
        self, threshold: int = 2, persona: str | None = None
    ) -> list[FeedbackEntry]:
        """Get summaries with low ratings.

        Args:
            threshold: Rating threshold (inclusive)
            persona: Optional persona to filter by

        Returns:
            List of low-rated feedback entries
        """
        low_rated = []

        for entry in self.feedback_entries:
            if entry.feedback_type != "rating":
                continue
            if persona and entry.persona != persona:
                continue

            if int(entry.feedback_value) <= threshold:
                low_rated.append(entry)

        return low_rated

    def export_training_data(self, output_path: Path) -> None:
        """Export feedback data for model training.

        Args:
            output_path: Path to export data
        """
        training_data = {
            "corrections": [],
            "positive_examples": [],
            "negative_examples": [],
        }

        for entry in self.feedback_entries:
            example = {
                "persona": entry.persona,
                "summary": entry.summary_text,
                "model": entry.model_used,
                "timestamp": entry.timestamp.isoformat(),
            }

            if entry.feedback_type == "correction":
                training_data["corrections"].append(
                    {
                        **example,
                        "corrected": entry.feedback_value,
                    }
                )
            elif entry.feedback_type == "rating":
                rating = int(entry.feedback_value)
                if rating >= 4:
                    training_data["positive_examples"].append(example)
                elif rating <= 2:
                    training_data["negative_examples"].append(example)

        with open(output_path, "w") as f:
            json.dump(training_data, f, indent=2)

        logger.info(
            f"Exported training data: "
            f"{len(training_data['corrections'])} corrections, "
            f"{len(training_data['positive_examples'])} positive, "
            f"{len(training_data['negative_examples'])} negative"
        )


class FeedbackIntegrator:
    """Integrates feedback to improve summary generation."""

    def __init__(self, feedback_store: FeedbackStore):
        """Initialize feedback integrator.

        Args:
            feedback_store: Store containing feedback data
        """
        self.feedback_store = feedback_store

    def should_adjust_prompt(self, persona: str, model: str) -> bool:
        """Check if prompt should be adjusted based on feedback.

        Args:
            persona: Persona type
            model: Model being used

        Returns:
            True if adjustments are recommended
        """
        stats = self.feedback_store.get_feedback_stats(persona)

        if persona not in stats:
            return False

        persona_stats = stats[persona]

        # Adjust if average rating is low or many corrections
        if persona_stats.average_rating and persona_stats.average_rating < 3.5:
            return True

        if persona_stats.correction_count > 5:
            return True

        if persona_stats.negative_count > persona_stats.positive_count:
            return True

        return False

    def get_prompt_adjustments(self, persona: str) -> dict[str, Any]:
        """Get recommended prompt adjustments.

        Args:
            persona: Persona type

        Returns:
            Dictionary of adjustments
        """
        adjustments = {
            "add_examples": False,
            "emphasize_clarity": False,
            "adjust_length": None,
            "avoid_patterns": [],
        }

        # Get corrections to learn from
        corrections = self.feedback_store.get_corrections(persona)
        if corrections:
            adjustments["add_examples"] = True

            # Analyze common issues
            for original, corrected in corrections[-5:]:  # Last 5 corrections
                if len(corrected) < len(original) * 0.8:
                    adjustments["adjust_length"] = "shorter"
                elif len(corrected) > len(original) * 1.2:
                    adjustments["adjust_length"] = "longer"

        # Check low-rated summaries
        low_rated = self.feedback_store.get_low_rated_summaries(persona=persona)
        if low_rated:
            adjustments["emphasize_clarity"] = True

            # Find common patterns in low-rated summaries
            common_phrases = self._find_common_phrases([e.summary_text for e in low_rated])
            adjustments["avoid_patterns"] = common_phrases

        return adjustments

    def _find_common_phrases(self, texts: list[str], min_length: int = 3) -> list[str]:
        """Find common phrases in texts.

        Args:
            texts: List of texts to analyze
            min_length: Minimum phrase length

        Returns:
            List of common phrases
        """
        from collections import Counter

        # Simple approach: find common word sequences
        all_phrases = []

        for text in texts:
            words = text.lower().split()
            for i in range(len(words) - min_length + 1):
                phrase = " ".join(words[i : i + min_length])
                all_phrases.append(phrase)

        # Count occurrences
        phrase_counts = Counter(all_phrases)

        # Return phrases that appear in multiple texts
        common = [
            phrase for phrase, count in phrase_counts.items() if count >= len(texts) * 0.3
        ]

        return common[:5]  # Top 5 common phrases