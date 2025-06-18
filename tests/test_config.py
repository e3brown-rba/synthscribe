"""
Test configuration management
"""
import pytest
import os
from pathlib import Path
from config import Config, LLMProvider, get_config


def test_config_defaults():
    """Test default configuration values"""
    config = Config()
    
    assert config.app_name == "SynthScribe"
    assert config.version == "1.0.0"
    assert config.llm.provider == LLMProvider.LOCAL
    assert config.llm.model_name == "mistral"
    assert config.cache.enabled is True
    assert config.analytics.enabled is True


def test_config_from_env(monkeypatch):
    """Test configuration from environment variables"""
    # Set test environment variables
    monkeypatch.setenv("LOCAL_LLM_ENABLED", "false")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")
    monkeypatch.setenv("SYNTHSCRIBE_DEBUG", "true")
    
    config = Config.from_env()
    
    assert config.llm.provider == LLMProvider.OPENAI
    assert config.llm.model_name == "gpt-4"
    assert config.features.enable_debug_mode is True


def test_llm_config_openai():
    """Test OpenAI specific configuration"""
    from config import LLMConfig
    
    config = LLMConfig(provider=LLMProvider.OPENAI)
    assert config.model_name == "gpt-3.5-turbo"
    assert config.base_url is None


def test_llm_config_local():
    """Test local LLM configuration"""
    from config import LLMConfig
    
    config = LLMConfig(provider=LLMProvider.LOCAL)
    assert config.base_url == "http://localhost:11434/v1"
    assert config.api_key == "ollama"


def test_get_config():
    """Test the global config getter"""
    config = get_config()
    assert isinstance(config, Config)
    assert config.app_name == "SynthScribe" 