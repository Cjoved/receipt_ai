"""Receipt AI design system.

Public exports:
- :mod:`receipt_ai.core.theme.tokens` — semantic colors, radius, shadow, nav.
- :mod:`receipt_ai.core.theme.shell` — shared split-pane CSS for Files and Chat.
- :mod:`receipt_ai.core.theme.a11y` — skip-link and reduced-motion CSS.

Legacy aliases live in :mod:`receipt_ai.core.constants` for gradual migration.
"""

from . import a11y, shell, tokens

__all__ = ["a11y", "shell", "tokens"]
