import os
from pathlib import Path

from loguru import logger

from src.pr_agents.logging_config import setup_logging


def get_logging_config():
    """Get logging configuration from environment variables with sensible defaults."""
    # Default to development settings if no environment specified
    environment = os.getenv("PR_AGENTS_ENV", "development").lower()

    # Environment-specific defaults
    if environment in ("production", "prod"):
        default_level = "WARNING"
        default_function_calls = False
        default_data_flow = False
    elif environment in ("staging", "stage"):
        default_level = "INFO"
        default_function_calls = False
        default_data_flow = False
    else:  # development, dev, or any other value
        default_level = "INFO"
        default_function_calls = True
        default_data_flow = True

    return {
        "level": os.getenv("LOG_LEVEL", default_level),
        "show_function_calls": os.getenv(
            "LOG_SHOW_FUNCTIONS", str(default_function_calls)
        ).lower()
        == "true",
        "show_data_flow": os.getenv(
            "LOG_SHOW_DATA_FLOW", str(default_data_flow)
        ).lower()
        == "true",
        "log_file": Path(log_file) if (log_file := os.getenv("LOG_FILE")) else None,
    }


def main():
    config = get_logging_config()
    setup_logging(**config)

    logger.info("🚀 Starting PR Agents application")
    logger.debug(f"Logging configured: {config}")
    logger.success("✅ PR Agents initialized successfully")


if __name__ == "__main__":
    main()
