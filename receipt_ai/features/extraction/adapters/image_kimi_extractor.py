from __future__ import annotations

from receipt_ai.features.extraction.adapters.kimi_vision_core import (
    guess_image_mime,
    kimi_extract_receipt_image_strict,
)
from receipt_ai.features.extraction.cancel_checks import raise_if_cancelled
from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.contracts import Extractor
from receipt_ai.features.extraction.models import ExtractionRequest


class ImageKimiExtractor(Extractor):
    name = "kimi-vision"

    def __init__(self, config: ExtractionConfig) -> None:
        self._config = config

    def supports(self, request: ExtractionRequest) -> bool:
        lowered = request.filename.lower()
        return lowered.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".jfif"))

    def extract(self, request: ExtractionRequest) -> str:
        raise_if_cancelled(request)
        mime = guess_image_mime(request.filename)
        return kimi_extract_receipt_image_strict(
            self._config,
            image_bytes=request.file_bytes,
            mime=mime,
            prompt_label=request.filename,
            cancel_event=request.cancel_event,
        )
