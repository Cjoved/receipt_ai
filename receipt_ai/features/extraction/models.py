from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ExtractionStatus = Literal["success", "failed", "skipped"]


@dataclass(frozen=True)
class ExtractionRequest:
    filename: str
    content_type: str | None
    file_bytes: bytes
    storage_folder: str


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
