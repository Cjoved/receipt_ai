from __future__ import annotations

import asyncio
import base64
import json
import logging
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.cancel_checks import raise_if_cancelled
from receipt_ai.features.extraction.errors import ExtractionCancelledError, ExtractionError
from receipt_ai.features.extraction.models import ExtractionRequest, ExtractionResult
from receipt_ai.features.extraction.persistence.local_txt_writer import write_extraction_txt
from receipt_ai.features.extraction.postprocess.normalize_text import low_quality_warnings, normalize_text
from receipt_ai.features.extraction.router import build_default_router
from receipt_ai.features.extraction.validators.image_receipt_validator import receipt_quality_warnings

logger = logging.getLogger(__name__)


class ExtractionOrchestrator:
    def __init__(self, config: ExtractionConfig | None = None) -> None:
        self.config = config or ExtractionConfig.from_env()
        self.router = build_default_router(self.config)

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        started = time.perf_counter()
        if len(request.file_bytes) > self.config.max_extract_bytes:
            elapsed = int((time.perf_counter() - started) * 1000)
            return ExtractionResult(
                filename=request.filename,
                status="failed",
                error=f"File exceeds max extraction size ({self.config.max_extract_bytes} bytes).",
                duration_ms=elapsed,
            )

        try:
            raise_if_cancelled(request)
            extractor = self.router.resolve(request)
            raise_if_cancelled(request)
            text = extractor.extract(request)
            text = normalize_text(text)
            warnings = low_quality_warnings(text)
            if extractor.name.startswith("kimi-vision"):
                warnings.extend(receipt_quality_warnings(text))

            elapsed = int((time.perf_counter() - started) * 1000)
            result = ExtractionResult(
                filename=request.filename,
                status="success",
                text=text,
                extractor_used=extractor.name,
                warnings=warnings,
                duration_ms=elapsed,
            )
            stats = getattr(extractor, "last_vision_stats", None)
            if isinstance(stats, dict):
                result.pages_total = int(stats.get("pages_total", 0) or 0)
                result.pages_extracted = int(stats.get("pages_extracted", 0) or 0)
                result.pages_skipped = int(stats.get("pages_skipped", 0) or 0)
                raw_reasons = stats.get("skip_reasons", {})
                if isinstance(raw_reasons, dict):
                    result.skip_reasons = {str(k): int(v) for k, v in raw_reasons.items()}
            if self.config.enable_txt_output and result.text:
                result.output_path = write_extraction_txt(self.config.output_dir, request.storage_folder, result)

            logger.info(
                "extraction_success file=%s extractor=%s duration_ms=%s warnings=%s output=%s",
                result.filename,
                result.extractor_used,
                result.duration_ms,
                len(result.warnings),
                result.output_path,
            )
            return result
        except ExtractionCancelledError as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            logger.info("extraction_cancelled file=%s", request.filename)
            return ExtractionResult(
                filename=request.filename,
                status="cancelled",
                error=str(exc),
                duration_ms=elapsed,
            )
        except ExtractionError as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            logger.warning("extraction_failed file=%s error=%s", request.filename, exc)
            return ExtractionResult(
                filename=request.filename,
                status="failed",
                error=str(exc),
                duration_ms=elapsed,
            )
        except Exception as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            logger.exception("extraction_unhandled file=%s", request.filename)
            return ExtractionResult(
                filename=request.filename,
                status="failed",
                error=str(exc),
                duration_ms=elapsed,
            )


async def run_upload_extraction(request: ExtractionRequest) -> ExtractionResult:
    orchestrator = ExtractionOrchestrator()
    if not orchestrator.config.enable_on_upload:
        return ExtractionResult(
            filename=request.filename,
            status="skipped",
            extractor_used="disabled",
        )
    if request.cancel_event is not None:
        return await _run_upload_extraction_subprocess(request)
    return await asyncio.to_thread(orchestrator.extract, request)


async def _run_upload_extraction_subprocess(request: ExtractionRequest) -> ExtractionResult:
    temp_dir = Path(tempfile.mkdtemp(prefix="receipt_extract_"))
    input_path = temp_dir / "input.json"
    output_path = temp_dir / "output.json"
    payload = {
        "filename": request.filename,
        "content_type": request.content_type,
        "storage_folder": request.storage_folder,
        "file_bytes_b64": base64.b64encode(request.file_bytes).decode("ascii"),
    }
    try:
        input_path.write_text(json.dumps(payload), encoding="utf-8")
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "receipt_ai.features.extraction.subprocess_worker",
            str(input_path),
            str(output_path),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        while True:
            if request.cancel_event is not None and request.cancel_event.is_set():
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                return ExtractionResult(filename=request.filename, status="cancelled", error="Upload stopped by user.")
            try:
                exit_code = await asyncio.wait_for(proc.wait(), timeout=0.15)
                break
            except asyncio.TimeoutError:
                continue
        if exit_code != 0:
            return ExtractionResult(
                filename=request.filename,
                status="failed",
                error=f"Extraction worker failed (exit={exit_code}).",
            )
        try:
            raw = json.loads(output_path.read_text(encoding="utf-8"))
            return ExtractionResult(
                filename=str(raw.get("filename", request.filename)),
                status=str(raw.get("status", "failed")),
                text=str(raw.get("text", "")),
                extractor_used=str(raw.get("extractor_used", "")),
                warnings=list(raw.get("warnings", [])),
                error=str(raw.get("error", "")),
                duration_ms=int(raw.get("duration_ms", 0) or 0),
                output_path=str(raw.get("output_path", "")),
                pages_total=int(raw.get("pages_total", 0) or 0),
                pages_extracted=int(raw.get("pages_extracted", 0) or 0),
                pages_skipped=int(raw.get("pages_skipped", 0) or 0),
                skip_reasons={str(k): int(v) for k, v in dict(raw.get("skip_reasons", {})).items()},
            )
        except Exception as exc:
            return ExtractionResult(filename=request.filename, status="failed", error=f"Invalid worker output: {exc}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
