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
    pdf_page_mode: bool = False,
) -> str:
    """Call Kimi vision API; return stripped assistant text (no receipt validation)."""
    _require_kimi(config)
    client = OpenAI(
        api_key=config.kimi_api_key,
        base_url=config.kimi_base_url,
        timeout=config.kimi_timeout_seconds,
    )
    b64 = base64.b64encode(image_bytes).decode("ascii")
    if pdf_page_mode:
        system_instruction = (
            "You extract text from scanned document pages used in expense packets. "
            "These pages may be receipts, invoices, service invoices, acknowledgement receipts, "
            "or other transaction proofs. Preserve visible text exactly where possible. "
            "Return clean plain text and include key fields when found: merchant, date, line items, tax, total, payment method. "
            "Return NOT_RECEIPT only if the page is clearly unrelated to finance/transaction documents "
            "(e.g., selfie, scenery, chat screenshot, blank art image)."
        )
        user_instruction = f"Extract all visible text from this document page: {prompt_label}"
    else:
        system_instruction = (
            "You extract text from receipt images only. "
            "If the image is not a receipt document, return exactly: NOT_RECEIPT. "
            "For valid receipts, return clean plain text and include key fields when found: "
            "merchant, date, line items, tax, total, payment method."
        )
        user_instruction = f"Extract the receipt text from this image: {prompt_label}"

    result = client.chat.completions.create(
        model=config.kimi_model,
        messages=[
            {
                "role": "system",
                "content": system_instruction,
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_instruction},
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
            pdf_page_mode=True,
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
    relax_receipt_validation: bool = False,
) -> tuple[str | None, str | None]:
    """
    PDF page (or soft-fail path): return (text, None) on success, or (None, reason) to skip the page.

    When ``relax_receipt_validation`` is True (multi-page PDF vision), still reject empty output and
    ``NOT_RECEIPT``, but keep text that fails :func:`is_likely_receipt` so invoices / odd layouts are
    not silently dropped between pages.
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
            if relax_receipt_validation:
                logger.info(
                    "kimi_pdf_page_relax_accept label=%s (output failed strict receipt heuristics)",
                    prompt_label,
                )
                return (text, None)
            logger.info("kimi_pdf_page_skip label=%s reason=receipt_validation", prompt_label)
            return (None, "receipt_validation")
        return (text, None)
    except Exception as exc:
        logger.warning("kimi_pdf_page_error label=%s error=%s", prompt_label, exc)
        return (None, f"error:{exc}")
