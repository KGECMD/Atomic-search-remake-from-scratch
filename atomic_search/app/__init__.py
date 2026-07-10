"""
Atomic Search Flask Application.

Main application factory and configuration.
"""

import asyncio
import os
from datetime import timedelta
from functools import wraps
from typing import Callable, Optional

from flask import Flask, g, jsonify, request, session
from flask_caching import Cache
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from flask_wtf.csrf import CSRFProtect

from atomic_search.config import config


def create_app(config_override: Optional[dict] = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
    app.config["SESSION_COOKIE_SECURE"] = config.SESSION_COOKIE_SECURE
    app.config["SESSION_COOKIE_HTTPONLY"] = config.SESSION_COOKIE_HTTPONLY
    app.config["SESSION_COOKIE_SAMESITE"] = config.SESSION_COOKIE_SAMESITE

    # Template and static folder
    app.template_folder = os.path.join(os.path.dirname(__file__), "templates")
    app.static_folder = os.path.join(os.path.dirname(__file__), "static")

    # Apply overrides
    if config_override:
        app.config.update(config_override)

    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    if config.CSRF_ENABLED:
        csrf = CSRFProtect()
        csrf.init_app(app)
        # Exempt API routes from CSRF protection
        from atomic_search.routes.api import bp as api_bp
        csrf.exempt(api_bp)

    # Setup caching
    if config.CACHE_TYPE == "redis" and config.REDIS_ENABLED:
        app.config["CACHE_TYPE"] = "redis"
        app.config["CACHE_REDIS_URL"] = config.REDIS_URL
    else:
        app.config["CACHE_TYPE"] = "simple"

    app.config["CACHE_DEFAULT_TIMEOUT"] = config.CACHE_DEFAULT_TIMEOUT
    app.config["CACHE_THRESHOLD"] = config.CACHE_THRESHOLD

    cache = Cache(app)

    # Setup rate limiting
    if config.RATE_LIMIT_ENABLED and config.REDIS_ENABLED:
        limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=[f"{config.RATE_LIMIT_PER_MINUTE} per minute"],
            storage_uri=config.REDIS_URL,
        )
    else:
        limiter = None

    # Apply security headers
    @app.after_request
    def add_security_headers(response):
        if config.SECURE_HEADERS:
            from atomic_search.utils.security import get_security_headers
            headers = get_security_headers()
            for key, value in headers.items():
                response.headers[key] = value
        return response

    # Health check endpoint
    @app.route("/health")
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "atomic-search",
            "version": "1.0.0"
        })

    # Register blueprints
    from atomic_search.routes.main import bp as main_bp
    from atomic_search.routes.api import bp as api_bp
    from atomic_search.routes.admin import bp as admin_bp
    from atomic_search.routes.ai import bp as ai_bp
    from atomic_search.routes.static import bp as static_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(static_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(429)
    def ratelimit_handler(error):
        return jsonify({"error": "Rate limit exceeded", "message": str(error)}), 429

    # Add context processors
    @app.context_processor
    def inject_config():
        return {
            "config": {
                "APP_NAME": config.APP_NAME,
                "VERSION": config.APP_VERSION,
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION,
                "default_theme": config.DEFAULT_THEME,
                "default_accent_color": config.DEFAULT_ACCENT_COLOR,
                "ai_enabled": config.AI_PROVIDER.value != "none",
                "ai_provider": config.AI_PROVIDER.value,
                "ai_summaries_enabled": config.AI_SUMMARIES_ENABLED,
                "voting_enabled": config.VOTING_ENABLED,
                "bookmarks_enabled": config.BOOKMARKS_ENABLED,
                "search_history_enabled": config.SEARCH_HISTORY_ENABLED,
                "keyboard_shortcuts_enabled": config.KEYBOARD_SHORTCUTS_ENABLED,
                "reading_mode_enabled": config.READING_MODE_ENABLED,
                "compact_mode": config.COMPACT_MODE,
                "animations_enabled": config.ANIMATIONS_ENABLED,
                "calculator_enabled": config.CALCULATOR_ENABLED,
                "translation_enabled": config.TRANSLATION_ENABLED,
                "unit_converter_enabled": config.UNIT_CONVERTER_ENABLED,
            }
        }

    return app
