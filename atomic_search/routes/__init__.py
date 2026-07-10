"""
Routes package for Atomic Search.
"""
from atomic_search.routes.main import bp as main_bp
from atomic_search.routes.api import bp as api_bp
from atomic_search.routes.admin import bp as admin_bp
from atomic_search.routes.ai import bp as ai_bp
from atomic_search.routes.static import bp as static_bp

__all__ = ["main_bp", "api_bp", "admin_bp", "ai_bp", "static_bp"]
