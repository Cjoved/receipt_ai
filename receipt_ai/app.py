import reflex as rx

from receipt_ai.features.chat.state import ChatState
from receipt_ai.features.files.state import FilesState
from receipt_ai.pages.chat_page import chat_page
from receipt_ai.pages.files_page import files_page


def create_app() -> rx.App:
    app = rx.App()
    app.add_page(files_page, route="/", on_load=FilesState.load_files)
    app.add_page(chat_page, route="/chat", on_load=ChatState.load_history)
    return app
