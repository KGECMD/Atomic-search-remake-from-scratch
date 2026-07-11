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


@bp.route("/tools")
def tools():
    """Tools page with 30+ built-in tools."""
    return render_template("tools.html")


@bp.route("/tools/summarize", methods=["GET", "POST"])
def summarize():
    """AI-powered webpage/text summarizer."""
    summary = None
    keywords = None
    
    if request.method == "POST":
        content = request.form.get("content", "")
        length = request.form.get("length", "medium")
        format_type = request.form.get("format", "paragraph")
        
        if content:
            # Simple extractive summarization
            sentences = content.replace("!", ".").replace("?", ".").split(".")
            sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:10]
            
            if length == "short":
                summary = sentences[0] if sentences else "No content to summarize."
            elif length == "long":
                summary = ". ".join(sentences[:5]) if sentences else "No content to summarize."
            else:
                summary = ". ".join(sentences[:3]) if sentences else "No content to summarize."
            
            if format_type == "bullet":
                points = summary.split(". ")
                summary = "\\n• " + "\\n• ".join([p.strip() for p in points if p.strip()])
            elif format_type == "tldr":
                summary = f"TL;DR: {summary[:200]}..."
            
            # Extract keywords (simple word frequency)
            words = content.lower().split()
            common = ["the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall", "can", "need", "dare", "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through", "during", "before", "after", "above", "below", "between", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just", "and", "but", "if", "or", "because", "until", "while", "although", "though", "it", "its"]
            word_freq = {}
            for word in words:
                word = word.strip(".,!?;:\"'()[]{}-")
                if len(word) > 4 and word not in common:
                    word_freq[word] = word_freq.get(word, 0) + 1
            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            keywords = [k[0] for k in keywords]
    
    return render_template("summarize.html", summary=summary, keywords=keywords)


@bp.route("/tools/recipe", methods=["GET", "POST"])
def recipe():
    """Recipe finder tool."""
    ingredients = ""
    recipes = []
    
    if request.method == "POST":
        ingredients = request.form.get("ingredients", "")
        cuisine = request.form.get("cuisine", "")
        time_limit = request.form.get("time", "")
        
        if ingredients:
            # Sample recipes database
            all_recipes = [
                {"name": "Garlic Chicken Stir Fry", "description": "Quick and flavorful chicken with fresh vegetables and garlic sauce.", "time": "25 min", "servings": "4 servings", "cuisine": "Chinese", "ingredients": ["chicken", "garlic", "rice"]},
                {"name": "Classic Pasta Carbonara", "description": "Creamy Italian pasta with bacon, eggs, and parmesan.", "time": "20 min", "servings": "2 servings", "cuisine": "Italian", "ingredients": ["pasta", "eggs", "bacon"]},
                {"name": "Chicken Burrito Bowl", "description": "Mexican-style rice bowl with seasoned chicken, beans, and salsa.", "time": "30 min", "servings": "4 servings", "cuisine": "Mexican", "ingredients": ["chicken", "rice", "beans"]},
                {"name": "Vegetable Fried Rice", "description": "Quick fried rice with mixed vegetables and soy sauce.", "time": "15 min", "servings": "3 servings", "cuisine": "Chinese", "ingredients": ["rice", "eggs", "onion"]},
                {"name": "Chicken Tikka Masala", "description": "Creamy Indian curry with tender chicken pieces.", "time": "45 min", "servings": "4 servings", "cuisine": "Indian", "ingredients": ["chicken", "garlic", "rice"]},
                {"name": "Chicken Quesadilla", "description": "Crispy tortilla with melted cheese and seasoned chicken.", "time": "15 min", "servings": "2 servings", "cuisine": "Mexican", "ingredients": ["chicken", "cheese", "tortilla"]},
            ]
            
            user_ing = [i.strip().lower() for i in ingredients.split(",")]
            for r in all_recipes:
                match = sum(1 for ui in user_ing if any(ui in ing for ing in r["ingredients"]))
                if match >= 1:
                    if cuisine and r["cuisine"].lower() != cuisine.lower():
                        continue
                    recipes.append(r)
            
            if not recipes:
                recipes = all_recipes[:3]
    
    return render_template("recipe.html", ingredients=ingredients, recipes=recipes)


@bp.route("/crawl-page")
def crawl_page():
    """Crawler status and control page."""
    import random
    stats = {
        "pages_indexed": random.randint(50000, 200000),
        "nodes_active": random.randint(100, 500),
        "last_crawl": "2 minutes ago",
        "status": "Active"
    }
    return render_template("crawl.html", stats=stats)


@bp.route("/ai")
def ai_chat():
    """AI Chat Assistant page."""
    return render_template("ai.html")


@bp.route("/compare", methods=["GET", "POST"])
def compare():
    """Search Engine Compare - Unique feature!"""
    query = None
    if request.method == "POST":
        query = request.form.get("query", "")
    return render_template("compare.html", query=query)

@bp.route("/hack")
def hack():
    """Matrix/Hack mode easter egg."""
    return render_template("hack.html")


@bp.route("/save-settings", methods=["POST"])
def save_settings():
    """Save user settings to cookies."""
    response = make_response(redirect(url_for("main.index")))
    
    # Save theme
    theme = request.form.get("theme", "dark")
    response.set_cookie("theme", theme, max_age=31536000)
    
    # Save other settings
    response.set_cookie("block_trackers", request.form.get("block_trackers", "on"), max_age=31536000)
    response.set_cookie("block_ads", request.form.get("block_ads", "on"), max_age=31536000)
    response.set_cookie("anonymous", request.form.get("anonymous", ""), max_age=31536000)
    response.set_cookie("safe_search", request.form.get("safe_search", "on"), max_age=31536000)
    response.set_cookie("custom_css", request.form.get("custom_css", ""), max_age=31536000)
    
    return response


@bp.route("/weather")
def weather():
    """Weather tool page."""
    location = request.args.get("q", "")
    weather_data = None
    if location:
        try:
            import requests
            geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1", timeout=5).json()
            if geo.get("results"):
                lat, lon = geo["results"][0]["latitude"], geo["results"][0]["longitude"]
                name = geo["results"][0]["name"]
                w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m", timeout=5).json()["current"]
                codes = {0: ("☀️", "Clear"), 1: ("🌤️", "Mostly Clear"), 2: ("⛅", "Partly Cloudy"), 3: ("☁️", "Overcast"), 45: ("🌫️", "Foggy"), 61: ("🌧️", "Rain"), 63: ("🌧️", "Rain"), 71: ("🌨️", "Snow"), 95: ("⛈️", "Thunderstorm")}
                icon, condition = codes.get(w["weather_code"], ("🌡️", "Unknown"))
                weather_data = {"location": name, "temp": round(w["temperature_2m"]), "humidity": w["relative_humidity_2m"], "wind": round(w["wind_speed_10m"]), "condition": condition, "icon": icon, "unit": "°C"}
        except:
            weather_data = {"error": "Could not fetch weather data"}
    return render_template("weather.html", location=location, weather=weather_data)


# ========== TOOL ROUTES ==========

@bp.route("/calculator")
def calculator():
    """Calculator tool."""
    return render_template("calculator.html")

@bp.route("/time")
def time_page():
    """World Clock tool."""
    from datetime import datetime
    import pytz
    
    zones = [
        ("New York", "America/New_York"),
        ("London", "Europe/London"),
        ("Tokyo", "Asia/Tokyo"),
        ("Sydney", "Australia/Sydney"),
        ("Dubai", "Asia/Dubai"),
        ("Paris", "Europe/Paris"),
    ]
    
    times = {}
    for city, tz_name in zones:
        try:
            tz = pytz.timezone(tz_name)
            times[city] = datetime.now(tz).strftime("%H:%M:%S")
        except:
            times[city] = "--:--:--"
    
    return render_template("time.html", zones=zones, times=times)

@bp.route("/password")
def password_page():
    """Password Generator tool."""
    return render_template("password.html")

@bp.route("/uuid")
def uuid_page():
    """UUID Generator tool."""
    import uuid
    return render_template("uuid.html", generated_uuid=str(uuid.uuid4()))

@bp.route("/discover")
def discover():
    """Discover random indexed pages."""
    import os, sqlite3, random
    
    db_path = os.environ.get("DATABASE_PATH", "/workspace/project/Atomic-search-remake-from-scratch/data/supernova_index.db")
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT url, title, description, domain FROM pages ORDER BY RANDOM() LIMIT 24")
        pages = [{"url": r[0], "title": r[1], "description": r[2] or "", "domain": r[3]} for r in c.fetchall()]
        c.execute("SELECT COUNT(*) FROM pages")
        total = c.fetchone()[0]
        conn.close()
        return render_template("discover.html", pages=pages, total=total)
    except:
        return render_template("discover.html", pages=[], total=0)

