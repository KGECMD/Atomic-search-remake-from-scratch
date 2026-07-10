"""
Configuration management for Atomic Search.

Provides environment-based configuration with validation.
"""

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from atomic_search.utils.validators import validator


@dataclass
class SearchConfig:
    """Search-related configuration."""
    default_results: int = 10
    max_results: int = 100
    default_engine: str = "multi"
    request_timeout: int = 30
    max_concurrent_requests: int = 5
    cache_ttl: int = 3600
    search_delay: float = 0.5


@dataclass
class PrivacyConfig:
    """Privacy-related configuration."""
    enable_logging: bool = False
    log_queries: bool = False
    anonymize_ip: bool = True
    block_trackers: bool = True
    safe_search_level: str = "moderate"  # off, moderate, strict
    require_https: bool = True
    cookie_consent: bool = True


@dataclass
class SecurityConfig:
    """Security-related configuration."""
    secret_key: str = ""
    session_ttl: int = 86400
    max_login_attempts: int = 5
    lockout_duration: int = 300
    require_captcha: bool = False
    enable_csrf: bool = True
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 60
    rate_limit_window: int = 60


@dataclass
class APIConfig:
    """API-related configuration."""
    enable_api: bool = True
    api_rate_limit: int = 100
    require_api_key: bool = False
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    max_request_size: int = 1048576  # 1MB


@dataclass
class DatabaseConfig:
    """Database-related configuration."""
    db_path: str = "/tmp/atomic_search.db"
    redis_url: Optional[str] = None
    enable_cache: bool = True


@dataclass
class UIConfig:
    """UI-related configuration."""
    app_name: str = "Atomic Search"
    app_description: str = "Privacy-first search engine"
    theme: str = "dark"
    accent_color: str = "#667eea"
    results_per_page: int = 10
    enable_instant_answers: bool = True
    enable_suggestions: bool = True


class Config:
    """Main configuration class."""

    def __init__(self):
        self.search = SearchConfig()
        self.privacy = PrivacyConfig()
        self.security = SecurityConfig()
        self.api = APIConfig()
        self.database = DatabaseConfig()
        self.ui = UIConfig()
        self.version = "1.0.0"
        self.environment = os.getenv("FLASK_ENV", "production")
        self.debug = self.environment == "development"
        self._load_from_env()

    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Search config
        self.search.default_results = int(os.getenv("SEARCH_DEFAULT_RESULTS", "10"))
        self.search.max_results = int(os.getenv("SEARCH_MAX_RESULTS", "100"))
        self.search.default_engine = os.getenv("SEARCH_DEFAULT_ENGINE", "multi")
        self.search.request_timeout = int(os.getenv("SEARCH_TIMEOUT", "30"))
        self.search.cache_ttl = int(os.getenv("CACHE_TTL", "3600"))

        # Privacy config
        self.privacy.enable_logging = os.getenv("ENABLE_LOGGING", "false").lower() == "true"
        self.privacy.log_queries = os.getenv("LOG_QUERIES", "false").lower() == "true"
        self.privacy.anonymize_ip = os.getenv("ANONYMIZE_IP", "true").lower() == "true"
        self.privacy.block_trackers = os.getenv("BLOCK_TRACKERS", "true").lower() == "true"
        self.privacy.safe_search_level = os.getenv("SAFE_SEARCH", "moderate")
        self.privacy.require_https = os.getenv("REQUIRE_HTTPS", "true").lower() == "true"

        # Security config
        self.security.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
        self.security.session_ttl = int(os.getenv("SESSION_TTL", "86400"))
        self.security.enable_csrf = os.getenv("ENABLE_CSRF", "true").lower() == "true"
        self.security.enable_rate_limiting = os.getenv("ENABLE_RATE_LIMIT", "true").lower() == "true"
        self.security.rate_limit_requests = int(os.getenv("RATE_LIMIT", "60"))

        # API config
        self.api.enable_api = os.getenv("ENABLE_API", "true").lower() == "true"
        self.api.require_api_key = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"

        # Database config
        self.database.db_path = os.getenv("DB_PATH", "/tmp/atomic_search.db")
        self.database.redis_url = os.getenv("REDIS_URL")
        self.database.enable_cache = os.getenv("ENABLE_CACHE", "true").lower() == "true"

        # UI config
        self.ui.app_name = os.getenv("APP_NAME", "Atomic Search")
        self.ui.theme = os.getenv("THEME", "dark")
        self.ui.accent_color = os.getenv("ACCENT_COLOR", "#667eea")
        self.ui.results_per_page = int(os.getenv("RESULTS_PER_PAGE", "10"))

        # Debug
        self.debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []

        # Search validation
        if self.search.default_results > self.search.max_results:
            errors.append("default_results cannot exceed max_results")

        # Security validation
        if len(self.security.secret_key) < 32:
            errors.append("SECRET_KEY must be at least 32 characters")

        # Privacy validation
        if self.privacy.safe_search_level not in ["off", "moderate", "strict"]:
            errors.append("SAFE_SEARCH must be off, moderate, or strict")

        # UI validation
        if not 0 < self.ui.results_per_page <= 100:
            errors.append("RESULTS_PER_PAGE must be between 1 and 100")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (safe for logging)."""
        return {
            "version": self.version,
            "environment": self.environment,
            "debug": self.debug,
            "search": {
                "default_engine": self.search.default_engine,
                "default_results": self.search.default_results,
                "max_results": self.search.max_results,
                "timeout": self.search.request_timeout,
            },
            "privacy": {
                "log_queries": self.privacy.log_queries,
                "anonymize_ip": self.privacy.anonymize_ip,
                "safe_search": self.privacy.safe_search_level,
            },
            "api": {
                "enabled": self.api.enable_api,
                "require_key": self.api.require_api_key,
            },
            "ui": {
                "name": self.ui.app_name,
                "theme": self.ui.theme,
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        parts = key.split(".")
        value = self

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """Set configuration value by key."""
        parts = key.split(".")
        target = self

        for part in parts[:-1]:
            if hasattr(target, part):
                target = getattr(target, part)

        if hasattr(target, parts[-1]):
            setattr(target, parts[-1], value)


# Global configuration
config = Config()
