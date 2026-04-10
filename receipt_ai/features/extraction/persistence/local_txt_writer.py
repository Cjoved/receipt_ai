from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from receipt_ai.features.extraction.models import ExtractionResult


_BAD = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_name(value: str) -> str:
    return _BAD.sub("_", value.strip()).strip("_") or "unknown"


def write_extraction_txt(output_dir: str, folder_name: str, result: ExtractionResult) -> str:
    base = Path(output_dir)
    stamp = datetime.now().strftime("%Y%m%d")
    target = base / _safe_name(folder_name) / stamp
    target.mkdir(parents=True, exist_ok=True)
    filename = _safe_name(result.filename) + ".txt"
    out = target / filename
    out.write_text(result.text, encoding="utf-8")
    return str(out)
