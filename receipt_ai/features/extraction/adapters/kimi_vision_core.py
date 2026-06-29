from __future__ import annotations

import base64
from datetime import date as date_cls
from datetime import datetime
import json
import logging
import re
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
# Supplier fields:
#   company_name      – registered name of the SUPPLIER / merchant
#   tin_no            – supplier's VAT Reg. TIN (from header)
#   non_vat_supplier  – true if document states "NOT VALID FOR CLAIMING INPUT TAXES"
#   location          – supplier's address
#
# Transaction fields:
#   date              – transaction date (YYYY-MM-DD)
#   inv_or_no         – invoice / OR number
#   document_type     – SALES INVOICE | SERVICE INVOICE | OFFICIAL RECEIPT | INVOICE
#
# Buyer fields:
#   sold_to           – buyer registered name
#   sold_to_address   – buyer business address
#   customer_tin      – buyer TIN (from Sold To section only)
#
# Amount fields:
#   vatable_sales     – VATable sales base (before VAT)
#   vat_amount        – 12% VAT
#   amount_net_of_vat – net of VAT
#   vat_exempt_sales  – VAT-exempt portion
#   zero_rated_sales  – zero-rated portion
#   withholding_tax   – withholding tax deducted
#   total_amount      – final total amount due
#   form_of_payment   – Cash | Check | Card | Others
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# SCHEMA
# ---------------------------------------------------------------------------
_RECEIPT_FIELDS_SCHEMA = """
You must return a single raw JSON object — no markdown, no code fences, no extra text.

{
  "company_name":      string | null,
  "tin_no":            string | null,
  "non_vat_supplier":  boolean,
  "location":          string | null,
  "date":              string | null,
  "inv_or_no":         string | null,
  "document_type":     string | null,
  "sold_to":           string | null,
  "sold_to_address":   string | null,
  "customer_tin":      string | null,
  "vatable_sales":     number | null,
  "vat_amount":        number | null,
  "amount_net_of_vat": number | null,
  "vat_exempt_sales":  number | null,
  "zero_rated_sales":  number | null,
  "withholding_tax":   number | null,
  "total_amount":      number | null,
  "form_of_payment":   string | null,
  "uncertain_fields":  string[]
}

FIELD DEFINITIONS:
- company_name    : Supplier or merchant name at the TOP of the document (letterhead/header area).
- tin_no          : Supplier VAT Reg. TIN — always near the company name in the HEADER. NEVER the buyer TIN.
- non_vat_supplier: Set true ONLY when the document explicitly says "NOT VALID FOR CLAIMING INPUT TAXES"
                    or the header says "NON-VAT REG" or "NONVAT REG". Otherwise false.
- location        : Supplier full address (near the company header).
- date            : Main transaction date (near Invoice No. or top of form). Format: YYYY-MM-DD.
                    IGNORE footer dates (Permit-to-Use, Date Issued, Date Expired, BIR ATP dates).
                    If footer and handwritten years disagree, use the handwritten transaction date
                    and mention the conflict in uncertain_fields.
- inv_or_no       : Invoice No. / OR No. / Receipt No. Only the document number, not the BIR ATP number.
- document_type   : Exact label printed on the document: "SALES INVOICE", "SERVICE INVOICE",
                    "OFFICIAL RECEIPT", or "INVOICE". If two labels appear and one is crossed out,
                    use the one that is NOT crossed out.
- sold_to         : Buyer/customer registered name. Found in the "SOLD TO", "RECEIVED FROM",
                    or "Customer's Name" section — NOT from the header.
- sold_to_address : Buyer's full business address from the "Address" or "Business Address" field
                    in the SOLD TO section. Do NOT include the TIN here.
- customer_tin    : Buyer's TIN. Found ONLY in the SOLD TO / customer section (labeled "TIN" under
                    the buyer name). NEVER from the supplier header. These are two different TINs.
- vatable_sales   : The VATable sales BASE amount (before adding VAT). This is the smaller number.
                    On most PH invoices: total = vatable_sales + vat_amount.
- vat_amount      : The 12% VAT amount (roughly 10.7% of total).
                    CROSS-CHECK: if vatable_sales is present, vat_amount should equal vatable_sales x 0.12.
                    If a field labeled "Zero Rated Sales" contains a value that equals vatable_sales x 0.12,
                    the cashier likely filled the wrong field — move that value to vat_amount instead.
- amount_net_of_vat: Amount after removing VAT. Usually equals vatable_sales.
- vat_exempt_sales: Only fill if explicitly labeled and non-zero.
- zero_rated_sales: Only fill if explicitly labeled and non-zero AND the value does NOT equal
                    vatable_sales x 0.12 (which would indicate a cashier field error — see vat_amount rule).
- total_amount    : The final TOTAL AMOUNT DUE. Use this priority order:
                    1) "TOTAL AMOUNT DUE" box if filled.
                    2) "TOTAL INVOICE" on POS/thermal receipts.
                    3) "Received the amount of: [number/words]" if total box is blank.
                    4) "the sum of [words] pesos (P [number])" on Official Receipts.
                    Do NOT leave null if any of the above sources are present.
- form_of_payment : Only fill if explicitly marked (checked checkbox or printed). "Cash" is acceptable
                    if a POS receipt shows "Cash: P[amount]" with change. Do NOT guess.
- uncertain_fields: List any field where the reading is ambiguous, unclear, or inferred. Be specific.
                    Example: "total_amount inferred from 'Received the amount of' — TOTAL box was blank".

If the image is NOT any kind of financial or transaction document, return exactly: NOT_RECEIPT
"""

