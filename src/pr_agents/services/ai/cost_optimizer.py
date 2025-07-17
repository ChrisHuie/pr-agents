"""Cost optimization for AI providers."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger


class ProviderName(Enum):
    """Supported AI providers."""

    GEMINI = "gemini"
    CLAUDE = "claude"
    OPENAI = "openai"


@dataclass
class ProviderCost:
    """Cost information for a provider."""

    provider: ProviderName
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    quality_score: float  # 0-1, subjective quality rating
    speed_score: float  # 0-1, relative speed rating
    max_context_tokens: int


@dataclass
class CostEstimate:
    """Estimated cost for a request."""

    provider: ProviderName
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost: float
    quality_score: float
    speed_score: float


@dataclass
class UsageRecord:
    """Record of actual usage and cost."""

    provider: ProviderName
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cost: float
    persona: str
    pr_url: str


class CostOptimizer:
    """Optimizes AI provider selection based on cost and quality."""

    # Provider costs as of 2024 (example values - should be configurable)
    PROVIDER_COSTS = {
        ProviderName.GEMINI: ProviderCost(
            provider=ProviderName.GEMINI,
            cost_per_1k_input_tokens=0.00025,  # Gemini 1.5 Flash
            cost_per_1k_output_tokens=0.00075,
            quality_score=0.85,
            speed_score=0.95,
            max_context_tokens=1_000_000,
        ),
        ProviderName.CLAUDE: ProviderCost(
            provider=ProviderName.CLAUDE,
            cost_per_1k_input_tokens=0.003,  # Claude 3 Haiku
            cost_per_1k_output_tokens=0.015,
            quality_score=0.95,
            speed_score=0.85,
            max_context_tokens=200_000,
        ),
        ProviderName.OPENAI: ProviderCost(
            provider=ProviderName.OPENAI,
            cost_per_1k_input_tokens=0.0005,  # GPT-3.5-turbo
            cost_per_1k_output_tokens=0.0015,
            quality_score=0.80,
            speed_score=0.90,
            max_context_tokens=16_000,
        ),
    }

    def __init__(
        self, quality_threshold: float = 0.8, budget_limit: float | None = None
    ):
        """Initialize cost optimizer.

        Args:
            quality_threshold: Minimum quality score (0-1)
            budget_limit: Optional daily budget limit in USD
        """
        self.quality_threshold = quality_threshold
        self.budget_limit = budget_limit
        self.usage_history: list[UsageRecord] = []
        self.daily_spend: dict[str, float] = {}  # date -> total spend

    def estimate_tokens(self, text: str, is_input: bool = True) -> int:
        """Estimate token count for text.

        Args:
            text: Text to estimate
            is_input: Whether this is input or output

        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters
        char_count = len(text)
        token_estimate = char_count // 4

        # Add buffer for output
        if not is_input:
            token_estimate = int(token_estimate * 1.2)  # 20% buffer

        return token_estimate

    def get_cost_estimate(
        self, provider: ProviderName, input_text: str, expected_output_tokens: int
    ) -> CostEstimate:
        """Get cost estimate for a provider.

        Args:
            provider: Provider to estimate
            input_text: Input text
            expected_output_tokens: Expected output token count

        Returns:
            Cost estimate
        """
        provider_info = self.PROVIDER_COSTS[provider]
        input_tokens = self.estimate_tokens(input_text)

        # Calculate cost
        input_cost = (input_tokens / 1000) * provider_info.cost_per_1k_input_tokens
        output_cost = (
            expected_output_tokens / 1000
        ) * provider_info.cost_per_1k_output_tokens
        total_cost = input_cost + output_cost

        return CostEstimate(
            provider=provider,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=expected_output_tokens,
            estimated_cost=total_cost,
            quality_score=provider_info.quality_score,
            speed_score=provider_info.speed_score,
        )

    def select_optimal_provider(
        self,
        input_text: str,
        expected_output_tokens: int,
        require_streaming: bool = False,
        require_speed: bool = False,
    ) -> ProviderName:
        """Select optimal provider based on cost and constraints.

        Args:
            input_text: Input text for the request
            expected_output_tokens: Expected output size
            require_streaming: Whether streaming is required
            require_speed: Whether speed is prioritized

        Returns:
            Optimal provider name
        """
        today = datetime.now().strftime("%Y-%m-%d")
        current_spend = self.daily_spend.get(today, 0.0)

        # Get estimates for all providers
        estimates = []
        for provider in ProviderName:
            estimate = self.get_cost_estimate(
                provider, input_text, expected_output_tokens
            )

            # Check quality threshold
            if estimate.quality_score < self.quality_threshold:
                continue

            # Check budget
            if (
                self.budget_limit
                and current_spend + estimate.estimated_cost > self.budget_limit
            ):
                logger.warning(f"Skipping {provider.value} due to budget constraints")
                continue

            estimates.append(estimate)

        if not estimates:
            # Fallback to cheapest if no providers meet criteria
            logger.warning("No providers meet criteria, using cheapest")
            return ProviderName.GEMINI

        # Sort by optimization criteria
        if require_speed:
            # Prioritize speed, then cost
            estimates.sort(key=lambda e: (-e.speed_score, e.estimated_cost))
        elif require_streaming:
            # For streaming, balance speed and quality
            estimates.sort(
                key=lambda e: (-(e.speed_score * e.quality_score), e.estimated_cost)
            )
        else:
            # Default: optimize for cost/quality ratio
            estimates.sort(key=lambda e: e.estimated_cost / e.quality_score)

        selected = estimates[0]
        logger.info(
            f"Selected {selected.provider.value} "
            f"(cost: ${selected.estimated_cost:.4f}, "
            f"quality: {selected.quality_score:.2f})"
        )

        return selected.provider

    def record_usage(
        self,
        provider: ProviderName,
        input_tokens: int,
        output_tokens: int,
        persona: str,
        pr_url: str,
    ) -> None:
        """Record actual usage for tracking.

        Args:
            provider: Provider used
            input_tokens: Actual input tokens
            output_tokens: Actual output tokens
            persona: Persona type
            pr_url: PR URL for reference
        """
        provider_info = self.PROVIDER_COSTS[provider]
        cost = (input_tokens / 1000) * provider_info.cost_per_1k_input_tokens + (
            output_tokens / 1000
        ) * provider_info.cost_per_1k_output_tokens

        record = UsageRecord(
            provider=provider,
            timestamp=datetime.now(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            persona=persona,
            pr_url=pr_url,
        )

        self.usage_history.append(record)

        # Update daily spend
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_spend[today] = self.daily_spend.get(today, 0.0) + cost

        logger.debug(
            f"Recorded usage: {provider.value} "
            f"({input_tokens} in, {output_tokens} out) = ${cost:.4f}"
        )

    def get_usage_report(self, days: int = 7) -> dict[str, Any]:
        """Get usage report for the specified period.

        Args:
            days: Number of days to report

        Returns:
            Usage statistics
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        recent_usage = [u for u in self.usage_history if u.timestamp >= cutoff]

        if not recent_usage:
            return {
                "period_days": days,
                "total_cost": 0.0,
                "total_requests": 0,
                "by_provider": {},
                "by_persona": {},
            }

        # Aggregate statistics
        total_cost = sum(u.cost for u in recent_usage)
        by_provider = {}
        by_persona = {}

        for usage in recent_usage:
            # By provider
            if usage.provider.value not in by_provider:
                by_provider[usage.provider.value] = {
                    "count": 0,
                    "cost": 0.0,
                    "tokens": 0,
                }
            by_provider[usage.provider.value]["count"] += 1
            by_provider[usage.provider.value]["cost"] += usage.cost
            by_provider[usage.provider.value]["tokens"] += (
                usage.input_tokens + usage.output_tokens
            )

            # By persona
            if usage.persona not in by_persona:
                by_persona[usage.persona] = {"count": 0, "cost": 0.0}
            by_persona[usage.persona]["count"] += 1
            by_persona[usage.persona]["cost"] += usage.cost

        return {
            "period_days": days,
            "total_cost": total_cost,
            "total_requests": len(recent_usage),
            "average_cost_per_request": total_cost / len(recent_usage),
            "by_provider": by_provider,
            "by_persona": by_persona,
            "daily_average": total_cost / days,
        }

    def get_provider_rankings(self) -> list[tuple[ProviderName, float]]:
        """Get providers ranked by cost-effectiveness.

        Returns:
            List of (provider, score) tuples, sorted by score
        """
        rankings = []

        for provider, info in self.PROVIDER_COSTS.items():
            # Calculate cost-effectiveness score
            # Lower cost and higher quality = better score
            avg_cost_per_request = (
                info.cost_per_1k_input_tokens * 2 + info.cost_per_1k_output_tokens * 0.5
            ) / 1000  # Assume 2k input, 500 output

            score = info.quality_score / (
                avg_cost_per_request + 0.001
            )  # Avoid division by zero
            rankings.append((provider, score))

        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings
