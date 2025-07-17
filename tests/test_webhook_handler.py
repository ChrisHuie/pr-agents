"""Tests for webhook handler."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.pr_agents.pr_processing.coordinator import PRCoordinator
from src.pr_agents.services.webhook_handler import WebhookConfig, WebhookEvent, WebhookHandler


class TestWebhookHandler:
    """Test webhook handling functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_coordinator = Mock(spec=PRCoordinator)
        self.config = WebhookConfig(
            secret="test_secret",
            allowed_events=["pull_request"],
            allowed_actions=["opened", "synchronize"],
        )
        self.handler = WebhookHandler(self.mock_coordinator, self.config)

    def test_signature_verification(self):
        """Test webhook signature verification."""
        payload = b'{"test": "data"}'
        
        # Test with no secret
        handler_no_secret = WebhookHandler(self.mock_coordinator, WebhookConfig())
        assert handler_no_secret.verify_signature(payload, "any_signature")
        
        # Test with correct signature
        import hmac
        import hashlib
        
        correct_sig = "sha256=" + hmac.new(
            b"test_secret",
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        assert self.handler.verify_signature(payload, correct_sig)
        
        # Test with incorrect signature
        assert not self.handler.verify_signature(payload, "sha256=wrong")

    @pytest.mark.asyncio
    async def test_handle_webhook_filtering(self):
        """Test webhook event filtering."""
        # Test ignored event type
        result = await self.handler.handle_webhook(
            event_type="issues",
            payload={"action": "opened"},
        )
        assert result["status"] == "ignored"
        assert result["reason"] == "event_type_not_allowed"
        
        # Test ignored action
        result = await self.handler.handle_webhook(
            event_type="pull_request",
            payload={"action": "closed"},
        )
        assert result["status"] == "ignored"
        assert result["reason"] == "action_not_allowed"
        
        # Test draft PR
        result = await self.handler.handle_webhook(
            event_type="pull_request",
            payload={
                "action": "opened",
                "pull_request": {"draft": True},
            },
        )
        assert result["status"] == "ignored"
        assert result["reason"] == "draft_pr"

    @pytest.mark.asyncio
    async def test_handle_webhook_queuing(self):
        """Test webhook event queuing."""
        # Valid webhook
        result = await self.handler.handle_webhook(
            event_type="pull_request",
            payload={
                "action": "opened",
                "pull_request": {
                    "html_url": "https://github.com/test/pr/1",
                    "draft": False,
                },
            },
            delivery_id="12345",
        )
        
        assert result["status"] == "queued"
        assert result["event_id"] == "12345"
        assert result["queue_size"] == 1

    @pytest.mark.asyncio
    async def test_process_pull_request_event(self):
        """Test processing pull request events."""
        # Mock analyze_pr_and_save
        self.mock_coordinator.analyze_pr_and_save = Mock(
            return_value=({"results": "test"}, "output.json")
        )
        
        # Create event
        event = WebhookEvent(
            event_type="pull_request",
            action="opened",
            payload={
                "pull_request": {
                    "html_url": "https://github.com/test/pr/1",
                },
            },
            timestamp=asyncio.get_event_loop().time(),
        )
        
        # Process event
        await self.handler._process_single_event(event)
        
        # Give async task time to complete
        await asyncio.sleep(0.1)
        
        # Should have triggered analysis
        assert self.mock_coordinator.analyze_pr_and_save.called

    @pytest.mark.asyncio
    async def test_callback_system(self):
        """Test webhook callback registration and triggering."""
        callback_called = False
        callback_event = None
        
        async def test_callback(event):
            nonlocal callback_called, callback_event
            callback_called = True
            callback_event = event
        
        # Register callback
        self.handler.register_callback("pull_request", test_callback)
        
        # Handle webhook
        await self.handler.handle_webhook(
            event_type="pull_request",
            payload={
                "action": "opened",
                "pull_request": {"html_url": "test_url", "draft": False},
            },
        )
        
        # Process queue
        await self.handler._process_events()
        
        # Check callback was triggered
        assert callback_called
        assert callback_event is not None
        assert callback_event.event_type == "pull_request"

    @pytest.mark.asyncio
    async def test_comment_triggered_analysis(self):
        """Test analysis triggered by PR comment."""
        event = WebhookEvent(
            event_type="pull_request_review_comment",
            action="created",
            payload={
                "comment": {
                    "body": "@pr-agent please analyze this PR",
                },
                "pull_request": {
                    "html_url": "https://github.com/test/pr/2",
                },
            },
            timestamp=asyncio.get_event_loop().time(),
        )
        
        # Process event
        await self.handler._process_single_event(event)
        
        # Should log the request (would trigger analysis if auto_analyze=True)
        # In real implementation, this would queue analysis

    def test_queue_status(self):
        """Test getting queue status."""
        status = self.handler.get_queue_status()
        
        assert "queue_size" in status
        assert "processing" in status
        assert "allowed_events" in status
        assert status["allowed_events"] == ["pull_request"]