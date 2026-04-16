from __future__ import annotations


_TOTAL_KEYS = ("total", "amount", "subtotal")
_PROOF_KEYS = ("date", "time", "invoice", "receipt")


def receipt_quality_warnings(extracted_text: str) -> list[str]:
    text = extracted_text.lower()
    warnings: list[str] = []
    if not any(key in text for key in _TOTAL_KEYS):
        warnings.append("Receipt signal missing: total/amount not detected.")
    if not any(key in text for key in _PROOF_KEYS):
        warnings.append("Receipt signal missing: date or receipt marker not detected.")
    if len(extracted_text.strip()) < 30:
        warnings.append("Image extraction output is too short.")
    return warnings


def is_likely_receipt(extracted_text: str) -> bool:
    """Strict receipt gate: require monetary cue + receipt/proof cue + minimum length."""
    text = extracted_text.lower()
    if len(text.strip()) < 30:
        return False
    has_total = any(key in text for key in _TOTAL_KEYS)
    has_proof = any(key in text for key in _PROOF_KEYS)
    return has_total and has_proof
