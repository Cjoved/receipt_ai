from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Literal

ExtractionStatus = Literal["success", "failed", "skipped", "cancelled"]


@dataclass(frozen=True)
class ExtractionRequest:
    filename: str
    content_type: str | None
    file_bytes: bytes
    storage_folder: str
    cancel_event: threading.Event | None = None


@dataclass
class ExtractionResult:
    filename: str
    status: ExtractionStatus
    text: str = ""
    extractor_used: str = ""
    warnings: list[str] = field(default_factory=list)
    error: str = ""
    duration_ms: int = 0
    output_path: str = ""
    pages_total: int = 0
    pages_extracted: int = 0
    pages_skipped: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)
