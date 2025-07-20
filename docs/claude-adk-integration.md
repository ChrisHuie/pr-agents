# Claude ADK Integration

## Overview

The PR Agents project now supports Claude-powered agent workflows for generating AI summaries. This integration provides an alternative to the Google ADK implementation, allowing you to use Anthropic's Claude models within the same agent framework.

## Features

- **Three Persona Agents**: Executive, Product Manager, and Developer summaries
- **Concurrent Processing**: All personas run in parallel for faster results
- **Claude-3 Opus**: Uses Claude's most capable model for high-quality summaries
- **Seamless Integration**: Works with existing PR analysis pipeline

## Configuration

### Environment Variables

```bash
# Enable Claude ADK
AI_PROVIDER=claude-adk

# Set your Anthropic API key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional: Configure other AI settings
AI_CACHE_TTL=86400  # Cache TTL in seconds
AI_MAX_RETRIES=3    # Maximum retry attempts
AI_TIMEOUT=30       # Request timeout in seconds
```

### Usage

```python
from src.pr_agents.pr_processing.coordinator import PRCoordinator

# Initialize with Claude ADK enabled
coordinator = PRCoordinator(
    github_token="your-github-token",
    ai_enabled=True  # Make sure AI is enabled
)

# The AI_PROVIDER env var will automatically select Claude ADK
# Analyze a PR with Claude-powered summaries
results = coordinator.analyze_pr("https://github.com/owner/repo/pull/123")

# Access Claude-generated summaries
print(results["ai_summaries"]["executive_summary"])
print(results["ai_summaries"]["product_summary"])
print(results["ai_summaries"]["developer_summary"])
```

## Architecture

### Components

1. **ClaudeADKService**: Main service orchestrating Claude agents
2. **ClaudeAgent**: Base class for persona-specific agents
3. **ClaudeAgentOrchestrator**: Manages concurrent agent execution
4. **Persona Agents**:
   - `ClaudeExecutiveAgent`: Business-focused summaries (150 tokens)
   - `ClaudeProductAgent`: Feature and capability summaries (300 tokens)
   - `ClaudeDeveloperAgent`: Technical implementation details (500 tokens)

### Integration Flow

```
PRCoordinator (ai_enabled=True)
    ↓
AIProcessor (registered when AI_PROVIDER=claude-adk)
    ↓
ClaudeADKService
    ↓
ClaudeAgentOrchestrator
    ↓
Claude Persona Agents (Executive, Product, Developer)
    ↓
Anthropic Claude API
```

## Prompt Engineering

Each persona agent uses tailored prompts that include:

- **Repository Context**: Type, description, module patterns
- **PR Metadata**: Title, description, file counts
- **Change Analysis**: Categories, languages, test coverage
- **Persona-Specific Focus**: Business impact, features, or technical details

## Example Output

### Executive Summary
"Integrated payment processing module with Stripe API, enabling subscription management and reducing payment failures by 30% through smart retry logic."

### Product Manager Summary
"Added Stripe payment integration supporting credit cards, ACH transfers, and digital wallets. Features automatic retry for failed payments, webhook handling for real-time updates, and comprehensive subscription lifecycle management including upgrades, downgrades, and cancellations. Includes admin dashboard for payment monitoring and customer self-service portal."

### Developer Summary
"Implemented StripePaymentProcessor class extending BasePaymentGateway interface in src/payments/stripe.py. Added webhook handlers for payment_intent.succeeded and subscription.updated events using async processing. Integrated with existing OrderService through dependency injection. Uses stripe-python@5.5.0 with custom retry logic implementing exponential backoff. Added 45 unit tests covering payment flows, webhook validation, and error scenarios. Implements idempotency keys for safe request retries and includes rate limiting (100 req/sec) to comply with Stripe API limits."

## Comparison with Google ADK

| Feature | Google ADK | Claude ADK |
|---------|------------|------------|
| Provider | Google Gemini | Anthropic Claude |
| Model | Gemini Pro | Claude-3 Opus |
| Agent Framework | Google's ADK | Custom implementation |
| Personas | 3 (Exec, PM, Dev) | 3 (Exec, PM, Dev) |
| Token Limits | Same | Same |
| Caching | Built-in | Via AI Service layer |

## Error Handling

The Claude ADK integration includes robust error handling:

- **API Failures**: Returns error summaries with 0.0 confidence
- **Missing API Key**: Logs error and gracefully degrades
- **Timeout Handling**: Configurable timeout with automatic retry
- **Partial Failures**: Individual persona failures don't block others

## Testing

Run tests for Claude ADK integration:

```bash
# Run all Claude ADK tests
uv run pytest tests/unit/services/ai/test_claude_adk_service.py

# Run with coverage
uv run pytest tests/unit/services/ai/test_claude_adk_service.py --cov=src.pr_agents.services.ai.claude_adk_service
```

## Future Enhancements

- **Custom Personas**: Add domain-specific personas (Security, QA, etc.)
- **Model Selection**: Support for Claude-3 Sonnet and Haiku
- **Fine-tuning**: Persona-specific prompt optimization
- **Streaming**: Real-time summary generation
- **Multi-PR Batch**: Concurrent analysis of multiple PRs