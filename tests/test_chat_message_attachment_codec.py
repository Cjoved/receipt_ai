import unittest

from receipt_ai.features.chat.service import _pack_user_message, _unpack_user_message
from receipt_ai.features.chat.suggestions import FALLBACK_SUGGESTIONS, build_hybrid_suggestions


class ChatAttachmentCodecTests(unittest.TestCase):
    def test_pack_unpack_roundtrip_with_attachments(self):
        packed = _pack_user_message(
            "hello",
            [{"name": "a.png", "preview_url": "data:image/png;base64,abc"}],
        )
        content, attachments = _unpack_user_message(packed)
        self.assertEqual(content, "hello")
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]["name"], "a.png")

    def test_unpack_plain_message_returns_no_attachments(self):
        content, attachments = _unpack_user_message("plain text")
        self.assertEqual(content, "plain text")
        self.assertEqual(attachments, [])

    def test_hybrid_suggestions_prioritize_context_then_fallback(self):
        prompts = build_hybrid_suggestions(folder_name="Testing Files", file_name="")
        self.assertGreaterEqual(len(prompts), 3)
        self.assertIn(FALLBACK_SUGGESTIONS[0], prompts)


if __name__ == "__main__":
    unittest.main()
