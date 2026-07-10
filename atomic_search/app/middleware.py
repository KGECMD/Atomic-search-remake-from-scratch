"""
Middleware for Atomic Search.

Provides Flask middleware for security, privacy, and performance.
"""

import time
from functools import wraps
from typing import Callable, Optional

from flask import Flask, g, request, jsonify, Response
from werkzeug.wrappers import Response as WerkzeugResponse

from atomic_search.utils.privacy import privacy_manager
from atomic_search.utils.rate_limiter import ip_limiter
from atomic_search.utils.logging import logger
from atomic_search.utils.validators import validator


class SecurityMiddleware:
    """Security middleware for Flask."""

    @staticmethod
    def init_app(app: Flask):
        """Initialize security middleware."""
        app.before_request(SecurityMiddleware.before_request)
        app.after_request(SecurityMiddleware.after_request)
        app.errorhandler(404)(SecurityMiddleware.not_found)
        app.errorhandler(500)(SecurityMiddleware.server_error)

    @staticmethod
    def before_request():
        """Process before request."""
        # Get client IP
        g.client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in g.client_ip:
            g.client_ip = g.client_ip.split(',')[0]

        # Anonymize IP for logging
        if hasattr(privacy_manager, 'anonymize_ip'):
            g.client_ip_anonymized = privacy_manager.anonymize_ip(g.client_ip)
        else:
            g.client_ip_anonymized = '***'

        # Start timing
        g.start_time = time.time()

        # Rate limiting
        if ip_limiter:
            allowed, remaining = ip_limiter.check_ip(g.client_ip)
            if not allowed:
                return jsonify({
                    "error": "Rate limit exceeded",
                    "retry_after": remaining.get("minute_remaining", 60)
                }), 429

        # Validate request
        if request.method in ['POST', 'PUT', 'PATCH']:
            if request.is_json:
                data = request.get_json(silent=True)
                if data:
                    result = validator.validate_config(data)
                    if not result.valid:
                        return jsonify({"error": "Invalid request", "details": result.errors}), 400

    @staticmethod
    def after_request(response: Response) -> Response:
        """Process after request."""
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Remove sensitive headers
        response.headers.pop('Server', None)
        response.headers.pop('X-Powered-By', None)

        # Log request duration
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            response.headers['X-Response-Time'] = f'{duration * 1000:.2f}ms'

        return response

    @staticmethod
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({
            "error": "Not found",
            "status": 404
        }), 404

    @staticmethod
    def server_error(error):
        """Handle 500 errors."""
        logger.error(f"Server error: {str(error)}")
        return jsonify({
            "error": "Internal server error",
            "status": 500
        }), 500


class CompressionMiddleware:
    """Compression middleware."""

    @staticmethod
    def init_app(app: Flask):
        """Initialize compression middleware."""
        @app.after_request
        def compress_response(response):
            # Check if response should be compressed
            if (
                response.status_code == 200
                and response.content_type
                and 'text' in response.content_type.lower()
                or 'application/json' in response.content_type
            ):
                # Enable gzip compression
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Vary'] = 'Accept-Encoding'

            return response


class CORSMiddleware:
    """CORS middleware."""

    def __init__(self, allowed_origins: list = None):
        self.allowed_origins = allowed_origins or ["*"]

    def init_app(self, app: Flask):
        """Initialize CORS middleware."""
        @app.after_request
        def add_cors_headers(response):
            origin = request.headers.get('Origin')
            
            if origin:
                if '*' in self.allowed_origins:
                    response.headers['Access-Control-Allow-Origin'] = '*'
                elif origin in self.allowed_origins:
                    response.headers['Access-Control-Allow-Origin'] = origin

            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Max-Age'] = '3600'

            return response


class RequestLoggingMiddleware:
    """Request logging middleware."""

    @staticmethod
    def init_app(app: Flask):
        """Initialize logging middleware."""
        @app.before_request
        def log_request():
            g.request_id = f"{int(time.time() * 1000)}-{id(request)}"

        @app.after_request
        def log_response(response):
            if hasattr(g, 'start_time'):
                duration = time.time() - g.start_time
                
                logger.api_request(
                    endpoint=request.path,
                    method=request.method,
                    status=response.status_code,
                    duration_ms=duration * 1000
                )

            return response


def require_api_key(f: Callable) -> Callable:
    """Decorator to require API key."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

        if not api_key:
            return jsonify({"error": "API key required"}), 401

        # Validate API key format
        result = validator.validate_api_key(api_key)
        if not result.valid:
            return jsonify({"error": "Invalid API key"}), 401

        return f(*args, **kwargs)

    return decorated


def rate_limit(requests: int = 60, window: int = 60):
    """Decorator for rate limiting a route."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            client_ip = g.get('client_ip', request.remote_addr)
            
            if ip_limiter:
                allowed, remaining = ip_limiter.check_ip(client_ip)
                if not allowed:
                    return jsonify({
                        "error": "Rate limit exceeded",
                        "retry_after": remaining.get("minute_remaining", 60)
                    }), 429

            return f(*args, **kwargs)

        return decorated

    return decorator


def validate_json(f: Callable) -> Callable:
    """Decorator to validate JSON request body."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json"}), 400

            data = request.get_json(silent=True)
            if data is None:
                return jsonify({"error": "Invalid JSON body"}), 400

        return f(*args, **kwargs)

    return decorated