# ---------------------------------------------------------------------------
# EXTRACTION RULES
# ---------------------------------------------------------------------------
_STRICT_RULES = """
STRICT EXTRACTION RULES — read every rule before extracting:

DOCUMENT STRUCTURE RULES:
R1.  There are TWO separate TIN fields on every Philippine BIR invoice:
     (a) SUPPLIER TIN — printed in the letterhead/header near the company name. Goes into "tin_no".
     (b) BUYER TIN    — handwritten in the SOLD TO section under the buyer name. Goes into "customer_tin".
     These are ALWAYS different values. Never put the buyer TIN into "tin_no" or vice versa.

R2.  The supplier header is always at the TOP (company logo, name, address, TIN).
     The SOLD TO section is always BELOW the header. Never mix fields from these two zones.

R3.  For OFFICIAL RECEIPTS: the buyer name and TIN appear after "RECEIVED from _____ with TIN _____".
     Extract the name into "sold_to" and the TIN into "customer_tin".

R4.  For POS/thermal printed receipts (gasoline stations, fast food): buyer info appears at the
     BOTTOM after the totals. Still extract it into sold_to and customer_tin correctly.

DATE RULES:
R5.  Extract ONLY the main transaction date near Invoice No. or top of form.
     IGNORE ALL of: "Date Issued", "Date Expired", "Permit-to-Use Date",
     "BIR Authority to Print Date", "ATP Date Issued", "Valid Until", "Accreditation Date".

R5a. Handwritten years: carefully distinguish "6" vs "4" in the last digit (e.g. 2026 vs 2024).
     If a printed footer shows a different year than the handwritten transaction date,
     trust the handwritten header/body date and note any conflict in uncertain_fields.

R6.  Convert all date formats to YYYY-MM-DD:
     - "April 18, 2026" or "Apr 18 2026"  →  2026-04-18
     - "4/18/26" or "4-18-26" (2-digit year)  →  2026-04-18 (always assume 20XX)
     - "04|18|24" (pipe-separated MM|DD|YY)  →  2024-04-18
     - "4/18-19/2026" (date range on hotel receipts)  →  take first date: 2026-04-18
     - If the resulting year is outside 2020-2030, set date to null and note it in uncertain_fields.

AMOUNT RULES:
R7.  Numeric fields: plain numbers only — no "P", currency symbols, commas, or spaces.
     "P 1,234.56" → 1234.56

R8.  TOTAL AMOUNT resolution priority (use first available):
     1. "TOTAL AMOUNT DUE" box — if filled and legible.
     2. "TOTAL INVOICE" on thermal/POS receipts.
     3. "Received the amount of: [number]" — use the number (not the written words).
     4. "(P ___) in partial/full payment for" on Official Receipts.
     5. Sum of words like "Four Hundred Eighteen pesos" — last resort only.
     NEVER leave total_amount null if any of the above are present.

R9.  VAT cross-check: If vatable_sales is present, verify vat_amount equals vatable_sales x 0.12.
     If a field labeled "Zero Rated Sales" holds a value that matches vatable_sales x 0.12,
     the cashier filled the wrong box — treat that value as vat_amount and set zero_rated_sales to 0.

R10. Non-VAT supplier: If the document header says "NON-VAT REG" / "NONVAT REG", or the footer
     says "THIS DOCUMENT IS NOT VALID FOR CLAIMING INPUT TAXES", set non_vat_supplier = true
     and set vatable_sales, vat_amount, amount_net_of_vat to null (no VAT breakdown).

DOCUMENT TYPE RULES:
R11. Use the exact printed label: "SALES INVOICE", "SERVICE INVOICE", "OFFICIAL RECEIPT", "INVOICE".
     If two labels appear and one is CROSSED OUT, use the one that is NOT crossed out.

R12. Some Jollibee and fast-food documents print only "INVOICE" with no Sales/Service prefix.
     Use "INVOICE" as the document_type in that case.

HANDWRITING RULES:
R13. For all handwritten text, always attempt the closest literal reading.
     Common misreads on Philippine handwritten receipts:
     - "Meals" may appear as: MeoN / MEXA / MEX / JAEML / Meall / Meats / MeaL
     - "005" may appear as: OOS / 00S / O05
     - "717" may appear as: 7l7 / 7I7 / TH / 7IT
     - "038" may appear as: 03Y / O3Y / 03B
     When uncertain, include your best reading AND note the ambiguity in uncertain_fields.

R14. Amounts written in words ("Three Hundred Seventy") — convert to numeric (370) only as a
     last resort when no numeric value is present for that field.

FORM OF PAYMENT RULES:
R15. Fill form_of_payment only when explicitly indicated:
     - A checkbox is visibly checked or marked
     - "Cash", "Check", or "Card" is written/printed in a payment section
     - POS receipt shows "Cash: P500.00" — this means Cash
     Do NOT infer from "Received the amount of" alone.

OUTPUT RULES:
R16. Return ONLY a raw JSON object. No markdown, no preamble, no explanation whatsoever.
R17. All string values: trimmed. All number values: plain decimal, no symbols.
R18. uncertain_fields must always be present (can be empty []).
R19. If the image is NOT a financial/transaction document at all, return exactly: NOT_RECEIPT
"""

