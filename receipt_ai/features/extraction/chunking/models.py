from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TextSegment:
    section_type: str
    content: str


@dataclass
class ChunkRecord:
    file_key: str
    source_name: str
    chunk_index: int
    content: str
    token_count_est: int
    char_start: int
    char_end: int
    section_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
