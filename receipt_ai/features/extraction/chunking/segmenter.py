from __future__ import annotations

import csv
import io
import re

from receipt_ai.features.extraction.chunking.models import TextSegment


def segment_text_for_chunking(text: str, filename: str) -> list[TextSegment]:
    lowered = filename.lower()
    if lowered.endswith(".csv"):
        return _segment_csv(text)
    if re.search(r"^##\s+(slide|sheet)\s+\d+", text, flags=re.IGNORECASE | re.MULTILINE):
        return _segment_by_heading(text)
    return _segment_paragraphs(text)


def _segment_csv(text: str) -> list[TextSegment]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    segments: list[TextSegment] = []
    batch_size = 60
    for i in range(0, len(rows), batch_size):
        window = rows[i : i + batch_size]
        lines = [" | ".join(cell.strip() for cell in row) for row in window]
        content = "\n".join(line for line in lines if line.strip())
        if content:
            segments.append(TextSegment(section_type="table", content=content))
    return segments


def _segment_by_heading(text: str) -> list[TextSegment]:
    raw_parts = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
    segments: list[TextSegment] = []
    for part in raw_parts:
        content = part.strip()
        if content:
            segments.append(TextSegment(section_type="heading", content=content))
    return segments


def _segment_paragraphs(text: str) -> list[TextSegment]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    return [TextSegment(section_type="paragraph", content=block) for block in blocks]