# ---------------------------------------------------------------------------
# FIELD LABELS for plain-text output
# ---------------------------------------------------------------------------
_FIELD_LABELS: list[tuple[str, str]] = [
    ("company_name",      "Company Name"),
    ("tin_no",            "TIN"),
    ("non_vat_supplier",  "Non-VAT Supplier"),
    ("location",          "Location"),
    ("date",              "Date"),
    ("inv_or_no",         "Invoice/OR No."),
    ("document_type",     "Document Type"),
    ("sold_to",           "Sold To"),
    ("sold_to_address",   "Sold To Address"),
    ("customer_tin",      "Customer TIN"),
    ("vatable_sales",     "VATable Sales"),
    ("vat_amount",        "VAT Amount"),
    ("amount_net_of_vat", "Amount Net of VAT"),
    ("vat_exempt_sales",  "VAT Exempt Sales"),
    ("zero_rated_sales",  "Zero Rated Sales"),
    ("withholding_tax",   "Withholding Tax"),
    ("total_amount",      "Total Amount"),
    ("form_of_payment",   "Form of Payment"),
]

# Year range considered plausible for Philippine BIR receipts
_MIN_PLAUSIBLE_YEAR = 2020
_MAX_PLAUSIBLE_YEAR = 2030


def _extract_full_dates_from_prompt_label(prompt_label: str) -> list[date_cls]:
    """
    Parse calendar dates embedded in upload path/filename (e.g. Screenshot 2026-04-20).

    Used to fix OCR year errors only when month/day agree with the extracted date.
    """
    if not prompt_label:
        return []
    found: list[date_cls] = []
    for m in re.finditer(
        r"(?<!\d)(19\d{2}|20\d{2})[-_/](\d{1,2})[-_/](\d{1,2})(?!\d)",
        prompt_label,
    ):
        try:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            found.append(date_cls(y, mo, d))
        except ValueError:
            continue
    return found


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

    system_instruction = (
        "You are a specialist in extracting structured data from Philippine BIR-compliant "
        "financial documents. You handle all document types: Sales Invoices, Service Invoices, "
        "Official Receipts, and generic Invoices — whether printed, handwritten, or mixed. "
        "You also handle thermal/POS-printed receipts (e.g. gasoline stations, fast food). "
        "You are highly accurate at separating supplier information (header) from buyer "
        "information (Sold To section), and you never confuse the two TIN fields.\n\n"
        + _STRICT_RULES
        + "\n\n"
        + _RECEIPT_FIELDS_SCHEMA
    )

    action = "document page" if pdf_page_mode else "image"
    user_instruction = (
        f"Extract all structured receipt/invoice fields from this {action}: {prompt_label}"
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
        temperature=0.1,
    )
    return (result.choices[0].message.content or "").strip()


