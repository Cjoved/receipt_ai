from __future__ import annotations

import re


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def normalize_extracted_text(text: str) -> str:
    cleaned = _CONTROL_CHARS.sub("", text)
    cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    cleaned = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", cleaned)
    cleaned = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", cleaned)
    cleaned = re.sub(r"[^\S\n]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
