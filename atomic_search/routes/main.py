"""
Main routes for Atomic Search.

Handles:
- Search requests
- Home page
- Settings
- Bookmarks
- Collections
"""

import asyncio
import hashlib
import time
from typing import Optional

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from atomic_search.config import (
    LanguageCode,
    RegionCode,
    SafeSearchLevel,
    config,
)
from atomic_search.search.backends import SearchType
from atomic_search.utils.security import (
    generate_session_id,
    hash_ip,
    sanitize_search_query,
)

bp = Blueprint("main", __name__)


def get_client_ip() -> str:
    """Get client IP address."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"


def get_session_id() -> str:
    """Get or create a session ID."""
    if "session_id" not in session:
        session["session_id"] = generate_session_id()
    return session["session_id"]


def get_user_hash() -> str:
    """Get a hash of the user for privacy-preserving identification."""
    ip = get_client_ip()
    session_id = get_session_id()
    combined = f"{ip}:{session_id}:{config.SECRET_KEY[:16]}"
    return hashlib.sha256(combined.encode()).hexdigest()


@bp.route("/")
def index():
    """Home page."""
    theme = request.cookies.get("theme", config.DEFAULT_THEME)
    accent_color = request.cookies.get("accent_color", config.DEFAULT_ACCENT_COLOR)
    compact_mode = request.cookies.get("compact_mode", "false") == "true"

    return render_template(
        "index.html",
        theme=theme,
        accent_color=accent_color,
        compact_mode=compact_mode,
        query=request.args.get("q", ""),
    )


@bp.route("/search")
def search():
    """Handle search requests."""
    from atomic_search.services.search import search_service
    from atomic_search.services.voting import voting_service
    
    query = request.args.get("q", "")
    search_type = request.args.get("type", "web")
    page = request.args.get("page", 1, type=int)
    language = request.args.get("lang", config.DEFAULT_LANGUAGE.value)
    region = request.args.get("region", config.DEFAULT_REGION.value)
    safe_search = request.args.get("safe", config.SAFE_SEARCH.value)
    time_period = request.args.get("time")

    # Validate and sanitize query
    query = sanitize_search_query(query)
    if not query:
        return redirect(url_for("main.index"))

    # Check for Google easter egg
    leaving_queries = ['google', 'bing', 'yahoo', 'duckduckgo', 'baidu', 'yandex', ' ecosia']
    is_leaving = any(lq in query.lower() for lq in leaving_queries)

    # Validate search type
    try:
        search_type_enum = SearchType(search_type)
    except ValueError:
        search_type_enum = SearchType.WEB

    # Validate language
    try:
        language_enum = LanguageCode(language)
    except ValueError:
        language_enum = config.DEFAULT_LANGUAGE

    # Validate region
    try:
        region_enum = RegionCode(region)
    except ValueError:
        region_enum = config.DEFAULT_REGION

    # Validate safe search
    try:
        safe_search_enum = SafeSearchLevel(safe_search)
    except ValueError:
        safe_search_enum = config.SAFE_SEARCH

    # Execute search (run async)
    results = asyncio.run(search_service.search(
        query=query,
        search_type=search_type_enum,
        page=page,
        language=language_enum,
        region=region_enum,
        safe_search=safe_search_enum,
        time_period=time_period,
    ))

    # Get vote stats for results
    result_urls = [r.url for r in results.results if r.url]
    vote_stats = voting_service.get_stats_for_urls(result_urls)

    # Apply vote stats to results
    for result in results.results:
        if result.url in vote_stats:
            stats = vote_stats[result.url]
            result.votes = stats["votes"]
            result.upvotes = stats["upvotes"]
            result.downvotes = stats["downvotes"]

    # Get user votes
    ip_hash = hash_ip(get_client_ip())
    session_id = get_session_id()
    user_votes = {}
    for url in result_urls:
        user_votes[url] = voting_service.get_user_vote(url, ip_hash, session_id)

    # Get theme preferences
    theme = request.cookies.get("theme", config.DEFAULT_THEME)
    accent_color = request.cookies.get("accent_color", config.DEFAULT_ACCENT_COLOR)
    compact_mode = request.cookies.get("compact_mode", "false") == "true"

    return render_template(
        "results.html",
        query=query,
        results=results,
        search_type=search_type_enum.value,
        page=page,
        language=language_enum.value,
        region=region_enum.value,
        safe_search=safe_search_enum.value,
        time_period=time_period,
        theme=theme,
        accent_color=accent_color,
        compact_mode=compact_mode,
        vote_stats=vote_stats,
        user_votes=user_votes,
        vote_limit=voting_service.get_vote_count(ip_hash, session_id) if config.VOTING_ENABLED else None,
        is_leaving=is_leaving,
    )


@bp.route("/vote", methods=["POST"])
def vote():
    """Handle vote submissions."""
    if not config.VOTING_ENABLED:
        return jsonify({"success": False, "error": "Voting is disabled"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Invalid request"}), 400

    url = data.get("url", "")
    vote_type = data.get("type")  # 1 for upvote, -1 for downvote

    if vote_type not in (1, -1):
        return jsonify({"success": False, "error": "Invalid vote type"}), 400

    ip_hash = hash_ip(get_client_ip())
    session_id = get_session_id()

    success, message, stats = voting_service.vote(
        url=url,
        vote_type=vote_type,
        ip_hash=ip_hash,
        session_id=session_id,
    )

    if success:
        return jsonify({
            "success": True,
            "message": message,
            "stats": stats,
        })
    else:
        return jsonify({
            "success": False,
            "error": message,
        }), 400


@bp.route("/bookmarks")
def bookmarks():
    """User bookmarks page."""
    theme = request.cookies.get("theme", config.DEFAULT_THEME)

    if not config.BOOKMARKS_ENABLED:
        return redirect(url_for("main.index"))

    session_id = get_session_id()
    bookmarks_list = []

    return render_template(
        "bookmarks.html",
        bookmarks=bookmarks_list,
        theme=theme,
    )


@bp.route("/collections")
def collections():
    """User collections page."""
    theme = request.cookies.get("theme", config.DEFAULT_THEME)

    if not config.BOOKMARKS_ENABLED:
        return redirect(url_for("main.index"))

    return render_template(
        "collections.html",
        theme=theme,
    )


@bp.route("/settings", methods=["GET", "POST"])
def settings():
    """User settings page."""
    theme = request.cookies.get("theme", config.DEFAULT_THEME)
    accent_color = request.cookies.get("accent_color", config.DEFAULT_ACCENT_COLOR)
    compact_mode = request.cookies.get("compact_mode", "false") == "true"

    if request.method == "POST":
        response = redirect(url_for("main.settings"))
        response.set_cookie("theme", request.form.get("theme", "auto"))
        response.set_cookie("accent_color", request.form.get("accent_color", "#6366f1"))
        response.set_cookie("compact_mode", str(request.form.get("compact_mode") == "on"))
        return response

    return render_template(
        "settings.html",
        theme=theme,
        accent_color=accent_color,
        compact_mode=compact_mode,
        config=config,
    )


@bp.route("/about")
def about():
    """About page."""
    return render_template("about.html")


@bp.route("/privacy")
def privacy():
    """Privacy policy page."""
    return render_template("privacy.html")


@bp.route("/terms")
def terms():
    """Terms of service page."""
    return render_template("terms.html")


@bp.route("/reading-mode")
async def reading_mode():
    """Reading mode view for a URL."""
    url = request.args.get("url", "")

    if not url or not config.READING_MODE_ENABLED:
        return redirect(url_for("main.index"))

    content = ""
    title = "Reading Mode"

    return render_template(
        "reading_mode.html",
        content=content,
        title=title,
        url=url,
    )


@bp.route("/privacy/insane")
def privacy_insane():
    """Insane privacy mode page."""
    return render_template(
        "privacy-insane.html",
    )


@bp.route("/privacy-info")
def privacy_page():
    """Privacy information page."""
    return render_template(
        "privacy.html",
    )


@bp.route("/about-info")
def about_page():
    """About page."""
    return render_template(
        "about.html",
    )


@bp.route("/terms-info")
def terms_page():
    """Terms of service page."""
    return render_template(
        "terms.html",
    )
