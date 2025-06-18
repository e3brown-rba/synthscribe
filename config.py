"""
config.py - Production-ready configuration management for SynthScribe

This module demonstrates enterprise configuration patterns including:
- Environment-based configuration
- Type safety with dataclasses
- Sensible defaults with overrides
- Feature flags for A/B testing
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
import json
from pathlib import Path


class LLMProvider(Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    MOCK = "mock"  # For testing


class LogLevel(Enum):
    """Logging levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class LLMConfig:
    """LLM-specific configuration"""

    provider: LLMProvider = LLMProvider.LOCAL
    api_key: Optional[str] = None
    model_name: str = "mistral"
    base_url: Optional[str] = None
    max_tokens: int = 500
    temperature: float = 0.7
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 1

    def __post_init__(self):
        """Validate and set provider-specific defaults"""
        if self.provider == LLMProvider.LOCAL:
            self.base_url = self.base_url or "http://localhost:11434/v1"
            self.api_key = self.api_key or "ollama"
        elif self.provider == LLMProvider.OPENAI:
            if self.model_name == "mistral":  # Change from default
                self.model_name = "gpt-3.5-turbo"
            if not self.api_key:
                self.api_key = os.getenv("OPENAI_API_KEY")
        elif self.provider == LLMProvider.ANTHROPIC:
            if self.model_name == "mistral":  # Change from default
                self.model_name = "claude-3-sonnet-20240229"
            if not self.api_key:
                self.api_key = os.getenv("ANTHROPIC_API_KEY")


@dataclass
class CacheConfig:
    """Caching configuration for performance optimization"""

    enabled: bool = True
    ttl_seconds: int = 3600  # 1 hour
    max_size: int = 1000
    cache_dir: Path = field(
        default_factory=lambda: Path.home() / ".synthscribe" / "cache"
    )

    def __post_init__(self):
        """Ensure cache directory exists"""
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class AnalyticsConfig:
    """Analytics configuration for tracking and improvement"""

    enabled: bool = True
    track_performance: bool = True
    track_errors: bool = True
    track_user_feedback: bool = True
    analytics_dir: Path = field(
        default_factory=lambda: Path.home() / ".synthscribe" / "analytics"
    )

    def __post_init__(self):
        """Ensure analytics directory exists"""
        if self.enabled:
            self.analytics_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class FeatureFlags:
    """Feature flags for gradual rollout and A/B testing"""

    enable_advanced_prompts: bool = True
    enable_user_profiling: bool = True
    enable_feedback_loop: bool = True
    enable_a_b_testing: bool = False
    enable_performance_mode: bool = True
    enable_debug_mode: bool = False

    # A/B test configurations
    ab_tests: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: {
            "prompt_style": {
                "enabled": True,
                "variants": ["zero_shot", "few_shot", "chain_of_thought"],
                "weights": [0.33, 0.33, 0.34],
            },
            "recommendation_count": {
                "enabled": False,
                "variants": [3, 4, 5],
                "weights": [0.25, 0.50, 0.25],
            },
        }
    )


@dataclass
class Config:
    """Main configuration class combining all settings"""

    # Component configurations
    llm: LLMConfig = field(default_factory=LLMConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)

    # General settings
    app_name: str = "SynthScribe"
    version: str = "1.0.0"
    log_level: LogLevel = LogLevel.INFO
    data_dir: Path = field(default_factory=lambda: Path.home() / ".synthscribe")

    # Performance settings
    request_timeout: int = 60
    max_history_items: int = 100
    max_favorites: int = 50

    def __post_init__(self):
        """Ensure base directories exist"""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables"""
        config = cls()

        # LLM configuration from environment
        if os.getenv("LOCAL_LLM_ENABLED", "true").lower() == "false":
            provider_name = os.getenv("LLM_PROVIDER", "openai").upper()
            config.llm.provider = LLMProvider[provider_name]

        if model := os.getenv("LLM_MODEL"):
            config.llm.model_name = model

        if api_key := os.getenv("LLM_API_KEY"):
            config.llm.api_key = api_key

        # Feature flags from environment
        if os.getenv("SYNTHSCRIBE_DEBUG", "false").lower() == "true":
            config.features.enable_debug_mode = True
            config.log_level = LogLevel.DEBUG

        if os.getenv("DISABLE_CACHE", "false").lower() == "true":
            config.cache.enabled = False

        if os.getenv("DISABLE_ANALYTICS", "false").lower() == "true":
            config.analytics.enabled = False

        return config

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from JSON file"""
        with open(config_path, "r") as f:
            config_dict = json.load(f)

        # Parse nested configurations
        llm_config = LLMConfig(**config_dict.get("llm", {}))
        cache_config = CacheConfig(**config_dict.get("cache", {}))
        analytics_config = AnalyticsConfig(**config_dict.get("analytics", {}))
        features = FeatureFlags(**config_dict.get("features", {}))

        # Remove nested configs from main dict
        for key in ["llm", "cache", "analytics", "features"]:
            config_dict.pop(key, None)

        return cls(
            llm=llm_config,
            cache=cache_config,
            analytics=analytics_config,
            features=features,
            **config_dict,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "app_name": self.app_name,
            "version": self.version,
            "log_level": self.log_level.value,
            "data_dir": str(self.data_dir),
            "llm": {
                "provider": self.llm.provider.value,
                "model_name": self.llm.model_name,
                "max_tokens": self.llm.max_tokens,
                "temperature": self.llm.temperature,
            },
            "cache": {
                "enabled": self.cache.enabled,
                "ttl_seconds": self.cache.ttl_seconds,
                "max_size": self.cache.max_size,
            },
            "analytics": {
                "enabled": self.analytics.enabled,
                "track_performance": self.analytics.track_performance,
                "track_errors": self.analytics.track_errors,
            },
            "features": {
                "enable_advanced_prompts": self.features.enable_advanced_prompts,
                "enable_user_profiling": self.features.enable_user_profiling,
                "enable_a_b_testing": self.features.enable_a_b_testing,
            },
        }

    def save_to_file(self, config_path: Path):
        """Save configuration to JSON file"""
        with open(config_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# Singleton configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global configuration instance"""
    global _config
    if _config is None:
        # Try loading from file first
        config_file = Path.home() / ".synthscribe" / "config.json"
        if config_file.exists():
            _config = Config.from_file(config_file)
        else:
            # Fall back to environment variables
            _config = Config.from_env()

    return _config


def reset_config():
    """Reset configuration (useful for testing)"""
    global _config
    _config = None


# Example usage and testing
if __name__ == "__main__":
    # Get configuration
    config = get_config()

    # Display current configuration
    print(f"SynthScribe Configuration (v{config.version})")
    print("=" * 50)
    print(f"LLM Provider: {config.llm.provider.value}")
    print(f"Model: {config.llm.model_name}")
    print(f"Cache Enabled: {config.cache.enabled}")
    print(f"Analytics Enabled: {config.analytics.enabled}")
    print(f"A/B Testing: {config.features.enable_a_b_testing}")
    print("\nFeature Flags:")
    for flag, value in config.features.__dict__.items():
        if flag != "ab_tests":
            print(f"  {flag}: {value}")

    # Save example configuration
    example_config_path = Path("config.example.json")
    config.save_to_file(example_config_path)
    print(f"\nExample configuration saved to: {example_config_path}")
