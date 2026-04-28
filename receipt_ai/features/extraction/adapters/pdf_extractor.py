from __future__ import annotations

import io
import logging

import fitz

from pypdf import PdfReader

from receipt_ai.features.extraction.adapters.kimi_vision_core import kimi_try_receipt_page
from receipt_ai.features.extraction.cancel_checks import raise_if_cancelled
from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.contracts import Extractor
from receipt_ai.features.extraction.errors import ExtractionCancelledError, ExternalAIError, ParsingError
from receipt_ai.features.extraction.models import ExtractionRequest

logger = logging.getLogger(__name__)


def extract_text_pypdf(file_bytes: bytes, request: ExtractionRequest | None = None) -> str:
    """Extract text from PDF using pypdf (digital text layer only)."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        chunks: list[str] = []
        for idx, page in enumerate(reader.pages):
            if request is not None and idx % 3 == 0:
                raise_if_cancelled(request)
            text = (page.extract_text() or "").strip()
            if text:
                chunks.append(f"--- Page {idx + 1} ---\n{text}")
        return "\n\n".join(chunks).strip()
    except ExtractionCancelledError:
        raise
    except Exception as exc:
        raise ParsingError(f"PDF parse failed: {exc}") from exc


def render_pdf_pages_to_png_bytes(
    file_bytes: bytes,
    max_pages: int,
    dpi: int,
    request: ExtractionRequest | None = None,
) -> list[bytes]:
    """Rasterize up to `max_pages` pages to PNG bytes using PyMuPDF."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise ParsingError(f"PDF open failed: {exc}") from exc
    try:
        n = min(doc.page_count, max_pages)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        out: list[bytes] = []
        for i in range(n):
            if request is not None:
                raise_if_cancelled(request)
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            out.append(pix.tobytes("png"))
        return out
    except ExtractionCancelledError:
        raise
    finally:
        doc.close()


class PdfExtractor(Extractor):
    """PDF: pypdf text and/or per-page Kimi vision (see `pdf_extraction_mode`)."""

    def __init__(self, config: ExtractionConfig) -> None:
        self._config = config
        self._last_route = "pypdf"
        self.last_vision_stats: dict[str, int | dict[str, int]] = {
            "pages_total": 0,
            "pages_extracted": 0,
            "pages_skipped": 0,
            "skip_reasons": {},
        }

    @property
    def name(self) -> str:
        return self._last_route

    def supports(self, request: ExtractionRequest) -> bool:
        return request.filename.lower().endswith(".pdf")

    def extract(self, request: ExtractionRequest) -> str:
        raise_if_cancelled(request)
        mode = self._config.pdf_extraction_mode
        if mode == "text":
            self._last_route = "pypdf"
            return extract_text_pypdf(request.file_bytes, request)
        if mode == "vision":
            return self._extract_vision(request)
        # auto
        text = extract_text_pypdf(request.file_bytes, request)
        if len(text.strip()) >= self._config.pdf_auto_min_text_chars:
            self._last_route = "pypdf"
            return text
        return self._extract_vision(request)

    def _extract_vision(self, request: ExtractionRequest) -> str:
        self._last_route = "kimi-vision-pdf"
        raise_if_cancelled(request)
        page_pngs = render_pdf_pages_to_png_bytes(
            request.file_bytes,
            self._config.pdf_max_pages,
            self._config.pdf_render_dpi,
            request,
        )
        if not page_pngs:
            raise ExternalAIError("PDF has no pages to extract.")

        chunks: list[str] = ["" for _ in page_pngs]
        skipped: dict[int, str] = {}
        skip_reasons: dict[str, int] = {}
        for i, png_bytes in enumerate(page_pngs):
            raise_if_cancelled(request)
            label = f"{request.filename} (page {i + 1})"
            page_text, skip_reason = kimi_try_receipt_page(
                self._config,
                image_bytes=png_bytes,
                mime="image/png",
                prompt_label=label,
                relax_receipt_validation=True,
                cancel_event=request.cancel_event,
            )
            if page_text is not None:
                chunks[i] = f"--- Page {i + 1} ---\n{page_text}"
            else:
                reason = skip_reason or "unknown"
                skipped[i] = reason
                skip_reasons[reason] = int(skip_reasons.get(reason, 0)) + 1
                chunks[i] = f"--- Page {i + 1} ---\n[Extraction skipped: {reason}]"
                logger.info(
                    "pdf_vision_page_skipped file=%s page=%s reason=%s",
                    request.filename,
                    i + 1,
                    reason,
                )

        # Retry skipped pages at higher DPI to recover faint/blurred scans.
        retries = max(0, int(self._config.pdf_retry_pages))
        if retries > 0 and skipped:
            for attempt in range(1, retries + 1):
                raise_if_cancelled(request)
                retry_dpi = int(self._config.pdf_render_dpi + (attempt * self._config.pdf_retry_dpi_step))
                retry_pngs = render_pdf_pages_to_png_bytes(
                    request.file_bytes, self._config.pdf_max_pages, retry_dpi, request
                )
                pending = list(skipped.items())
                for page_idx, prev_reason in pending:
                    raise_if_cancelled(request)
                    if page_idx >= len(retry_pngs):
                        continue
                    label = f"{request.filename} (page {page_idx + 1}, retry {attempt}, dpi {retry_dpi})"
                    page_text, skip_reason = kimi_try_receipt_page(
                        self._config,
                        image_bytes=retry_pngs[page_idx],
                        mime="image/png",
                        prompt_label=label,
                        relax_receipt_validation=True,
                        cancel_event=request.cancel_event,
                    )
                    if page_text is not None:
                        chunks[page_idx] = f"--- Page {page_idx + 1} ---\n{page_text}"
                        skipped.pop(page_idx, None)
                        skip_reasons[prev_reason] = max(0, int(skip_reasons.get(prev_reason, 0)) - 1)
                    else:
                        next_reason = skip_reason or "unknown"
                        if next_reason != prev_reason:
                            skip_reasons[prev_reason] = max(0, int(skip_reasons.get(prev_reason, 0)) - 1)
                            skip_reasons[next_reason] = int(skip_reasons.get(next_reason, 0)) + 1
                        skipped[page_idx] = next_reason
                        chunks[page_idx] = f"--- Page {page_idx + 1} ---\n[Extraction skipped: {next_reason}]"
                if not skipped:
                    break

        merged = "\n\n".join(chunks).strip()
        pages_total = len(page_pngs)
        pages_skipped = len(skipped)
        self.last_vision_stats = {
            "pages_total": pages_total,
            "pages_extracted": pages_total - pages_skipped,
            "pages_skipped": pages_skipped,
            "skip_reasons": {k: v for k, v in skip_reasons.items() if int(v) > 0},
        }
        if not merged:
            raise ExternalAIError("No usable receipt text extracted from any PDF page.")
        return merged
