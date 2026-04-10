from __future__ import annotations

import io

import docx

from receipt_ai.features.extraction.contracts import Extractor
from receipt_ai.features.extraction.errors import ParsingError
from receipt_ai.features.extraction.models import ExtractionRequest


class DocxExtractor(Extractor):
    name = "python-docx"

    def supports(self, request: ExtractionRequest) -> bool:
        return request.filename.lower().endswith(".docx")

    def extract(self, request: ExtractionRequest) -> str:
        try:
            parsed = docx.Document(io.BytesIO(request.file_bytes))
            lines: list[str] = []
            for paragraph in parsed.paragraphs:
                text = paragraph.text.strip()
                if text:
                    lines.append(text)
            for table in parsed.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells]
                    if any(row_text):
                        lines.append(" | ".join(row_text))
            return "\n".join(lines).strip()
        except Exception as exc:
            raise ParsingError(f"DOCX parse failed: {exc}") from exc