def parse_receipt_json(raw_text: str) -> dict:
    """
    Parse the JSON returned by Kimi into a Python dict.
    Strips accidental markdown code fences if the model adds them.
    Returns an empty dict on parse failure.
    """
    text = raw_text.strip()
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
    if isinstance(value, bool):
        return "Yes" if value else ""   # Only show Non-VAT Supplier when true
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            return f"{value:.2f}".rstrip("0").rstrip(".")
        return str(value)
    return str(value).strip()


def _normalize_receipt_date(value: Any) -> tuple[str | None, str | None, bool]:
    """
    Normalize OCR date-like values to YYYY-MM-DD.

    Returns:
      - normalized date string (or None)
      - uncertainty note (or None)
      - used_two_digit_year flag
    """
    raw = _format_value(value)
    if not raw:
        return (None, None, False)

    # Strip ordinal suffixes
    text = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", raw, flags=re.IGNORECASE).strip()

    # Fast path: already YYYY-MM-DD
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        year = int(text[:4])
        if not (_MIN_PLAUSIBLE_YEAR <= year <= _MAX_PLAUSIBLE_YEAR):
            return (None, f"Date {text!r} has implausible year {year}; set to null.", False)
        return (text, None, False)

    # Numeric forms: MM/DD/YY, MM-DD-YYYY, YYYY/MM/DD, pipe-separated, date ranges
    token_match = re.search(
        r"(?<!\d)(\d{1,4})[|/\-](\d{1,2})[|/\-](\d{1,4})(?!\d)",
        text,
    )
    if token_match:
        a, b, c = token_match.groups()
        try:
            if len(a) == 4:
                year = int(a)
                if not (_MIN_PLAUSIBLE_YEAR <= year <= _MAX_PLAUSIBLE_YEAR):
                    return (None, f"Implausible year {year} in date; set to null.", False)
                parsed = date_cls(year, int(b), int(c))
                return (parsed.isoformat(), None, False)

            used_two_digit_year = len(c) != 4
            raw_year = int(c) if len(c) == 4 else int(f"20{c.zfill(2)}")

            if not (_MIN_PLAUSIBLE_YEAR <= raw_year <= _MAX_PLAUSIBLE_YEAR):
                return (
                    None,
                    f"Implausible year {raw_year} parsed from {text!r}; date set to null.",
                    False,
                )

            parsed = date_cls(raw_year, int(a), int(b))
            return (parsed.isoformat(), None, used_two_digit_year)
        except ValueError:
            pass

    # Month-name forms: "April 18, 2026", "18 April 2026", etc.
    for fmt in (
        "%B %d, %Y", "%b %d, %Y",
        "%B %d %Y",  "%b %d %Y",
        "%d %B %Y",  "%d %b %Y",
    ):
        try:
            parsed = datetime.strptime(text, fmt).date()
            year = parsed.year
            if not (_MIN_PLAUSIBLE_YEAR <= year <= _MAX_PLAUSIBLE_YEAR):
                return (None, f"Implausible year {year} in date; set to null.", False)
            return (parsed.isoformat(), None, False)
        except ValueError:
            continue

    # Partial dates (no year)
    has_partial_numeric = re.search(r"(?<!\d)\d{1,2}[/-]\d{1,2}(?!\d)", text) is not None
    has_partial_month_name = re.search(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}\b",
        text, flags=re.IGNORECASE,
    ) is not None
    if has_partial_numeric or has_partial_month_name:
        return (None, "Date detected but year is missing/unclear; date set to null.", False)

    return (text, "Date format not confidently normalized to YYYY-MM-DD.", False)


