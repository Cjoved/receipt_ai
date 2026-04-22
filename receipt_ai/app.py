import reflex as rx
from reflex.constants import Page404

from receipt_ai.features.auth.state import AuthState
from receipt_ai.features.chat.state import ChatState
from receipt_ai.features.files.state import FilesState
from receipt_ai.pages.chat_page import chat_page
from receipt_ai.pages.files_page import files_page
from receipt_ai.pages.login_page import login_page
from receipt_ai.pages.not_found_page import not_found_page


def create_app() -> rx.App:
    """Application factory: Radix theme, routes, document titles, and page loads.

    Phase 7: global Radix theme (green accent, slate gray, medium radius) and shared
    split-pane CSS in :mod:`receipt_ai.core.theme.shell`. Phase 8: page titles,
    descriptions, ``html_lang``, smooth scrolling.

    Phase 9: skip link, ``main`` landmark, ``header``/``footer``, reduced-motion CSS.
    Phase 10: branded 404 route and site footer on main pages.
    """
    app = rx.App(
        theme=rx.theme(
            accent_color="green",
            gray_color="slate",
            radius="medium",
        ),
        html_lang="en",
        style={
            "scrollBehavior": "smooth",
        },
    )
    app.add_page(
        login_page,
        route="/",
        title="Receipt AI — Login",
        description="Sign in to access files and chat.",
        on_load=AuthState.guard_login_route,
    )
    app.add_page(
        files_page,
        route="/files",
        title="Receipt AI — Files",
        description="Browse and manage receipts and documents in your workspace.",
        on_load=[AuthState.guard_protected_route, AuthState.guard_admin_route, FilesState.load_files],
    )
    app.add_page(
        chat_page,
        route="/chat",
        title="Receipt AI — Chat",
        description="Ask questions about your receipts, crops, and uploaded documents.",
        on_load=[AuthState.guard_protected_route, ChatState.load_history],
    )
    app.add_page(
        login_page,
        route="/login",
        title="Receipt AI — Login",
        description="Sign in to access files and chat.",
        on_load=AuthState.guard_login_route,
    )
    app.add_page(
        not_found_page,
        route=Page404.SLUG,
        title="Page not found — Receipt AI",
        description="This page does not exist or was moved.",
    )
    return app
