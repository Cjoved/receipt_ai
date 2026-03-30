def child_file_meta(filename: str) -> dict[str, str]:
    """Build display metadata (ext/icon/badge) for a file name."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in {"png", "jpg", "jpeg", "gif", "webp", "svg"}:
        return {"name": filename, "ext": ext.upper(), "icon": "file-image", "badge": "purple", "type": "Image"}
    if ext in {"xls", "xlsx", "csv"}:
        return {"name": filename, "ext": ext.upper(), "icon": "file-spreadsheet", "badge": "green", "type": "Spreadsheet"}
    if ext in {"doc", "docx", "txt", "md"}:
        return {"name": filename, "ext": ext.upper(), "icon": "file-text", "badge": "blue", "type": "Document"}
    if ext == "pdf":
        return {"name": filename, "ext": "PDF", "icon": "file-text", "badge": "red", "type": "PDF"}
    if ext in {"zip", "rar", "7z"}:
        return {"name": filename, "ext": ext.upper(), "icon": "file-archive", "badge": "orange", "type": "Archive"}
    return {"name": filename, "ext": (ext.upper() if ext else "FILE"), "icon": "file", "badge": "gray", "type": "File"}
