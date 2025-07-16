# AI Service Layer Architecture

## Overview

The AI Service Layer enables LLM-powered code summarization with persona-based outputs. It provides intelligent, context-aware summaries of pull request changes at three levels of detail: executive, product manager, and developer.

## Design Philosophy

- **Service Isolation**: AI calls are isolated from processors to maintain architectural boundaries
- **Provider Agnostic**: Support for multiple LLM providers (Gemini, Claude, OpenAI) with easy extensibility
- **Caching Strategy**: Consistent summaries for similar changes reduce API costs and latency
- **Async First**: Non-blocking LLM interactions for optimal performance
- **Context Aware**: Repository-specific context enhances summary quality

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           PR Analysis Request                         │
└─────────────────────────────────────────────────────────┬────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         PRCoordinator                                │
│  - ai_enabled: bool                                                  │
│  - analyze_pr_with_ai()                                             │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AIProcessor                                  │
│  - Extracts code changes and metadata                               │
│  - Builds repository context                                         │
│  - Invokes AI service                                               │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AIService                                    │
│  - Manages LLM provider lifecycle                                    │
│  - Handles caching                                                   │
│  - Orchestrates persona summaries                                    │
└────────────┬──────────────────────────────────┬─────────────────────┘
             │                                  │
             ▼                                  ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│      PromptBuilder          │    │      SummaryCache           │
│  - Persona templates         │    │  - Key generation           │
│  - Context formatting        │    │  - TTL management           │
└─────────────────────────────┘    └─────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LLM Providers                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │   Gemini    │  │   Claude    │  │   OpenAI    │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. AIService (`services/ai/service.py`)

The main service orchestrating AI-powered summarization:

```python
class AIService(BaseAIService):
    async def generate_summaries(
        self,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
    ) -> AISummaries
```

**Responsibilities:**
- Provider lifecycle management
- Cache integration
- Concurrent persona summary generation
- Error handling and fallbacks

### 2. LLM Providers (`services/ai/providers/`)

Abstract interface with concrete implementations:

```python
class BaseLLMProvider(ABC):
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
    ) -> LLMResponse
```

**Available Providers:**
- **GeminiProvider**: Google's Gemini models
- **ClaudeProvider**: Anthropic's Claude models
- **OpenAIProvider**: OpenAI's GPT models

### 3. Prompt Management (`services/ai/prompts/`)

Sophisticated prompt construction with repository context:

```python
class PromptBuilder:
    def build_prompt(
        self,
        persona: str,
        code_changes: CodeChanges,
        repo_context: dict[str, Any],
        pr_metadata: dict[str, Any],
    ) -> str
```

**Persona Templates:**
- **Executive**: High-level business impact (1-2 sentences)
- **Product Manager**: Feature capabilities and user impact (2-4 sentences)
- **Developer**: Technical implementation details (4-6 sentences)

### 4. Caching System (`services/ai/cache/`)

Intelligent caching for consistent summaries:

```python
class SummaryCache:
    def get_key(
        self,
        code_changes: CodeChanges,
        repo_name: str,
        repo_type: str,
    ) -> str
```

**Cache Key Components:**
- Repository name and type
- Change magnitude (small/medium/large)
- File patterns (e.g., "*BidAdapter.js")
- Primary directories affected

### 5. AIProcessor (`processors/ai_processor.py`)

Bridges the gap between PR analysis and AI services:

```python
class AIProcessor(BaseProcessor):
    def process(self, component_data: dict[str, Any]) -> ProcessingResult
```

**Processing Steps:**
1. Extract code changes and metadata
2. Build repository context from configuration
3. Detect programming languages
4. Invoke AI service
5. Return structured results

## Data Flow

### 1. Request Initiation
```python
coordinator = PRCoordinator(github_token="...", ai_enabled=True)
results = coordinator.analyze_pr_with_ai("https://github.com/owner/repo/pull/123")
```

### 2. Component Extraction
The coordinator extracts required components:
- **metadata**: PR title, description, branches
- **code_changes**: File diffs, additions, deletions
- **repository**: Repo context and configuration

### 3. Context Building
The AIProcessor builds rich context:
```python
repo_context = {
    "name": "prebid/Prebid.js",
    "type": "prebid-js",
    "module_patterns": {...},
    "primary_language": "JavaScript",
    "structure": {...}
}
```

### 4. Prompt Generation
PromptBuilder creates persona-specific prompts with:
- Repository context
- Code change statistics
- File type analysis
- Pattern detection

### 5. LLM Interaction
Concurrent requests to the LLM provider:
- Executive summary (150 tokens max)
- Product summary (300 tokens max)
- Developer summary (500 tokens max)

### 6. Response Processing
Results are structured as:
```python
AISummaries(
    executive_summary=PersonaSummary(...),
    product_summary=PersonaSummary(...),
    developer_summary=PersonaSummary(...),
    model_used="gemini-pro",
    generation_timestamp=datetime.now(),
    cached=False,
    total_tokens=950,
    generation_time_ms=2500
)
```

## Configuration

### Environment Variables

```env
# Provider Selection
AI_PROVIDER=gemini  # Options: gemini, claude, openai

# API Keys (set the one for your chosen provider)
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key

# Optional Configuration
AI_CACHE_TTL=86400  # Cache TTL in seconds (default: 24 hours)
AI_MAX_RETRIES=3    # Maximum retry attempts
AI_TIMEOUT=30       # Request timeout in seconds
```

### Repository Configuration

Repository-specific context is loaded from `config/repositories/`:

```json
{
  "prebid/Prebid.js": {
    "repo_type": "prebid-js",
    "description": "Header bidding library",
    "module_locations": {
      "bid_adapter": ["modules/*BidAdapter.js"],
      "analytics": ["modules/*AnalyticsAdapter.js"]
    }
  }
}
```

## Error Handling

### Provider Failures
- Graceful degradation with error summaries
- Automatic retry with exponential backoff
- Fallback to cached results when available

### Rate Limiting
- Respect provider rate limits
- Queue management for batch operations
- Cost tracking and alerting

### Input Validation
- PR URL validation
- Component data verification
- Context sanitization

## Performance Considerations

### Concurrency
- Parallel persona summary generation
- Async provider interactions
- Non-blocking cache operations

### Optimization
- Token usage optimization per persona
- Smart caching for similar PRs
- Batch processing support

### Monitoring
- Request latency tracking
- Token usage metrics
- Cache hit rate monitoring

## Security Considerations

### API Key Management
- Environment variable storage
- No hardcoded credentials
- Secure key rotation support

### Data Privacy
- No sensitive data in prompts
- Sanitized repository context
- Configurable data retention

### Access Control
- Provider-level authentication
- Repository access validation
- User permission checks

## Future Enhancements

### Planned Features
1. **Streaming Support**: Real-time summary generation
2. **Fine-tuning**: Custom models for repository types
3. **Multi-language**: Summaries in different languages
4. **Feedback Loop**: User feedback integration
5. **Cost Optimization**: Smart routing between providers

### Extensibility Points
- Custom prompt templates
- Additional personas
- New LLM providers
- Alternative caching backends
- Webhook integrations