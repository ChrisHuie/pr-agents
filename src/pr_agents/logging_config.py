"""Logging configuration module using loguru for enhanced console output."""

import json
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger


def setup_logging(
    level: str = "INFO",
    show_function_calls: bool = True,
    show_data_flow: bool = True,
    log_file: Path | None = None,
) -> None:
    """
    Configure loguru logger for improved console visualization.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        show_function_calls: Whether to include function names in logs
        show_data_flow: Whether to show data being passed between functions
        log_file: Optional file path for log output
    """
    # Remove default handler
    logger.remove()

    # Create colorized console format
    if show_function_calls:
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    else:
        # Simplified format with better visual consistency
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<dim>general</dim> | "  # Consistent placeholder
            "<level>{message}</level>"
        )

    # Add console handler
    logger.add(
        sys.stderr,
        format=console_format,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Add file handler if specified
    if log_file:
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} | {message}"
        )
        logger.add(
            log_file,
            format=file_format,
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            compression="zip",
        )

    # Configure for data flow visualization
    if show_data_flow:
        logger.info("🚀 Logging configured with data flow visualization enabled")
    else:
        logger.info("📝 Basic logging configured")


def log_function_entry(func_name: str, **kwargs: Any) -> None:
    """Log function entry with parameters."""
    if kwargs:
        params = ", ".join(f"{k}={repr(v)[:100]}" for k, v in kwargs.items())
        logger.debug(f"🔵 Entering {func_name}({params})")
    else:
        logger.debug(f"🔵 Entering {func_name}()")


def log_function_exit(func_name: str, result: Any = None) -> None:
    """Log function exit with result."""
    if result is not None:
        result_str = repr(result)[:200]
        logger.debug(f"🔴 Exiting {func_name} → {result_str}")
    else:
        logger.debug(f"🔴 Exiting {func_name}")


def log_data_flow(operation: str, data: Any, context: str = "") -> None:
    """Log data being passed between operations."""
    data_preview = repr(data)[:300] if data is not None else "None"
    context_str = f" [{context}]" if context else ""
    logger.debug(f"📊 {operation}{context_str}: {data_preview}")


def log_processing_step(step: str, details: str = "") -> None:
    """Log a processing step with optional details."""
    details_str = f" - {details}" if details else ""
    logger.info(f"⚙️ {step}{details_str}")


def log_api_call(
    method: str,
    url: str,
    status: int | None = None,
    request_data: Any = None,
    response_data: Any = None,
    duration_ms: int | None = None,
) -> None:
    """
    Log API calls for external service interactions.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        status: HTTP status code
        request_data: Request body/data (will be sanitized)
        response_data: Response body/data (will be sanitized)
        duration_ms: Request duration in milliseconds
    """
    if status:
        status_emoji = "✅" if 200 <= status < 300 else "❌"
        duration_str = f" ({duration_ms}ms)" if duration_ms else ""
        logger.info(f"🌐 {method} {url} {status_emoji} {status}{duration_str}")

        # Log request/response details at DEBUG level for debugging
        if request_data is not None:
            sanitized_request = _sanitize_and_truncate_data(request_data, "REQUEST")
            logger.debug(f"🔵 Request data: {sanitized_request}")

        if response_data is not None:
            sanitized_response = _sanitize_and_truncate_data(response_data, "RESPONSE")
            if status >= 400:
                # Log error responses at WARNING level for visibility
                logger.warning(f"🔴 Error response: {sanitized_response}")
            else:
                logger.debug(f"🔵 Response data: {sanitized_response}")
    else:
        logger.info(f"🌐 {method} {url} ⏳ Requesting...")


def log_error_with_context(error: Exception, context: str = "") -> None:
    """Log errors with additional context."""
    context_str = f" [{context}]" if context else ""
    logger.error(f"💥 Error{context_str}: {type(error).__name__}: {error}")


def _sanitize_and_truncate_data(data: Any, data_type: str = "DATA") -> str:
    """
    Sanitize and truncate data for safe logging.

    Args:
        data: Data to sanitize (dict, str, list, etc.)
        data_type: Type of data for context (REQUEST, RESPONSE, etc.)

    Returns:
        Sanitized and truncated string representation
    """
    try:
        # Convert to string representation
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, indent=None, separators=(",", ":"))
        else:
            data_str = str(data)

        # Sanitize sensitive information
        data_str = _sanitize_sensitive_data(data_str)

        # Truncate if too long (keep it reasonable for logs)
        max_length = 1000
        if len(data_str) > max_length:
            truncated = data_str[:max_length]
            return f"{truncated}... [TRUNCATED - {len(data_str)} total chars]"

        return data_str

    except Exception as e:
        return f"[{data_type} SERIALIZATION ERROR: {type(e).__name__}]"


def _sanitize_sensitive_data(data_str: str) -> str:
    """
    Remove or mask sensitive information from data strings.

    Args:
        data_str: String data to sanitize

    Returns:
        Sanitized string with sensitive data masked
    """
    # Patterns for sensitive data
    sensitive_patterns = [
        # API keys, tokens, secrets
        (
            r'"(api_?key|token|secret|password|passwd|pwd)":\s*"[^"]*"',
            r'"\1": "[REDACTED]"',
        ),
        (
            r"'(api_?key|token|secret|password|passwd|pwd)':\s*'[^']*'",
            r"'\1': '[REDACTED]'",
        ),
        # Authorization headers
        (r'"authorization":\s*"[^"]*"', r'"authorization": "[REDACTED]"'),
        (r"'authorization':\s*'[^']*'", r"'authorization': '[REDACTED]'"),
        # Bearer tokens
        (r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", r"Bearer [REDACTED]"),
        # Email addresses (partial masking)
        (
            r"\b([a-zA-Z0-9._%+-]{1,3})[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
            r"\1***@\2",
        ),
        # Credit card numbers (basic pattern)
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", r"****-****-****-****"),
        # GitHub tokens (basic pattern)
        (r"\bgh[po]_[A-Za-z0-9]{36}\b", r"gh*_[REDACTED]"),
    ]

    sanitized = data_str
    for pattern, replacement in sensitive_patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized


# Create a decorator for automatic function logging
def log_calls(show_params: bool = True, show_result: bool = True):
    """Decorator to automatically log function calls."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"

            # Log entry
            if show_params:
                all_params = {}
                # Get positional args
                if args:
                    all_params.update({f"arg_{i}": arg for i, arg in enumerate(args)})
                # Get keyword args
                all_params.update(kwargs)
                log_function_entry(func_name, **all_params)
            else:
                log_function_entry(func_name)

            try:
                result = func(*args, **kwargs)

                # Log exit
                if show_result:
                    log_function_exit(func_name, result)
                else:
                    log_function_exit(func_name)

                return result
            except Exception as e:
                log_error_with_context(e, f"in {func_name}")
                raise

        return wrapper

    return decorator
