from dataclasses import dataclass


@dataclass(frozen=True)
class FileItem:
    """Domain model for a file shown in the explorer/cards."""

    name: str
    size: str
    file_type: str
    status: str = "Completed"
