import unittest
from pathlib import Path


class ChatComponentBindingsTests(unittest.TestCase):
    def test_composer_has_enter_send_script_binding(self):
        source = Path("receipt_ai/components/chat_components.py").read_text(encoding="utf-8")
        self.assertIn("enter_key_submit=True", source)
        self.assertIn("on_submit=ChatState.submit_chat_form", source)

    def test_assistant_bubble_has_retry_and_citations(self):
        source = Path("receipt_ai/components/chat_components.py").read_text(encoding="utf-8")
        self.assertIn("on_click=ChatState.retry_last_turn", source)
        self.assertIn("on_click=ChatState.copy_message_citation(", source)

    def test_history_has_hover_delete_button(self):
        source = Path("receipt_ai/components/chat_components.py").read_text(encoding="utf-8")
        self.assertIn("chat-thread-delete-btn", source)
        self.assertIn("on_click=ChatState.request_delete_thread(thread[\"id\"])", source)
        self.assertIn("delete_chat_confirm_modal()", source)

    def test_empty_state_has_suggestion_chips(self):
        source = Path("receipt_ai/components/chat_components.py").read_text(encoding="utf-8")
        self.assertIn("ChatState.show_suggestions", source)
        self.assertIn("ChatState.suggested_prompts", source)
        self.assertIn("on_click=ChatState.apply_suggestion(prompt)", source)

    def test_user_bubble_renders_attachment_preview(self):
        source = Path("receipt_ai/components/chat_components.py").read_text(encoding="utf-8")
        self.assertIn("m.get(\"attachment_preview_url_1\", \"\")", source)
        self.assertIn("on_click=ChatState.open_message_image_preview_group(", source)

    def test_message_action_tray_controls_present(self):
        source = Path("receipt_ai/components/chat_components.py").read_text(encoding="utf-8")
        self.assertIn("class_name=\"chat-bubble-actions\"", source)
        self.assertIn("on_click=ChatState.copy_message_action(m[\"content\"], \"assistant\", idx)", source)
        self.assertIn("on_click=ChatState.edit_message_to_draft(m[\"content\"], m.get(\"id\", \"\"), idx)", source)
        self.assertIn("on_submit=ChatState.submit_inline_edit_form", source)
        self.assertIn("on_click=ChatState.cancel_inline_edit", source)
        self.assertIn("on_click=ChatState.resend_message_from_bubble(m[\"content\"], m.get(\"id\", \"\"), idx)", source)
        self.assertIn("on_click=ChatState.regenerate_assistant_message(m.get(\"id\", \"\"), idx)", source)
        self.assertIn("on_click=ChatState.request_stop_generation", source)

    def test_feedback_and_share_export_stubs_present(self):
        source = Path("receipt_ai/components/chat_components.py").read_text(encoding="utf-8")
        self.assertIn("on_click=ChatState.set_message_feedback(m.get(\"id\", \"\"), \"up\")", source)
        self.assertIn("on_click=ChatState.set_message_feedback(m.get(\"id\", \"\"), \"down\")", source)
        self.assertIn("on_click=ChatState.open_message_source(m.get(\"id\", \"\"))", source)
        self.assertIn("source_selector_modal()", source)
        self.assertNotIn("on_click=ChatState.share_message_stub", source)
        self.assertNotIn("on_click=ChatState.export_message_stub", source)

    def test_preview_overlay_supports_escape_close(self):
        source = Path("receipt_ai/components/chat_components.py").read_text(encoding="utf-8")
        self.assertIn("chat-image-preview-overlay", source)
        self.assertIn("on_click=ChatState.close_chat_image_preview", source)


if __name__ == "__main__":
    unittest.main()
