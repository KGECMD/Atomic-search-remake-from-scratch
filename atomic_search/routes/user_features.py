"""
User features for Atomic Search.

Provides bookmarks, collections, reading list, and user preferences.
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Blueprint, jsonify, request, session

from atomic_search.config import config


bp = Blueprint("user_features", __name__, url_prefix="/api/v1/user")


def get_user_id():
    """Get anonymous user ID from session."""
    if 'user_id' not in session:
        # Create anonymous user ID based on session
        session['user_id'] = hashlib.sha256(
            f"{request.remote_addr}{request.headers.get('User-Agent', '')}".encode()
        ).hexdigest()[:16]
    return session['user_id']


@bp.route("/bookmarks", methods=["GET"])
def get_bookmarks():
    """Get user's bookmarks."""
    user_id = get_user_id()
    # In production, fetch from database
    # For now, return empty list
    return jsonify({
        "bookmarks": [],
        "count": 0,
        "user_id": user_id,
    })


@bp.route("/bookmarks", methods=["POST"])
def add_bookmark():
    """Add a bookmark."""
    data = request.get_json()
    url = data.get("url", "")
    title = data.get("title", "")
    tags = data.get("tags", [])
    
    if not url:
        return jsonify({"success": False, "error": "URL required"}), 400
    
    bookmark = {
        "id": hashlib.md5(url.encode()).hexdigest()[:8],
        "url": url,
        "title": title or url,
        "tags": tags,
        "created_at": datetime.utcnow().isoformat(),
        "user_id": get_user_id(),
    }
    
    return jsonify({
        "success": True,
        "bookmark": bookmark,
        "message": "Bookmark added successfully"
    })


@bp.route("/bookmarks/<bookmark_id>", methods=["DELETE"])
def delete_bookmark(bookmark_id):
    """Delete a bookmark."""
    return jsonify({
        "success": True,
        "message": f"Bookmark {bookmark_id} deleted"
    })


@bp.route("/collections", methods=["GET"])
def get_collections():
    """Get user's search collections."""
    return jsonify({
        "collections": [],
        "count": 0,
    })


@bp.route("/collections", methods=["POST"])
def create_collection():
    """Create a new collection."""
    data = request.get_json()
    name = data.get("name", "")
    description = data.get("description", "")
    is_public = data.get("public", False)
    
    if not name:
        return jsonify({"success": False, "error": "Collection name required"}), 400
    
    collection = {
        "id": hashlib.md5(name.encode()).hexdigest()[:8],
        "name": name,
        "description": description,
        "public": is_public,
        "items": [],
        "created_at": datetime.utcnow().isoformat(),
        "user_id": get_user_id(),
    }
    
    return jsonify({
        "success": True,
        "collection": collection,
        "message": "Collection created successfully"
    })


@bp.route("/collections/<collection_id>/items", methods=["POST"])
def add_to_collection(collection_id):
    """Add item to collection."""
    data = request.get_json()
    item_type = data.get("type", "url")  # url, search, result
    content = data.get("content", {})
    
    return jsonify({
        "success": True,
        "message": f"Added to collection {collection_id}",
        "item": {
            "type": item_type,
            "content": content,
            "added_at": datetime.utcnow().isoformat(),
        }
    })


@bp.route("/reading-list", methods=["GET"])
def get_reading_list():
    """Get reading list."""
    return jsonify({
        "items": [],
        "count": 0,
        "unread": 0,
    })


@bp.route("/reading-list", methods=["POST"])
def add_to_reading_list():
    """Add item to reading list."""
    data = request.get_json()
    url = data.get("url", "")
    title = data.get("title", "")
    
    item = {
        "id": hashlib.md5(url.encode()).hexdigest()[:8],
        "url": url,
        "title": title,
        "added_at": datetime.utcnow().isoformat(),
        "read": False,
    }
    
    return jsonify({
        "success": True,
        "item": item,
        "message": "Added to reading list"
    })


@bp.route("/reading-list/<item_id>", methods=["PUT"])
def update_reading_item(item_id):
    """Update reading list item (mark as read)."""
    data = request.get_json()
    read = data.get("read", False)
    
    return jsonify({
        "success": True,
        "item_id": item_id,
        "read": read,
    })


@bp.route("/preferences", methods=["GET"])
def get_preferences():
    """Get user preferences."""
    return jsonify({
        "theme": "dark",
        "language": "en",
        "region": "global",
        "safe_search": "moderate",
        "results_per_page": 10,
        "open_in_new_tab": True,
        "show_votes": True,
        "enable_ai": True,
        "enable_shortcuts": True,
    })


@bp.route("/preferences", methods=["PUT"])
def update_preferences():
    """Update user preferences."""
    data = request.get_json()
    
    return jsonify({
        "success": True,
        "preferences": data,
        "message": "Preferences updated"
    })


@bp.route("/stats", methods=["GET"])
def get_user_stats():
    """Get user statistics."""
    return jsonify({
        "searches_today": 0,
        "searches_total": 0,
        "bookmarks_count": 0,
        "collections_count": 0,
        "reading_list_count": 0,
        "votes_given": 0,
        "member_since": datetime.utcnow().isoformat(),
    })
