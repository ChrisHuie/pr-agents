"""
Reviews extractor - handles reviews, comments, discussions, etc.
"""

from typing import Any

from github.PullRequest import PullRequest

from ..models import Review, ReviewComment, ReviewData
from .base import BaseExtractor


class ReviewsExtractor(BaseExtractor):
    """Extracts review data without any metadata or code context."""

    @property
    def component_name(self) -> str:
        return "reviews"

    def extract(self, pr: PullRequest) -> dict[str, Any] | None:
        """Extract review and discussion data only."""
        try:
            # Get reviews
            reviews = []
            approved_by = []
            changes_requested_by = []

            for review in pr.get_reviews():
                review_obj = Review(
                    author=review.user.login,
                    state=review.state,
                    body=review.body,
                    submitted_at=review.submitted_at,
                )
                reviews.append(review_obj)

                # Track approval status
                if review.state == "APPROVED":
                    approved_by.append(review.user.login)
                elif review.state == "CHANGES_REQUESTED":
                    changes_requested_by.append(review.user.login)

            # Get review comments
            comments = []
            for comment in pr.get_review_comments():
                comment_obj = ReviewComment(
                    author=comment.user.login,
                    body=comment.body,
                    created_at=comment.created_at,
                    updated_at=comment.updated_at,
                    position=comment.position,
                    path=comment.path,
                    commit_sha=comment.commit_id,
                )
                comments.append(comment_obj)

            # Get requested reviewers
            requested_reviewers = [
                reviewer.login for reviewer in pr.requested_reviewers
            ]

            review_data = ReviewData(
                reviews=reviews,
                comments=comments,
                requested_reviewers=requested_reviewers,
                approved_by=list(set(approved_by)),  # Remove duplicates
                changes_requested_by=list(set(changes_requested_by)),
            )

            return review_data.model_dump()

        except Exception:
            return None
