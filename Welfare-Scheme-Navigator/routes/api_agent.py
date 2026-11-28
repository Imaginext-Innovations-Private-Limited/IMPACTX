"""
Agent Chat API Routes for Sahaaya AI.
Exposes REST endpoints for conversational AI welfare scheme navigation:
- POST /api/agent/chat: Main multi-turn conversation endpoint with tool calling
- GET  /api/agent/session/<conversation_id>: Inspect active session state
- POST /api/agent/reset: Reset a conversation session
- GET  /api/agent/status: Check Gemini client and tool calling availability
"""

import logging
from flask import Blueprint, request, jsonify
from agent.agent_orchestrator import AgentOrchestrator
from agent.conversation_manager import ConversationManager
from agent.gemini_client import GeminiClient

logger = logging.getLogger("api_agent")

agent_bp = Blueprint("agent_bp", __name__)

# Shared orchestrator and conversation manager instances
_gemini_client = GeminiClient()
_conversation_manager = ConversationManager()
_orchestrator = AgentOrchestrator(
    gemini_client=_gemini_client,
    conversation_manager=_conversation_manager,
)


@agent_bp.route("/agent/chat", methods=["POST"])
def agent_chat():
    """
    Main conversational agent endpoint for citizens.
    Accepts natural-language queries, runs Gemini tool-calling, and returns structured grounded guidance.
    """
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Request body must be a valid JSON object.",
            "status_code": 400,
        }), 400

    payload = request.get_json() or {}
    message = payload.get("message")
    conversation_id = payload.get("conversation_id")
    citizen_profile = payload.get("citizen_profile")

    if message is None or not str(message).strip():
        return jsonify({
            "success": False,
            "conversation_id": _conversation_manager.sanitize_conversation_id(conversation_id),
            "error": "The 'message' field is required and cannot be empty.",
            "status_code": 400,
        }), 400

    if citizen_profile is not None and not isinstance(citizen_profile, dict):
        return jsonify({
            "success": False,
            "conversation_id": _conversation_manager.sanitize_conversation_id(conversation_id),
            "error": "'citizen_profile' must be a dictionary of demographic attributes.",
            "status_code": 400,
        }), 400

    try:
        response_data = _orchestrator.process_message(
            message=str(message),
            conversation_id=conversation_id,
            citizen_profile=citizen_profile,
        )
        status_code = response_data.get("status_code", 200) if not response_data.get("success") else 200
        return jsonify(response_data), status_code
    except Exception as exc:
        logger.error(f"Unhandled error in agent_chat endpoint: {exc}")
        return jsonify({
            "success": False,
            "conversation_id": _conversation_manager.sanitize_conversation_id(conversation_id),
            "error": "An unexpected error occurred while processing your request. Please try again.",
            "status_code": 500,
        }), 500


@agent_bp.route("/agent/session/<conversation_id>", methods=["GET"])
def get_session(conversation_id):
    """Inspect the state and history count of an active session."""
    session = _conversation_manager.get_session(conversation_id)
    if not session:
        return jsonify({
            "success": False,
            "conversation_id": conversation_id,
            "error": f"Session '{conversation_id}' was not found or has expired.",
            "status_code": 404,
        }), 404

    return jsonify({
        "success": True,
        "session": session.to_dict(),
    }), 200


@agent_bp.route("/agent/reset", methods=["POST"])
def reset_session():
    """Reset and clear an existing conversation session."""
    payload = request.get_json(silent=True) or {}
    conversation_id = payload.get("conversation_id")

    if not conversation_id:
        return jsonify({
            "success": False,
            "error": "'conversation_id' is required to reset a session.",
            "status_code": 400,
        }), 400

    cleared = _conversation_manager.reset_session(conversation_id)
    return jsonify({
        "success": True,
        "conversation_id": conversation_id,
        "cleared": cleared,
        "message": f"Session '{conversation_id}' has been reset.",
    }), 200


@agent_bp.route("/agent/status", methods=["GET"])
def agent_status():
    """Check agent and Gemini API readiness."""
    status = _gemini_client.get_status()
    return jsonify({
        "success": True,
        "service": "Sahaaya AI Agent",
        "gemini_status": status,
        "supported_tools": [
            "search_schemes",
            "retrieve_scheme_information",
            "check_eligibility",
            "get_required_documents",
            "compare_schemes",
            "get_application_guidance",
        ],
    }), 200
