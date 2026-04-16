import reflex as rx

from receipt_ai.features.auth.service import authenticate_user, create_session_token, delete_session_token, get_session_user


class AuthState(rx.State):
    """DB-backed auth state for login gating."""

    # Pre-filled for local dev: open login and press Enter to sign in.
    email: str = "admin@receipt.ai"
    password: str = "admin123"
    show_password: bool = False
    auth_error: str = ""
    is_submitting: bool = False
    is_authenticated: bool = False
    user_id: str = ""
    user_display_name: str = "Demo user"
    auth_token: str = ""

    def toggle_show_password(self) -> None:
        self.show_password = not self.show_password

    def clear_auth_error(self) -> None:
        self.auth_error = ""

    def login(self):
        """Authenticate against DB users table and issue a session token."""
        email = self.email.strip().lower()
        password = self.password

        self.auth_error = ""
        if not email or not password:
            self.auth_error = "Email and password are required."
            return None

        self.is_submitting = True
        try:
            user = authenticate_user(email, password)
            if user is not None:
                token = create_session_token(user.id)
                self.auth_token = token
                self.is_authenticated = True
                self.user_id = user.id
                self.user_display_name = user.display_name
                return rx.redirect("/files")
            self.auth_error = "Invalid credentials."
            return None
        finally:
            self.is_submitting = False

    def logout(self):
        if self.auth_token:
            delete_session_token(self.auth_token)
        self.auth_token = ""
        self.is_authenticated = False
        self.user_id = ""
        self.email = "admin@receipt.ai"
        self.password = "admin123"
        self.auth_error = ""
        self.show_password = False
        self.user_display_name = "Demo user"
        return rx.redirect("/login")

    def guard_protected_route(self):
        """Redirect guests away from protected pages."""
        if not self.auth_token:
            return rx.redirect("/login")
        user = get_session_user(self.auth_token)
        if user is None:
            self.auth_token = ""
            self.is_authenticated = False
            self.user_id = ""
            self.user_display_name = "Demo user"
            return rx.redirect("/login")
        self.is_authenticated = True
        self.user_id = user.id
        self.user_display_name = user.display_name
        return None

    def guard_login_route(self):
        """Redirect authenticated users away from login page."""
        if self.auth_token:
            user = get_session_user(self.auth_token)
            if user is not None:
                self.is_authenticated = True
                self.user_id = user.id
                self.user_display_name = user.display_name
                return rx.redirect("/files")
            self.auth_token = ""
            self.is_authenticated = False
            self.user_id = ""
        return None
