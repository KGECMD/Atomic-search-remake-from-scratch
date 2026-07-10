"""
API routes for Atomic Search.

Provides REST API endpoints for external access.
"""

import asyncio
from flask import Blueprint, jsonify, request

from atomic_search.config import config
from atomic_search.utils.security import sanitize_search_query

bp = Blueprint("api", __name__, url_prefix="/api/v1")


@bp.route("/search")
def search():
    """API endpoint for search requests."""
    if not config.API_ENABLED:
        return jsonify({"error": "API is disabled"}), 403

    query = request.args.get("q", "")
    search_type = request.args.get("type", "web")
    page = request.args.get("page", 1, type=int)
    language = request.args.get("lang", "en")
    region = request.args.get("region", "global")
    safe_search = request.args.get("safe", "moderate")

    query = sanitize_search_query(query)
    if not query:
        return jsonify({"error": "Query is required"}), 400

    from atomic_search.search.backends import SearchType
    from atomic_search.services.search import search_service
    from atomic_search.config import LanguageCode, RegionCode, SafeSearchLevel

    try:
        search_type_enum = SearchType(search_type)
    except ValueError:
        search_type_enum = SearchType.WEB

    try:
        language_enum = LanguageCode(language)
    except ValueError:
        language_enum = LanguageCode.EN

    try:
        region_enum = RegionCode(region)
    except ValueError:
        region_enum = RegionCode.GLOBAL

    try:
        safe_search_enum = SafeSearchLevel(safe_search)
    except ValueError:
        safe_search_enum = SafeSearchLevel.MODERATE

    results = asyncio.run(search_service.search(
        query=query,
        search_type=search_type_enum,
        page=page,
        language=language_enum,
        region=region_enum,
        safe_search=safe_search_enum,
    ))

    return jsonify(results.to_dict())


@bp.route("/suggestions")
def suggestions():
    """API endpoint for search suggestions."""
    if not config.API_ENABLED:
        return jsonify({"error": "API is disabled"}), 403

    query = request.args.get("q", "")

    if len(query) < 2:
        return jsonify([])

    from atomic_search.services.search import search_service
    suggestions = asyncio.run(search_service.get_suggestions(query))
    return jsonify(suggestions)


@bp.route("/trending")
def trending():
    """API endpoint for trending searches."""
    if not config.API_ENABLED:
        return jsonify({"error": "API is disabled"}), 403

    limit = request.args.get("limit", 10, type=int)
    region = request.args.get("region")

    from atomic_search.services.voting import voting_service
    trending = voting_service.get_trending(limit=limit, region=region)

    # If no trending from voting service, return sample trending topics
    if not trending:
        sample_trending = [
            {"query": "Python Programming", "url": "/search?q=python+programming"},
            {"query": "Machine Learning", "url": "/search?q=machine+learning"},
            {"query": "Web Development", "url": "/search?q=web+development"},
            {"query": "Privacy Tools", "url": "/search?q=privacy+tools"},
            {"query": "Open Source", "url": "/search?q=open+source"},
            {"query": "AI Assistants", "url": "/search?q=ai+assistants"},
            {"query": "Cloud Computing", "url": "/search?q=cloud+computing"},
            {"query": "Cybersecurity", "url": "/search?q=cybersecurity"},
        ]
        return jsonify(sample_trending[:limit])

    return jsonify([
        {
            "url": t.url,
            "title": t.title,
            "snippet": t.snippet,
            "votes": t.votes,
            "upvotes": t.upvotes,
            "downvotes": t.downvotes,
            "trending_score": t.trending_score,
        }
        for t in trending
    ])


@bp.route("/stats", methods=["GET"])
def stats():
    """Get voting statistics for the current user."""
    from atomic_search.utils.security import hash_ip
    from atomic_search.services.voting import voting_service
    
    ip_hash = hash_ip(request.remote_addr or "0.0.0.0")
    session_id = request.headers.get("X-Session-ID", "")
    
    vote_stats = voting_service.get_vote_count(ip_hash, session_id)
    
    return jsonify({
        "votes_today": vote_stats.get("votes_today", 0),
        "votes_remaining": vote_stats.get("votes_remaining", 100),
        "in_cooldown": vote_stats.get("in_cooldown", False),
        "max_votes_per_day": config.MAX_VOTES_PER_DAY,
    })


