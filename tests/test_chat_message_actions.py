import unittest
from pathlib import Path


class ChatMessageActionsStateSourceTests(unittest.TestCase):
    def test_state_contains_core_message_actions(self):
        source = Path("receipt_ai/features/chat/state.py").read_text(encoding="utf-8")
        self.assertIn("def copy_message_action(", source)
        self.assertIn("def edit_message_to_draft(", source)
        self.assertIn("def submit_inline_edit(", source)
        self.assertIn("def submit_inline_edit_form(", source)
        self.assertIn("def cancel_inline_edit(", source)
        self.assertIn("def resend_message_from_bubble(", source)
        self.assertIn("def regenerate_assistant_message(", source)
        self.assertIn("def regenerate_last_response(", source)
        self.assertIn("def request_stop_generation(", source)
        self.assertIn("def submit_chat_form(", source)

    def test_state_contains_feedback_and_stub_actions(self):
        source = Path("receipt_ai/features/chat/state.py").read_text(encoding="utf-8")
        self.assertIn("def set_message_feedback(", source)
        self.assertIn("def share_message_stub(", source)
        self.assertIn("def export_message_stub(", source)
        self.assertIn("def copy_message_citation(", source)
        self.assertIn("def open_message_source(", source)
        self.assertIn("def open_source_selector_item(", source)
        self.assertIn("def show_prev_response_version(", source)
        self.assertIn("def show_next_response_version(", source)

    def test_shell_contains_action_tray_motion_rules(self):
        source = Path("receipt_ai/core/theme/shell.py").read_text(encoding="utf-8")
        self.assertIn(".chat-bubble-actions", source)
        self.assertIn(".chat-user-row > div:first-child:hover + .chat-bubble-actions", source)
        self.assertIn("@media (prefers-reduced-motion: reduce)", source)


if __name__ == "__main__":
    unittest.main()
