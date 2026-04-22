import reflex as rx

from receipt_ai.features.auth.service import authenticate_user, create_session_token, delete_session_token, get_session_user


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
    show_password: bool = False
    auth_error: str = ""
    is_submitting: bool = False
    is_authenticated: bool = False
    user_id: str = ""
    user_display_name: str = "Demo user"
    auth_token: str = ""
    user_roles: list[str] = []
    user_permissions: list[str] = []
    primary_role: str = "user"

    @rx.var
    def is_admin(self) -> bool:
        return self.has_role("admin")

    def toggle_show_password(self) -> None:
        self.show_password = not self.show_password

    def clear_auth_error(self) -> None:
        self.auth_error = ""

    def has_role(self, role: str) -> bool:
        return has_role_value(self.user_roles, role)

    def has_permission(self, permission: str) -> bool:
        return has_permission_value(self.user_roles, self.user_permissions, permission)

    def _apply_auth_user(self, user) -> None:
        self.is_authenticated = True
        self.user_id = user.id
        self.user_display_name = user.display_name
        self.user_roles = list(user.roles)
        self.user_permissions = list(user.permissions)
        self.primary_role = primary_role_value(self.user_roles)

    def _clear_auth_identity(self) -> None:
        self.auth_token = ""
        self.is_authenticated = False
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
        if not email or not password:
            self.auth_error = "Email and password are required."
            return None

        self.is_submitting = True
        try:
            user = await authenticate_user(email, password)
            if user is not None:
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
        if self.auth_token:
            await delete_session_token(self.auth_token)
        self._clear_auth_identity()
        self.email = ""
        self.password = ""
        self.auth_error = ""
        self.show_password = False
        return rx.redirect("/login")

    async def guard_protected_route(self):
        """Redirect guests away from protected pages."""
        if not self.auth_token:
            return rx.redirect("/login")
        user = await get_session_user(self.auth_token)
        if user is None:
            self._clear_auth_identity()
            return rx.redirect("/login")
        self._apply_auth_user(user)
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
            user = await get_session_user(self.auth_token)
            if user is not None:
                self._apply_auth_user(user)
                return rx.redirect(post_login_route_value(self.user_roles))
            self._clear_auth_identity()
        return None
