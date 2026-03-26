import reflex as rx
from pathlib import Path
from typing import Any
from receipt_ai.core.upload_constants import FILES_UPLOAD_ZONE_ID
from receipt_ai.features.files.file_meta import child_file_meta
from receipt_ai.features.files.service import list_files_payload


class FilesState(rx.State):
    """State container for files feature."""

    files: list[dict[str, str]] = list_files_payload()
    selected_file_name: str = files[0]["name"] if files else ""
    show_new_folder_input: bool = False
    new_folder_name: str = ""
    show_rename_input: bool = False
    rename_value: str = ""
    view_mode: str = "grid"

    # Upload overlay state (global drag/drop modal).
    show_drop_overlay: bool = False
    is_uploading: bool = False
    upload_error: str = ""
    upload_dir: str = "assets/uploads"
    upload_zone_id: str = FILES_UPLOAD_ZONE_ID

    # Which folder is currently expanded in the sidebar.
    expanded_folder_name: str = ""

    # Demo children files per folder (local mock for now).
    folder_children: dict[str, list[dict[str, str]]] = {
        "My Files": [
            {"name": "invoice_jan.pdf", "ext": "PDF", "icon": "file-text", "badge": "red"},
            {"name": "receipt_store.png", "ext": "PNG", "icon": "file-image", "badge": "purple"},
            {"name": "report.xlsx", "ext": "XLSX", "icon": "file-spreadsheet", "badge": "green"},
        ],
    }

    # Reload list from the service layer (used on page load).
    def load_files(self) -> None:
        """Refresh files from service layer."""

        self.files = list_files_payload()
        if self.files and not self.selected_file_name:
            self.selected_file_name = self.files[0]["name"]

    # Track which file/folder row is currently selected in the sidebar.
    def select_file(self, file_name: str) -> None:
        """Select a file by name."""

        self.selected_file_name = file_name
    
    # Show inline input controls for creating a new folder.
    def open_new_folder_input(self) -> None:
        self.show_new_folder_input = True

    # Close create-folder form and reset its input value.
    def cancel_new_folder(self) -> None:
        self.show_new_folder_input = False
        self.new_folder_name = ""

    # Keep new-folder input field synchronized with state.
    def set_new_folder_name(self, value: str) -> None:
        self.new_folder_name = value

    # Add a new folder entry to the in-memory file list.
    def create_new_folder(self) -> None:
        new_folder_name = self.new_folder_name.strip()
        if not new_folder_name:
            return
        
        self.files.insert(0,{"name" : f"{new_folder_name}", "size": "0 KB", "file_type": "folder", "status": "Ready"},)
        self.show_new_folder_input = False
        self.new_folder_name = ""
        self.folder_children[new_folder_name] = []

    # Open rename form and prefill with selected file/folder name.
    def open_rename_input(self) -> None:
        if not self.has_open_folder:
            return
        if self.selected_file_name:
            self.rename_value = self.selected_file_name
            self.show_rename_input = True

    # Keep rename input synchronized with state.
    def set_rename_value(self, value: str) -> None:
        self.rename_value = value

    # Persist rename change into the selected list item.
    def save_rename(self) -> None:
        new_name = self.rename_value.strip()
        if not new_name:
            return

        old_name = self.selected_file_name
        for item in self.files:
            if item["name"] == old_name:
                item["name"] = new_name
                self.selected_file_name = new_name
                if old_name in self.folder_children:
                    self.folder_children[new_name] = self.folder_children.pop(old_name)
                if self.expanded_folder_name == old_name:
                    self.expanded_folder_name = new_name
                break
        self.show_rename_input = False
        self.rename_value = ""

    # Close rename form without applying changes.
    def cancel_rename(self) -> None:
        self.show_rename_input = False
        self.rename_value = ""

    # Delete currently selected item and move selection to first remaining row.
    def delete_file(self) -> None:
        if not self.has_open_folder:
            return
        if self.selected_file_name in self.folder_children:
            del self.folder_children[self.selected_file_name]
        if not self.selected_file_name:
            return
        
        self.files = [f for f in self.files if f["name"] != self.selected_file_name]
        self.selected_file_name = self.files[0]["name"] if self.files else ""
        self.expanded_folder_name = ""

    # Open upload modal from the upload icon button.
    def open_upload_input(self) -> None:
        """Open upload overlay from toolbar upload button."""
        if not self.has_open_folder:
            return
        self.show_drop_overlay = True
        self.upload_error = ""

    # Reserved for future global drag-enter behavior.
    def open_drop_overlay(self) -> None:
        """Open upload overlay when a drag enters the page."""
        self.show_drop_overlay = True
        self.upload_error = ""

    # Cancel active transfer (if any) and close modal.
    def cancel_upload(self) -> None:
        """Cancel active upload and close the overlay."""
        self.show_drop_overlay = False
        self.is_uploading = False
        self.upload_error = ""
        return rx.cancel_upload(self.upload_zone_id)

    # Save dropped/selected files into local upload directory and add them to UI list.
    async def upload_files(self, files: list[rx.UploadFile]) -> None:
        """Persist uploaded files locally and reflect them in explorer list."""
        if not files:
            return
        if not self.expanded_folder_name:
            self.upload_error = "Please open a folder first."
            return

        self.is_uploading = True
        self.upload_error = ""

        try:
            target_dir = Path(self.upload_dir)
            target_dir.mkdir(parents=True, exist_ok=True)

            for file in files:
                data = await file.read()
                save_path = target_dir / file.filename
                save_path.write_bytes(data)
                target_folder = self.expanded_folder_name
                if target_folder not in self.folder_children:
                    self.folder_children[target_folder] = []
                self.folder_children[target_folder].insert(0, child_file_meta(file.filename))
            self.selected_file_name = files[0].filename
            self.show_drop_overlay = False

        except Exception as e:
            self.upload_error = f"Upload failed: {e}"
        finally:
            self.is_uploading = False

    # Toggle the expansion state of a folder.
    def toggle_folder(self, folder_name: str) -> None:
        """Toggle the expansion state of a folder."""
        if self.expanded_folder_name == folder_name:
            self.expanded_folder_name = ""
            self.selected_file_name = ""
        else:
            self.expanded_folder_name = folder_name
            self.selected_file_name = folder_name

    # Switch right panel into grid card mode.
    def set_grid_view(self) -> None:
        self.view_mode = "grid"

    # Switch right panel into list/explorer mode.
    def set_list_view(self) -> None:
        self.view_mode = "list"
    
    @rx.var
    # True when a folder expanded (enables folder-only actions)
    def has_open_folder(self) -> bool:
        return self.expanded_folder_name != ""
    
    @rx.var
    # Convenience flag for UI enable/disable logic.
    def can_cancel_upload(self) -> bool:
        return not self.is_uploading

    @rx.var
    # Derived list used by the sidebar foreach renderer.
    def file_names(self) -> list[str]:
        return [item["name"] for item in self.files]

    @rx.var
    # Folder-only list for rendering expandable rows in sidebar.
    def folder_names(self) -> list[str]:
        return [item["name"] for item in self.files if item.get("file_type", "").lower() == "folder"]

    @rx.var
    # Child file rows for the currently expanded folder.
    def active_folder_children(self) -> list[dict[str, str]]:
        if not self.expanded_folder_name:
            return []
        children: list[Any] = self.folder_children.get(self.expanded_folder_name, [])
        normalized: list[dict[str, str]] = []
        for child in children:
            if isinstance(child, dict):
                name = child.get("name", "")
                if name:
                    normalized.append(
                        {
                            "name": name,
                            "ext": child.get("ext", "FILE"),
                            "icon": child.get("icon", "file"),
                            "badge": child.get("badge", "gray"),
                        }
                    )
            elif isinstance(child, str):
                normalized.append(child_file_meta(child))
        return normalized
