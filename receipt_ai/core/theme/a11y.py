"""Global accessibility helpers (Phase 9).

Skip-link visibility on focus, reduced-motion respect for smooth scroll.
"""

A11Y_GLOBAL_CSS = """
/* Phase 5: full-height layout, no horizontal scroll, mobile safe areas */
html {
  min-height: 100%;
  min-height: 100dvh;
}
body {
  overflow-x: clip;
}
.skip-to-main {
  position: absolute;
  left: -9999px;
  top: 0;
  z-index: 100;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  text-decoration: none;
  background: var(--gray-1, #ffffff);
  color: var(--green-11, #15803d);
  border: 2px solid var(--green-9, #16a34a);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}
.skip-to-main:focus {
  left: 1rem;
  top: 1rem;
  outline: none;
}
@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto !important;
  }
}
/* Files / Chat mobile rails: comfortable tap targets (WCAG ~44px) */
@media (max-width: 767px) {
  .files-mobile-bar button,
  .chat-mobile-bar button {
    min-height: 44px;
    min-width: 44px;
  }
}
"""
