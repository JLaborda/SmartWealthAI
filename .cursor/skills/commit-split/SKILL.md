---
name: commit-split
description: Splits the working tree into focused conventional commits with path exclusions, a user-approved plan, and a pre-commit gate (format, lint, test) before any git commit. Use when the user invokes /commit_split, asks to split commits, or wants separate conventional commits from a large diff.
argument-hint: "Optional: paths or globs to exclude (e.g. src/, notebooks/)"
disable-model-invocation: true
---

# Commit split

Split unstaged/staged changes into **small, reviewable commits**. Message format: [CONVENTION.md](CONVENTION.md) and `.cursor/rules/git-conventions.mdc`. **Never commit without explicit user approval** of the plan (and per-commit confirmation unless they say to run all).

## Quick start

1. Load exclusions (below).
2. Inventory the working tree (`git status`, `git diff --stat`, `git diff` for ambiguous hunks).
3. Propose a **commit plan** table: order, subject line, files/paths, rationale.
4. User edits exclusions or plan → revise.
5. Run the **pre-commit gate** (format → lint → test) — see below. Do not commit until all pass.
6. Execute commits **one at a time** (stage subset → `git commit` with HEREDOC message → show `git status`).

## Exclusions (required step)

**Out-of-scope paths never appear in any commit** unless the user explicitly removes them from exclusions for this run.

Load in order (later sources add to exclusions; do not override explicit user removals in chat):

1. **Repo `.gitignore`** — for each candidate path, skip if ignored: `git check-ignore -q -- <path>` (exit 0 = ignored).
2. **User message** — paths/globs from `/commit_split` arguments or follow-up (e.g. `exclude src/ and notebooks/`).
3. **Confirm** — if no exclusions stated and many paths are in scope, ask once: *"Any paths to leave unstaged (e.g. `src/`, WIP docs)?"*

Treat as excluded: matching files in `git status` (modified, untracked, staged). Report excluded paths in a short **Excluded** section before the plan.

Skip entirely (do not suggest commits for): `.DS_Store`, `__pycache__/`, `.env`, credentials, unless user asks to include.

## Invocation

- `/commit_split`
- "Split commits with conventional messages"
- Optional: extra exclude globs in the same message

## Conventional commit format

Subject (required):

```text
<type>(<optional scope>): <description>
```

Rules: imperative present tense; **lowercase** description; **no** trailing period; scope optional, project-defined, **not** issue IDs. Breaking changes: `!` before `:` and `BREAKING CHANGE:` footer. Full type checklist and examples: [CONVENTION.md](CONVENTION.md).

### SmartWealthAI scopes (when this repo)

| Scope | Use for |
| --- | --- |
| `docs` | `docs/`, `CONTEXT.md`, `AGENTS.md` |
| `agents` | `.cursor/rules/` |
| `mvp` | `spec/**` specs |
| `skills` | `.cursor/skills/` |
| `chore` | `.gitignore`, repo hygiene with no domain doc change |

Prefer **one concern per commit** (e.g. `docs(mvp): …` separate from `chore(agents): …`).

## Grouping strategy

Cluster changes so each commit is independently understandable:

| Signal | Typical type | Example subject |
| --- | --- | --- |
| MVP spec only | `docs(mvp)` | `docs(mvp): align cheap-stocks EY validation with architecture` |
| `CONTEXT.md` / ADR | `docs` | `docs: add ubiquitous language for sell-watch` |
| Agent rules | `docs(agents)` or `chore(agents)` | `chore(agents): add spec-driven workflow rule` |
| `.gitignore` | `chore` | `chore: ignore local data and notebook outputs` |
| CI / deploy | `ops` or `ci` | `ci: add daily pipeline workflow` |
| Deps / lockfile | `build` | **Excluded by default** unless user includes |
| App code `src/` | `feat` / `fix` / `refactor` | **Excluded by default** until user includes |
| Notebooks | `chore` or exclude | **Excluded by default** |

Do **not** mix unrelated types in one commit (docs + cursor rules is OK only if one atomic story; prefer split).

Order commits: **chore/build** → **docs** → **feat/fix/refactor** (dependencies and review flow).

## Commit plan output

Present before any `git commit`:

```markdown
## Excluded
- `src/` (…)
- …

## Commit plan

| # | Subject | Paths | Notes |
| --- | --- | --- | --- |
| 1 | `docs(agents): …` | `.cursor/rules/domain.md` | … |
| 2 | … | … | … |

**Total commits:** N | **Files in plan:** M | **Excluded files:** K
```

Ask: *"Approve this plan as-is, edit numbering/subjects, or exclude more paths?"*

## Pre-commit gate (required)

After the user approves the plan, **before the first `git commit`**, run the repo quality checks in order. Fix failures and re-run until all pass. **Never** use `--no-verify` to skip hooks or checks.

```bash
make format   # auto-fix ruff formatting
make lint     # ruff check + format --check (must exit 0)
make test     # pytest with coverage (must exit 0)
```

If `make` is unavailable, use the equivalent Poetry targets from the repo `Makefile`:

```bash
poetry run ruff format .
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest --cov=smartwealthai --cov-report=term-missing
```

### When format changes the working tree

1. Show `git status` and `git diff --stat` after `make format`.
2. Attach each formatted file to the commit plan row that already owns that path (preferred).
3. If formatting touched many unrelated paths, add a leading commit: `style: apply ruff format` — only when no single feature commit owns the bulk of the changes.
4. Do **not** ask for re-approval unless the plan structure changes (new commit row or moved paths).

### When lint or test fails

1. Fix the code (not the gate commands).
2. Re-run from `make format` through `make test`.
3. Only then start executing the commit plan.

Report a short **Pre-commit gate** summary before the first commit:

```markdown
## Pre-commit gate
- format: applied (N files changed) | no changes
- lint: passed
- test: passed (M tests)
```

## Executing commits

After approval **and a green pre-commit gate**:

```bash
git reset HEAD

git add -- <paths from row N only>
git commit -m "$(cat <<'EOF'
<type>(<scope>): <description>

<optional body: why, not what>
EOF
)"
git status
```

- Use `git add -p` only when a single file spans two commits and the user agrees to split hunks.
- If a path is partially wanted, ask before patch staging.
- After all commits, summarize SHAs and subjects; remind user excluded paths remain dirty/untracked.
- Do **not** re-run the full gate after each individual commit unless a commit introduced new changes that might break lint or tests; if in doubt, run `make lint && make test` once at the end.

## Dependency files

`pyproject.toml` and `poetry.lock` are **tracked** (not in `.gitignore`). When they change, prefer a dedicated `build:` or `chore:` commit unless the user folds them into another approved row.

## Safety

- **Never** `git push`, `--force`, `commit --amend`, or `--no-verify` unless the user explicitly requests it.
- **Never** `git add .` or `git add -A` when exclusions exist.
- **Never** update `git config`.
- **Never** commit secrets (`.env`, credentials).
- If nothing remains after exclusions, say so and list excluded files only.

## References

- [CONVENTION.md](CONVENTION.md) — types, scopes, bodies, footers, examples
- `.cursor/rules/git-conventions.mdc` — repo branch and PR conventions
