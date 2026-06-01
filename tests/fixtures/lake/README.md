# Fixture Lake Contract

This directory contains deterministic test fixtures for CI and local development.
The fixtures are static snapshots downloaded from internet sources (SEC EDGAR and
yfinance), then reduced and committed for hermetic tests.

## Directory layout

- `raw/sec_edgar/...`: reduced real SEC companyfacts snapshots
- `raw/yfinance/...`: reduced real yfinance history snapshots
- `curated/fundamentals.csv`: stable derived dataset for PIT tests
- `MANIFEST.json`: provenance and SHA-256 checksums

## Fundamentals fixture

File: `curated/fundamentals.csv`

| Column | Type | Description |
| --- | --- | --- |
| `cik` | string | SEC issuer identifier. |
| `ticker` | string | Ticker symbol used in tests. |
| `entity_name` | string | Issuer name from SEC companyfacts. |
| `metric` | string | SEC us-gaap metric key (for this fixture: `OperatingIncomeLoss`). |
| `fiscal_period_end` | date | Fiscal period end date reported by issuer. |
| `as_of_date` | date | Filing availability date used for point-in-time filtering. |
| `version_id` | integer | Monotonic version ordered by filing date for the same fiscal period and metric. |
| `form` | string | SEC form type (`10-K`). |
| `source_accession` | string | SEC accession id for source traceability. |
| `value_usd` | integer | Reported metric value in USD. |

## Point-in-time rule used in tests

For a decision date `D`, tests only use rows where `as_of_date <= D`.  
For each `(cik, fiscal_period_end, metric)`, the selected row is the latest by:

1. `as_of_date` ascending
2. `version_id` ascending

and taking the final row of that ordering.

This contract keeps PR CI hermetic (no AWS, no S3, no network calls) while preserving
point-in-time semantics.

## Source provenance

`curated/fundamentals.csv` rows are derived from downloaded SEC snapshots and validated
against yfinance history snapshots:

- `raw/sec_edgar/cik=0000320193/endpoint=companyfacts/as_of_date=2026-05-21/response.json`
- `raw/sec_edgar/cik=0000789019/endpoint=companyfacts/as_of_date=2026-05-21/response.json`
- `raw/yfinance/ticker=AAPL/endpoint=history/as_of_date=2026-05-21/history.json`
- `raw/yfinance/ticker=MSFT/endpoint=history/as_of_date=2026-05-21/history.json`

Exact upstream URLs, download timestamp, and checksums are stored in `MANIFEST.json`.
