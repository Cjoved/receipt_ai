from __future__ import annotations

import asyncio
import logging
import time

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.errors import ExtractionError
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
            extractor = self.router.resolve(request)
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
    return await asyncio.to_thread(orchestrator.extract, request)
