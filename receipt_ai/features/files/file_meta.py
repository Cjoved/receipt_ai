def child_file_meta(filename: str) -> dict[str, str]:
    """Build display metadata (ext/icon/badge) for a file name."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in {"png", "jpg", "jpeg", "gif", "webp", "svg"}:
        return {"name": filename, "ext": ext.upper(), "icon": "file-image", "badge": "purple"}
    if ext in {"xls", "xlsx", "csv"}:
        return {"name": filename, "ext": ext.upper(), "icon": "file-spreadsheet", "badge": "green"}
    if ext in {"doc", "docx", "txt", "md"}:
        return {"name": filename, "ext": ext.upper(), "icon": "file-text", "badge": "blue"}
    if ext == "pdf":
        return {"name": filename, "ext": "PDF", "icon": "file-text", "badge": "red"}
    if ext in {"zip", "rar", "7z"}:
        return {"name": filename, "ext": ext.upper(), "icon": "file-archive", "badge": "orange"}
    return {"name": filename, "ext": (ext.upper() if ext else "FILE"), "icon": "file", "badge": "gray"}
