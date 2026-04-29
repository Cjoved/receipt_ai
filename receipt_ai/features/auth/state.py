import reflex as rx

from receipt_ai.features.auth.config import AuthConfig
from receipt_ai.features.auth.service import (
    authenticate_user,
    create_session_token,
    delete_session_token,
    get_session_user,
    register_user,
    request_email_verification,
    request_password_reset,
    reset_password_with_token,
    update_user_display_name,
    verify_email_with_token,
)


def has_role_value(roles: list[str] | tuple[str, ...], role: str) -> bool:
    wanted = role.strip().lower()
    if not wanted:
        return False
    return wanted in {r.strip().lower() for r in roles}


def has_permission_value(roles: list[str] | tuple[str, ...], permissions: list[str] | tuple[str, ...], wanted: str) -> bool:
    permission = wanted.strip().lower()
    if not permission:
        return False
    if has_role_value(roles, "admin"):
        return True
    return permission in {p.strip().lower() for p in permissions}


def primary_role_value(roles: list[str] | tuple[str, ...]) -> str:
    return roles[0] if roles else "user"


def post_login_route_value(roles: list[str] | tuple[str, ...]) -> str:
    return "/files" if has_role_value(roles, "admin") else "/chat"


class AuthState(rx.State):
    """DB-backed auth state for login gating."""

    email: str = ""
    password: str = ""
    register_email: str = ""
    register_password: str = ""
    register_password_confirm: str = ""
    register_display_name: str = ""
    forgot_email: str = ""
    reset_token: str = ""
    reset_password: str = ""
    reset_password_confirm: str = ""
    verify_token: str = ""
    show_password: bool = False
    auth_error: str = ""
    auth_info: str = ""
    is_submitting: bool = False
    is_authenticated: bool = False
    user_id: str = ""
    user_display_name: str = "Demo user"
    auth_token: str = ""
    email_verified: bool = False
    user_roles: list[str] = []
    user_permissions: list[str] = []
    primary_role: str = "user"
    settings_display_name: str = ""
    settings_default_page: str = "chat"
    settings_compact_mode: bool = False
    settings_is_submitting: bool = False
    settings_error: str = ""
    settings_success: str = ""

    @rx.var
    def is_admin(self) -> bool:
        return self.has_role("admin")

    @rx.var
    def is_standard_user(self) -> bool:
        return self.has_role("user") and not self.has_role("admin")

    @rx.var
    def can_chat_image_upload(self) -> bool:
        return self.has_permission("chat:image_upload")

    @rx.var
    def can_access_files(self) -> bool:
        return self.has_permission("files:read")

    @rx.var
    def home_route(self) -> str:
        return "/files" if self.can_access_files else "/chat"

    def toggle_show_password(self) -> None:
        self.show_password = not self.show_password

    def clear_auth_error(self) -> None:
        self.auth_error = ""
        self.auth_info = ""

    def clear_settings_feedback(self) -> None:
        self.settings_error = ""
        self.settings_success = ""

    def load_settings_form(self) -> None:
        self.settings_display_name = self.user_display_name
        self.settings_default_page = "files" if self.can_access_files else "chat"
        self.settings_error = ""
        self.settings_success = ""

    def set_settings_default_page(self, value: str) -> None:
        clean = value.strip().lower()
        if clean not in {"chat", "files"}:
            return
        if clean == "files" and not self.can_access_files:
            self.settings_error = "Files page is available to admins only."
            self.settings_success = ""
            return
        self.settings_default_page = clean
        self.settings_error = ""

    def go_to_settings(self):
        return rx.redirect("/settings")

    async def save_settings(self):
        if not self.user_id:
            self.settings_error = "Session expired. Please sign in again."
            self.settings_success = ""
            return rx.redirect("/login")

        name = self.settings_display_name.strip()
        if not name:
            self.settings_error = "Display name is required."
            self.settings_success = ""
            return None
        if len(name) < 2:
            self.settings_error = "Display name must be at least 2 characters."
            self.settings_success = ""
            return None
        if len(name) > 120:
            self.settings_error = "Display name must be at most 120 characters."
            self.settings_success = ""
            return None

        self.settings_is_submitting = True
        self.settings_error = ""
        self.settings_success = ""
        try:
            user = await update_user_display_name(self.user_id, name)
            if user is None:
                self.settings_error = "Unable to update settings. Please try again."
                return None
            self._apply_auth_user(user)
            self.settings_display_name = self.user_display_name
            self.settings_success = "Settings saved."
            return None
        except Exception:
            self.settings_error = "Settings save failed. Please try again."
            return None
        finally:
            self.settings_is_submitting = False

    def has_role(self, role: str) -> bool:
        return has_role_value(self.user_roles, role)

    def has_permission(self, permission: str) -> bool:
        return has_permission_value(self.user_roles, self.user_permissions, permission)

    def _apply_auth_user(self, user) -> None:
        self.is_authenticated = True
        self.user_id = user.id
        self.email = user.email
        self.email_verified = bool(getattr(user, "email_verified", False))
        self.user_display_name = user.display_name
        self.settings_display_name = user.display_name
        self.user_roles = list(user.roles)
        self.user_permissions = list(user.permissions)
        self.primary_role = primary_role_value(self.user_roles)

    def _clear_auth_identity(self) -> None:
        self.auth_token = ""
        self.is_authenticated = False
        self.email_verified = False
        self.user_id = ""
        self.user_display_name = "Demo user"
        self.user_roles = []
        self.user_permissions = []
        self.primary_role = "user"

    async def login(self):
        """Authenticate against DB users table and issue a session token."""
        email = self.email.strip().lower()
        password = self.password

        self.auth_error = ""
        self.auth_info = ""
        if not email or not password:
            self.auth_error = "Email and password are required."
            return None

        self.is_submitting = True
        try:
            user = await authenticate_user(email, password, identity_key=email)
            if user is not None:
                cfg = AuthConfig.from_env()
                if cfg.require_email_verified and not user.email_verified:
                    self.auth_error = "Please verify your email before signing in."
                    self.auth_info = "Check your inbox for the verification link."
                    return None
                token = await create_session_token(user.id)
                self.auth_token = token
                self._apply_auth_user(user)
                return rx.redirect(post_login_route_value(self.user_roles))
            self.auth_error = "Invalid credentials."
            return None
        except Exception:
            # Avoid exposing internal details but make the failure actionable.
            self.auth_error = "Login failed: database is unreachable or not initialized."
            return None
        finally:
            self.is_submitting = False

    async def logout(self):
        token = self.auth_token
        self._clear_auth_identity()
        self.email = ""
        self.password = ""
        self.auth_error = ""
        self.show_password = False
        if token:
            try:
                await delete_session_token(token)
            except Exception:
                # Local logout should still succeed even if token revoke fails.
                pass
        return rx.redirect("/login")

    async def guard_protected_route(self):
        """Redirect guests away from protected pages."""
        if not self.auth_token:
            return rx.redirect("/login")
        try:
            user = await get_session_user(self.auth_token)
        except Exception:
            self._clear_auth_identity()
            self.auth_error = "Session check failed. Please sign in again."
            return rx.redirect("/login")
        if user is None:
            self._clear_auth_identity()
            return rx.redirect("/login")
        self._apply_auth_user(user)
        cfg = AuthConfig.from_env()
        if cfg.require_email_verified and not user.email_verified:
            self.auth_info = "Please verify your email to continue."
            return rx.redirect("/verify-email")
        if not self.settings_display_name:
            self.settings_display_name = self.user_display_name
        return None

    async def guard_admin_route(self):
        guard = await self.guard_protected_route()
        if guard is not None:
            return guard
        if not self.has_role("admin"):
            return rx.redirect("/chat")
        return None

    async def guard_login_route(self):
        """Redirect authenticated users away from login page."""
        if self.auth_token:
            try:
                user = await get_session_user(self.auth_token)
            except Exception:
                self._clear_auth_identity()
                self.auth_error = "Session check failed. Please sign in."
                return None
            if user is not None:
                self._apply_auth_user(user)
                cfg = AuthConfig.from_env()
                if cfg.require_email_verified and not user.email_verified:
                    self.auth_info = "Please verify your email to continue."
                    return rx.redirect("/verify-email")
                return rx.redirect(post_login_route_value(self.user_roles))
            self._clear_auth_identity()
        return None

    async def register(self):
        email = self.register_email.strip().lower()
        password = self.register_password
        confirm = self.register_password_confirm
        display_name = self.register_display_name.strip()
        self.auth_error = ""
        self.auth_info = ""
        if not email or not password or not confirm:
            self.auth_error = "Email and password are required."
            return None
        if password != confirm:
            self.auth_error = "Password confirmation does not match."
            return None
        self.is_submitting = True
        try:
            await register_user(
                email=email,
                password=password,
                display_name=(display_name or "User"),
                identity_key=email,
            )
            self.auth_info = "Registration successful. Check your email for verification link."
            self.register_password = ""
            self.register_password_confirm = ""
            return rx.redirect("/verify-email")
        except Exception as exc:
            self.auth_error = str(exc) or "Registration failed."
            return None
        finally:
            self.is_submitting = False

    async def request_password_reset(self):
        email = self.forgot_email.strip().lower()
        self.auth_error = ""
        self.auth_info = ""
        if not email:
            self.auth_error = "Email is required."
            return None
        self.is_submitting = True
        try:
            await request_password_reset(email, identity_key=email)
            self.auth_info = "If the email exists, a password reset link was sent."
            return None
        except Exception as exc:
            self.auth_error = str(exc) or "Password reset request failed."
            return None
        finally:
            self.is_submitting = False

    async def submit_password_reset(self):
        token = self.reset_token.strip()
        password = self.reset_password
        confirm = self.reset_password_confirm
        self.auth_error = ""
        self.auth_info = ""
        if not token or not password or not confirm:
            self.auth_error = "Token and new password are required."
            return None
        if password != confirm:
            self.auth_error = "Password confirmation does not match."
            return None
        self.is_submitting = True
        try:
            user = await reset_password_with_token(token, password)
            if user is None:
                self.auth_error = "Invalid or expired reset token."
                return None
            self.auth_info = "Password updated. You can sign in now."
            self.reset_password = ""
            self.reset_password_confirm = ""
            return rx.redirect("/login")
        except Exception as exc:
            self.auth_error = str(exc) or "Password reset failed."
            return None
        finally:
            self.is_submitting = False

    async def resend_verification(self):
        email = self.email.strip().lower()
        if not email:
            email = self.register_email.strip().lower()
        self.auth_error = ""
        self.auth_info = ""
        if not email:
            self.auth_error = "Provide your account email first."
            return None
        self.is_submitting = True
        try:
            await request_email_verification(email, identity_key=email)
            self.auth_info = "Verification email sent (if account is eligible)."
            return None
        except Exception as exc:
            self.auth_error = str(exc) or "Unable to send verification email."
            return None
        finally:
            self.is_submitting = False

    async def verify_email(self):
        token = self.verify_token.strip()
        self.auth_error = ""
        self.auth_info = ""
        if not token:
            self.auth_error = "Verification token is required."
            return None
        self.is_submitting = True
        try:
            user = await verify_email_with_token(token)
            if user is None:
                self.auth_error = "Invalid or expired verification token."
                return None
            self.auth_info = "Email verified successfully. You can now sign in."
            return rx.redirect("/login")
        except Exception as exc:
            self.auth_error = str(exc) or "Email verification failed."
            return None
        finally:
            self.is_submitting = False

    def go_to_register(self):
        return rx.redirect("/register")

    def go_to_forgot_password(self):
        return rx.redirect("/forgot-password")

    def go_to_login(self):
        return rx.redirect("/login")

    def load_reset_route(self):
        router = getattr(self, "router_data", None)
        params = getattr(router, "query_params", {}) if router is not None else {}
        token = ""
        if isinstance(params, dict):
            raw = params.get("token", "")
            token = str(raw[0] if isinstance(raw, list) and raw else raw).strip()
        if token:
            self.reset_token = token

    def load_verify_route(self):
        router = getattr(self, "router_data", None)
        params = getattr(router, "query_params", {}) if router is not None else {}
        token = ""
        if isinstance(params, dict):
            raw = params.get("token", "")
            token = str(raw[0] if isinstance(raw, list) and raw else raw).strip()
        if token:
            self.verify_token = token
