# Commit split

The **`commit_split`** agent skill (global: `~/.agents/skills/commit_split/`) splits the working tree into focused [conventional commits](https://gist.github.com/qoomon/5dfcdf8eec66a051ecd85625518cfd13).

## Repo exclusions

Default out-of-scope paths are listed in [`.commit-split-ignore`](../../.commit-split-ignore) at the repo root:

- `src/`, `notebooks/`, `pyproject.toml`, `poetry.lock`, `data/*` except `data/reference/**`

Override for a single run by telling the agent in chat (e.g. "include `src/preprocessing` this time").

## Invocation

In Cursor/Codex: `/commit_split` or ask to "split commits with conventional messages".

Optional argument: extra globs to exclude, e.g. `/commit_split docs/mvp/backlog/`.

## Workflow

1. Agent reads `.commit-split-ignore` + your exclusions.
2. Proposes a numbered commit plan (subject + paths per commit).
3. You approve or edit.
4. Agent runs `git add` + `git commit` per row — **only after approval**.

Commits are not pushed automatically.
