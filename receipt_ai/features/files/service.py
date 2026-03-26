from receipt_ai.features.files.models import FileItem


_SEED_FILES: tuple[FileItem, ...] = (
    FileItem("My Files", "-", "FOLDER"),
)


def list_files() -> list[FileItem]:
    """Return the current file list.

    In production this should read from a database or storage service.
    """

    # Return a copy so seed data stays immutable.
    return list(_SEED_FILES)


def list_files_payload() -> list[dict[str, str]]:
    """Serialize files to UI-friendly payload for state/components."""

    # Convert domain model objects to simple dictionaries for UI state usage.
    return [
        {
            "name": item.name,
            "size": item.size,
            "file_type": item.file_type,
            "status": item.status,
        }
        for item in list_files()
    ]
