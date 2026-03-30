"""Validation rules for file/folder operations in FilesState."""

from __future__ import annotations

import os

MAX_ITEM_NAME_LENGTH = 120
FORBIDDEN_NAME_CHARS = set('/\\:*?"<>|')
ALLOWED_UPLOAD_EXTENSIONS = {
    "pdf",
    "jpg",
    "jpeg",
    "png",
    "webp",
    "gif",
    "svg",
    "csv",
    "txt",
    "md",
    "xls",
    "xlsx",
    "doc",
    "docx",
}


def normalize_item_name(name: str) -> str:
    """Trim surrounding spaces for file/folder names."""
    return name.strip()


def validate_item_name(name: str, *, kind: str) -> str | None:
    """Validate folder/file name format and constraints."""
    candidate = normalize_item_name(name)
    if not candidate:
        return f"{kind.capitalize()} name is required."
    if len(candidate) > MAX_ITEM_NAME_LENGTH:
        return f"{kind.capitalize()} name must be <= {MAX_ITEM_NAME_LENGTH} characters."
    if any(ch in FORBIDDEN_NAME_CHARS for ch in candidate):
        return f"{kind.capitalize()} name contains forbidden characters: / \\ : * ? \" < > |"
    if candidate in {".", ".."}:
        return f"{kind.capitalize()} name cannot be '.' or '..'."
    return None


def validate_upload_filename(filename: str) -> str | None:
    """Validate upload filename and extension allowlist."""
    name = os.path.basename(filename or "").strip()
    base_error = validate_item_name(name, kind="file")
    if base_error:
        return base_error
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        return f"Unsupported file type: .{ext or 'unknown'}"
    return None


def duplicate_name_error(name: str, existing: set[str], *, kind: str) -> str | None:
    """Case-insensitive duplicate name check."""
    needle = normalize_item_name(name).lower()
    if needle in {x.lower() for x in existing}:
        return f"{kind.capitalize()} '{normalize_item_name(name)}' already exists."
    return None
