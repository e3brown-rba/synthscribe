"""
logger.py - Enterprise-grade structured logging for SynthScribe

This module provides:
- JSON-formatted structured logging
- Performance tracking
- Error monitoring with context
- Request correlation IDs
"""

import logging
import json
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
import uuid
from functools import wraps
import time


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Base log structure
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id

        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id

        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms

        if hasattr(record, "metadata"):
            log_obj["metadata"] = record.metadata

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_obj)


class PerformanceLogger:
    """Context manager for logging performance metrics"""

    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.logger = logger
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(
            f"Starting {self.operation}", extra={"metadata": self.metadata}
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type:
            self.logger.error(
                f"{self.operation} failed after {duration_ms:.2f}ms",
                exc_info=(exc_type, exc_val, exc_tb),
                extra={"duration_ms": duration_ms, "metadata": self.metadata},
            )
        else:
            self.logger.info(
                f"{self.operation} completed in {duration_ms:.2f}ms",
                extra={"duration_ms": duration_ms, "metadata": self.metadata},
            )


class SynthScribeLogger:
    """Main logger class for SynthScribe application"""

    def __init__(
        self,
        name: str,
        log_dir: Optional[Path] = None,
        console_output: bool = True,
        file_output: bool = True,
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        # Add console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(StructuredFormatter())
            console_handler.setLevel(logging.INFO)
            self.logger.addHandler(console_handler)

        # Add file handler
        if file_output and log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = (
                log_dir / f"synthscribe_{datetime.utcnow().strftime('%Y%m%d')}.log"
            )
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(StructuredFormatter())
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)

    def log_request(self, user_id: str, mood: str, provider: str) -> str:
        """Log an incoming request and return request ID"""
        request_id = str(uuid.uuid4())
        self.logger.info(
            "New recommendation request",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "metadata": {"mood": mood, "provider": provider},
            },
        )
        return request_id

    def log_llm_call(
        self, request_id: str, provider: str, model: str, prompt_length: int
    ):
        """Log LLM API call"""
        self.logger.debug(
            "Calling LLM API",
            extra={
                "request_id": request_id,
                "metadata": {
                    "provider": provider,
                    "model": model,
                    "prompt_length": prompt_length,
                },
            },
        )

    def log_llm_response(
        self,
        request_id: str,
        response_length: int,
        duration_ms: float,
        cached: bool = False,
    ):
        """Log LLM API response"""
        self.logger.info(
            "LLM response received",
            extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
                "metadata": {"response_length": response_length, "cached": cached},
            },
        )

    def log_recommendation(
        self, request_id: str, user_id: str, recommendation_count: int, genres: list
    ):
        """Log generated recommendations"""
        self.logger.info(
            "Recommendations generated",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "metadata": {"count": recommendation_count, "genres": genres},
            },
        )

    def log_user_feedback(self, user_id: str, genre: str, rating: float):
        """Log user feedback on recommendations"""
        self.logger.info(
            "User feedback received",
            extra={"user_id": user_id, "metadata": {"genre": genre, "rating": rating}},
        )

    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log error with context"""
        self.logger.error(
            f"Error occurred: {str(error)}", exc_info=True, extra={"metadata": context}
        )

    def performance(
        self, operation: str, metadata: Optional[Dict[str, Any]] = None
    ) -> PerformanceLogger:
        """Create performance logger context manager"""
        return PerformanceLogger(self.logger, operation, metadata)


# Global logger instance
_logger: Optional[SynthScribeLogger] = None


def get_logger(name: str = "synthscribe") -> SynthScribeLogger:
    """Get or create logger instance"""
    global _logger
    if _logger is None:
        from config import get_config

        config = get_config()

        log_dir = config.data_dir / "logs" if config.analytics.enabled else None
        _logger = SynthScribeLogger(
            name=name, log_dir=log_dir, file_output=config.analytics.enabled
        )

        # Set log level from config
        _logger.logger.setLevel(config.log_level.value)

    return _logger


def log_performance(operation: str):
    """Decorator for automatic performance logging"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            with logger.performance(operation):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Example usage
if __name__ == "__main__":
    # Initialize logger
    logger = get_logger()

    # Log a request
    request_id = logger.log_request(
        user_id="user123", mood="coding late at night", provider="local"
    )

    # Log with performance tracking
    with logger.performance("generate_recommendations", {"request_id": request_id}):
        # Simulate some work
        time.sleep(0.1)

        # Log LLM call
        logger.log_llm_call(
            request_id=request_id, provider="local", model="mistral", prompt_length=250
        )

        # Simulate LLM response
        time.sleep(0.5)
        logger.log_llm_response(
            request_id=request_id, response_length=500, duration_ms=500, cached=False
        )

    # Log recommendations
    logger.log_recommendation(
        request_id=request_id,
        user_id="user123",
        recommendation_count=4,
        genres=["Lofi Hip Hop", "Ambient", "Jazz", "Classical"],
    )

    # Log user feedback
    logger.log_user_feedback(user_id="user123", genre="Lofi Hip Hop", rating=5.0)

    # Log an error
    try:
        raise ValueError("Example error")
    except Exception as e:
        logger.log_error(e, {"request_id": request_id, "phase": "testing"})

    print("\nCheck logs for structured output!")
