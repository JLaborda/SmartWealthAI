---
description: GitHub Issues conventions for Matt Pocock engineering skills
alwaysApply: false
---

# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v` — `gh` does this automatically when run inside a clone (`JLaborda/SmartWealthAI`).

## Relationship to Git specs and Notion

| Layer | Where | Role |
| --- | --- | --- |
| **MVP specs (canonical)** | `docs/mvp/features/*.md`, `docs/mvp/architecture/architecture.md` | Product and engineering truth; update before closing work |
| **GitHub issues** | This repo's GitHub Issues | PRDs, vertical slices, and triage for Matt Pocock engineering skills (`to-issues`, `to-prd`, `triage`) |
| **Notion tasks** | Board `Cursor Agent Tasks` | Optional execution tracking via Notion MCP; see `AGENTS.md` and `docs/mvp/NOTION_SETUP.md` |

When a skill publishes to the issue tracker, create or update a **GitHub issue**. Link the relevant `docs/mvp/features/...` path in the issue body. Do not treat Notion as the issue tracker for those skills unless the user explicitly asks to sync there.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.
