# AI Features Documentation

## Overview

The PR Agents AI service provides advanced features for intelligent PR analysis, including cost management, user feedback integration, and real-time processing capabilities. These features are optional and can be configured based on your needs.

## Table of Contents

1. [Cost Management](#cost-management)
2. [Feedback System](#feedback-system)
3. [Streaming Generation](#streaming-generation)
4. [Custom Models](#custom-models)
5. [Real-time Analysis](#real-time-analysis)
6. [Configuration](#configuration)
7. [Usage Examples](#usage-examples)

## Cost Management

Automatically optimize AI provider selection to balance cost and quality for your PR analysis needs.

### Features

- **Smart Provider Selection**: Automatically chooses between Gemini, Claude, and OpenAI based on cost and quality
- **Budget Control**: Set daily spending limits
- **Usage Analytics**: Monitor costs per persona and provider
- **Detailed Reports**: Generate comprehensive usage reports

### Configuration

```python
# Environment variables
export AI_DAILY_BUDGET_USD="10.0"  # Daily budget limit

# In code
from src.pr_agents.services.ai.service import AIService

service = AIService(enable_cost_optimization=True)
```

### Usage

```python
# Get cost report
report = service.get_cost_report(days=7)
print(f"Total spent: ${report['total_cost']:.2f}")
print(f"By provider: {report['by_provider']}")

# Get provider rankings
from src.pr_agents.services.ai.cost_optimizer import CostOptimizer
optimizer = CostOptimizer()
rankings = optimizer.get_provider_rankings()
```

## Feedback System

Improve summary quality over time by collecting and learning from user feedback.

### Features

- **Ratings**: Rate summaries on a 1-5 star scale
- **Corrections**: Provide improved versions of summaries
- **Comments**: Add free-form feedback
- **Automatic Learning**: Prompts adapt based on feedback patterns

### Usage

```python
# Add rating
service.add_feedback(
    pr_url="https://github.com/owner/repo/pull/123",
    persona="executive",
    summary="Generated summary text...",
    feedback_type="rating",
    feedback_value=5
)

# Submit correction
service.add_feedback(
    pr_url="https://github.com/owner/repo/pull/124",
    persona="developer",
    summary="Original summary",
    feedback_type="correction",
    feedback_value="Improved summary with better technical details"
)

# View statistics
stats = service.get_feedback_stats()
print(f"Executive avg rating: {stats['executive']['average_rating']}")
```

### Export Training Data

```python
from src.pr_agents.services.ai.feedback import FeedbackStore

store = FeedbackStore()
store.export_training_data(Path("training_data.json"))
```

## Streaming Generation

Generate summaries in real-time with streaming support (currently in beta).

### Features

- **Real-time Output**: View summaries as they're generated
- **Parallel Generation**: Stream all personas simultaneously
- **Progress Monitoring**: Track generation progress

### Usage

```python
# Stream summaries
async for persona, chunk in service.generate_summaries_streaming(
    code_changes, repo_context, pr_metadata
):
    print(f"{persona}: {chunk}", end="", flush=True)
```

## Custom Models

Manage custom models and prompts for specific repository types.

### Features

- **Model Management**: Track and version custom models
- **Repository-Specific Prompts**: Customize prompts per repository type
- **Performance Comparison**: Compare models side-by-side
- **Training Data Export**: Convert feedback to training data

### Configuration

```python
from src.pr_agents.services.ai.fine_tuning import FineTuningManager

manager = FineTuningManager()

# Register a custom model
manager.register_model(
    model_id="custom-prebid-v1",
    base_model="gemini",
    version="1.0.0",
    training_date="2024-01-15",
    metrics={"accuracy": 0.95, "loss": 0.05},
    description="Optimized for Prebid.js repositories"
)

# Activate the model
manager.activate_model("custom-prebid-v1")

# Add repository-specific prompt
manager.add_custom_prompt(
    repository_type="prebid",
    persona="executive",
    prompt_template="""
    You are summarizing a Prebid.js pull request for executives.
    Focus on business impact and advertiser benefits.
    Keep it under 2 sentences.
    
    {base_prompt}
    """
)
```

### Training Data Preparation

```python
# Convert feedback to training data
stats = manager.prepare_training_data(
    feedback_store=service.feedback_store,
    output_path=Path("training_data.json"),
    min_rating=4  # Only use highly-rated examples
)
```

## Real-time Analysis

Enable automatic PR analysis triggered by GitHub webhooks.

### Features

- **Automatic Triggers**: Analyze PRs when opened or updated
- **Event Filtering**: Configure which events trigger analysis
- **Secure Webhooks**: GitHub signature verification
- **Comment Commands**: Trigger analysis via PR comments

### Setup

```python
from src.pr_agents.services.webhook_handler import WebhookHandler, WebhookConfig
from src.pr_agents.pr_processing.coordinator import PRCoordinator

# Configure webhook handler
config = WebhookConfig(
    secret="your-webhook-secret",
    allowed_events=["pull_request", "pull_request_review_comment"],
    allowed_actions=["opened", "synchronize", "ready_for_review"],
    process_drafts=False,
    auto_analyze=True,
    output_path="webhook_results"
)

coordinator = PRCoordinator(github_token="your-token", ai_enabled=True)
handler = WebhookHandler(coordinator, config)

# Handle incoming webhook
result = await handler.handle_webhook(
    event_type=request.headers["X-GitHub-Event"],
    payload=request.json(),
    signature=request.headers.get("X-Hub-Signature-256"),
    delivery_id=request.headers.get("X-GitHub-Delivery")
)
```

### GitHub Setup

1. Go to Settings → Webhooks in your repository
2. Add webhook URL: `https://your-server.com/webhook`
3. Content type: `application/json`
4. Secret: Your webhook secret
5. Events: Select "Pull requests" and "Pull request review comments"

### Comment Triggers

Users can trigger analysis by commenting:
- `@pr-agent analyze` - Run full analysis
- `!analyze` - Alternative trigger

## Configuration

### Environment Variables

```bash
# AI Provider
export AI_PROVIDER="gemini"  # Options: gemini, claude, openai

# API Keys
export GEMINI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export OPENAI_API_KEY="your-key"

# Cost Control
export AI_DAILY_BUDGET_USD="10.0"

# Caching
export AI_CACHE_TTL=86400  # 24 hours

# Webhooks
export WEBHOOK_SECRET="your-secret"
```

### Programmatic Configuration

```python
from src.pr_agents.services.ai.config import AIConfig

config = AIConfig(
    provider="gemini",
    cache_enabled=True,
    cache_ttl_seconds=86400,
    max_retries=3,
    persona_configs={
        "executive": PersonaConfig(max_tokens=150, temperature=0.7),
        "product": PersonaConfig(max_tokens=300, temperature=0.7),
        "developer": PersonaConfig(max_tokens=500, temperature=0.8),
    }
)

service = AIService(config=config)
```

## Usage Examples

### Complete Integration Example

```python
import asyncio
from pathlib import Path
from src.pr_agents.pr_processing.coordinator import PRCoordinator
from src.pr_agents.services.webhook_handler import WebhookHandler, WebhookConfig

async def main():
    # Initialize with AI features
    coordinator = PRCoordinator(
        github_token="your-token",
        ai_enabled=True
    )
    
    # Analyze a PR
    results = await coordinator.analyze_pr_with_ai(
        "https://github.com/prebid/Prebid.js/pull/12345"
    )
    
    # View summaries
    print("Executive:", results["ai_summaries"]["executive_summary"])
    print("Product:", results["ai_summaries"]["product_summary"])
    print("Developer:", results["ai_summaries"]["developer_summary"])
    
    # Provide feedback
    coordinator.ai_service.add_feedback(
        pr_url="https://github.com/prebid/Prebid.js/pull/12345",
        persona="executive",
        summary=results["ai_summaries"]["executive_summary"]["summary"],
        feedback_type="rating",
        feedback_value=5
    )
    
    # Check costs
    cost_report = coordinator.ai_service.get_cost_report(days=1)
    print(f"Today's spend: ${cost_report['total_cost']:.4f}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Batch Analysis with Progress

```python
async def analyze_release(coordinator, repo, release_tag):
    """Analyze all PRs in a release."""
    
    prs = coordinator.get_prs_by_release(repo, release_tag)
    print(f"Analyzing {len(prs)} PRs in {release_tag}...")
    
    for i, pr in enumerate(prs, 1):
        print(f"\n[{i}/{len(prs)}] {pr.html_url}")
        
        # Analyze with AI
        results = await coordinator.analyze_pr_with_ai(pr.html_url)
        
        # Save results
        output_path = f"analysis/{release_tag}/pr_{pr.number}.json"
        coordinator.save_results(results, output_path, format="json")
        
        # Auto-rate high quality summaries
        exec_summary = results["ai_summaries"]["executive_summary"]["summary"]
        if "business" in exec_summary.lower():
            coordinator.ai_service.add_feedback(
                pr_url=pr.html_url,
                persona="executive",
                summary=exec_summary,
                feedback_type="rating",
                feedback_value=5
            )
    
    print(f"\nComplete! Results in analysis/{release_tag}/")
```

## Best Practices

### Cost Control

1. **Set Budgets**: Configure `AI_DAILY_BUDGET_USD` in production
2. **Monitor Usage**: Check cost reports regularly
3. **Enable Caching**: Avoid redundant API calls
4. **Batch Processing**: Analyze multiple PRs efficiently

### Quality Improvement

1. **Gather Feedback**: Encourage users to rate summaries
2. **Review Low Scores**: Investigate ratings ≤ 2
3. **Customize Prompts**: Use repository-specific prompts
4. **Export Data**: Regular exports for model improvements

### Performance

1. **Use Webhooks**: For immediate analysis
2. **Cache Results**: Reuse summaries when possible
3. **Parallel Processing**: Service handles concurrent requests

### Security

1. **Verify Webhooks**: Always validate signatures
2. **Secure Keys**: Use environment variables
3. **Rate Limits**: Automatic handling included
4. **Data Privacy**: Local feedback storage by default

## Troubleshooting

### Provider Selection
```python
# Debug provider choice
optimizer = service.cost_optimizer
selected = optimizer.select_optimal_provider(
    "test prompt", 
    expected_output_tokens=300
)
print(f"Selected: {selected}")
```

### Feedback Application
```python
# Check feedback influence
if service.feedback_integrator:
    should_adjust = service.feedback_integrator.should_adjust_prompt(
        "executive", "gemini"
    )
    print(f"Adjust prompt: {should_adjust}")
```

### Webhook Status
```python
# Check webhook configuration
status = webhook_handler.get_queue_status()
print(f"Queue: {status}")
```

## Future Roadmap

Planned features include:

1. **Enhanced Streaming**: Full provider support
2. **Multi-language**: Generate summaries in multiple languages
3. **Auto Fine-tuning**: Automated model improvements
4. **Analytics Dashboard**: Visual metrics and insights
5. **Collaboration**: Multi-user feedback support

## API Reference

For detailed API documentation:
- [AIService API](api/ai-service.md)
- [Cost Management API](api/cost-management.md)
- [Feedback API](api/feedback.md)
- [Webhook API](api/webhook.md)