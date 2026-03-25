from receipt_ai.features.files.models import FileItem


_SEED_FILES: tuple[FileItem, ...] = (
    FileItem("AI Trainer Budget Summary.xlsx", "173 KB", "XLSX"),
    FileItem("Ceiling Labor Estimate.pdf", "157 KB", "PDF"),
    FileItem("pldt_dexter.pdf", "539 KB", "PDF"),
    FileItem("viber_image_2026-03-22.jpg", "145 KB", "JPG"),
    FileItem("Sovereign_AL_for_Filipino_Farmers.pdf", "1.7 MB", "PDF"),
    FileItem("JAS & Digi fiesta Attendance launching.pdf", "4.9 MB", "PDF"),
)


def list_files() -> list[FileItem]:
    """Return the current file list.

    In production this should read from a database or storage service.
    """

    return list(_SEED_FILES)


def list_files_payload() -> list[dict[str, str]]:
    """Serialize files to UI-friendly payload for state/components."""

    return [
        {
            "name": item.name,
            "size": item.size,
            "file_type": item.file_type,
            "status": item.status,
        }
        for item in list_files()
    ]
