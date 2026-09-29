"""Offline /api/chat contract regressions using an injected adaptive chat service."""

import unittest
from adaptive_agent.flask_app import create_app


class FakeChatService:
    def __init__(self):
        self.calls = []
        self.resets = []

    def chat(self, session_id, message):
        self.calls.append((session_id, message))
        return {"assistant": "已回复", "tools_used": [], "status": "ASK", "steps": 1}

    def reset(self, session_id):
        self.resets.append(session_id)


class ChatSessionTests(unittest.TestCase):
    def setUp(self):
        self.service = FakeChatService()
        self.app = create_app(self.service)
        self.client = self.app.test_client()

    def post(self, message, session_id=None):
        response = self.client.post("/api/chat", json={"message": message, "session_id": session_id})
        return response.get_json(), response.status_code

    def test_api_preserves_session_id_and_adaptive_response_contract(self):
        response, status = self.post("我应该早点上床吗？")

        self.assertEqual(status, 200)
        self.assertIn("session_id", response)
        self.assertEqual(response["assistant"], "已回复")
        self.assertEqual(response["status"], "ASK")
        self.assertEqual(self.service.calls, [(response["session_id"], "我应该早点上床吗？")])

    def test_existing_session_id_is_reused(self):
        response, _ = self.post("继续", "session-1")

        self.assertEqual(response["session_id"], "session-1")
        self.assertEqual(self.service.calls, [("session-1", "继续")])

    def test_reset_delegates_to_adaptive_session_service(self):
        response = self.client.post("/api/reset", json={"session_id": "session-1"})
        response, status = response.get_json(), response.status_code

        self.assertEqual((response, status), ({"ok": True}, 200))
        self.assertEqual(self.service.resets, ["session-1"])

    def test_blank_message_does_not_invoke_service(self):
        response, status = self.post("  ")

        self.assertEqual((response, status), ({"error": "message is required"}, 400))
        self.assertEqual(self.service.calls, [])


if __name__ == "__main__":
    unittest.main()
