"""
Atomic Search Configuration System.

Provides comprehensive configuration management with support for:
- Environment variables
- Encrypted settings
- Default values
- Type validation
- Privacy-first defaults
"""

import os
import secrets
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class SearchBackend(str, Enum):
    """Available search backends."""
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    GOOGLE = "google"
    SEARX = "searx"
    STARTPAGE = "startpage"
    MWMBL = "mwmbl"


class SafeSearchLevel(str, Enum):
    """Safe search levels."""
    OFF = "off"
    MODERATE = "moderate"
    STRICT = "strict"


class RegionCode(str, Enum):
    """Search region codes."""
    GLOBAL = "global"
    US = "us"
    UK = "gb"
    DE = "de"
    FR = "fr"
    ES = "es"
    IT = "it"
    NL = "nl"
    PL = "pl"
    RU = "ru"
    JP = "jp"
    CN = "cn"
    KR = "kr"
    IN = "in"
    AU = "au"
    CA = "ca"
    BR = "br"


class LanguageCode(str, Enum):
    """Search language codes."""
    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"
    IT = "it"
    PT = "pt"
    RU = "ru"
    ZH = "zh"
    JA = "ja"
    KO = "ko"
    AR = "ar"
    HI = "hi"


class AIProvider(str, Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    NONE = "none"


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Atomic Search"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Field(default=Environment.PRODUCTION)
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8080)  # Railway uses 8080
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_hex(32))
    BASE_URL: str = Field(default="http://localhost:8080")

    # Paths
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    DATA_DIR: Path = Field(default_factory=lambda: Path.home() / ".atomic_search")
    LOG_DIR: Path = Field(default_factory=lambda: Path.home() / ".atomic_search" / "logs")
    CACHE_DIR: Path = Field(default_factory=lambda: Path.home() / ".atomic_search" / "cache")

    # Database
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./atomic_search.db")
    DATABASE_ECHO: bool = Field(default=False)

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_ENABLED: bool = Field(default=False)

    # Search
    SEARCH_BACKEND: str = Field(default="bing_html")
    SEARCH_RESULTS_PER_PAGE: int = Field(default=20)
    SEARCH_MAX_PAGES: int = Field(default=5)
    SAFE_SEARCH: SafeSearchLevel = Field(default=SafeSearchLevel.MODERATE)
    DEFAULT_REGION: RegionCode = Field(default=RegionCode.GLOBAL)
    DEFAULT_LANGUAGE: LanguageCode = Field(default=LanguageCode.EN)

    # Privacy
    ENABLE_TOR: bool = Field(default=False)
    TOR_PROXY: str = Field(default="socks5://127.0.0.1:9050")
    DNS_OVER_HTTPS: bool = Field(default=True)
    DOH_URL: str = Field(default="https://1.1.1.1/dns-query")
    BLOCK_TRACKERS: bool = Field(default=True)
    BLOCK_ADS: bool = Field(default=True)
    MINIMAL_LOGGING: bool = Field(default=True)
    DISABLE_ANALYTICS: bool = Field(default=True)
    ANONYMOUS_MODE: bool = Field(default=True)
    COOKIES_ENABLED: bool = Field(default=False)

    # Security
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_PER_HOUR: int = Field(default=1000)
    CSRF_ENABLED: bool = Field(default=True)
    XSS_PROTECTION: bool = Field(default=True)
    SECURE_HEADERS: bool = Field(default=True)
    CONTENT_SECURITY_POLICY: bool = Field(default=True)
    HSTS_ENABLED: bool = Field(default=True)
    ENCRYPTED_SETTINGS: bool = Field(default=True)
    SESSION_COOKIE_SECURE: bool = Field(default=True)
    SESSION_COOKIE_HTTPONLY: bool = Field(default=True)
    SESSION_COOKIE_SAMESITE: str = Field(default="Lax")

    # AI Features
    AI_PROVIDER: AIProvider = Field(default=AIProvider.NONE)
    AI_MODEL: str = Field(default="gpt-4")
    AI_API_KEY: Optional[str] = Field(default=None)
    AI_API_ENDPOINT: Optional[str] = Field(default=None)
    AI_MAX_TOKENS: int = Field(default=2048)
    AI_TEMPERATURE: float = Field(default=0.7)
    AI_STREAMING: bool = Field(default=True)
    AI_SUMMARIES_ENABLED: bool = Field(default=True)
    AI_CHAT_ENABLED: bool = Field(default=True)

    # Community Features
    VOTING_ENABLED: bool = Field(default=True)
    VOTING_ANONYMOUS: bool = Field(default=True)
    VOTING_COOLDOWN_MINUTES: int = Field(default=5)
    MAX_VOTES_PER_DAY: int = Field(default=100)

    # Admin
    ADMIN_ENABLED: bool = Field(default=True)
    ADMIN_USERNAME: str = Field(default="admin")
    ADMIN_PASSWORD: Optional[str] = Field(default=None)
    ADMIN_API_KEY: Optional[str] = Field(default=None)
    TWO_FACTOR_ENABLED: bool = Field(default=False)

    # Caching
    CACHE_TYPE: str = Field(default="simple")
    CACHE_DEFAULT_TIMEOUT: int = Field(default=300)
    CACHE_THRESHOLD: int = Field(default=500)
    SEARCH_CACHE_TIMEOUT: int = Field(default=3600)
    ENABLE_RESPONSE_CACHE: bool = Field(default=True)

    # Features
    READING_MODE_ENABLED: bool = Field(default=True)
    TRANSLATION_ENABLED: bool = Field(default=True)
    CALCULATOR_ENABLED: bool = Field(default=True)
    CURRENCY_CONVERTER_ENABLED: bool = Field(default=True)
    UNIT_CONVERTER_ENABLED: bool = Field(default=True)
    WEATHER_ENABLED: bool = Field(default=True)
    RSS_ENABLED: bool = Field(default=True)
    BOOKMARKS_ENABLED: bool = Field(default=True)
    SEARCH_HISTORY_ENABLED: bool = Field(default=True)
    KEYBOARD_SHORTCUTS_ENABLED: bool = Field(default=True)
    PLUGINS_ENABLED: bool = Field(default=True)
    THEMES_ENABLED: bool = Field(default=True)

    # UI
    DEFAULT_THEME: str = Field(default="auto")
    DEFAULT_ACCENT_COLOR: str = Field(default="#6366f1")
    DEFAULT_FONT_SIZE: str = Field(default="medium")
    COMPACT_MODE: bool = Field(default=False)
    GLASSMORPHISM_ENABLED: bool = Field(default=False)
    ANIMATIONS_ENABLED: bool = Field(default=True)

    # API
    API_ENABLED: bool = Field(default=True)
    API_KEY_REQUIRED: bool = Field(default=False)
    API_RATE_LIMIT: int = Field(default=100)
    GRAPHQL_ENABLED: bool = Field(default=True)
    OPENAPI_ENABLED: bool = Field(default=True)

    # Logging
    LOG_LEVEL: str = Field(default="WARNING")
    LOG_FORMAT: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_FILE: Optional[str] = Field(default=None)

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def set_secret_key(cls, v: Optional[str]) -> str:
        if not v:
            return secrets.token_hex(32)
        return v

    @field_validator("ADMIN_PASSWORD", mode="before")
    @classmethod
    def hash_admin_password(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith("pbkdf2:"):
            from atomic_search.utils.security import hash_password
            return hash_password(v)
        return v

    def get_csp_policy(self) -> str:
        """Generate Content Security Policy header."""
        policies = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https: blob:",
            "font-src 'self' data:",
            "connect-src 'self' https://*.openai.com https://*.anthropic.com https://*.googleapis.com",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "worker-src 'self' blob:",
        ]
        return "; ".join(policies)

    def get_secure_headers(self) -> Dict[str, str]:
        """Generate secure HTTP headers."""
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block" if self.XSS_PROTECTION else "0",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
        }
        if self.HSTS_ENABLED:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        if self.CONTENT_SECURITY_POLICY:
            headers["Content-Security-Policy"] = self.get_csp_policy()
        return headers


class Config:
    """Legacy configuration class for compatibility."""

    def __init__(self):
        self._settings = Settings()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._settings, name, None)

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls()


# Global configuration instance
config = Settings()
