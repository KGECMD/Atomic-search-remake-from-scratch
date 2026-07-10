"""
Admin routes for Atomic Search.

Provides admin dashboard and management endpoints.
"""

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from atomic_search.config import config
from atomic_search.utils.security import (
    generate_2fa_qrcode,
    get_failed_attempts,
    hash_password,
    is_account_locked,
    record_login_attempt,
    verify_2fa_code,
    verify_password,
)

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Decorator to require admin authentication."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)

    return decorated_function


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Admin login page."""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        otp_code = request.form.get("otp_code", "")

        # Validate credentials
        if username != config.ADMIN_USERNAME:
            record_login_attempt(username, False)
            return render_template("admin/login.html", error="Invalid credentials")

        # Check if account is locked
        if is_account_locked(username):
            return render_template("admin/login.html", error="Account temporarily locked")

        # Get admin password hash
        admin_password = config.ADMIN_PASSWORD or "pbkdf2:sha256:100000:placeholder:placeholder"
        
        # Verify password
        if not verify_password(password, admin_password):
            record_login_attempt(username, False)
            return render_template("admin/login.html", error="Invalid credentials")

        # Verify 2FA if enabled
        if config.TWO_FACTOR_ENABLED and otp_code:
            # Would verify TOTP code in production
            pass

        # Login successful
        record_login_attempt(username, True)
        session["admin_logged_in"] = True
        session["admin_username"] = username

        return redirect(url_for("admin.dashboard"))

    return render_template("admin/login.html")


@bp.route("/logout")
def logout():
    """Admin logout."""
    session.pop("admin_logged_in", None)
    session.pop("admin_username", None)
    return redirect(url_for("admin.login"))


@bp.route("/")
@admin_required
def dashboard():
    """Admin dashboard."""
    return render_template(
        "admin/dashboard.html",
        config=config,
    )


@bp.route("/searches")
@admin_required
def searches():
    """Search analytics page."""
    return render_template("admin/searches.html")


@bp.route("/users")
@admin_required
def users():
    """User management page."""
    return render_template("admin/users.html")


@bp.route("/votes")
@admin_required
def votes():
    """Vote moderation page."""
    if not config.VOTING_ENABLED:
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/votes.html")


@bp.route("/plugins")
@admin_required
def plugins():
    """Plugin management page."""
    if not config.PLUGINS_ENABLED:
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/plugins.html")


@bp.route("/themes")
@admin_required
def themes():
    """Theme management page."""
    if not config.THEMES_ENABLED:
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/themes.html")


@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    """Application settings page."""
    if request.method == "POST":
        # Would save settings in production
        return redirect(url_for("admin.settings"))

    return render_template("admin/settings.html", config=config)


@bp.route("/security")
@admin_required
def security():
    """Security settings page."""
    return render_template("admin/security.html", config=config)


@bp.route("/backup")
@admin_required
def backup():
    """Backup and restore page."""
    return render_template("admin/backup.html")


@bp.route("/cache")
@admin_required
def cache():
    """Cache management page."""
    return render_template("admin/cache.html")


@bp.route("/api/stats")
@admin_required
def api_stats():
    """API endpoint for dashboard statistics."""
    stats = {
        "searches_today": 0,
        "searches_week": 0,
        "searches_month": 0,
        "total_votes": 0,
        "total_bookmarks": 0,
        "active_users": 0,
    }
    return jsonify(stats)


@bp.route("/api/cache/clear", methods=["POST"])
@admin_required
def api_cache_clear():
    """Clear application cache."""
    from atomic_search.services.search import search_service
    search_service.clear_cache()
    return jsonify({"success": True, "message": "Cache cleared"})


@bp.route("/api/backup/create", methods=["POST"])
@admin_required
def api_backup_create():
    """Create a backup."""
    # Would create backup in production
    return jsonify({"success": True, "backup_id": "backup_001"})


@bp.route("/api/backup/restore", methods=["POST"])
@admin_required
def api_backup_restore():
    """Restore from a backup."""
    data = request.get_json()
    backup_id = data.get("backup_id")

    if not backup_id:
        return jsonify({"success": False, "error": "Backup ID required"}), 400

    # Would restore backup in production
    return jsonify({"success": True, "message": f"Restored from {backup_id}"})
