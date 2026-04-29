from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    display_name: str
    roles: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    email_verified: bool = False
