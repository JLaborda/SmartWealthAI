# GitHub Issues workflow

Git specs under `spec/` are canonical. **GitHub Issues** track execution.

## One issue per feature

When a feature moves to implementation:

1. Open **one GitHub issue** for the feature (e.g. `Feature: Cheap stocks — EY rank`).
2. Add label `ready-for-agent` when the spec is complete and work can start.
3. Create `plan.md` and `tasks.md` under `spec/features/00N-slug/` when implementation begins.

## Issue body template

```markdown
## Spec
spec/features/003-cheap-stocks/spec.md

## Plan
spec/features/003-cheap-stocks/plan.md (when exists)

## Tasks
See spec/features/003-cheap-stocks/tasks.md
```

Copy acceptance criteria from `spec.md` into the issue description or link to the spec path.

## Sync discipline

1. Change MVP decisions in the Git spec first (`spec.md`, or `constitution/` for cross-cutting rules).
2. Create or update the GitHub issue.
3. On completion: update `spec.md` (implementation status, acceptance criteria), check off `tasks.md`, then close the issue.

## `tasks.md` format

Markdown checklist in the feature folder. Example:

```markdown
# Tasks: Cheap stocks

- [ ] Implement EY from curated fundamentals
- [ ] Cross-sectional EY rank
- [ ] Wire into combined rank
```

`tasks.md` is the versioned checklist; the GitHub issue is the tracking unit on the project board.

## Issue tracker

Repository: `JLaborda/SmartWealthAI` via `gh` CLI. See [`.cursor/rules/issue-tracker.md`](../../.cursor/rules/issue-tracker.md).
