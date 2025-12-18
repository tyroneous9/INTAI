<!-- Copilot / AI agent instructions for INTAI project -->
# INTAI — Copilot Instructions (concise)

Purpose
- Help AI coding assistants become productive quickly in this repository by describing structure, run/build/test workflows, and code patterns that are specific to INTAI.

Quick start
- Run the app interactively: `python main.py` from the repository root.
- Build a distributable executable: run `build.bat` (this uses the PyInstaller spec `INTAI.spec`).
- Config precedence: `config/config.json` overrides `config/config_default.json` at runtime.

Key files & entry points (start here)
- `main.py` — top-level startup that loads config and initializes the core manager.
- `INTAI.spec` and `build.bat` — packaging with PyInstaller; produced artifacts appear in `build/INTAI`.
- `core/` — main runtime components; see `core/bot_manager.py`, `core/run_aram.py`, `core/run_arena.py`, `core/run_test.py` for mode-specific logic.
- `utils/` — helper modules (e.g., `utils/config_utils.py`, `utils/game_utils.py`) used across the app.
- `config/` — runtime and default configuration; update `config/config.json` for changes.
- `tesseract/` — bundled Tesseract data/config; OCR integration and language models live here.
- `logs/` — runtime logs; check here for debugging output.

Architecture & data flow (high level)
- `main.py` reads configuration and delegates to the `core` package.
- `core.bot_manager` orchestrates bot lifecycle and invokes mode-specific runners in `core/run_*.py`.
- Utility modules in `utils/` provide stateless helpers (configuration parsing, game utilities, general helpers) — prefer adding shared logic here rather than globals.
- External integration points: Tesseract (local `tesseract/` folder) and League Client API data referenced in `docs/` and `tests/` (see `tests/dump_lcu_data.py`).

Project-specific conventions
- Runtimes live in `core/` with filenames `run_<mode>.py` (e.g., `run_aram.py`) — add new modes following this convention.
- Configuration is centralized in `config/config.json`. Use `utils/config_utils.py` to read/merge defaults.
- Packaging uses PyInstaller via `INTAI.spec`; do not invent alternate packaging flows without updating `build.bat`.
- Tests are lightweight scripts under `tests/` (not a full pytest harness). Run them directly (e.g., `python tests/dump_lcu_data.py`).

What to change (patterns when editing)
- When adding new functionality that affects runtime behavior, update `config/config_default.json` and add a sample to `config/config.json`.
- Prefer adding helpers to `utils/` rather than introducing cross-module global state.
- Keep core orchestration in `core/bot_manager.py` — business logic for bots should live in per-mode modules under `core/`.

Debugging & logs
- Runtime logging writes to `logs/`; inspect those files for failures in packaged and dev runs.
- For packaging issues inspect `build/INTAI/warn-INTAI.txt` and `build/INTAI/EXE-00.toc` produced by PyInstaller.

External dependencies & environment notes
- The repo bundles Tesseract data under `tesseract/` — ensure `tesseract` binary on PATH or adapt `tesseract` lookup if testing on other systems.
- Packaging assumes Windows (the workspace contains `build.bat`). Adjust scripts for other OSes only when absolutely necessary.

Examples (common edits)
- Add a new game mode: create `core/run_my_mode.py`, implement `run()` or `main()` consistent with other `run_*.py`, and register how `main.py` chooses it (follow existing selection logic in `main.py`).
- Change configuration keys: update both `config/config_default.json` and `config/config.json` and use `utils/config_utils.py` to read values.

Where to look first when investigating bugs
- `logs/` for runtime errors
- `build/INTAI/warn-INTAI.txt` for packaging warnings
- `core/bot_manager.py` and the `core/run_*.py` files for behavior orchestration

When to ask maintainers
- If you need to change packaging targets, modify `build.bat`/`INTAI.spec`, or add external OS-level dependencies (e.g., different Tesseract installs), ask before changing the build flow.

If anything here is unclear or you need more examples from real files, say so and I will expand the instructions or merge additional content from repository files.