def _normalize_receipt_payload(
    payload: dict[str, Any], *, prompt_label: str = ""
) -> dict[str, Any]:
    normalized = dict(payload)

    # --- Date normalization + year correction ---
    date_value, date_note, used_two_digit_year = _normalize_receipt_date(
        normalized.get("date")
    )

    # Prefer upload path only when it embeds the SAME month/day (avoids wrong bumps
    # e.g. receipt Apr 9 vs filename Apr 20 screenshot).
    parsed: date_cls | None = None
    if date_value:
        try:
            parsed = date_cls.fromisoformat(date_value)
        except ValueError:
            parsed = None

    if parsed and prompt_label:
        label_dates = _extract_full_dates_from_prompt_label(prompt_label)
        for ld in label_dates:
            if ld.month == parsed.month and ld.day == parsed.day and ld.year != parsed.year:
                old_y = parsed.year
                parsed = date_cls(ld.year, parsed.month, parsed.day)
                date_value = parsed.isoformat()
                date_note = (
                    f"Year corrected from {old_y} to {ld.year} using upload path date "
                    f"{ld.isoformat()} (same month/day as extracted date)."
                )
                break

        # Two-digit OCR year only: if filename has a single plausible 4-digit year, use it.
        if used_two_digit_year and date_value:
            try:
                parsed2 = date_cls.fromisoformat(date_value)
            except ValueError:
                parsed2 = None
            if parsed2:
                years_in_label = [int(m.group(0)) for m in re.finditer(
                    r"\b(19|20)\d{2}\b", prompt_label
                )]
                unique_years = sorted(set(years_in_label))
                if len(unique_years) == 1 and unique_years[0] != parsed2.year:
                    old_y = parsed2.year
                    parsed2 = date_cls(unique_years[0], parsed2.month, parsed2.day)
                    date_value = parsed2.isoformat()
                    date_note = (
                        f"Year corrected from {old_y} to {unique_years[0]} "
                        "(2-digit OCR year + single year in upload filename)."
                    )

    normalized["date"] = date_value

    if date_note:
        notes = normalized.get("uncertain_fields")
        if not isinstance(notes, list):
            notes = []
        if date_note not in notes:
            notes.append(date_note)
        normalized["uncertain_fields"] = notes

    # --- Non-VAT: null out VAT fields ---
    if normalized.get("non_vat_supplier") is True:
        for vat_field in ("vatable_sales", "vat_amount", "amount_net_of_vat"):
            normalized.setdefault(vat_field, None)

    # --- VAT cross-check: catch cashier wrong-field entry ---
    vatable = normalized.get("vatable_sales")
    vat = normalized.get("vat_amount")
    zero_rated = normalized.get("zero_rated_sales")
    if (
        vatable is not None
        and (vat is None or vat == 0)
        and zero_rated is not None
        and zero_rated > 0
    ):
        expected_vat = round(vatable * 0.12, 2)
        if abs(zero_rated - expected_vat) < 1.0:
            notes = normalized.get("uncertain_fields")
            if not isinstance(notes, list):
                notes = []
            notes.append(
                f"zero_rated_sales {zero_rated} equals vatable_sales x 12% ({expected_vat})"
                " — likely cashier field error; moved to vat_amount."
            )
            normalized["vat_amount"] = zero_rated
            normalized["zero_rated_sales"] = 0
            normalized["uncertain_fields"] = notes

    return normalized


def _receipt_json_to_plain_text(raw_text: str, *, prompt_label: str = "") -> str:
    """
    Convert structured JSON output into clean plain text for indexing/RAG.
    Excludes particulars and uncertain_fields (noisy for indexing).
    Falls back to original text on parse failure.
    """
    text = raw_text.strip()
    if not text or text == "NOT_RECEIPT":
        return text

    payload = parse_receipt_json(text)
    if not payload:
        return text

    payload = _normalize_receipt_payload(payload, prompt_label=prompt_label)

    lines: list[str] = ["Receipt Extraction"]
    for key, label in _FIELD_LABELS:
        value = _format_value(payload.get(key))
        if value:
            lines.append(f"{label}: {value}")

    # particulars and uncertain_fields intentionally excluded from plain-text output.

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
        text = _receipt_json_to_plain_text(raw_text, prompt_label=prompt_label)
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
    Raises ExternalAIError on hard failures.
    Returns empty dict if JSON parsing fails (caller may fall back to raw text).
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
    payload = parse_receipt_json(raw)
    if not payload:
        return {}
    return _normalize_receipt_payload(payload, prompt_label=prompt_label)


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
    PDF page soft-fail path: return (text, None) on success, (None, reason) to skip.
    When relax_receipt_validation=True, keeps text that fails is_likely_receipt so
    unusual layouts are not silently dropped.
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
        text = _receipt_json_to_plain_text(raw_text, prompt_label=prompt_label)
        if text == "":
            logger.info("kimi_pdf_page_skip label=%s reason=empty", prompt_label)
            return (None, "empty")
        if text == "NOT_RECEIPT":
            logger.info("kimi_pdf_page_skip label=%s reason=not_receipt", prompt_label)
            return (None, "not_receipt")
        if config.require_receipt_signals and not is_likely_receipt(text):
            if relax_receipt_validation:
                logger.info(
                    "kimi_pdf_page_relax_accept label=%s "
                    "(output failed strict receipt heuristics)",
                    prompt_label,
                )
                return (text, None)
            logger.info(
                "kimi_pdf_page_skip label=%s reason=receipt_validation", prompt_label
            )
            return (None, "receipt_validation")
        return (text, None)
    except ExtractionCancelledError:
        raise
    except Exception as exc:
        logger.warning("kimi_pdf_page_error label=%s error=%s", prompt_label, exc)
        return (None, f"error:{exc}")