import reflex as rx

from receipt_ai.features.files.service import list_files_payload


class FilesState(rx.State):
    """State container for files feature."""

    files: list[dict[str, str]] = list_files_payload()
    selected_file_name: str = files[0]["name"] if files else ""
    show_new_folder_input: bool = False
    new_folder_name: str = ""
    show_rename_input: bool = False
    rename_value: str = ""
    
    def load_files(self) -> None:
        """Refresh files from service layer."""

        self.files = list_files_payload()
        if self.files and not self.selected_file_name:
            self.selected_file_name = self.files[0]["name"]

    def select_file(self, file_name: str) -> None:
        """Select a file by name."""

        self.selected_file_name = file_name
    
    def open_new_folder_input(self) -> None:
        self.show_new_folder_input = True

    def cancel_new_folder(self) -> None:
        self.show_new_folder_input = False
        self.new_folder_name = ""

    def set_new_folder_name(self, value: str) -> None:
        self.new_folder_name = value

    def create_new_folder(self) -> None:
        new_folder_name = self.new_folder_name.strip()
        if not new_folder_name:
            return
        
        self.files.insert(0,{"name" : f"{new_folder_name}", "size": "0 KB", "file_type": "folder", "status": "Ready"},)
        self.show_new_folder_input = False
        self.new_folder_name = ""

    def open_rename_input(self) -> None:
        if self.selected_file_name:
            self.rename_value = self.selected_file_name
            self.show_rename_input = True

    def set_rename_value(self, value: str) -> None:
        self.rename_value = value

    def save_rename(self) -> None:
        new_name = self.rename_value.strip()
        if not new_name:
            return

        for item in self.files:
            if item["name"] == self.selected_file_name:
                item["name"] = new_name
                self.selected_file_name = new_name
                break
        self.show_rename_input = False
        self.rename_value = ""

    def cancel_rename(self) -> None:
        self.show_rename_input = False
        self.rename_value = ""

    def delete_file(self) -> None:
        if not self.selected_file_name:
            return
        
        self.files = [f for f in self.files if f["name"] != self.selected_file_name]
        self.selected_file_name = self.files[0]["name"] if self.files else ""


    @rx.var
    def file_names(self) -> list[str]:
        return [item["name"] for item in self.files]
