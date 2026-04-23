"""Shared split-pane shell CSS for Files and Chat (Phase 7).

Technical AI–style responsive rails: mobile single-panel switch, desktop resizable
sidebar, agri divider grip. Each route injects its own ``rx.el.style(...)`` block.
"""

# Primary nav (Phase 1): TA-style logo row, desktop pills, mobile sheet, account label.
NAV_SHELL_CSS = """
.nav-shell-row {
  min-height: 3.5rem;
  gap: 0.75rem;
  flex-wrap: nowrap;
}
.nav-shell-inner {
  width: 100%;
  max-width: 100%;
  margin-left: auto;
  margin-right: auto;
  padding-left: max(1rem, env(safe-area-inset-left, 0px));
  padding-right: max(1rem, env(safe-area-inset-right, 0px));
}
@media (min-width: 1024px) {
  .nav-shell-inner {
    padding-left: max(1.5rem, env(safe-area-inset-left, 0px));
    padding-right: max(1.5rem, env(safe-area-inset-right, 0px));
  }
}
.nav-brand-link {
  border-radius: 0.5rem;
  padding: 0.125rem 0.5rem;
  margin-left: -0.5rem;
  text-decoration: none;
  color: inherit;
  transition: background 0.15s ease;
}
.nav-brand-link:hover {
  background: var(--nav-brand-hover, rgba(0, 0, 0, 0.04));
}
.dark .nav-brand-link:hover,
[data-theme="dark"] .nav-brand-link:hover {
  background: var(--nav-brand-hover-dark, rgba(255, 255, 255, 0.06));
}
.nav-desktop-only {
  display: none !important;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: nowrap;
  white-space: nowrap;
  position: relative;
  z-index: 2;
  isolation: isolate;
}
.nav-desktop-only a {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  margin: 0;
  padding: 0;
  position: relative;
  z-index: 1;
}
.nav-desktop-only a + a {
  margin-left: 0.125rem;
}
.nav-desktop-only button {
  white-space: nowrap;
  min-height: 30px;
  padding-left: 0.5rem;
  padding-right: 0.5rem;
  line-height: 1;
}
.nav-shell-row > div:first-child {
  min-width: 0;
  flex: 1 1 auto;
}
.nav-shell-row > div:last-child {
  flex: 0 0 auto;
}
.nav-brand-link {
  flex-shrink: 0;
}
@media (min-width: 640px) {
  .nav-desktop-only {
    display: flex !important;
  }
}
.nav-mobile-only {
  display: flex !important;
}
@media (min-width: 640px) {
  .nav-mobile-only {
    display: none !important;
  }
}
.nav-account-label {
  display: none;
}
@media (min-width: 640px) {
  .nav-account-label {
    display: inline;
  }
}
.nav-mobile-panel {
  flex-direction: column;
  width: 100%;
}
@media (min-width: 640px) {
  .nav-mobile-panel {
    display: none !important;
  }
}
.nav-mobile-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.15s ease;
}
"""

# Files route: tree ↔ content mobile switch, explorer width slider.
FILES_SHELL_CSS = """
.files-split-inner {
  width: 100%;
  align-items: stretch;
}
.files-sidebar-col {
  width: 100%;
  box-sizing: border-box;
  min-width: 0;
}
.files-main-col {
  width: 100%;
  min-width: 0;
  flex: 1 1 auto;
}
.files-divider-col {
  display: none;
  flex-shrink: 0;
  align-self: stretch;
}
.files-mobile-bar {
  display: none;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.75rem;
  border-bottom: 1px solid;
  border-color: var(--files-border);
  background: var(--files-canvas);
}
@media (min-width: 768px) {
  .files-split-inner {
    flex-direction: row !important;
  }
  .files-sidebar-col {
    width: var(--files-sidebar-pct, 28%) !important;
    max-width: min(960px, 78vw);
    min-width: 220px;
    flex-shrink: 0;
  }
  .files-main-col {
    flex: 1 1 0%;
    width: auto !important;
  }
  .files-divider-col {
    display: flex;
  }
  .files-mobile-bar {
    display: none !important;
  }
}
@media (max-width: 767px) {
  .files-shell[data-files-view="content"] .files-sidebar-col {
    display: none !important;
  }
  .files-shell[data-files-view="tree"] .files-main-col {
    display: none !important;
  }
}
.files-divider-grip {
  width: 6px;
  align-self: stretch;
  min-height: 120px;
  border-radius: 4px;
  background: transparent;
  cursor: col-resize;
  transition: background 0.15s ease;
}
.files-divider-grip:hover {
  background: var(--files-divider-hover, rgba(34, 197, 94, 0.18));
}
.files-grid-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem;
  align-items: stretch;
}
.files-grid-card {
  box-sizing: border-box;
  min-height: 200px;
}
.files-view-toggle {
  position: relative;
  z-index: 2;
  isolation: isolate;
  gap: 0.375rem;
}
.files-no-folder-placeholder {
  box-sizing: border-box;
  padding: 0.5rem 0.25rem;
}
"""

