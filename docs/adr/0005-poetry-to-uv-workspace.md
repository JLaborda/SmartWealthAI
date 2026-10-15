---
status: accepted
---

# Primary tooling: Poetry → uv workspace

**Decision:** The monorepo uses a root **uv** workspace whose members are `credit` and `investing`. Install/run via `uv sync` / `uv run` (or `make install` / `make test` / `make lint`). Poetry is no longer the primary path; `poetry.lock` is removed.

**Why:** Domain-first layout (`credit/`, `investing/`) needs per-member `pyproject.toml` without a second installer story. uv workspaces give one lockfile (`uv.lock`), fast sync, and a clear path to lean per-domain installs later ([#183](https://github.com/JLaborda/SmartWealthAI/issues/183)). See [#182](https://github.com/JLaborda/SmartWealthAI/issues/182).

**Trade-offs:**

| Chosen | Rejected | Reason |
| --- | --- | --- |
| Flat `credit/` + `investing/` workspace members | Gemini-style `domains/*` + `shared/` | Keep domain folders; avoid premature shared package |
| `platform/` not a workspace member | platform as Python member | Infra/scripts only for now |
| Full dep set on both members (temporary) | Lean credit-only / investing-only deps | Owned by #183 |
| Make + CI verification | New `tests/tooling/` contract suite | Occam; existing gates enough |

**Consequences:**

- Operators use `make install`, `uv run <script>`, or `uv run pytest`
- Docker/credit serve images install with `uv sync --frozen`
- Devcontainer `postCreateCommand` uses uv (optional; local uv is the default path)
- Do not reintroduce Poetry as the primary driver
