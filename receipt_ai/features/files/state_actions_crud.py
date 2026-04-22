import reflex as rx

from receipt_ai.features.auth.state import AuthState
from receipt_ai.features.files.validation import (
    duplicate_name_error,
    normalize_item_name,
    validate_item_name,
)


class FilesCrudActionsMixin:
    """CRUD and selection actions for files/folders."""

    def _explorer_folder_names(self) -> list[str]:
        """Folder row names in the sidebar (same rules as FilesComputedMixin.folder_names)."""
        names: list[str] = []
        for item in self.files:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            ft = str(item.get("file_type", "folder")).lower()
            if ft == "folder":
                names.append(name)
        return names

    def _sync_create_folder_button(self) -> None:
        """Keep Create enabled state in sync (plain bool for reliable button disabled binding)."""
        if not self.show_new_folder_input:
            self.create_folder_btn_enabled = False
            return
        candidate = normalize_item_name(self.new_folder_name)
        if candidate == "":
            self.create_folder_btn_enabled = False
            return
        if validate_item_name(candidate, kind="folder"):
            self.create_folder_btn_enabled = False
            return
        dup = duplicate_name_error(candidate, set(self._explorer_folder_names()), kind="folder")
        self.create_folder_btn_enabled = dup is None

    def _sync_rename_save_button(self) -> None:
        """Keep Save enabled state in sync for inline rename."""
        if not self.show_rename_input:
            self.rename_save_btn_enabled = False
            return
        candidate = normalize_item_name(self.rename_value)
        if candidate == "":
            self.rename_save_btn_enabled = False
            return
        kind = "file" if self.selected_child_file_name else "folder"
        if validate_item_name(candidate, kind=kind):
            self.rename_save_btn_enabled = False
            return
        if self.selected_child_file_name:
            existing = {
                child["name"]
                for child in self.active_folder_children
                if child.get("name", "").lower() != self.selected_child_file_name.lower()
            }
            dup = duplicate_name_error(candidate, existing, kind="file")
            self.rename_save_btn_enabled = dup is None
            return
        if self.expanded_folder_name:
            existing_folders = {
                name
                for name in self._explorer_folder_names()
                if name.lower() != self.expanded_folder_name.lower()
            }
            dup = duplicate_name_error(candidate, existing_folders, kind="folder")
            self.rename_save_btn_enabled = dup is None
            return
        self.rename_save_btn_enabled = False

    async def _ensure_files_read_permission(self) -> bool:
        auth = await self.get_state(AuthState)
        if auth.has_permission("files:read"):
            return True
        self.upload_error = "Access denied: admin Files access is required."
        return False

    async def _ensure_files_write_permission(self) -> bool:
        auth = await self.get_state(AuthState)
        if auth.has_permission("files:write"):
            return True
        self.upload_error = "Access denied: admin Files write access is required."
        return False

    # Reload list from the service layer (used on page load).
    async def load_files(self) -> None:
        """Load files from wasabi and reflect them in the explorer list."""
        if not await self._ensure_files_read_permission():
            self.files = []
            self.folder_children = {}
            self.expanded_folder_name = ""
            self.selected_file_name = ""
            self.selected_child_file_name = ""
            self._clear_preview_state()
            self.upload_error = "Access denied: admin Files access is required."
            return
        try:
            storage = self._get_storage()
            folder_names = storage.list_folders()
            if folder_names:
                self.files = [
                    {"name": folder, "size": "-", "file_type": "folder", "status": "Ready"}
                    for folder in folder_names
                ]
            else:
                # Fallback seed so UI never appears empty when bucket has no folder markers yet.
                self.files = [
                    {"name": "My Files", "size": "-", "file_type": "folder", "status": "Ready"}
                ]
                folder_names = [item["name"] for item in self.files if item.get("file_type", "").lower() == "folder"]

            # Reset per-folder file lists so stale demo/cache rows never mix with Wasabi.
            # Actual objects load when the user expands a folder (_reload_folder_children).
            self.folder_children = {name: [] for name in folder_names}

            # Start with no folder expanded — user picks a folder from the Explorer first.
            self.selected_file_name = ""
            self.expanded_folder_name = ""
            self.selected_child_file_name = ""
            self._clear_preview_state()
        except Exception as e:
            self.upload_error = f"Failed to load files: {e}"

    # Show inline input controls for creating a new folder.
    def open_new_folder_input(self) -> None:
        self.show_new_folder_input = True
        self._sync_create_folder_button()

    # Close create-folder form and reset its input value.
    def cancel_new_folder(self) -> None:
        """Close create-folder form without applying changes."""
        self.show_new_folder_input = False
        self.new_folder_name = ""
        self.create_folder_btn_enabled = False

    # Keep new-folder input field synchronized with state.
    def set_new_folder_name(self, value: str) -> None:
        self.new_folder_name = value
        self._sync_create_folder_button()

    # Add a new folder entry to the in-memory file list.
    async def create_new_folder(self) -> None:
        """Create a new folder in Wasabi and reflect it in the explorer list."""
        if not await self._ensure_files_write_permission():
            return rx.toast.error(self.upload_error)
        new_folder_name = normalize_item_name(self.new_folder_name)
        base_error = validate_item_name(new_folder_name, kind="folder")
        if base_error:
            self.upload_error = base_error
            return
        duplicate_error = duplicate_name_error(new_folder_name, set(self.folder_names), kind="folder")
        if duplicate_error:
            self.upload_error = duplicate_error
            return

        try:
            storage = self._get_storage()
            # Create virtual folder object in bucket (key ending with slash).
            storage.create_folder(new_folder_name)

            self.files = [
                {
                    "name": new_folder_name,
                    "size": "-",
                    "file_type": "folder",
                    "status": "Ready",
                },
                *self.files,
            ]
            self.folder_children = {**self.folder_children, new_folder_name: []}
            self.show_new_folder_input = False
            self.new_folder_name = ""
            self.create_folder_btn_enabled = False
            self.upload_error = ""
            return rx.toast.success(f"Folder created: {new_folder_name}")
        except Exception as e:
            self.upload_error = f"Failed to create folder: {e}"
            return rx.toast.error(f"Failed to create folder: {e}")

    # Open rename form and prefill with selected file name or folder name.
    def open_rename_input(self) -> None:
        if not self.expanded_folder_name:
            return
        if self.selected_child_file_name:
            self.rename_value = self.selected_child_file_name
        elif self.expanded_folder_name:
            self.rename_value = self.expanded_folder_name
        else:
            return
        self.show_rename_input = True
        self._sync_rename_save_button()

    # Keep rename input synchronized with state.
    def set_rename_value(self, value: str) -> None:
        self.rename_value = value
        self._sync_rename_save_button()

    # Persist rename change into the selected list item.
    async def save_rename(self) -> None:
        """Rename selected file or folder in wasabi and sync local state"""
        if not await self._ensure_files_write_permission():
            return rx.toast.error(self.upload_error)
        new_name = normalize_item_name(self.rename_value)

        try:
            storage = self._get_storage()
            toast_message = ""
            # Rename a single file inside the expanded folder.
            if self.selected_child_file_name and self.expanded_folder_name:
                base_error = validate_item_name(new_name, kind="file")
                if base_error:
                    self.upload_error = base_error
                    return
                if any(sep in new_name for sep in ("/", "\\")):
                    self.upload_error = "Use a file name only (no path)."
                    return
                folder = self.expanded_folder_name
                storage_folder = self._resolve_storage_folder_name(folder)
                old_base = self.selected_child_file_name
                existing_children = {
                    child["name"]
                    for child in self.active_folder_children
                    if child.get("name", "").lower() != old_base.lower()
                }
                duplicate_error = duplicate_name_error(new_name, existing_children, kind="file")
                if duplicate_error:
                    self.upload_error = duplicate_error
                    return
                old_rel = f"{storage_folder}/{old_base}"
                new_rel = f"{storage_folder}/{new_name}"
                storage.rename_object(old_rel, new_rel)
                self.selected_child_file_name = new_name
                self._reload_folder_children(folder)
                self._refresh_preview_url()
                toast_message = f"File renamed to: {new_name}"
            else:
                # Rename whole folder prefix recursively in Wasabi.
                old_name = self.expanded_folder_name
                if not old_name:
                    return
                old_storage_name = self._resolve_storage_folder_name(old_name)
                base_error = validate_item_name(new_name, kind="folder")
                if base_error:
                    self.upload_error = base_error
                    return
                existing_folders = {name for name in self.folder_names if name.lower() != old_name.lower()}
                duplicate_error = duplicate_name_error(new_name, existing_folders, kind="folder")
                if duplicate_error:
                    self.upload_error = duplicate_error
                    return
                storage.rename_prefix(old_storage_name, new_name)

                for item in self.files:
                    if item["name"] == old_name:
                        item["name"] = new_name
                        self.selected_file_name = new_name
                        if old_name in self.folder_children:
                            moved_children = self.folder_children.get(old_name, [])
                            self.folder_children = {
                                key: value
                                for key, value in self.folder_children.items()
                                if key != old_name
                            }
                            self.folder_children = {**self.folder_children, new_name: moved_children}
                        if self.expanded_folder_name == old_name:
                            self.expanded_folder_name = new_name
                        toast_message = f"Folder renamed to: {new_name}"
                        break
            self.show_rename_input = False
            self.rename_value = ""
            self.rename_save_btn_enabled = False
            self.show_rename_confirm = False
            self.upload_error = ""
            if toast_message:
                return rx.toast.success(toast_message)
        except Exception as e:
            self.upload_error = f"Failed to rename: {e}"
            return rx.toast.error(f"Failed to rename: {e}")

    # Close rename form without applying changes.
    def cancel_rename(self) -> None:
        self.show_rename_input = False
        self.rename_value = ""
        self.rename_save_btn_enabled = False
        self.show_rename_confirm = False

    def request_rename_confirm(self) -> None:
        """Open rename confirmation modal after passing frontend validations."""
        self._sync_rename_save_button()
        if not self.rename_save_btn_enabled:
            return
        self.show_rename_confirm = True

    def cancel_rename_confirm(self) -> None:
        """Close rename confirmation modal without applying changes."""
        self.show_rename_confirm = False

    # Delete currently selected file or folder and sync UI state.
    async def delete_file(self) -> None:
        """Delete selected file in the open folder, or the whole folder if none selected."""
        if not await self._ensure_files_write_permission():
            return rx.toast.error(self.upload_error)
        if not self.expanded_folder_name:
            return

        try:
            storage = self._get_storage()
            if self.selected_child_file_name and self.expanded_folder_name:
                folder = self.expanded_folder_name
                fname = self.selected_child_file_name
                storage_folder = self._resolve_storage_folder_name(folder)
                storage.delete_object(f"{storage_folder}/{fname}")
                self.selected_child_file_name = ""
                self._reload_folder_children(folder)
                self._clear_preview_state()
                self.upload_error = ""
                return rx.toast.success(f"Deleted file: {fname}")

            target_name = self.selected_file_name
            if not target_name:
                return
            storage_target = self._resolve_storage_folder_name(target_name)
            storage.delete_prefix(storage_target)

            if target_name in self.folder_children:
                self.folder_children = {
                    key: value
                    for key, value in self.folder_children.items()
                    if key != target_name
                }

            self.files = [f for f in self.files if f["name"] != target_name]
            self.selected_file_name = self.files[0]["name"] if self.files else ""
            self.expanded_folder_name = ""
            self.selected_child_file_name = ""
            self._clear_preview_state()
            self.upload_error = ""
            return rx.toast.success(f"Deleted folder: {target_name}")
        except Exception as e:
            self.upload_error = f"Failed to delete: {e}"
            return rx.toast.error(f"Failed to delete: {e}")

    def request_delete_confirm(self) -> None:
        """Open delete confirmation modal for selected file/folder."""
        if not self.expanded_folder_name:
            return
        self.show_delete_confirm = True

    def request_delete_child_confirm(self, filename: str) -> None:
        """Select a child file then open delete confirmation modal."""
        self.selected_child_file_name = filename
        self.show_delete_confirm = True

    def cancel_delete_confirm(self) -> None:
        """Close delete confirmation modal without deleting."""
        self.show_delete_confirm = False

    async def confirm_delete(self) -> None:
        """Confirm destructive delete action."""
        result = await self.delete_file()
        self.show_delete_confirm = False
        return result

    async def delete_child_file(self, filename: str) -> None:
        """Delete one specific child file from current folder (row action)."""
        if not await self._ensure_files_write_permission():
            return rx.toast.error(self.upload_error)
        if not self.expanded_folder_name:
            return
        try:
            storage = self._get_storage()
            folder = self.expanded_folder_name
            storage_folder = self._resolve_storage_folder_name(folder)
            storage.delete_object(f"{storage_folder}/{filename}")
            if self.selected_child_file_name == filename:
                self.close_preview()
            self._reload_folder_children(folder)
            return rx.toast.success(f"Deleted file: {filename}")
        except Exception as e:
            self.upload_error = f"Failed to delete file: {e}"
            return rx.toast.error(f"Failed to delete file: {e}")

    # Toggle the expansion state of a folder.
    async def toggle_folder(self, folder_name: str) -> None:
        """Toggle the expansion state of a folder."""
        if not await self._ensure_files_read_permission():
            return rx.toast.error(self.upload_error)
        if self.expanded_folder_name == folder_name:
            self.expanded_folder_name = ""
            self.selected_file_name = ""
            self.selected_child_file_name = ""
            self._clear_preview_state()
            return
        self.expanded_folder_name = folder_name
        self.selected_file_name = folder_name
        self.selected_child_file_name = ""
        self._clear_preview_state()
        self.upload_error = ""

        try:
            self._reload_folder_children(folder_name)
        except Exception as e:
            self.upload_error = f"Failed to load folder files: {e}"

    # Switch right panel into grid card mode.
    def set_grid_view(self) -> None:
        self.view_mode = "grid"

    # Switch right panel into list/explorer mode.
    def set_list_view(self) -> None:
        self.view_mode = "list"

    def set_search_query(self, value: str) -> None:
        """Update free-text search query for visible files."""
        self.search_query = value

    def clear_search_query(self) -> None:
        """Reset search query."""
        self.search_query = ""

    def set_type_filter(self, value: str) -> None:
        """Set file type filter key."""
        self.active_type_filter = value

    def set_sort_mode(self, value: str) -> None:
        """Set active sort mode for visible files."""
        self.sort_mode = value
