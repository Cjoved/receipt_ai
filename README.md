# receipt_ai

Reflex (Python) web app with modular architecture. The `.web` folder is generated on first run and is not committed to Git.

## Prerequisites

| Tool | Notes |
|------|--------|
| **Python** | 3.12 or newer (see `requires-python` in `pyproject.toml`) |
| **[uv](https://docs.astral.sh/uv/)** | Installs Python deps and runs the app in a virtualenv |
| **Node.js** | **20.19.0 or higher** (Reflex uses npm to install the frontend under `.web`) |

Check versions:

```bash
python --version
uv --version
node -v
```

## Clone and run

```bash
git clone <your-repo-url>
cd receipt_ai
uv sync
uv run reflex run
```

- **`uv sync`** creates/updates `.venv` and installs packages from `uv.lock` / `pyproject.toml`.
- The first successful run downloads **npm** dependencies into `.web` (needs a working internet connection and DNS for `registry.npmjs.org`). This can take a few minutes.

Then open the URL Reflex prints in the terminal (usually [http://localhost:3000](http://localhost:3000)).

## Commands (Reflex 0.8+)

| Task | Command |
|------|---------|
| Run the app (dev) | `uv run reflex run` |
| Init / templates (new project only) | `uv run reflex init` |

There is **no** `reflex dev` in current Reflex CLI — use **`reflex run`**.

Optional:

```bash
uv run reflex run --env dev
```

## Project layout

| Path | Purpose |
|------|---------|
| `receipt_ai/receipt_ai.py` | Reflex entrypoint module (creates `app`) |
| `receipt_ai/app.py` | App factory and route registration |
| `receipt_ai/pages/` | Route/page composition (`files_page`, `chat_page`) |
| `receipt_ai/components/` | Reusable UI blocks (nav, file panels, chat panels) |
| `receipt_ai/features/files/` | Files feature domain (`models`, `service`, `state`) |
| `receipt_ai/features/chat/` | Chat feature domain (`models`, `service`, `state`) |
| `receipt_ai/core/constants.py` | Shared sample data and style tokens |
| `receipt_ai/state.py` | Global app state placeholders |
| `rxconfig.py` | Reflex config (`app_name`, plugins) |
| `pyproject.toml` / `uv.lock` | Python dependencies |
| `.web/` | **Generated** frontend (npm, Vite, etc.) — **do not edit as source of truth**; listed in `.gitignore` |

## Editor / IDE

If imports like `reflex` show warnings, set the Python interpreter to the project venv:

`.venv\Scripts\python.exe` (Windows) or `.venv/bin/python` (macOS/Linux).

## Troubleshooting

### `Reflex requires node version 20.19.0 or higher`

Upgrade Node (e.g. from [nodejs.org](https://nodejs.org) or `winget upgrade --id OpenJS.NodeJS.20`). Restart the terminal and run `node -v` again.

### `getaddrinfo ENOTFOUND registry.npmjs.org` / npm install fails

DNS or network is blocking access to the npm registry. Fix connectivity, try another DNS (e.g. 1.1.1.1 / 8.8.8.8), run `ipconfig /flushdns` on Windows, or configure `npm` proxy settings if required by your network.

### Reflex warns about OneDrive / WSL

- **OneDrive:** syncing the project folder can slow installs; a path outside synced folders (e.g. `C:\dev\receipt_ai`) is often faster.
- **WSL:** optional on Windows for faster tooling; not required if Node and npm work on Windows.

## License

Add your license here if applicable.