@bp.route("/vote", methods=["POST"])
def vote():
    """API endpoint for voting."""
    if not config.API_ENABLED or not config.VOTING_ENABLED:
        return jsonify({"error": "Voting is disabled"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    url = data.get("url", "")
    vote_type = data.get("type")

    # Handle string vote types
    if isinstance(vote_type, str):
        if vote_type in ("1", "up", "upvote"):
            vote_type = 1
        elif vote_type in ("-1", "down", "downvote"):
            vote_type = -1
        else:
            return jsonify({"error": "Invalid vote type"}), 400

    if vote_type not in (1, -1):
        return jsonify({"error": "Invalid vote type"}), 400

    from atomic_search.utils.security import hash_ip
    from atomic_search.services.voting import voting_service

    ip_hash = hash_ip(request.remote_addr or "0.0.0.0")
    session_id = request.headers.get("X-Session-ID", "")

    success, message, stats = voting_service.vote(
        url=url,
        vote_type=vote_type,
        ip_hash=ip_hash,
        session_id=session_id,
    )

    return jsonify({
        "success": success,
        "message": message,
        "stats": stats,
    })


@bp.route("/tools/translate", methods=["POST"])
async def translate():
    """API endpoint for translation."""
    if not config.API_ENABLED or not config.TRANSLATION_ENABLED:
        return jsonify({"error": "Translation is disabled"}), 403

    data = request.get_json()
    text = data.get("text", "")
    target_lang = data.get("target", "en")
    source_lang = data.get("source", "auto")

    if not text:
        return jsonify({"error": "Text is required"}), 400

    # Would use translation API in production
    translated = f"[Translated to {target_lang}] {text}"

    return jsonify({
        "original": text,
        "translated": translated,
        "source_lang": source_lang,
        "target_lang": target_lang,
    })


@bp.route("/tools/calculator", methods=["GET"])
def calculator():
    """API endpoint for calculator."""
    if not config.API_ENABLED or not config.CALCULATOR_ENABLED:
        return jsonify({"error": "Calculator is disabled"}), 403

    expression = request.args.get("expr", "")

    try:
        # Safe evaluation for basic math
        allowed_chars = set("0123456789+-*/().^ ")
        if all(c in allowed_chars for c in expression):
            result = eval(expression)  # Note: In production, use a safer evaluator
            return jsonify({"expression": expression, "result": result})
        else:
            return jsonify({"error": "Invalid expression"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/tools/convert", methods=["POST"])
async def convert():
    """API endpoint for currency/unit conversion."""
    if not config.API_ENABLED:
        return jsonify({"error": "API is disabled"}), 403

    data = request.get_json()
    conversion_type = data.get("type")  # "currency" or "unit"
    value = data.get("value")
    from_unit = data.get("from")
    to_unit = data.get("to")

    if not all([conversion_type, value, from_unit, to_unit]):
        return jsonify({"error": "Missing required fields"}), 400

    # Would perform actual conversion in production
    return jsonify({
        "type": conversion_type,
        "from": f"{value} {from_unit}",
        "to": f"{value} {to_unit}",
        "result": value,  # Placeholder
    })


@bp.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "version": config.APP_VERSION,
        "uptime": "N/A",  # Would track in production
    })


@bp.route("/info")
def info():
    """API information endpoint."""
    return jsonify({
        "name": config.APP_NAME,
        "version": config.APP_VERSION,
        "features": {
            "search": True,
            "images": True,
            "videos": True,
            "news": True,
            "voting": config.VOTING_ENABLED,
            "ai": config.AI_PROVIDER.value != "none",
            "bookmarks": config.BOOKMARKS_ENABLED,
            "translations": config.TRANSLATION_ENABLED,
            "calculator": config.CALCULATOR_ENABLED,
        },
        "endpoints": {
            "search": "/api/v1/search",
            "suggestions": "/api/v1/suggestions",
            "trending": "/api/v1/trending",
            "vote": "/api/v1/vote",
            "health": "/api/v1/health",
            "stats": "/api/v1/stats",
        },
    })
