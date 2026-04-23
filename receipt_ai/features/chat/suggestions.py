from __future__ import annotations


FALLBACK_SUGGESTIONS: list[str] = [
    "Summarize the total amount and date from my latest receipt.",
    "List line items from this receipt in a clean table.",
    "Find VAT/tax amount and subtotal from the uploaded image.",
    "Check if this receipt looks complete or missing fields.",
]


def _extension(name: str) -> str:
    text = (name or "").strip().lower()
    if "." not in text:
        return ""
    return text.rsplit(".", 1)[-1]


def build_contextual_suggestions(*, folder_name: str, file_name: str, role: str = "user") -> list[str]:
    folder = (folder_name or "").strip()
    file = (file_name or "").strip()
    role_name = (role or "user").strip().lower()
    ext = _extension(file)
    if file:
        prompts = [
            f"Extract merchant, date, and total from {file}.",
            f"Give me a short expense summary for {file}.",
            f"Check if {file} has tax/VAT details.",
        ]
        if ext in {"jpg", "jpeg", "png", "webp", "gif", "bmp", "jfif"}:
            prompts.append(f"Read this image receipt from {file} and list all line items.")
        if ext == "pdf":
            prompts.append(f"Compare totals per page for {file}.")
        if role_name == "admin":
            prompts.append(f"Flag anomalies and possible duplicates for {file}.")
        return prompts
    if folder:
        prompts = [
            f"Compare totals across receipts in {folder}.",
            f"Find possible duplicate receipts inside {folder}.",
            f"Show unusual amounts from files in {folder}.",
        ]
        if role_name == "admin":
            prompts.append(f"Summarize expense trends in {folder} by week.")
        return prompts
    if role_name == "admin":
        return [
            "Show me the riskiest receipts by unusual totals.",
            "Suggest a quick audit checklist for recent uploads.",
        ]
    return []


def build_hybrid_suggestions(*, folder_name: str, file_name: str, role: str = "user") -> list[str]:
    contextual = build_contextual_suggestions(folder_name=folder_name, file_name=file_name, role=role)
    merged: list[str] = []
    for prompt in [*contextual, *FALLBACK_SUGGESTIONS]:
        if prompt not in merged:
            merged.append(prompt)
    return merged[:6]
