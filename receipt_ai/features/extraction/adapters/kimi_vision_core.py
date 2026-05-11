from __future__ import annotations

import base64
import json
import logging
import threading
from typing import Any

from openai import OpenAI

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.errors import ExtractionCancelledError, ExternalAIError
from receipt_ai.features.extraction.validators.image_receipt_validator import is_likely_receipt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured fields extracted from every receipt / invoice
# ---------------------------------------------------------------------------
#
# Required by the business:
#   company_name      – registered name of the SUPPLIER / merchant
#   tin_no            – supplier's VAT Reg. TIN
#   location          – supplier's address
#   date              – transaction date (YYYY-MM-DD when determinable)
#   inv_or_no         – invoice number or official receipt (OR) number
#   particulars       – list of line-item descriptions (array of strings)
#   vat_amount        – 12% VAT amount as a number (null if not shown)
#   total_amount      – total amount due / total invoice as a number
#
# Additional fields captured because they appear on PH BIR invoices and
# are useful for accounting / reimbursement reconciliation:
#   sold_to           – customer / buyer registered name
#   customer_tin      – buyer's TIN
#   vatable_sales     – VAT-able sales base amount (before VAT)
#   amount_net_of_vat – amount net of VAT (same as vatable_sales in most cases)
#   vat_exempt_sales  – VAT-exempt portion (null if zero / not shown)
#   zero_rated_sales  – zero-rated sales (null if zero / not shown)
#   form_of_payment   – e.g. "Cash", "Check", "Card"
#   withholding_tax   – withholding tax deducted (null if not shown)
#   document_type     – "SALES INVOICE", "SERVICE INVOICE", "OFFICIAL RECEIPT", etc.
# ---------------------------------------------------------------------------

_RECEIPT_FIELDS_SCHEMA = """
Return a JSON object with these keys (use null for any field not found):

{
  "company_name":      string,   // Supplier / merchant registered name
  "tin_no":            string,   // Supplier VAT Reg. TIN
  "location":          string,   // Supplier full address
  "date":              string,   // Transaction date – prefer YYYY-MM-DD
  "inv_or_no":         string,   // Invoice No. / OR No. (e.g. "0000346")
  "document_type":     string,   // "SALES INVOICE" | "SERVICE INVOICE" | "OFFICIAL RECEIPT" | ...
  "sold_to":           string,   // Buyer / customer registered name
  "customer_tin":      string,   // Buyer TIN
  "particulars":       string[], // Line-item descriptions (one entry per line item)
  "vatable_sales":     number,   // VATable sales base (before 12% VAT)
  "vat_amount":        number,   // 12% VAT amount
  "amount_net_of_vat": number,   // Amount net of VAT
  "vat_exempt_sales":  number,   // VAT-exempt sales (0 if not shown)
  "zero_rated_sales":  number,   // Zero-rated sales (0 if not shown)
  "withholding_tax":   number,   // Withholding tax deducted (null if not shown)
  "total_amount":      number,   // Total amount due / total invoice
  "form_of_payment":   string,   // "Cash" | "Check" | "Card" | ...
  "uncertain_fields":  string[]  // Notes for ambiguous/unclear reads
}

Return ONLY the raw JSON object – no markdown, no extra text, no code fences.
If the image is NOT a financial/transaction document at all, return exactly: NOT_RECEIPT
"""

