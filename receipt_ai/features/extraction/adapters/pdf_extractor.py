from __future__ import annotations

import io

from pypdf import PdfReader

from receipt_ai.features.extraction.contracts import Extractor
from receipt_ai.features.extraction.errors import ParsingError
from receipt_ai.features.extraction.models import ExtractionRequest


class PdfExtractor(Extractor):
    name = "pypdf"

    def supports(self, request: ExtractionRequest) -> bool:
        return request.filename.lower().endswith(".pdf")

    def extract(self, request: ExtractionRequest) -> str:
        try:
            reader = PdfReader(io.BytesIO(request.file_bytes))
            chunks: list[str] = []
            for idx, page in enumerate(reader.pages):
                text = (page.extract_text() or "").strip()
                if text:
                    chunks.append(f"--- Page {idx + 1} ---\n{text}")
            return "\n\n".join(chunks).strip()
        except Exception as exc:
            raise ParsingError(f"PDF parse failed: {exc}") from exc