# Chat route: history ↔ content mobile switch, optional center + recent inner split.
CHAT_SHELL_CSS = """
.chat-split-inner {
  width: 100%;
  align-items: stretch;
}
.chat-sidebar-col {
  width: 100%;
  box-sizing: border-box;
  min-width: 0;
}
.chat-main-col {
  width: 100%;
  min-width: 0;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
}
.chat-inner-split {
  width: 100%;
  flex: 1 1 auto;
  min-height: 0;
  align-items: stretch;
}
.chat-center-wrap {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.chat-recent-col {
  width: 100%;
  flex-shrink: 0;
  box-sizing: border-box;
}
.chat-divider-col {
  display: none;
  flex-shrink: 0;
  align-self: stretch;
}
.chat-mobile-bar {
  display: none;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.75rem;
  border-bottom: 1px solid;
  border-color: var(--chat-border);
  background: var(--chat-canvas);
}
@media (min-width: 768px) {
  .chat-split-inner {
    flex-direction: row !important;
  }
  .chat-sidebar-col {
    width: var(--chat-sidebar-pct, 22%) !important;
    max-width: 280px;
    min-width: 220px;
    flex-shrink: 0;
  }
  .chat-main-col {
    flex: 1 1 0%;
    width: auto !important;
  }
  .chat-divider-col {
    display: flex;
  }
  .chat-mobile-bar {
    display: none !important;
  }
}
@media (min-width: 1024px) {
  .chat-recent-col {
    width: 280px !important;
    flex-shrink: 0;
  }
  .chat-inner-split {
    flex-direction: row !important;
  }
}
@media (max-width: 767px) {
  .chat-shell[data-chat-view="content"] .chat-sidebar-col {
    display: none !important;
  }
  .chat-shell[data-chat-view="history"] .chat-main-col {
    display: none !important;
  }
}
.chat-divider-grip {
  width: 6px;
  align-self: stretch;
  min-height: 120px;
  border-radius: 4px;
  background: transparent;
  cursor: col-resize;
  transition: background 0.15s ease;
}
.chat-divider-grip:hover {
  background: var(--chat-divider-hover, rgba(34, 197, 94, 0.18));
}
.chat-thread-header {
  display: none;
}
.chat-thread-row .chat-thread-delete-btn {
  opacity: 0;
  pointer-events: none;
  transform: translateX(2px);
  transition: opacity 0.14s ease, transform 0.14s ease;
}
.chat-thread-row {
  border-radius: 10px;
}
.chat-thread-row:focus-within {
  background: var(--chat-thread-focus, rgba(34, 197, 94, 0.08));
}
.chat-thread-row:hover .chat-thread-delete-btn,
.chat-thread-row:focus-within .chat-thread-delete-btn {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(0);
}
.chat-bubble-actions {
  opacity: 0;
  transition: opacity 0.14s ease, transform 0.14s ease;
  transform: translateY(2px);
  pointer-events: none;
  padding-top: 0.12rem;
}
.chat-bubble-actions button {
  min-width: 28px;
  height: 25px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(2, 6, 23, 0.2);
}
.chat-user-row .chat-bubble-actions {
  padding-right: 2.4rem;
}
.chat-assistant-row .chat-bubble-actions {
  padding-left: 2.4rem;
}
.chat-user-bubble:hover,
.chat-assistant-bubble:hover {
  box-shadow: 0 8px 20px rgba(2, 6, 23, 0.22);
}
.chat-user-row:hover .chat-bubble-actions,
.chat-user-row:focus-within .chat-bubble-actions,
.chat-assistant-row:hover .chat-bubble-actions,
.chat-assistant-row:focus-within .chat-bubble-actions {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}
@media (min-width: 768px) {
  .chat-thread-header {
    display: flex;
  }
}
"""

# Assistant markdown thread (Technical AI chat-prose feel).
CHAT_MARKDOWN_CSS = """
.chat-md-prose .markdown {
  font-size: 0.8125rem;
  line-height: 1.55;
}
.chat-md-prose .markdown p {
  margin: 0 0 0.45rem 0;
}
.chat-md-prose .markdown p:last-child {
  margin-bottom: 0;
}
.chat-md-prose .markdown blockquote {
  margin: 0.35rem 0;
  padding-left: 0.65rem;
  border-left: 3px solid rgba(34, 197, 94, 0.45);
  color: inherit;
  opacity: 0.92;
}
.chat-md-prose .markdown pre,
.chat-md-prose .markdown code {
  font-size: 12px;
}
.chat-md-prose .markdown pre {
  padding: 0.55rem 0.65rem;
  border-radius: 8px;
  overflow-x: auto;
}
.chat-thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 9999px;
  background: rgba(34, 197, 94, 0.85);
  animation: chat-dot-pulse 1.15s ease-in-out infinite;
}
.chat-thinking-dots .chat-thinking-dot:nth-child(2) {
  animation-delay: 0.18s;
}
.chat-thinking-dots .chat-thinking-dot:nth-child(3) {
  animation-delay: 0.36s;
}
@keyframes chat-dot-pulse {
  0%, 80%, 100% {
    opacity: 0.35;
    transform: scale(0.92);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}
.chat-stream-cursor-wrap.chat-md-prose .markdown::after {
  content: "";
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 2px;
  vertical-align: text-bottom;
  background: rgba(34, 197, 94, 0.95);
  animation: chat-caret-blink 1s step-end infinite;
}
@keyframes chat-caret-blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .chat-thinking-dot {
    animation: none;
  }
  .chat-stream-cursor-wrap.chat-md-prose .markdown::after {
    animation: none;
  }
  .chat-bubble-actions {
    transition: none;
  }
}
"""
