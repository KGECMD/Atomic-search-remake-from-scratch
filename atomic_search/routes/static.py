"""
Static routes for Atomic Search.

Serves static files and assets.
"""

from flask import Blueprint, send_from_directory

from atomic_search.config import config

bp = Blueprint("static", __name__)


@bp.route("/favicon.ico")
def favicon():
    """Serve favicon."""
    return send_from_directory(
        "static/img",
        "favicon.ico",
        mimetype="image/x-icon",
    )


@bp.route("/robots.txt")
def robots():
    """Serve robots.txt."""
    return send_from_directory(
        "static",
        "robots.txt",
        mimetype="text/plain",
    )


@bp.route("/sitemap.xml")
def sitemap():
    """Serve sitemap.xml."""
    return send_from_directory(
        "static",
        "sitemap.xml",
        mimetype="application/xml",
    )


@bp.route("/.well-known/security.txt")
def security_txt():
    """Serve security.txt for security researchers."""
    return """Contact: contact@atomicsearch.dev
Expires: 2025-12-31T23:59:59.000Z
Preferred-Languages: en
Canonical: https://atomicsearch.dev/.well-known/security.txt
Encryption: https://atomicsearch.dev/pgp-key.txt
""", 200, {"Content-Type": "text/plain"}
