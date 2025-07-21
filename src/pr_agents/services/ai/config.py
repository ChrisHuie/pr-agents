"""Configuration for AI service settings."""

from dataclasses import dataclass


@dataclass
class PersonaConfig:
    """Configuration for a specific persona."""

    max_tokens: int
    temperature: float
    min_length: int
    max_length: int


@dataclass
class AIConfig:
    """AI service configuration."""

    # Model settings
    default_provider: str = "gemini"
    default_model: str = "gemini-pro"

    # Retry settings
    max_retries: int = 3
    initial_retry_delay: float = 1.0
    retry_backoff_factor: float = 2.0

    # Cache settings
    cache_enabled: bool = True
    cache_ttl_seconds: int = 86400  # 24 hours

    # Persona-specific settings
    persona_configs: dict[str, PersonaConfig] = None

    def __post_init__(self):
        """Initialize default persona configurations."""
        if self.persona_configs is None:
            self.persona_configs = {
                "executive": PersonaConfig(
                    max_tokens=150,
                    temperature=0.3,
                    min_length=20,
                    max_length=100,
                ),
                "product": PersonaConfig(
                    max_tokens=300,
                    temperature=0.4,
                    min_length=50,
                    max_length=200,
                ),
                "developer": PersonaConfig(
                    max_tokens=500,
                    temperature=0.5,
                    min_length=100,
                    max_length=400,
                ),
                "reviewer": PersonaConfig(
                    max_tokens=400,
                    temperature=0.4,
                    min_length=80,
                    max_length=300,
                ),
                "technical_writer": PersonaConfig(
                    max_tokens=350,
                    temperature=0.3,
                    min_length=60,
                    max_length=250,
                ),
            }

    @classmethod
    def from_env(cls) -> "AIConfig":
        """Create config from environment variables."""
        import os

        config = cls()

        # Override from environment if set
        if provider := os.getenv("AI_PROVIDER"):
            config.default_provider = provider.lower()

        if model := os.getenv("AI_MODEL"):
            config.default_model = model

        if max_retries := os.getenv("AI_MAX_RETRIES"):
            config.max_retries = int(max_retries)

        if cache_enabled := os.getenv("AI_CACHE_ENABLED"):
            config.cache_enabled = cache_enabled.lower() in ("true", "1", "yes")

        if cache_ttl := os.getenv("AI_CACHE_TTL"):
            config.cache_ttl_seconds = int(cache_ttl)

        return config


# Default configuration instance
default_config = AIConfig()
