"""
Test logging functionality
"""
import pytest
import json
import tempfile
from pathlib import Path
from logger import SynthScribeLogger, StructuredFormatter, get_logger
import logging


def test_structured_formatter():
    """Test JSON log formatting"""
    formatter = StructuredFormatter()
    
    # Create test log record
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="/test/path.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.funcName = "test_function"
    record.module = "test_module"
    
    # Format the record
    formatted = formatter.format(record)
    
    # Parse as JSON to verify structure
    log_data = json.loads(formatted)
    
    assert log_data["level"] == "INFO"
    assert log_data["message"] == "Test message"
    assert log_data["module"] == "test_module"
    assert log_data["function"] == "test_function"
    assert log_data["line"] == 42
    assert "timestamp" in log_data


def test_synthscribe_logger():
    """Test SynthScribe logger initialization"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_dir = Path(temp_dir)
        
        logger = SynthScribeLogger(
            name="test_logger",
            log_dir=log_dir,
            console_output=False,
            file_output=True
        )
        
        assert logger.logger.name == "test_logger"
        assert len(logger.logger.handlers) > 0
        
        # Test logging
        logger.logger.info("Test log message")
        
        # Check if log file was created
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) > 0


def test_performance_logging():
    """Test performance logging context manager"""
    logger = SynthScribeLogger("test_perf", console_output=False, file_output=False)
    
    with logger.performance("test_operation", metadata={"test": "data"}):
        # Simulate some work
        pass
    
    # If we get here without exception, the context manager worked


def test_request_logging():
    """Test request logging functionality"""
    logger = SynthScribeLogger("test_request", console_output=False, file_output=False)
    
    request_id = logger.log_request(
        user_id="test_user",
        mood="happy",
        provider="openai"
    )
    
    assert request_id is not None
    assert len(request_id) > 0


def test_get_logger():
    """Test global logger getter"""
    logger = get_logger("test_global")
    assert isinstance(logger, SynthScribeLogger)
    assert logger.logger.name == "test_global" 