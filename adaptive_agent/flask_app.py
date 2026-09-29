"""Import-light production Flask factory for the adaptive chat route."""
from __future__ import annotations

import uuid

from flask import Flask, jsonify, request
from flask_cors import CORS

from .service import AdaptiveChatService


def _create_adaptive_chat_service() -> AdaptiveChatService:
    """Lazily construct the existing production Agent components on demand."""
    from model_config import create_chat_model
    from .answer_generation import LLMAnswerGenerator
    from .input_understanding import LLMInputUnderstander
    from .runner import AdaptiveAgentLoop
    from .tools import RagRetrievalTool, SessionDiaryTool

    model = create_chat_model()
    return AdaptiveChatService(AdaptiveAgentLoop(
        understander=LLMInputUnderstander(model), retrieval_tool=RagRetrievalTool(),
        diary_tool=SessionDiaryTool(), answer_generator=LLMAnswerGenerator(model),
    ))


def create_app(chat_service=None):
    """Create the production adaptive `/api/chat` route with injectable service."""
    app = Flask(__name__)
    CORS(app, supports_credentials=True)
    chat_service = chat_service or _create_adaptive_chat_service()

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/api/chat", methods=["POST"])
    def chat():
        data = request.get_json(force=True) or {}
        message = (data.get("message") or "").strip()
        session_id = data.get("session_id")
        if not message:
            return jsonify({"error": "message is required"}), 400
        if not session_id:
            session_id = str(uuid.uuid4())
        return jsonify({"session_id": session_id, **chat_service.chat(session_id, message)}), 200

    @app.route("/api/reset", methods=["POST"])
    def reset():
        data = request.get_json(force=True) or {}
        session_id = data.get("session_id")
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        chat_service.reset(session_id)
        return jsonify({"ok": True}), 200

    return app
