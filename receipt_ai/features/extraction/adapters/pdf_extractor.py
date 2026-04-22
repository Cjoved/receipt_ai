from __future__ import annotations

import io
import logging

import fitz

from pypdf import PdfReader

from receipt_ai.features.extraction.adapters.kimi_vision_core import kimi_try_receipt_page
from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.contracts import Extractor
from receipt_ai.features.extraction.errors import ExternalAIError, ParsingError
from receipt_ai.features.extraction.models import ExtractionRequest

logger = logging.getLogger(__name__)


def extract_text_pypdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pypdf (digital text layer only)."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        chunks: list[str] = []
        for idx, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            if text:
                chunks.append(f"--- Page {idx + 1} ---\n{text}")
        return "\n\n".join(chunks).strip()
    except Exception as exc:
        raise ParsingError(f"PDF parse failed: {exc}") from exc


def render_pdf_pages_to_png_bytes(file_bytes: bytes, max_pages: int, dpi: int) -> list[bytes]:
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
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            out.append(pix.tobytes("png"))
        return out
    finally:
        doc.close()


class PdfExtractor(Extractor):
    """PDF: pypdf text and/or per-page Kimi vision (see `pdf_extraction_mode`)."""

    def __init__(self, config: ExtractionConfig) -> None:
        self._config = config
        self._last_route = "pypdf"

    @property
    def name(self) -> str:
        return self._last_route

    def supports(self, request: ExtractionRequest) -> bool:
        return request.filename.lower().endswith(".pdf")

    def extract(self, request: ExtractionRequest) -> str:
        mode = self._config.pdf_extraction_mode
        if mode == "text":
            self._last_route = "pypdf"
            return extract_text_pypdf(request.file_bytes)
        if mode == "vision":
            return self._extract_vision(request)
        # auto
        text = extract_text_pypdf(request.file_bytes)
        if len(text.strip()) >= self._config.pdf_auto_min_text_chars:
            self._last_route = "pypdf"
            return text
        return self._extract_vision(request)

    def _extract_vision(self, request: ExtractionRequest) -> str:
        self._last_route = "kimi-vision-pdf"
        page_pngs = render_pdf_pages_to_png_bytes(
            request.file_bytes,
            self._config.pdf_max_pages,
            self._config.pdf_render_dpi,
        )
        if not page_pngs:
            raise ExternalAIError("PDF has no pages to extract.")

        chunks: list[str] = []
        for i, png_bytes in enumerate(page_pngs):
            label = f"{request.filename} (page {i + 1})"
            page_text, skip_reason = kimi_try_receipt_page(
                self._config,
                image_bytes=png_bytes,
                mime="image/png",
                prompt_label=label,
            )
            if page_text is not None:
                chunks.append(f"--- Page {i + 1} ---\n{page_text}")
            elif skip_reason:
                logger.info("pdf_vision_page_skipped file=%s page=%s reason=%s", request.filename, i + 1, skip_reason)

        merged = "\n\n".join(chunks).strip()
        if not merged:
            raise ExternalAIError("No usable receipt text extracted from any PDF page.")
        return merged
