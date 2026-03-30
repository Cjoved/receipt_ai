"""Global UI constants.

Semantic colors are defined in :mod:`receipt_ai.core.theme.tokens` and re-exported
here for backward compatibility. Prefer importing ``theme.tokens`` in new code.
"""

from receipt_ai.core.theme.tokens import (
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    RADIUS_XL,
    RADIUS_FULL,
    SHADOW_LG,
    SHADOW_MD,
    SHADOW_NAV,
    SHADOW_SM,
    BLUR_NAV,
    NAV_HEIGHT,
    border_default as BORDER_COLOR,
    surface_canvas as APP_BACKGROUND,
    surface_panel as PANEL_BG,
    surface_subtle as SUBTLE_BG,
    text_primary as APP_FOREGROUND,
    text_muted as MUTED_TEXT,
    text_secondary as SECONDARY_TEXT,
)

# Global UI scale tokens (single place to tune sizing).
ICON_SIZE_XS = 16
ICON_SIZE_SM = 24
ICON_SIZE_MD = 32
ICON_SIZE_LG = 40
ICON_SIZE_XL = 48
ICON_SIZE_XXL = 56
TEXT_SIZE_SM = "2"
TEXT_SIZE_MD = "3"
HEADING_SIZE_SM = "4"
