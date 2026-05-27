---
name: commit-split
description: Splits the working tree into focused Conventional Commits with a numbered plan and user approval before each git commit. Use when the user invokes /commit_split, asks to split commits, or wants separate conventional commits from a large diff.
disable-model-invocation: true
---

# Commit split

Split unstaged/staged changes into **focused [Conventional Commits](https://www.conventionalcommits.org)**. Follow `.cursor/rules/git-conventions.mdc` for message format.

## Out of scope (default)

Treat paths as **out of scope** when they match the repo root `.gitignore`:

1. Read `.gitignore`.
2. For each candidate path, skip if ignored: `git check-ignore -q -- <path>` (exit 0 = ignored).

Do not stage or propose commits for ignored paths unless the user overrides in chat (e.g. "include `data/clean/` this time").

Optional per-run exclusions: user may add extra globs in chat (e.g. `/commit_split docs/mvp/backlog/`).

## Invocation

- `/commit_split`
- "Split commits with conventional messages"
- Optional: extra exclude globs in the same message

## Workflow

1. `git status` and `git diff` (staged and unstaged) for in-scope paths only.
2. Propose a **numbered commit plan**: conventional subject + file paths per row.
3. **Stop for approval** — user may edit the plan.
4. After approval only: `git add` + `git commit` per row (HEREDOC messages).
5. Do **not** push unless the user asks.

## Commit plan format

```markdown
## Proposed commits

1. `docs(mvp): align cheap-stocks spec with architecture`
   - docs/mvp/features/cheap-stocks.md
   - docs/mvp/architecture/architecture.md

2. `chore(cursor): add commit-split skill`
   - .cursor/skills/commit-split/SKILL.md
```

Group related files; one logical change per commit; prefer `docs`, `feat`, `fix`, `chore`, `ci` types from git conventions.

## Dependency files

`pyproject.toml` and `poetry.lock` are **tracked** (not in `.gitignore`). When they change:

- Prefer a dedicated commit: `chore(deps): ...` or `chore: sync poetry lockfile`
- Or fold into a commit only if the user includes them in the approved plan

## Safety

- Never commit secrets (`.env`, credentials).
- Never use `--no-verify` unless the user asks.
- Never amend/push unless the user asks (see user commit rules).
