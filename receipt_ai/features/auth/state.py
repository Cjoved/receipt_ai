import reflex as rx


class AuthState(rx.State):
    """Simple auth state for login gating (phase 1 mock auth)."""

    # Pre-filled for local dev: open login and press Enter to sign in.
    email: str = "admin@receipt.ai"
    password: str = "admin123"
    show_password: bool = False
    auth_error: str = ""
    is_submitting: bool = False
    is_authenticated: bool = False
    user_display_name: str = "Demo user"

    def toggle_show_password(self) -> None:
        self.show_password = not self.show_password

    def clear_auth_error(self) -> None:
        self.auth_error = ""

    def login(self):
        """Mock login for now; replace with real backend auth later."""
        email = self.email.strip().lower()
        password = self.password

        self.auth_error = ""
        if not email or not password:
            self.auth_error = "Email and password are required."
            return None

        self.is_submitting = True
        try:
            # Phase 1: local mock auth check.
            if email == "admin@receipt.ai" and password == "admin123":
                self.is_authenticated = True
                self.user_display_name = "Admin"
                return rx.redirect("/files")
            self.auth_error = "Invalid credentials. Try admin@receipt.ai / admin123."
            return None
        finally:
            self.is_submitting = False

    def logout(self):
        self.is_authenticated = False
        self.email = "admin@receipt.ai"
        self.password = "admin123"
        self.auth_error = ""
        self.show_password = False
        self.user_display_name = "Demo user"
        return rx.redirect("/login")

    def guard_protected_route(self):
        """Redirect guests away from protected pages."""
        if not self.is_authenticated:
            return rx.redirect("/login")
        return None

    def guard_login_route(self):
        """Redirect authenticated users away from login page."""
        if self.is_authenticated:
            return rx.redirect("/")
        return None
