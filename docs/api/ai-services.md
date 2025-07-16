# AI Services API Reference

## Overview

The AI Services API provides intelligent, LLM-powered summarization of pull request changes. This document covers the complete API surface for integrating and extending AI capabilities in PR Agents.

## Table of Contents

1. [BaseAIService](#baseaiservice)
2. [AIService](#aiservice)
3. [LLM Providers](#llm-providers)
4. [Prompt Management](#prompt-management)
5. [Caching System](#caching-system)
6. [Data Models](#data-models)
7. [Usage Examples](#usage-examples)

## BaseAIService

Abstract base class defining the AI service interface.

### Class Definition

```python
from abc import ABC, abstractmethod
from typing import Any
from src.pr_agents.pr_processing.analysis_models import AISummaries
from src.pr_agents.pr_processing.models import CodeChanges

class BaseAIService(ABC):
    """Abstract base class for AI service implementations."""
```

### Methods

#### `generate_summaries`

```python
@abstractmethod
async def generate_summaries(
    self,
    code_changes: CodeChanges,
    repo_context: dict[str, Any],
    pr_metadata: dict[str, Any],
) -> AISummaries
```

Generate AI-powered summaries for code changes.

**Parameters:**
- `code_changes` (CodeChanges): Extracted code change data including file diffs
- `repo_context` (dict): Repository-specific context and patterns
- `pr_metadata` (dict): PR metadata including title and description

**Returns:**
- `AISummaries`: Object containing persona-based summaries

**Raises:**
- `AIServiceError`: If summary generation fails

#### `health_check`

```python
@abstractmethod
async def health_check(self) -> dict[str, Any]
```

Check if the AI service is healthy and configured properly.

**Returns:**
- `dict`: Health status and diagnostic information

## AIService

Main implementation of the AI service.

### Class Definition

```python
from src.pr_agents.services.ai.base import BaseAIService
from src.pr_agents.services.ai.providers.base import BaseLLMProvider

class AIService(BaseAIService):
    """Main AI service for generating code summaries."""
```

### Constructor

```python
def __init__(
    self,
    provider: Optional[BaseLLMProvider] = None,
    cache_ttl: int = 86400,
    enable_cache: bool = True,
)
```

**Parameters:**
- `provider`: LLM provider instance (if None, creates from environment)
- `cache_ttl`: Cache time-to-live in seconds (default: 86400)
- `enable_cache`: Whether to enable summary caching (default: True)

### Configuration

The service can be configured via environment variables:

```env
AI_PROVIDER=gemini        # Options: gemini, claude, openai
GEMINI_API_KEY=...       # For Gemini provider
ANTHROPIC_API_KEY=...    # For Claude provider
OPENAI_API_KEY=...       # For OpenAI provider
```

## LLM Providers

### BaseLLMProvider

Abstract base class for LLM provider implementations.

```python
class BaseLLMProvider(ABC):
    """Abstract base class for LLM provider implementations."""
    
    def __init__(self, api_key: str, **kwargs):
        """Initialize the provider with API credentials."""
```

### Provider Methods

#### `generate`

```python
@abstractmethod
async def generate(
    self,
    prompt: str,
    max_tokens: int = 500,
    temperature: float = 0.3,
    **kwargs,
) -> LLMResponse
```

Generate text completion from the LLM.

**Parameters:**
- `prompt`: The prompt to send to the LLM
- `max_tokens`: Maximum tokens to generate
- `temperature`: Temperature for response randomness (0-1)
- `**kwargs`: Additional provider-specific parameters

**Returns:**
- `LLMResponse`: Generated text and metadata

### Available Providers

#### GeminiProvider

```python
from src.pr_agents.services.ai.providers.gemini import GeminiProvider

provider = GeminiProvider(
    api_key="your-api-key",
    model_name="gemini-pro"  # Optional, default: gemini-pro
)
```

**Supported Models:**
- `gemini-pro`
- `gemini-pro-vision` (future support)

#### ClaudeProvider

```python
from src.pr_agents.services.ai.providers.claude import ClaudeProvider

provider = ClaudeProvider(
    api_key="your-api-key",
    model_name="claude-3-sonnet-20240229"  # Optional
)
```

**Supported Models:**
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

#### OpenAIProvider

```python
from src.pr_agents.services.ai.providers.openai import OpenAIProvider

provider = OpenAIProvider(
    api_key="your-api-key",
    model_name="gpt-4-turbo-preview"  # Optional
)
```

**Supported Models:**
- `gpt-4-turbo-preview`
- `gpt-4`
- `gpt-3.5-turbo`

## Prompt Management

### PromptBuilder

Constructs context-aware prompts for different personas.

```python
from src.pr_agents.services.ai.prompts import PromptBuilder

builder = PromptBuilder()
```

#### `build_prompt`

```python
def build_prompt(
    self,
    persona: str,
    code_changes: CodeChanges,
    repo_context: dict[str, Any],
    pr_metadata: dict[str, Any],
) -> str
```

Build a prompt for the specified persona.

**Parameters:**
- `persona`: Target persona ("executive", "product", "developer")
- `code_changes`: Extracted code change data
- `repo_context`: Repository-specific context
- `pr_metadata`: PR metadata

**Returns:**
- `str`: Formatted prompt string

### Prompt Templates

Templates are defined in `prompts/templates.py`:

- **EXECUTIVE_TEMPLATE**: High-level business summary
- **PRODUCT_TEMPLATE**: Feature and capability focused
- **DEVELOPER_TEMPLATE**: Technical implementation details

## Caching System

### SummaryCache

In-memory cache for AI-generated summaries.

```python
from src.pr_agents.services.ai.cache import SummaryCache

cache = SummaryCache(ttl_seconds=86400)
```

#### Key Methods

##### `get_key`

```python
def get_key(
    self,
    code_changes: CodeChanges,
    repo_name: str,
    repo_type: str,
) -> str
```

Generate a cache key from code changes and repository info.

##### `get`

```python
def get(self, key: str) -> Optional[AISummaries]
```

Retrieve cached summaries if available and not expired.

##### `set`

```python
def set(self, key: str, summaries: AISummaries) -> None
```

Store summaries in cache.

##### `find_similar`

```python
def find_similar(
    self,
    code_changes: CodeChanges,
    repo_name: str,
    repo_type: str,
    similarity_threshold: float = 0.8,
) -> Optional[AISummaries]
```

Find cached summaries for similar code changes.

## Data Models

### LLMResponse

Response from an LLM provider.

```python
@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int
    response_time_ms: int
    finish_reason: str = "complete"
    metadata: dict[str, Any] | None = None
```

### PersonaSummary

Summary for a specific persona.

```python
@dataclass
class PersonaSummary:
    persona: str  # "executive", "product", "developer"
    summary: str
    confidence: float
```

### AISummaries

Complete set of AI-generated summaries.

```python
@dataclass
class AISummaries:
    executive_summary: PersonaSummary
    product_summary: PersonaSummary
    developer_summary: PersonaSummary
    model_used: str
    generation_timestamp: datetime
    cached: bool = False
    total_tokens: int = 0
    generation_time_ms: int = 0
```

## Usage Examples

### Basic Usage

```python
from src.pr_agents.services.ai import AIService
from src.pr_agents.pr_processing.models import CodeChanges

# Initialize service
ai_service = AIService()

# Prepare data
code_changes = CodeChanges(...)
repo_context = {
    "name": "owner/repo",
    "type": "project-type",
    "primary_language": "Python"
}
pr_metadata = {
    "title": "Add new feature",
    "description": "This PR adds..."
}

# Generate summaries
summaries = await ai_service.generate_summaries(
    code_changes,
    repo_context,
    pr_metadata
)

# Access results
print(f"Executive: {summaries.executive_summary.summary}")
print(f"Product: {summaries.product_summary.summary}")
print(f"Developer: {summaries.developer_summary.summary}")
```

### With Custom Provider

```python
from src.pr_agents.services.ai import AIService
from src.pr_agents.services.ai.providers.gemini import GeminiProvider

# Create custom provider
provider = GeminiProvider(
    api_key="your-key",
    model_name="gemini-pro"
)

# Initialize service with provider
ai_service = AIService(
    provider=provider,
    cache_ttl=3600,  # 1 hour cache
    enable_cache=True
)
```

### Integration with PRCoordinator

```python
from src.pr_agents.pr_processing.coordinator import PRCoordinator

# Initialize with AI enabled
coordinator = PRCoordinator(
    github_token="your-token",
    ai_enabled=True
)

# Analyze PR with AI summaries
results = coordinator.analyze_pr_with_ai(
    "https://github.com/owner/repo/pull/123"
)

# Access AI summaries
ai_summaries = results["ai_summaries"]
```

### Error Handling

```python
try:
    summaries = await ai_service.generate_summaries(
        code_changes,
        repo_context,
        pr_metadata
    )
except Exception as e:
    # Handle errors gracefully
    logger.error(f"AI generation failed: {e}")
    # Summaries will contain error messages
```

## Advanced Features

### Custom Prompt Templates

```python
from src.pr_agents.services.ai.prompts import PromptBuilder

class CustomPromptBuilder(PromptBuilder):
    def __init__(self):
        super().__init__()
        self.templates["security"] = SECURITY_TEMPLATE
    
    def build_security_prompt(self, ...):
        # Custom prompt logic
```

### Provider-Specific Parameters

```python
# Gemini specific
response = await provider.generate(
    prompt,
    max_tokens=500,
    temperature=0.3,
    top_p=0.9,
    top_k=40
)

# Claude specific
response = await provider.generate(
    prompt,
    max_tokens=500,
    temperature=0.3,
    stop_sequences=["\n\n"]
)

# OpenAI specific
response = await provider.generate(
    prompt,
    max_tokens=500,
    temperature=0.3,
    presence_penalty=0.1,
    frequency_penalty=0.1
)
```

### Cache Management

```python
# Clear cache
ai_service.cache.clear()

# Cleanup expired entries
removed = ai_service.cache.cleanup_expired()

# Check cache statistics
if ai_service.cache:
    entries = len(ai_service.cache.cache)
    print(f"Cache entries: {entries}")
```

## Best Practices

1. **Token Optimization**: Use appropriate max_tokens per persona
   - Executive: 150 tokens
   - Product: 300 tokens
   - Developer: 500 tokens

2. **Error Handling**: Always handle provider failures gracefully

3. **Caching**: Enable caching for production to reduce costs

4. **Context Building**: Provide rich repository context for better summaries

5. **Security**: Store API keys in environment variables, never in code

6. **Monitoring**: Track token usage and generation times

7. **Testing**: Use mock providers for unit tests