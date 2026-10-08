# Platform

Shared AWS / Terraform and operator scripts. Domain language stays in `credit/` and investing docs — see [`CONTEXT-MAP.md`](../CONTEXT-MAP.md) and [ADR-0004](../docs/adr/0004-platform-ephemeral-fargate-serve.md).

## Scripts (credit CSS serve demo)

| Script | Purpose |
| --- | --- |
| `scripts/prepare-serve-demo-artifact.sh` | Hermetic fit → `credit/demo_artifact/pipeline.joblib` for `credit/Dockerfile.serve.demo` (#173) |

AWS `demo-up` / `demo-down` land with [#174](https://github.com/JLaborda/SmartWealthAI/issues/174).
