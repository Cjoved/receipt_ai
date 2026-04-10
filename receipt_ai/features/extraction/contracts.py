from __future__ import annotations

from typing import Protocol

from receipt_ai.features.extraction.models import ExtractionRequest


class Extractor(Protocol):
    name: str

    def supports(self, request: ExtractionRequest) -> bool:
        ...

    def extract(self, request: ExtractionRequest) -> str:
        ...
