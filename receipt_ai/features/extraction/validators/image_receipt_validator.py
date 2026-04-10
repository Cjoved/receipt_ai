from __future__ import annotations


def receipt_quality_warnings(extracted_text: str) -> list[str]:
    text = extracted_text.lower()
    warnings: list[str] = []
    if not any(key in text for key in ("total", "amount", "subtotal")):
        warnings.append("Receipt signal missing: total/amount not detected.")
    if not any(key in text for key in ("date", "time", "invoice", "receipt")):
        warnings.append("Receipt signal missing: date or receipt marker not detected.")
    if len(extracted_text.strip()) < 30:
        warnings.append("Image extraction output is too short.")
    return warnings
