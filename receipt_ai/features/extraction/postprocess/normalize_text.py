from __future__ import annotations


def normalize_text(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    compact: list[str] = []
    prev_blank = False
    for line in lines:
        blank = line.strip() == ""
        if blank and prev_blank:
            continue
        compact.append(line)
        prev_blank = blank
    return "\n".join(compact).strip()


def low_quality_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    stripped = text.strip()
    if stripped == "":
        warnings.append("No text extracted.")
        return warnings
    if len(stripped) < 20:
        warnings.append("Extracted text is very short.")
    if "�" in stripped:
        warnings.append("Extracted text contains replacement characters (encoding issue).")
    return warnings
