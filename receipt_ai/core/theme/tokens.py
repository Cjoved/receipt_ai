"""Semantic design tokens aligned with Technical AI (agri accent + neutral shells).

All theme-switching colors use :func:`_mode` so light/dark stay in sync with
``rx.color_mode``. Static values (radius, shadow) are plain strings for CSS.

Phase 0 scope (locked):
- **Accent**: green (Tailwind ``agri`` family) for primary emphasis and nav active.
- **Surfaces**: gray-50 / gray-950 style canvas; white / gray-900 panels.
- **Files + nav** are the first-class surfaces for this token set.
"""

from __future__ import annotations

import reflex as rx

PALETTE_PRIMARY_LIGHT = "#60ca72"
PALETTE_PRIMARY_DEEP = "#1a6b45"


def theme_pair(light: str, dark: str):
    """Theme-aware color (matches Reflex light/dark mode). Public API for components."""
    return rx.color_mode_cond(light, dark)


# ---------------------------------------------------------------------------
# Surfaces (canvas → panel → subtle)
# ---------------------------------------------------------------------------
surface_canvas = theme_pair("#f9fafb", "#030712")
surface_panel = theme_pair("#ffffff", "#111827")
surface_subtle = theme_pair("#f3f4f6", "#1f2937")
surface_inset = theme_pair("#e5e7eb", "#0b1220")

# ---------------------------------------------------------------------------
# Borders
# ---------------------------------------------------------------------------
border_default = theme_pair("#e5e7eb", "#374151")
border_strong = theme_pair("#d1d5db", "#4b5563")
border_accent = theme_pair("#b7eac0", "#2f5f3b")

# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------
text_primary = theme_pair("#111827", "#f9fafb")
text_secondary = theme_pair("#4b5563", "#d1d5db")
text_muted = theme_pair("#6b7280", "#9ca3af")
text_on_accent_soft = theme_pair(PALETTE_PRIMARY_DEEP, "#b9efc4")

# ---------------------------------------------------------------------------
# Accent — agri green (Technical AI primary)
# ---------------------------------------------------------------------------
accent_solid = theme_pair(PALETTE_PRIMARY_DEEP, PALETTE_PRIMARY_LIGHT)
accent_solid_hover = theme_pair("#145535", "#53b864")
accent_soft_bg = theme_pair("#e8f7eb", "rgba(96, 202, 114, 0.18)")
accent_soft_bg_strong = theme_pair("#d7f0dd", "rgba(96, 202, 114, 0.28)")
accent_muted_fg = theme_pair(PALETTE_PRIMARY_DEEP, "#a7e8b2")

# ---------------------------------------------------------------------------
# Semantic (alerts, destructive — extend as needed)
# ---------------------------------------------------------------------------
success_fg = theme_pair(PALETTE_PRIMARY_DEEP, "#a7e8b2")
success_bg_soft = theme_pair("#e8f7eb", "rgba(96, 202, 114, 0.16)")
danger_fg = theme_pair("#dc2626", "#f87171")
danger_bg_soft = theme_pair("#fef2f2", "rgba(248, 113, 113, 0.12)")

# ---------------------------------------------------------------------------
# App shell / frosted nav (Technical AI sticky bar)
# ---------------------------------------------------------------------------
nav_surface = theme_pair("rgba(255, 255, 255, 0.85)", "rgba(17, 24, 39, 0.85)")
nav_border = border_default

# ---------------------------------------------------------------------------
# Layout tokens (CSS string constants — not theme-dependent)
# ---------------------------------------------------------------------------
RADIUS_SM = "6px"
RADIUS_MD = "10px"
RADIUS_LG = "12px"
RADIUS_XL = "16px"
RADIUS_FULL = "9999px"

SHADOW_SM = "0 1px 2px rgba(0, 0, 0, 0.05)"
SHADOW_MD = "0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.05)"
SHADOW_LG = "0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.05)"
SHADOW_NAV = "0 1px 3px 0 rgba(0, 0, 0, 0.06)"

BLUR_NAV = "12px"
NAV_HEIGHT = "3.5rem"
