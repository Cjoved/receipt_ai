from __future__ import annotations

import base64
import json
import sys
from dataclasses import asdict
from pathlib import Path

from receipt_ai.features.extraction.models import ExtractionRequest
from receipt_ai.features.extraction.orchestrator import ExtractionOrchestrator


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    req = ExtractionRequest(
        filename=str(raw.get("filename", "")),
        content_type=(str(raw.get("content_type")) if raw.get("content_type") is not None else None),
        file_bytes=base64.b64decode(str(raw.get("file_bytes_b64", ""))),
        storage_folder=str(raw.get("storage_folder", "")),
    )
    orchestrator = ExtractionOrchestrator()
    result = orchestrator.extract(req)
    output_path.write_text(json.dumps(asdict(result), ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