_FIELD_LABELS: list[tuple[str, str]] = [
    ("company_name", "Company Name"),
    ("tin_no", "TIN"),
    ("location", "Location"),
    ("date", "Date"),
    ("inv_or_no", "Invoice/OR No."),
    ("document_type", "Document Type"),
    ("sold_to", "Sold To"),
    ("customer_tin", "Customer TIN"),
    ("vatable_sales", "VATable Sales"),
    ("vat_amount", "VAT Amount"),
    ("amount_net_of_vat", "Amount Net of VAT"),
    ("vat_exempt_sales", "VAT Exempt Sales"),
    ("zero_rated_sales", "Zero Rated Sales"),
    ("withholding_tax", "Withholding Tax"),
    ("total_amount", "Total Amount"),
    ("form_of_payment", "Form of Payment"),
]


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
    cancel_event: threading.Event | None = None,
) -> str:
    """Call Kimi vision API; return stripped assistant text (no receipt validation)."""
    if cancel_event is not None and cancel_event.is_set():
        raise ExtractionCancelledError("Upload stopped by user.")
    _require_kimi(config)
    client = OpenAI(
        api_key=config.kimi_api_key,
        base_url=config.kimi_base_url,
        timeout=config.kimi_timeout_seconds,
    )
    b64 = base64.b64encode(image_bytes).decode("ascii")

    strict_rules = (
        "STRICT EXTRACTION RULES:\n"
        "1) Extract only what is visibly present in the image; do not guess missing fields.\n"
        "2) If a field is unreadable or not present, set it to null.\n"
        "3) For unclear handwriting, keep the closest literal reading and add a short note in uncertain_fields.\n"
        "4) Keep names exactly as seen; do not auto-correct spellings.\n"
        "5) Set document_type only when explicitly printed; otherwise null.\n"
        "6) Normalize handwritten dates like M/D/YY or MM/DD/YY to YYYY-MM-DD assuming 20YY.\n"
        "7) Numeric fields must be plain numbers only (no currency symbols/commas).\n"
        "8) If clearly not a financial/transaction document, return exactly NOT_RECEIPT.\n"
        "9) Return only raw JSON object; no markdown, no code fences, no extra text.\n"
    )

    if pdf_page_mode:
        system_instruction = (
            "You are an expert at extracting structured data from Philippine BIR-compliant "
            "receipts, sales invoices, service invoices, and official receipts. "
            "These documents may be handwritten, printed, or a mix of both. "
            "Extract ALL visible fields accurately, including handwritten annotations.\n\n"
            + strict_rules
            + "\n"
            + _RECEIPT_FIELDS_SCHEMA
        )
        user_instruction = (
            f"Extract all structured receipt/invoice fields from this document page: {prompt_label}"
        )
    else:
        system_instruction = (
            "You are an expert at extracting structured data from Philippine BIR-compliant "
            "receipts, sales invoices, service invoices, and official receipts. "
            "These documents may be handwritten, printed, or a mix of both. "
            "Extract ALL visible fields accurately, including handwritten annotations.\n\n"
            + strict_rules
            + "\n"
            + _RECEIPT_FIELDS_SCHEMA
        )
        user_instruction = (
            f"Extract all structured receipt/invoice fields from this image: {prompt_label}"
        )

    result = client.chat.completions.create(
        model=config.kimi_model,
        messages=[
            {"role": "system", "content": system_instruction},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_instruction},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            },
        ],
        temperature=0.1,  # Lower temperature for more consistent structured output
    )
    return (result.choices[0].message.content or "").strip()


def parse_receipt_json(raw_text: str) -> dict:
    """
    Parse the JSON returned by Kimi into a Python dict.

    Strips accidental markdown code fences if the model adds them despite
    the system prompt asking for raw JSON.

    Returns an empty dict on parse failure (caller decides how to handle).
    """
    text = raw_text.strip()
    # Strip markdown fences just in case
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("parse_receipt_json failed: %s | raw=%r", exc, raw_text[:200])
        return {}


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            return f"{value:.2f}".rstrip("0").rstrip(".")
        return str(value)
    return str(value).strip()


def _receipt_json_to_plain_text(raw_text: str) -> str:
    """
    Convert structured JSON output into readable plain text for indexing/RAG.

    If parsing fails, return the original text so callers keep graceful fallback behavior.
    """
    text = raw_text.strip()
    if not text or text == "NOT_RECEIPT":
        return text

    payload = parse_receipt_json(text)
    if not payload:
        return text

    lines: list[str] = ["Receipt Extraction"]
    for key, label in _FIELD_LABELS:
        value = _format_value(payload.get(key))
        if value:
            lines.append(f"{label}: {value}")

    particulars = payload.get("particulars")
    if isinstance(particulars, list):
        cleaned_items: list[str] = []
        for item in particulars:
            formatted = _format_value(item)
            if formatted:
                cleaned_items.append(formatted)
        if cleaned_items:
            lines.append("Particulars:")
            for item in cleaned_items:
                lines.append(f"- {item}")

    uncertain_fields = payload.get("uncertain_fields")
    if isinstance(uncertain_fields, list):
        uncertain_items: list[str] = []
        for item in uncertain_fields:
            formatted = _format_value(item)
            if formatted:
                uncertain_items.append(formatted)
        if uncertain_items:
            lines.append("Uncertain Fields:")
            for note in uncertain_items:
                lines.append(f"- {note}")

    if len(lines) == 1:
        return text
    return "\n".join(lines).strip()


