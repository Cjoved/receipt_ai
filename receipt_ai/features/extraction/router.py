from __future__ import annotations

from receipt_ai.features.extraction.adapters.docx_extractor import DocxExtractor
from receipt_ai.features.extraction.adapters.image_kimi_extractor import ImageKimiExtractor
from receipt_ai.features.extraction.adapters.pdf_extractor import PdfExtractor
from receipt_ai.features.extraction.adapters.sheet_extractor import SheetExtractor
from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.contracts import Extractor
from receipt_ai.features.extraction.errors import UnsupportedFileTypeError
from receipt_ai.features.extraction.models import ExtractionRequest


class ExtractionRouter:
    def __init__(self, extractors: list[Extractor]) -> None:
        self._extractors = extractors

    def resolve(self, request: ExtractionRequest) -> Extractor:
        for extractor in self._extractors:
            if extractor.supports(request):
                return extractor
        raise UnsupportedFileTypeError(f"Unsupported file type for '{request.filename}'.")


def build_default_router(config: ExtractionConfig) -> ExtractionRouter:
    return ExtractionRouter(
        [
            PdfExtractor(config),
            DocxExtractor(),
            SheetExtractor(config),
            ImageKimiExtractor(config),
        ]
    )
