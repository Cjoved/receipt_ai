from __future__ import annotations

import base64
import logging

from openai import OpenAI

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.errors import ExternalAIError
from receipt_ai.features.extraction.validators.image_receipt_validator import is_likely_receipt

logger = logging.getLogger(__name__)


def guess_image_mime(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith(".png"):
        return "image/png"
    if lowered.endswith(".gif"):
        return "image/gif"
    if lowered.endswith(".webp"):
        return "image/webp"
    if lowered.endswith(".bmp"):
        return "image/bmp"
    return "image/jpeg"


def _require_kimi(config: ExtractionConfig) -> None:
    if not config.kimi_api_key:
        raise ExternalAIError("KIMI_API_KEY is not configured.")


def kimi_raw_vision_completion(
    config: ExtractionConfig,
    *,
    image_bytes: bytes,
    mime: str,
    prompt_label: str,
) -> str:
    """Call Kimi vision API; return stripped assistant text (no receipt validation)."""
    _require_kimi(config)
    client = OpenAI(
        api_key=config.kimi_api_key,
        base_url=config.kimi_base_url,
        timeout=config.kimi_timeout_seconds,
    )
    b64 = base64.b64encode(image_bytes).decode("ascii")
    result = client.chat.completions.create(
        model=config.kimi_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract text from receipt images only. "
                    "If the image is not a receipt document, return exactly: NOT_RECEIPT. "
                    "For valid receipts, return clean plain text and include key fields when found: "
                    "merchant, date, line items, tax, total, payment method."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Extract the receipt text from this image: {prompt_label}"},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            },
        ],
        temperature=0.2,
    )
    return (result.choices[0].message.content or "").strip()


def kimi_extract_receipt_image_strict(
    config: ExtractionConfig,
    *,
    image_bytes: bytes,
    mime: str,
    prompt_label: str,
) -> str:
    """Single image upload: raise if not a receipt or validation fails."""
    try:
        text = kimi_raw_vision_completion(
            config,
            image_bytes=image_bytes,
            mime=mime,
            prompt_label=prompt_label,
        )
        if text == "":
            raise ExternalAIError("Kimi returned empty output.")
        if text == "NOT_RECEIPT":
            raise ExternalAIError("Uploaded image does not look like a receipt.")
        if config.require_receipt_signals and not is_likely_receipt(text):
            raise ExternalAIError("Extraction output failed receipt validation checks.")
        return text
    except ExternalAIError:
        raise
    except Exception as exc:
        raise ExternalAIError(f"Kimi extraction failed: {exc}") from exc


def kimi_try_receipt_page(
    config: ExtractionConfig,
    *,
    image_bytes: bytes,
    mime: str,
    prompt_label: str,
) -> tuple[str | None, str | None]:
    """
    PDF page (or soft-fail path): return (text, None) on success, or (None, reason) to skip the page.
    """
    try:
        text = kimi_raw_vision_completion(
            config,
            image_bytes=image_bytes,
            mime=mime,
            prompt_label=prompt_label,
        )
        if text == "":
            logger.info("kimi_pdf_page_skip label=%s reason=empty", prompt_label)
            return (None, "empty")
        if text == "NOT_RECEIPT":
            logger.info("kimi_pdf_page_skip label=%s reason=not_receipt", prompt_label)
            return (None, "not_receipt")
        if config.require_receipt_signals and not is_likely_receipt(text):
            logger.info("kimi_pdf_page_skip label=%s reason=receipt_validation", prompt_label)
            return (None, "receipt_validation")
        return (text, None)
    except Exception as exc:
        logger.warning("kimi_pdf_page_error label=%s error=%s", prompt_label, exc)
        return (None, f"error:{exc}")