def kimi_extract_receipt_image_strict(
    config: ExtractionConfig,
    *,
    image_bytes: bytes,
    mime: str,
    prompt_label: str,
    cancel_event: threading.Event | None = None,
) -> str:
    """Single image upload: raise if not a receipt or validation fails."""
    try:
        raw_text = kimi_raw_vision_completion(
            config,
            image_bytes=image_bytes,
            mime=mime,
            prompt_label=prompt_label,
            pdf_page_mode=True,
            cancel_event=cancel_event,
        )
        text = _receipt_json_to_plain_text(raw_text)
        if text == "":
            raise ExternalAIError("Kimi returned empty output.")
        if text == "NOT_RECEIPT":
            raise ExternalAIError("Uploaded image does not look like a receipt.")
        if config.require_receipt_signals and not is_likely_receipt(text):
            raise ExternalAIError("Extraction output failed receipt validation checks.")
        return text
    except ExtractionCancelledError:
        raise
    except ExternalAIError:
        raise
    except Exception as exc:
        raise ExternalAIError(f"Kimi extraction failed: {exc}") from exc


def kimi_extract_receipt_structured(
    config: ExtractionConfig,
    *,
    image_bytes: bytes,
    mime: str,
    prompt_label: str,
    cancel_event: threading.Event | None = None,
) -> dict:
    """
    Convenience wrapper: extract receipt fields and return a parsed dict.

    Raises ExternalAIError on hard failures (not a receipt, empty output, etc.).
    Returns an empty dict if JSON parsing fails but text was non-empty — the
    caller can fall back to the raw text via kimi_extract_receipt_image_strict.

    Example return value::

        {
            "company_name":      "McDonald's San Simon Branch",
            "tin_no":            "000-121-242-00788",
            "location":          "Quezon Road, Brgy. San Isidro, 2015 San Simon, Pampanga",
            "date":              "2026-04-18",
            "inv_or_no":         "0000346",
            "document_type":     "SALES INVOICE",
            "sold_to":           "Leads Agricultural Products Corporation",
            "customer_tin":      "005-038-717",
            "particulars":       ["Meals"],
            "vatable_sales":     330.36,
            "vat_amount":        39.64,
            "amount_net_of_vat": 330.36,
            "vat_exempt_sales":  0,
            "zero_rated_sales":  0,
            "withholding_tax":   null,
            "total_amount":      370.0,
            "form_of_payment":   "Cash"
        }
    """
    raw = kimi_raw_vision_completion(
        config,
        image_bytes=image_bytes,
        mime=mime,
        prompt_label=prompt_label,
        pdf_page_mode=True,
        cancel_event=cancel_event,
    )
    if raw == "":
        raise ExternalAIError("Kimi returned empty output.")
    if raw == "NOT_RECEIPT":
        raise ExternalAIError("Uploaded image does not look like a receipt.")
    return parse_receipt_json(raw)


def kimi_try_receipt_page(
    config: ExtractionConfig,
    *,
    image_bytes: bytes,
    mime: str,
    prompt_label: str,
    relax_receipt_validation: bool = False,
    cancel_event: threading.Event | None = None,
) -> tuple[str | None, str | None]:
    """
    PDF page (or soft-fail path): return (text, None) on success, or (None, reason) to skip.

    When ``relax_receipt_validation`` is True (multi-page PDF vision), still reject empty
    output and ``NOT_RECEIPT``, but keep text that fails :func:`is_likely_receipt` so
    invoices / odd layouts are not silently dropped between pages.
    """
    try:
        if cancel_event is not None and cancel_event.is_set():
            raise ExtractionCancelledError("Upload stopped by user.")
        raw_text = kimi_raw_vision_completion(
            config,
            image_bytes=image_bytes,
            mime=mime,
            prompt_label=prompt_label,
            cancel_event=cancel_event,
        )
        text = _receipt_json_to_plain_text(raw_text)
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
    except ExtractionCancelledError:
        raise
    except Exception as exc:
        logger.warning("kimi_pdf_page_error label=%s error=%s", prompt_label, exc)
        return (None, f"error:{exc}")