"""Cooperative cancellation for long-running extraction (upload Stop button)."""

from __future__ import annotations

from receipt_ai.features.extraction.errors import ExtractionCancelledError
from receipt_ai.features.extraction.models import ExtractionRequest


def raise_if_cancelled(request: ExtractionRequest) -> None:
    ev = request.cancel_event
    if ev is not None and ev.is_set():
        raise ExtractionCancelledError("Upload stopped by user.")
