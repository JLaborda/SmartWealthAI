---
status: accepted
---

# Primary tooling: Poetry → uv workspace

**Decision:** The monorepo uses a root **uv** workspace whose members are `credit` and `investing`. Install/run via `uv sync` / `uv run` (or `make install` / `make test` / `make lint`). Poetry is no longer the primary path; `poetry.lock` is removed.

**Why:** Domain-first layout (`credit/`, `investing/`) needs per-member `pyproject.toml` without a second installer story. uv workspaces give one lockfile (`uv.lock`), fast sync, and lean per-domain installs ([#183](https://github.com/JLaborda/SmartWealthAI/issues/183)). See [#182](https://github.com/JLaborda/SmartWealthAI/issues/182).

**Trade-offs:**

| Chosen | Rejected | Reason |
| --- | --- | --- |
| Flat `credit/` + `investing/` workspace members | Gemini-style `domains/*` + `shared/` | Keep domain folders; avoid premature shared package |
| `platform/` not a workspace member | platform as Python member | Infra/scripts only for now |
| Lean per-domain deps; shared libs duplicated in both members | Full dep set on both; or a `shared/` workspace member | #183; extract `shared/` later when shared *code* or a 3rd domain appears |
| Make + CI verification (`--package` matrix) | New `tests/tooling/` contract suite | Occam; existing gates enough |

**Consequences:**

- Operators use `make install` (full), `make install-credit` / `make install-investing` (one domain), `uv run <script>`, or `uv run pytest`
- Docker/credit serve images install with `uv sync --frozen --package credit` (sibling `investing/pyproject.toml` COPY still required for lock resolution — [#188](https://github.com/JLaborda/SmartWealthAI/issues/188))
- Devcontainer `postCreateCommand` uses uv (optional; local uv is the default path)
- Do not reintroduce Poetry as the primary driver
