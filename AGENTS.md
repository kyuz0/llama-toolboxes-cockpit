# AI Agent Context: Llama Toolboxes Cockpit

**Primary Goal:** This project is a Python-based Terminal User Interface (TUI) called "Llama Toolboxes Cockpit". It provides a modern, interactive frontend for managing, running, and configuring Llama.cpp Docker/Podman containers (toolboxes) optimized for AMD Ryzen AI Max "Strix Halo" APUs.

## Core Technologies
*   **Framework**: [Textual](https://textual.textualize.io/) (Python) - Used for building the TUI.
*   **Container Engines**: `podman` or `docker` (auto-detected via CLI subprocess calls).
*   **External API**: Docker Hub API v2 (used for checking image updates and fetching release dates).

## Repository Structure Overview
*   `src/`: Contains all Python source code for the TUI.
    *   `main.py`: The core application class (`LlamaCockpitApp`), layout configuration, CSS definitions, and UI event handlers.
    *   `toolbox_manager.py`: Subprocess wrappers for interacting with the local container engine (creating, deleting, checking status).
    *   `server_runner.py`: Logic for launching non-interactive background Llama.cpp server instances.
    *   `widgets.py`: Custom Textual widgets (e.g., `SearchableSelect` for filterable dropdowns).
    *   `config.py`: Utilities for loading local models and parsing configuration JSONs.
*   `config/`: Contains static configuration files like `toolboxes.json`, which maps repository images to UI representations.
*   `pyproject.toml`: Project metadata, dependencies, and CLI entry point definitions (`llama-cockpit = "src.main:cli_main"`).

## Architectural Patterns & UI Rules
*   **Strict Red Theme**: The application enforces a custom Red theme (`#d32f2f` primary, `#e57373` accent, `#333333` subtle backgrounds). To override Textual's default blue accents, use the native Python `Theme` object registered in `on_mount` rather than relying solely on global CSS variable overrides.
*   **DataTables Multi-Selection**: The TUI handles batch operations using a custom `[ ]` / `[x]` toggle logic inside `DataTable` columns. **Do not use row-highlighting (the navigation cursor) as a selection mechanism.** Batch operations must strictly iterate over `self.selected_toolboxes`.
*   **Event Handling**: Use the `@on(Event, selector)` decorator syntax for capturing UI interactions.
*   **Subprocess Execution**: When dropping the user into an interactive shell or prompting for CLI input, use `with self.suspend():` to safely pause the Textual UI event loop before executing `os.system()`, `input()`, or `subprocess.call()`.

## Known Quirks
*   **Textual Tab States**: Textual aggressively applies backgrounds to focused tabs by default. Explicit CSS targeting with `!important` (`Tab, Tab:hover, Tab:focus, Tab.-active { background: transparent !important; }`) is required to keep the UI clean.
*   **Date Truncation**: When displaying remote registry dates in DataTables, truncate ISO strings to `[:10]` (`YYYY-MM-DD`) to prevent layout clipping in standard terminal widths.

## Development & Testing Workflow
*   **Remote Testing Only**: The user tests the application on a dedicated remote server accessed via SSH. The local development environment where the AI agent runs lacks the necessary runtime dependencies (e.g., `huggingface-cli`, Podman/Docker engines with ROCm).
*   **No Local Execution**: DO NOT attempt to enter toolboxes, or start servers locally to test your code. 
*   **Ask the User**: Instead of executing potentially failing environment-dependent commands with `run_command`, clearly state what needs to be tested and ask the user to run it on their test server.
