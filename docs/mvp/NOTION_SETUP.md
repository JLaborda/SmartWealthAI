# Notion setup for SmartWealthAI

Git specs under `docs/mvp/` stay canonical. Notion tracks tasks only.

## Default board

The project task board in Notion is named **`Cursor Agent Tasks`** (in this repo’s Notion workspace). Agents locate it via **Notion MCP search** — no board URL is committed to Git. See [AGENTS.md](../../AGENTS.md).

## 1. Board in Notion

Use the existing **`Cursor Agent Tasks`** database/board in the project Notion space. If you need a fresh board, you can duplicate the [Code with Notion template](https://notion.notion.site/code-with-notion-board) and name it `Cursor Agent Tasks`.

## 2. Project home page (optional)

Create a Notion page with:

- Link to this repository
- Link to [architecture.md](architecture/architecture.md) on GitHub
- List of [feature specs](features/)

## 3. Connect Cursor

1. Cursor **Settings → MCP** → ensure the Notion plugin is enabled.
2. Authenticate when prompted (or run `mcp_auth` for Notion if tool calls fail).

## 4. First tasks from a spec

In Agent mode, after MCP auth:

- Ask to create tasks on **`Cursor Agent Tasks`** from e.g. `docs/mvp/features/universe-construction.md`, or
- Ask to use **spec-to-implementation** (point the agent at the Git spec path; specs live in this repo, not in Notion).

## Task discipline

| Step | Where |
| --- | --- |
| Change MVP decision | Update Git spec first |
| Track work | Notion task with `docs/mvp/features/...` path |
| Finish work | Update Git spec (status + acceptance criteria), then mark Notion done |
