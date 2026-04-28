from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import re
import time
from typing import Any

from receipt_ai.features.extraction.chunking.models import ChunkRecord
from receipt_ai.features.extraction.config import ExtractionConfig


_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def _sanitize(value: str) -> str:
    return _SAFE.sub("_", value).strip("_") or "unknown"


def sanitize_index_path_segment(value: str) -> str:
    """Stable folder/filename segment for on-disk index paths (matches persisted chunk files)."""
    return _sanitize(value)


def _status_key(file_key: str) -> str:
    """Case-insensitive key for index status rows."""
    return str(file_key or "").strip().casefold()


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
        now_epoch = int(time.time())
        key = _status_key(file_key)
        existing = state.get(key, {})
        row = {
            "status": status,
            "reason": reason,
            "updated_at_epoch": now_epoch,
        }
        if status == "processing":
            prev_started = existing.get("processing_started_epoch")
            row["processing_started_epoch"] = int(prev_started) if prev_started else now_epoch
        state[key] = row
        self._write_statuses(state)

    def begin_processing(self, file_key: str, *, stale_after_seconds: int) -> tuple[bool, bool]:
        state = self._load_statuses()
        now_epoch = int(time.time())
        key = _status_key(file_key)
        row = state.get(key, {})
        recovered_stale = False

        if isinstance(row, dict) and str(row.get("status", "")).lower() == "processing":
            started_raw = row.get("processing_started_epoch")
            try:
                started_epoch = int(started_raw)
            except (TypeError, ValueError):
                # Legacy status rows may miss processing_started_epoch; treat as stale.
                started_epoch = now_epoch - max(1, stale_after_seconds) - 1
            if now_epoch - started_epoch < max(1, stale_after_seconds):
                return False, False
            recovered_stale = True

        state[key] = {
            "status": "processing",
            "reason": "",
            "updated_at_epoch": now_epoch,
            "processing_started_epoch": now_epoch,
        }
        self._write_statuses(state)
        return True, recovered_stale

    def get_status(self, file_key: str) -> str:
        state = self._load_statuses()
        row = state.get(_status_key(file_key), {})
        return str(row.get("status", "pending"))

    def get_status_row(self, file_key: str) -> dict[str, Any]:
        state = self._load_statuses()
        row = state.get(_status_key(file_key), {})
        if not isinstance(row, dict):
            return {}
        return row

    def _load_statuses(self) -> dict[str, Any]:
        try:
            raw = json.loads(self._status_file.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return {}
            normalized: dict[str, Any] = {}
            for key, row in raw.items():
                norm_key = _status_key(str(key))
                normalized[norm_key] = row
            return normalized
        except Exception:
            return {}

    def _write_statuses(self, state: dict[str, Any]) -> None:
        self._status_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
