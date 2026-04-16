from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from receipt_ai.features.extraction.chunking.models import ChunkRecord


def chunk_record_from_dict(row: dict[str, Any]) -> ChunkRecord | None:
    try:
        emb = row.get("embedding")
        if not isinstance(emb, list):
            emb = None
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            meta = {}
        return ChunkRecord(
            file_key=str(row["file_key"]),
            source_name=str(row["source_name"]),
            chunk_index=int(row["chunk_index"]),
            content=str(row["content"]),
            token_count_est=int(row["token_count_est"]),
            char_start=int(row["char_start"]),
            char_end=int(row["char_end"]),
            section_type=str(row["section_type"]),
            metadata=meta,
            embedding=emb,
        )
    except (KeyError, TypeError, ValueError):
        return None


def iter_chunk_files(base: Path) -> Iterator[Path]:
    if not base.is_dir():
        return
    for path in base.rglob("*.chunks.json"):
        if path.is_file():
            yield path


def load_chunks_from_file(path: Path) -> list[ChunkRecord]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    out: list[ChunkRecord] = []
    for row in raw:
        if isinstance(row, dict):
            rec = chunk_record_from_dict(row)
            if rec is not None:
                out.append(rec)
    return out


def load_all_chunk_records(index_root: Path) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    for fp in iter_chunk_files(index_root):
        chunks.extend(load_chunks_from_file(fp))
    return chunks
