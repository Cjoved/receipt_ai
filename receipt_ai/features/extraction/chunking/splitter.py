from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha1

from langchain_text_splitters import RecursiveCharacterTextSplitter

from receipt_ai.features.extraction.chunking.models import ChunkRecord, TextSegment
from receipt_ai.features.extraction.config import ExtractionConfig


@dataclass(frozen=True)
class ChunkBuildInput:
    file_key: str
    source_name: str
    doc_type: str
    segments: list[TextSegment]


def build_chunks(payload: ChunkBuildInput, config: ExtractionConfig) -> list[ChunkRecord]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    chunks: list[ChunkRecord] = []
    running_char = 0
    seen_hashes: set[str] = set()
    idx = 0

    for segment in payload.segments:
        texts = splitter.split_text(segment.content)
        for piece in texts:
            stripped = piece.strip()
            if len(stripped) < config.chunk_min_chars:
                continue
            fingerprint = sha1(stripped.encode("utf-8")).hexdigest()
            if fingerprint in seen_hashes:
                continue
            seen_hashes.add(fingerprint)
            char_start = running_char
            char_end = running_char + len(stripped)
            running_char = char_end + 1
            chunks.append(
                ChunkRecord(
                    file_key=payload.file_key,
                    source_name=payload.source_name,
                    chunk_index=idx,
                    content=stripped,
                    token_count_est=max(1, len(stripped.split())),
                    char_start=char_start,
                    char_end=char_end,
                    section_type=segment.section_type or "fallback",
                    metadata={
                        "chunk_of": 0,
                        "doc_type": payload.doc_type,
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                )
            )
            idx += 1

    total = len(chunks)
    for chunk in chunks:
        chunk.metadata["chunk_of"] = total
    return chunks
