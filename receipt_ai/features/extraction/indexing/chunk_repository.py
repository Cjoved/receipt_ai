from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import re
from typing import Any

from receipt_ai.features.extraction.chunking.models import ChunkRecord
from receipt_ai.features.extraction.config import ExtractionConfig


_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def _sanitize(value: str) -> str:
    return _SAFE.sub("_", value).strip("_") or "unknown"


def sanitize_index_path_segment(value: str) -> str:
    """Stable folder/filename segment for on-disk index paths (matches persisted chunk files)."""
    return _sanitize(value)


class ChunkRepository:
    def __init__(self, config: ExtractionConfig) -> None:
        self._base = Path(config.index_output_dir)
        self._status_file = self._base / "index_status.json"
        self._base.mkdir(parents=True, exist_ok=True)
        if not self._status_file.exists():
            self._status_file.write_text("{}", encoding="utf-8")

    def save_chunks(self, folder: str, filename: str, chunks: list[ChunkRecord]) -> str:
        target_dir = self._base / _sanitize(folder)
        target_dir.mkdir(parents=True, exist_ok=True)
        out = target_dir / f"{_sanitize(filename)}.chunks.json"
        payload = [asdict(chunk) for chunk in chunks]
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(out)

    def set_status(self, file_key: str, status: str, *, reason: str = "") -> None:
        state = self._load_statuses()
        state[file_key] = {"status": status, "reason": reason}
        self._status_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_status(self, file_key: str) -> str:
        state = self._load_statuses()
        row = state.get(file_key, {})
        return str(row.get("status", "pending"))

    def _load_statuses(self) -> dict[str, Any]:
        try:
            return json.loads(self._status_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
