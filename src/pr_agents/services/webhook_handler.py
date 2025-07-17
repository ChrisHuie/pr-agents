"""Webhook handler for real-time PR analysis."""

import asyncio
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from loguru import logger

from src.pr_agents.pr_processing.coordinator import PRCoordinator


@dataclass
class WebhookConfig:
    """Configuration for webhook handling."""

    secret: str | None = None  # GitHub webhook secret
    allowed_events: list[str] | None = None
    allowed_actions: list[str] | None = None
    process_drafts: bool = False
    auto_analyze: bool = True
    output_path: str = "webhook_results"


@dataclass
class WebhookEvent:
    """Represents a webhook event."""

    event_type: str
    action: str
    payload: dict[str, Any]
    timestamp: datetime
    delivery_id: str | None = None


class WebhookHandler:
    """Handles GitHub webhooks for PR analysis."""

    def __init__(
        self,
        coordinator: PRCoordinator,
        config: WebhookConfig | None = None,
    ):
        """Initialize webhook handler.

        Args:
            coordinator: PR coordinator for analysis
            config: Webhook configuration
        """
        self.coordinator = coordinator
        self.config = config or WebhookConfig()
        self.event_queue: asyncio.Queue[WebhookEvent] = asyncio.Queue()
        self.processing = False
        self.callbacks: dict[str, list[Callable]] = {}

        # Default allowed events
        if self.config.allowed_events is None:
            self.config.allowed_events = [
                "pull_request",
                "pull_request_review",
                "pull_request_review_comment",
            ]

        # Default allowed actions
        if self.config.allowed_actions is None:
            self.config.allowed_actions = [
                "opened",
                "synchronize",
                "ready_for_review",
                "submitted",
            ]

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature.

        Args:
            payload: Raw payload bytes
            signature: Signature from X-Hub-Signature-256 header

        Returns:
            True if signature is valid
        """
        if not self.config.secret:
            logger.warning("No webhook secret configured, skipping verification")
            return True

        expected_signature = "sha256=" + hmac.new(
            self.config.secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    async def handle_webhook(
        self,
        event_type: str,
        payload: dict[str, Any],
        signature: str | None = None,
        delivery_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle incoming webhook.

        Args:
            event_type: GitHub event type
            payload: Event payload
            signature: Optional signature for verification
            delivery_id: GitHub delivery ID

        Returns:
            Response dictionary
        """
        # Verify event type
        if event_type not in self.config.allowed_events:
            logger.info(f"Ignoring event type: {event_type}")
            return {"status": "ignored", "reason": "event_type_not_allowed"}

        # Extract action
        action = payload.get("action", "")
        if action not in self.config.allowed_actions:
            logger.info(f"Ignoring action: {action}")
            return {"status": "ignored", "reason": "action_not_allowed"}

        # Check if PR is draft
        if event_type == "pull_request":
            pr = payload.get("pull_request", {})
            if pr.get("draft", False) and not self.config.process_drafts:
                logger.info("Ignoring draft PR")
                return {"status": "ignored", "reason": "draft_pr"}

        # Create event
        event = WebhookEvent(
            event_type=event_type,
            action=action,
            payload=payload,
            timestamp=datetime.now(),
            delivery_id=delivery_id,
        )

        # Queue for processing
        await self.event_queue.put(event)

        # Start processor if not running
        if not self.processing:
            asyncio.create_task(self._process_events())

        return {
            "status": "queued",
            "event_id": delivery_id,
            "queue_size": self.event_queue.qsize(),
        }

    async def _process_events(self) -> None:
        """Process queued webhook events."""
        self.processing = True

        try:
            while not self.event_queue.empty():
                event = await self.event_queue.get()
                await self._process_single_event(event)
        finally:
            self.processing = False

    async def _process_single_event(self, event: WebhookEvent) -> None:
        """Process a single webhook event.

        Args:
            event: Event to process
        """
        logger.info(f"Processing {event.event_type}:{event.action} event")

        try:
            if event.event_type == "pull_request":
                await self._handle_pull_request(event)
            elif event.event_type == "pull_request_review":
                await self._handle_review(event)
            elif event.event_type == "pull_request_review_comment":
                await self._handle_review_comment(event)

            # Trigger callbacks
            await self._trigger_callbacks(event)

        except Exception as e:
            logger.error(f"Error processing webhook event: {e}")

    async def _handle_pull_request(self, event: WebhookEvent) -> None:
        """Handle pull_request events.

        Args:
            event: Pull request event
        """
        pr = event.payload.get("pull_request", {})
        pr_url = pr.get("html_url", "")

        if not pr_url:
            logger.error("No PR URL in payload")
            return

        if event.action in ["opened", "synchronize", "ready_for_review"]:
            if self.config.auto_analyze:
                logger.info(f"Auto-analyzing PR: {pr_url}")

                # Run analysis asynchronously
                asyncio.create_task(self._analyze_pr_async(pr_url, event))

    async def _analyze_pr_async(self, pr_url: str, event: WebhookEvent) -> None:
        """Analyze PR asynchronously.

        Args:
            pr_url: PR URL to analyze
            event: Original webhook event
        """
        try:
            # Analyze with AI if enabled
            if hasattr(self.coordinator, "ai_enabled") and self.coordinator.ai_enabled:
                results, output_path = await asyncio.to_thread(
                    self.coordinator.analyze_pr_and_save,
                    pr_url,
                    output_path=self.config.output_path,
                    output_format="markdown",
                )
            else:
                results, output_path = await asyncio.to_thread(
                    self.coordinator.analyze_pr_and_save,
                    pr_url,
                    output_path=self.config.output_path,
                    output_format="json",
                )

            logger.info(f"Analysis complete for {pr_url}, saved to {output_path}")

            # Post comment on PR if configured
            if self._should_post_comment(event):
                await self._post_pr_comment(pr_url, results, output_path)

        except Exception as e:
            logger.error(f"Error analyzing PR {pr_url}: {e}")

    async def _handle_review(self, event: WebhookEvent) -> None:
        """Handle pull_request_review events.

        Args:
            event: Review event
        """
        review = event.payload.get("review", {})
        state = review.get("state", "").lower()

        # Log review activity
        pr = event.payload.get("pull_request", {})
        pr_url = pr.get("html_url", "")

        logger.info(f"Review {state} on PR: {pr_url}")

        # Could trigger re-analysis if review requests changes
        if state == "changes_requested" and self.config.auto_analyze:
            # Give time for developer to make changes
            pass

    async def _handle_review_comment(self, event: WebhookEvent) -> None:
        """Handle pull_request_review_comment events.

        Args:
            event: Review comment event
        """
        comment = event.payload.get("comment", {})
        pr = event.payload.get("pull_request", {})

        # Could extract feedback from comments
        comment_body = comment.get("body", "")
        if "@pr-agent" in comment_body or "!analyze" in comment_body:
            pr_url = pr.get("html_url", "")
            logger.info(f"Analysis requested via comment on {pr_url}")
            
            if self.config.auto_analyze:
                asyncio.create_task(self._analyze_pr_async(pr_url, event))

    def _should_post_comment(self, event: WebhookEvent) -> bool:
        """Check if we should post a comment on the PR.

        Args:
            event: Webhook event

        Returns:
            True if comment should be posted
        """
        # For now, don't auto-post comments
        # This could be configurable
        return False

    async def _post_pr_comment(
        self, pr_url: str, results: dict[str, Any], output_path: str
    ) -> None:
        """Post analysis results as PR comment.

        Args:
            pr_url: PR URL
            results: Analysis results
            output_path: Path to full results
        """
        # This would require GitHub API access to post comments
        # Implementation depends on GitHub client setup
        pass

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register callback for event type.

        Args:
            event_type: Event type to listen for
            callback: Async callback function
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)

    async def _trigger_callbacks(self, event: WebhookEvent) -> None:
        """Trigger registered callbacks.

        Args:
            event: Event that occurred
        """
        callbacks = self.callbacks.get(event.event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

    def get_queue_status(self) -> dict[str, Any]:
        """Get current queue status.

        Returns:
            Queue statistics
        """
        return {
            "queue_size": self.event_queue.qsize(),
            "processing": self.processing,
            "allowed_events": self.config.allowed_events,
            "allowed_actions": self.config.allowed_actions,
        }