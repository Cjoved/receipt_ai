import unittest
from pathlib import Path


class ChatComponentBindingsTests(unittest.TestCase):
    def test_composer_has_enter_send_script_binding(self):
        source = Path("receipt_ai/components/chat_components.py").read_text(encoding="utf-8")
        self.assertIn("if (event.key === 'Enter' && !event.shiftKey && !event.isComposing)", source)
        self.assertIn("callback=ChatState.handle_composer_key_signal", source)

    def test_assistant_bubble_has_retry_and_citations(self):
        source = Path("receipt_ai/components/chat_components.py").read_text(encoding="utf-8")
        self.assertIn("on_click=ChatState.retry_last_turn", source)
        self.assertIn("sources_preview", source)

    def test_history_has_hover_delete_button(self):
        source = Path("receipt_ai/components/chat_components.py").read_text(encoding="utf-8")
        self.assertIn("chat-thread-delete-btn", source)
        self.assertIn("on_click=ChatState.delete_thread(thread[\"id\"])", source)


if __name__ == "__main__":
    unittest.main()
