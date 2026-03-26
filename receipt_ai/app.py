import reflex as rx

from receipt_ai.features.chat.state import ChatState
from receipt_ai.features.files.state import FilesState
from receipt_ai.pages.chat_page import chat_page
from receipt_ai.pages.files_page import files_page


def create_app() -> rx.App:
    """Application factory that wires routes and page load handlers."""
    app = rx.App()
    # Files page is the home route.
    app.add_page(files_page, route="/", on_load=FilesState.load_files)
    # Chat page route and initial history load.
    app.add_page(chat_page, route="/chat", on_load=ChatState.load_history)
    return app
