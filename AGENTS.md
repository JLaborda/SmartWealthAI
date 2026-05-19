# AGENTS.md

## Cursor Cloud specific instructions

### Project overview
SmartWealthAI is a Python-based financial screener using `yfinance` and `pandas`. It is in early scaffolding phase (no `main.py` or source package exists yet). See `README.md` for the roadmap.

### Runtime requirements
- **Python 3.13+** (installed from `ppa:deadsnakes/ppa` as `python3.13`)
- **Poetry** (installed via `pip3 install poetry`; binary is at `~/.local/bin/poetry`)

### Running the project
- `poetry install --no-root` — installs dependencies. The `--no-root` flag is required because no Python package/source directory exists yet; without it Poetry errors out.
- `poetry run python <script.py>` — runs a script inside the virtualenv.
- The project has no tests, no linter config, and no build step at this time.

### Gotchas
- `yfinance` calls Yahoo Finance public APIs over the network. If the VM has no internet, data fetches will fail.
- The `pyproject.toml` declares `requires-python = "^3.13"`, so `python3.13` must be explicitly selected via `poetry env use python3.13` if the system default Python is older.
- Poetry is installed under the user-local `~/.local/bin` directory; ensure `PATH` includes it.
