"""
AI routes for Atomic Search.

Provides endpoints for AI-powered features:
- Chat assistant
- Search summaries
- Webpage summarization
"""

import asyncio
import json
import secrets
from flask import Blueprint, Response, jsonify, request, stream_with_context, session

from atomic_search.config import config
from atomic_search.ai import ai_service, AIMessage

bp = Blueprint("ai", __name__, url_prefix="/ai")


def get_conversation_id() -> str:
    """Get or create a conversation ID."""
    if "ai_conversation_id" not in session:
        session["ai_conversation_id"] = secrets.token_hex(16)
    return session["ai_conversation_id"]


@bp.route("/chat", methods=["POST"])
def chat():
    """Chat with the AI assistant."""
    if not config.AI_CHAT_ENABLED or not ai_service.is_available():
        return jsonify({"error": "AI chat is not available"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    message = data.get("message", "")
    conversation_id = data.get("conversation_id") or get_conversation_id()
    context = data.get("context")

    if not message:
        return jsonify({"error": "Message is required"}), 400

    response = asyncio.run(ai_service.chat(
        message=message,
        conversation_id=conversation_id,
        context=context,
    ))

    return jsonify({
        "response": response.content,
        "conversation_id": conversation_id,
        "provider": response.provider.value,
        "model": response.model,
        "error": response.error,
    })


@bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    """Stream chat with the AI assistant."""
    if not config.AI_CHAT_ENABLED or not ai_service.is_available():
        return jsonify({"error": "AI chat is not available"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    message = data.get("message", "")
    conversation_id = data.get("conversation_id") or get_conversation_id()
    context = data.get("context")

    if not message:
        return jsonify({"error": "Message is required"}), 400

    async def generate():
        full_response = ""
        async for chunk in ai_service.stream_chat(
            message=message,
            conversation_id=conversation_id,
            context=context,
        ):
            full_response += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        yield f"data: {json.dumps({'done': True, 'full': full_response})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
    )


@bp.route("/summarize/search", methods=["POST"])
def summarize_search():
    """Summarize search results."""
    if not config.AI_SUMMARIES_ENABLED or not ai_service.is_available():
        return jsonify({"error": "AI summaries are not available"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    query = data.get("query", "")
    results = data.get("results", [])

    if not query or not results:
        return jsonify({"error": "Query and results are required"}), 400

    summary = asyncio.run(ai_service.summarize_search_results(query, results))

    return jsonify({
        "summary": summary,
        "query": query,
        "result_count": len(results),
    })


@bp.route("/summarize/webpage", methods=["POST"])
def summarize_webpage():
    """Summarize a webpage."""
    if not ai_service.is_available():
        return jsonify({"error": "AI is not available"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    content = data.get("content", "")
    url = data.get("url", "")

    if not content:
        return jsonify({"error": "Content is required"}), 400

    summary = asyncio.run(ai_service.summarize_webpage(content, url))

    return jsonify({
        "summary": summary,
        "url": url,
    })


@bp.route("/conversation/<conversation_id>")
def get_conversation(conversation_id: str):
    """Get conversation history."""
    if not config.AI_CHAT_ENABLED:
        return jsonify({"error": "AI chat is not available"}), 403

    history = ai_service.get_conversation_history(conversation_id)

    return jsonify({
        "conversation_id": conversation_id,
        "messages": [m.to_dict() for m in history],
    })


@bp.route("/conversation/<conversation_id>", methods=["DELETE"])
def clear_conversation(conversation_id: str):
    """Clear conversation history."""
    if not config.AI_CHAT_ENABLED:
        return jsonify({"error": "AI chat is not available"}), 403

    ai_service.clear_conversation(conversation_id)

    return jsonify({
        "success": True,
        "conversation_id": conversation_id,
    })


@bp.route("/status")
def status():
    """Get AI service status."""
    return jsonify({
        "available": ai_service.is_available(),
        "provider": config.AI_PROVIDER.value,
        "model": config.AI_MODEL,
        "features": {
            "chat": config.AI_CHAT_ENABLED,
            "summaries": config.AI_SUMMARIES_ENABLED,
            "streaming": config.AI_STREAMING,
        },
    })
