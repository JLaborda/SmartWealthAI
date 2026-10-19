# Problem Definition: Early safe credit-environment readiness check

- **Slug**: credit-css-doctor
- **Created**: 2026-10-16
- **Inputs used**: intake.md | research.md

## Problem Statement

Credit-domain operators (and agents preparing CSS runs) cannot confirm, early and safely, that the local credit package and credit-related environment look ready before heavier scoring or data stages. Feedback today arrives late as command failure, or via ad-hoc env inspection that risks exposing secrets; the maintainers also lack a small, bounded Spec Kit discovery→delivery practice slice with deletable scope.

## Affected Users & Stakeholders

- **Users**: Local CSS operators / demo runners — hit late failures in fit, score, serve, or mart stages when install or env is wrong; may inspect env vars manually and risk leaking values (research: issue #191; guides describing serve artifact failures).
- **Users**: Delivery agents practicing Spec Kit — need a thin, clearly scoped feature to exercise assess→specify→implement without touching mart/model/AWS (research: intake primary driver; issue #191).
- **Stakeholders**: Maintainer (JLaborda) — owns go/kill and wants Spec Kit fluency plus a low-risk operator smoke signal (research: issue author; `ready-for-agent` label).

## Goals

- Operators can learn, in one local action and without secret leakage, whether package/runtime identity and configured credit paths/env look present before starting heavier CSS work.
- Maintainers can complete one full Spec Kit funnel (assessment through delivery artifacts) on a credit-domain slice that does not expand into scoring, mart, or cloud work.
- Any readiness report stays boolean / identity-only (no secret values; no investing/SIMFIN coupling).

## Non-Goals

- Improving or changing scoring, mart transforms, model fit, or PSI behavior.
- Network calls or remote health checks.
- Emitting secret values or printing secret path strings as values.
- Structured machine-readable output in this slice (deferred; may return later as Living Spec).
- Validating multi-user product demand or building a general observability platform.
- Coupling credit readiness checks to investing-domain configuration.

## Success Metrics

- An operator (or agent) can obtain a local readiness snapshot covering package identity, runtime identity, and presence/absence of a closed set of credit paths/env signals in under one minute without reading application data (baseline: unknown; today requires `--version` + manual env/path inspection or waiting for a later command failure — research).
- Zero incidents of secret values appearing in the readiness snapshot in automated checks for this slice (baseline: N/A until built; qualitative gate until then).
- Spec Kit assessment for this slug reaches a recorded decide verdict, and (if go) a Living Spec under `specs/` can be closed with testable acceptance criteria without mart/AWS scope creep (baseline: assessment in progress; no `specs/016-…` yet — research).

## Cost of Inaction

Operators keep discovering misconfiguration only inside heavier commands; env debugging stays ad-hoc with leak risk. Spec Kit practice must pick another slice (likely larger or less deletable). Partial substitutes (`--version`, serve error messages) remain, but there is still no single early, secret-safe readiness view (research: Market & Context; Evidence Against).

## Open Questions

- [NEEDS CLARIFICATION: Which exact credit env vars and expected data paths belong in the closed readiness checklist?]
- [NEEDS CLARIFICATION: Should the readiness capability remain as a permanent operator tool after the Spec Kit dry run, or is it disposable scaffolding?]
- [NEEDS CLARIFICATION: What exit / failure policy applies when paths or env vars are missing — report-only success, or fail when something is absent?]
- [NEEDS CLARIFICATION: For artifact-related env, is “set” enough, or must “referenced file exists” also be signaled without revealing the path value?]
