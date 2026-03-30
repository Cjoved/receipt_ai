from receipt_ai.features.files.validation import (
    duplicate_name_error,
    normalize_item_name,
    validate_item_name,
)


class FilesCrudActionsMixin:
    """CRUD and selection actions for files/folders."""

    # Reload list from the service layer (used on page load).
    def load_files(self) -> None:
        """Load files from wasabi and reflect them in the explorer list."""
        try:
            storage = self._get_storage()
            folder_names = storage.list_folders()
            use_storage_folders = len(folder_names) > 0
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

            # Ensure local child cache has keys for fetched folders.
            next_children = dict(self.folder_children)
            for folder_name in folder_names:
                if folder_name not in next_children:
                    next_children[folder_name] = []
            self.folder_children = next_children

            self.selected_file_name = self.files[0]["name"] if self.files else ""
            # Auto-open first folder so users immediately see files.
            if self.selected_file_name:
                self.expanded_folder_name = self.selected_file_name
                # Keep seed children when no Wasabi folders are available.
                if use_storage_folders:
                    self._reload_folder_children(self.selected_file_name)
            else:
                self.expanded_folder_name = ""
                self.selected_child_file_name = ""
                self._clear_preview_state()
        except Exception as e:
            self.upload_error = f"Failed to load files: {e}"

    # Show inline input controls for creating a new folder.
    def open_new_folder_input(self) -> None:
        self.show_new_folder_input = True

    # Close create-folder form and reset its input value.
    def cancel_new_folder(self) -> None:
        """Close create-folder form without applying changes."""
        self.show_new_folder_input = False
        self.new_folder_name = ""

    # Keep new-folder input field synchronized with state.
    def set_new_folder_name(self, value: str) -> None:
        self.new_folder_name = value

    # Add a new folder entry to the in-memory file list.
    def create_new_folder(self) -> None:
        """Create a new folder in Wasabi and reflect it in the explorer list."""
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
            self.upload_error = ""
        except Exception as e:
            self.upload_error = f"Failed to create folder: {e}"

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

    # Keep rename input synchronized with state.
    def set_rename_value(self, value: str) -> None:
        self.rename_value = value

    # Persist rename change into the selected list item.
    def save_rename(self) -> None:
        """Rename selected file or folder in wasabi and sync local state"""
        new_name = normalize_item_name(self.rename_value)

        try:
            storage = self._get_storage()
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
                        break
            self.show_rename_input = False
            self.rename_value = ""
            self.show_rename_confirm = False
            self.upload_error = ""
        except Exception as e:
            self.upload_error = f"Failed to rename: {e}"

    # Close rename form without applying changes.
    def cancel_rename(self) -> None:
        self.show_rename_input = False
        self.rename_value = ""
        self.show_rename_confirm = False

    def request_rename_confirm(self) -> None:
        """Open rename confirmation modal after passing frontend validations."""
        if not self.can_save_rename:
            return
        self.show_rename_confirm = True

    def cancel_rename_confirm(self) -> None:
        """Close rename confirmation modal without applying changes."""
        self.show_rename_confirm = False

    # Delete currently selected file or folder and sync UI state.
    def delete_file(self) -> None:
        """Delete selected file in the open folder, or the whole folder if none selected."""
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
                return

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
        except Exception as e:
            self.upload_error = f"Failed to delete: {e}"

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

    def confirm_delete(self) -> None:
        """Confirm destructive delete action."""
        self.delete_file()
        self.show_delete_confirm = False

    def delete_child_file(self, filename: str) -> None:
        """Delete one specific child file from current folder (row action)."""
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
        except Exception as e:
            self.upload_error = f"Failed to delete file: {e}"

    # Toggle the expansion state of a folder.
    def toggle_folder(self, folder_name: str) -> None:
        """Toggle the expansion state of a folder."""
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
