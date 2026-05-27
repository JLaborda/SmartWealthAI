# Conventional commits (qoomon)

Reference: [qoomon cheatsheet](https://gist.github.com/qoomon/5dfcdf8eec66a051ecd85625518cfd13). Opinionated but valid [Conventional Commits](https://www.conventionalcommits.org/).

Repo-wide rules also live in `.cursor/rules/git-conventions.mdc`. Use this file when `/commit_split` needs type/scope/footer detail beyond the skill workflow.

## Message shape

```text
<type>(<optional scope>): <description>

<optional body>

<optional footer>
```

## Type checklist (use first match)

| Order | Question | Type |
| --- | --- | --- |
| 1 | Bug fix? | `fix` |
| 2 | New/changed API or UI behavior? | `feat` |
| 3 | Performance-only improvement? | `perf` |
| 4 | Restructure without behavior change? | `refactor` |
| 5 | Formatting only? | `style` |
| 6 | Tests only? | `test` |
| 7 | Documentation only? | `docs` |
| 8 | Build tools, deps, version? | `build` |
| 9 | CI/CD, infra, backups, monitoring? | `ops` |
| 10 | Otherwise (maintenance, `.gitignore`, init) | `chore` |

`perf` is a performance-focused `refactor`; mention perf in changelog-worthy refactors.

## Description rules

- Imperative, present tense: "add" not "added"
- Lowercase first letter
- No period at end
- Max ~72 chars in subject when possible

## Scope

- Optional; noun for area (`docs`, `mvp`, `api`, `agents`)
- **Do not** use issue IDs as scope (`#123`, `JIRA-456` go in footer)

## Breaking changes

Subject: `feat(api)!: remove status endpoint`

Footer:

```text
BREAKING CHANGE: ticket endpoints no longer support list all entities.
```

## Footer

- `Closes #123`, `Fixes JIRA-456`
- Required when using `!` and subject alone is insufficient

## Examples

```text
docs(mvp): document EY review queue for negative EBIT

chore(agents): add english-language cursor rule

docs: add CONTEXT ubiquitous language for pipeline terms

feat(universe): filter banks via SIC codes

fix(scores): exclude rows with EV <= 0 from EY rank

build: bump pandas in poetry lockfile
```

## Merge / revert (do not rewrite)

- Merge: default `Merge branch '…'`
- Revert: default `Revert "…"`
