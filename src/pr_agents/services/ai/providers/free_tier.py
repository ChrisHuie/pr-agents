"""Free tier provider implementations."""

import asyncio
import os
import time
from typing import Any

from loguru import logger

from src.pr_agents.services.ai.providers.base import BaseLLMProvider, LLMResponse


class FreeTierGeminiProvider(BaseLLMProvider):
    """Google Gemini free tier provider.

    Note: Google's free tier still requires an API key, but it's free to obtain
    from Google AI Studio and includes 60 requests per minute.
    """

    def __init__(self, model_name: str = "gemini-1.5-flash", **kwargs):
        """Initialize free tier Gemini provider.

        Args:
            model_name: Model to use (gemini-1.5-flash has generous free tier)
            **kwargs: Additional configuration
        """
        # Check for free API key
        api_key = os.getenv("GEMINI_FREE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
        super().__init__(api_key, **kwargs)
        self.model_name = model_name
        self._rate_limit_delay = 1.0  # 1 second between requests for free tier
        self._last_request_time = 0
        self._initialize_free_tier()

    def _initialize_free_tier(self):
        """Initialize Gemini for free tier usage."""
        try:
            if self.api_key:
                import google.generativeai as genai

                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                self._available = True
                logger.info(
                    f"Gemini free tier initialized with model {self.model_name}"
                )
            else:
                # No API key available
                self._available = False
                self.model = None
        except Exception as e:
            logger.warning(f"Free tier Gemini initialization failed: {e}")
            self._available = False
            self.model = None

    @property
    def is_available(self) -> bool:
        """Check if free tier is available."""
        return self._available

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        **kwargs,
    ) -> LLMResponse:
        """Generate text using free tier with rate limiting."""
        if not self._available:
            raise Exception("Free tier Gemini is not available - API key required")

        # Apply rate limiting for free tier
        await self._apply_rate_limit()

        # Limit token usage for free tier
        max_tokens = min(max_tokens, 1000)  # Cap at 1000 tokens

        start_time = time.time()

        try:
            from google.generativeai.types import GenerationConfig

            # Create generation config
            generation_config = GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                candidate_count=1,
            )

            # Generate response
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=generation_config,
                ),
            )

            # Extract response
            if response.candidates:
                content = response.candidates[0].content.parts[0].text
            else:
                content = ""

            response_time_ms = int((time.time() - start_time) * 1000)
            estimated_tokens = len(prompt.split()) + len(content.split())

            return LLMResponse(
                content=content,
                model=self.model_name,
                tokens_used=estimated_tokens,
                response_time_ms=response_time_ms,
                finish_reason="stop",
                metadata={"tier": "free", "rate_limited": True},
            )

        except Exception as e:
            raise Exception(f"Gemini free tier error: {str(e)}") from e

    async def _apply_rate_limit(self):
        """Apply rate limiting for free tier (60 requests/minute)."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self._rate_limit_delay:
            wait_time = self._rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self._last_request_time = time.time()

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "gemini-free"
    
    async def health_check(self) -> dict[str, Any]:
        """Check health of free tier provider."""
        return {
            "healthy": self._available,
            "provider": self.name,
            "model": self.model_name,
            "tier": "free",
            "rate_limited": True
        }
    
    @property
    def supports_streaming(self) -> bool:
        """Free tier supports streaming."""
        return True


class BasicSummaryProvider(BaseLLMProvider):
    """Fallback provider that generates basic summaries without AI."""

    def __init__(self, **kwargs):
        """Initialize basic summary provider."""
        super().__init__("", **kwargs)
        self.model_name = "basic-summary"

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        **kwargs,
    ) -> LLMResponse:
        """Generate basic summary without AI."""
        start_time = time.time()

        # Extract key information from prompt
        summary = self._generate_basic_summary(
            prompt, kwargs.get("persona", "executive")
        )

        return LLMResponse(
            content=summary,
            model=self.model_name,
            tokens_used=len(summary.split()),
            response_time_ms=int((time.time() - start_time) * 1000),
            finish_reason="complete",
            metadata={"type": "basic", "ai_used": False},
        )

    def _generate_basic_summary(self, prompt: str, persona: str) -> str:
        """Generate a basic summary based on the prompt content."""
        # Extract basic information from the prompt
        lines = prompt.split("\n")

        # Try to find key information
        files_changed = 0
        additions = 0
        deletions = 0
        pr_title = ""

        for line in lines:
            if "Files Changed:" in line:
                try:
                    files_changed = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
            elif "Lines Added:" in line:
                try:
                    additions = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
            elif "Lines Deleted:" in line:
                try:
                    deletions = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
            elif "PR Title:" in line:
                pr_title = line.split(":", 1)[-1].strip()

        # Generate persona-specific summary
        if persona == "executive":
            return f"PR '{pr_title}' modifies {files_changed} files with {additions} additions and {deletions} deletions."
        elif persona == "product":
            return f"PR '{pr_title}' updates {files_changed} files. Total changes: {additions + deletions} lines ({additions} added, {deletions} removed)."
        else:  # developer
            return f"PR '{pr_title}' changes {files_changed} files: +{additions}/-{deletions} lines. Review the specific file changes for implementation details."

    async def health_check(self) -> dict[str, Any]:
        """Health check for basic provider."""
        return {
            "healthy": True,
            "provider": self.name,
            "model": self.model_name,
            "response_time_ms": 0,
        }

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "basic"

    @property
    def supports_streaming(self) -> bool:
        """Basic provider doesn't support streaming."""
        return False
