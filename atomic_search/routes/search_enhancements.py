"""
Search enhancements for Atomic Search.

Provides advanced search features, filters, and utilities.
"""

import re
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from flask import Blueprint, jsonify, request

from atomic_search.config import config


bp = Blueprint("search_enhance", __name__, url_prefix="/api/v1/search")


# Search operators
SEARCH_OPERATORS = {
    "site:": "Filter by domain",
    "inurl:": "Search in URL",
    "intitle:": "Search in title",
    "intext:": "Search in body text",
    "filetype:": "Search by file type",
    "related:": "Related sites",
    "cache:": "Cached version",
    "define:": "Definition",
    "weather:": "Weather",
    "stock:": "Stock quote",
    "movie:": "Movie info",
    "map:": "Maps",
    "books:": "Book search",
    "-": "Exclude term",
    "+": "Require term",
    '"': "Exact phrase",
    "OR": "Logical OR",
    "AND": "Logical AND",
}


# Time filters
TIME_FILTERS = {
    "d": ("Past 24 hours", 1),
    "w": ("Past week", 7),
    "m": ("Past month", 30),
    "y": ("Past year", 365),
}


# Safe search levels
SAFE_SEARCH_LEVELS = {
    "off": "No filtering",
    "moderate": "Some filtering",
    "strict": "Strict filtering",
}


@bp.route("/operators")
def get_operators():
    """Get list of supported search operators."""
    return jsonify({
        "operators": SEARCH_OPERATORS,
        "examples": {
            "site:wikipedia.org python": "Search Wikipedia for Python",
            '"exact phrase"': "Search for exact phrase",
            "filetype:pdf python": "Find PDF documents about Python",
            "python -java": "Python but not Java",
        }
    })


@bp.route("/parse", methods=["POST"])
def parse_query():
    """Parse a search query and extract components."""
    data = request.get_json()
    query = data.get("query", "")
    
    parsed = {
        "original": query,
        "terms": [],
        "operators": [],
        "filters": {},
        "clean_query": query,
    }
    
    # Extract quoted phrases
    phrases = re.findall(r'"([^"]+)"', query)
    if phrases:
        parsed["phrases"] = phrases
        parsed["clean_query"] = re.sub(r'"[^"]+"', '', query)
    
    # Extract operators
    for op in SEARCH_OPERATORS.keys():
        if op in query:
            parsed["operators"].append(op)
    
    # Extract time filter
    for code, (name, days) in TIME_FILTERS.items():
        if f"tbs=qdr:{code}" in query or f"time:{code}" in query.lower():
            parsed["filters"]["time"] = {"code": code, "name": name, "days": days}
            parsed["clean_query"] = re.sub(rf'time:{code}', '', parsed["clean_query"], flags=re.IGNORECASE)
    
    # Clean up query
    parsed["clean_query"] = ' '.join(parsed["clean_query"].split())
    
    return jsonify(parsed)


@bp.route("/suggest")
def suggest():
    """Get search suggestions based on query."""
    query = request.args.get("q", "")
    
    if not query or len(query) < 2:
        return jsonify({"suggestions": []})
    
    # Generate suggestions based on common patterns
    suggestions = []
    
    # Common completions
    common_suffixes = [
        " tutorial", " documentation", " github", " api",
        " examples", " download", " free", " online",
        " python", " javascript", " java", " rust",
    ]
    
    for suffix in common_suffixes:
        if query.lower() in f"{query}{suffix}".lower()[:len(query)+3]:
            suggestions.append(f"{query}{suffix}")
    
    # Trending searches (mock data)
    trending = [
        f"{query} news",
        f"{query} latest",
        f"{query} 2024",
        f"best {query}",
        f"how to {query}",
    ]
    
    suggestions.extend(trending[:5])
    
    return jsonify({
        "query": query,
        "suggestions": list(set(suggestions))[:8]
    })


@bp.route("/filters")
def get_filters():
    """Get available search filters."""
    return jsonify({
        "time": TIME_FILTERS,
        "safe_search": SAFE_SEARCH_LEVELS,
        "types": {
            "web": "Web results",
            "images": "Image results",
            "videos": "Video results",
            "news": "News articles",
            "shopping": "Product listings",
            "books": "Book results",
            "maps": "Map locations",
        },
        "regions": {
            "global": "Worldwide",
            "us": "United States",
            "uk": "United Kingdom",
            "ca": "Canada",
            "au": "Australia",
            "de": "Germany",
            "fr": "France",
            "jp": "Japan",
            "in": "India",
            "br": "Brazil",
        },
        "languages": {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
        }
    })


@bp.route("/advanced", methods=["POST"])
def advanced_search():
    """Execute advanced search with multiple filters."""
    data = request.get_json()
    query = data.get("query", "")
    filters = data.get("filters", {})
    
    # Build advanced query
    advanced_query = query
    
    # Add time filter
    if filters.get("time"):
        advanced_query += f" tbs=qdr:{filters['time']}"
    
    # Add site filter
    if filters.get("site"):
        advanced_query += f" site:{filters['site']}"
    
    # Add filetype filter
    if filters.get("filetype"):
        advanced_query += f" filetype:{filters['filetype']}"
    
    return jsonify({
        "query": query,
        "advanced_query": advanced_query,
        "filters_applied": filters,
        "search_url": f"/search?q={advanced_query}",
    })


@bp.route("/history")
def search_history():
    """Get search history for current user."""
    # In production, this would use the database
    # For now, return empty history
    return jsonify({
        "history": [],
        "recent": [],
        "saved": [],
    })


@bp.route("/trending")
def trending():
    """Get trending searches."""
    # Mock trending data - in production, this would be computed from actual searches
    return jsonify({
        "trending": [
            {"query": "AI developments 2024", "count": 15000},
            {"query": "Python 3.13 release", "count": 12000},
            {"query": "privacy focused search", "count": 9500},
            {"query": "local LLM setup", "count": 8200},
            {"query": "Rust vs Go", "count": 7800},
        ],
        "categories": {
            "technology": ["AI", "Python", "Rust", "JavaScript"],
            "news": ["election", "climate", "economy"],
            "entertainment": ["movies", "gaming", "music"],
        }
    })
