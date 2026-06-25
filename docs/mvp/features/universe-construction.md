# Feature: Universe Construction

## Implementation status

**in progress** — universe builder implemented ([#58](https://github.com/JLaborda/SmartWealthAI/issues/58)); industry exclusions reference CSV ([#56](https://github.com/JLaborda/SmartWealthAI/issues/56)) done.

Demo mode ships first ([`demo-slice.md`](../demo-slice.md)); full S&P 500 historical mode in phase 2.

## Objective

Produce the investable universe of US common stocks for each decision date. This module is the single entry point for "which tickers does the strategy consider today?" and is the upstream dependency of every downstream module. It must be point-in-time correct and survivorship-bias-free.

## MVP scope

### Demo slice (June 30)

- Seed universe: all SimFin US companies (`load_companies(market='us')`).
- Exclude banks, insurers, and utilities via `data/reference/simfin_industry_exclusions.csv` (`IndustryId` list built from `load_industries()`).
- **Regeneration rules** (applied by `build_exclusions` in `src/smartwealthai/simfin_industry_exclusions.py`):
  - `bank`: SimFin industry name exactly `Banks`
  - `insurer`: industry name contains `Insurance`
  - `utility`: SimFin sector exactly `Utilities`
- Regenerate after SimFin industry label changes: `poetry run generate-simfin-industry-exclusions --industries <path-to-industries.csv>`
- Sanity check: exclude tickers present in SimFin `income-banks` or `income-insurance` bulk datasets even if `IndustryId` is missing from the CSV.
- No S&P 500 historical file required for demo.
- No market-cap or ADV floors in demo (optional parameters disabled).
- Produce daily snapshot under `curated/universe/run_date=<YYYY-MM-DD>/`.

### Full MVP (phase 2)

- S&P 500 historical constituents (incl. delisted) from `data/reference/sp500_constituents.csv`.
- Common-stock filters (exclude ADRs, REITs, BDCs, ETFs, preferred-only).
- SIC-based sector exclusions when SEC ETL is available.
- Share-class deduplication by ADV.
- Optional market-cap and volume floors.

## Out of MVP scope

- Non-US universes.
- Index families other than S&P 500 (Russell 3000, MSCI USA, etc.) as the seed.
- Liquidity rules beyond a static daily-volume threshold.
- Sector exposure limits (out of MVP scope per architecture decision).
- Automatic re-classification of issuers as they change SIC code.

## Inputs

| Input | Source | Notes |
| --- | --- | --- |
| US company list | SimFin `companies` (demo) | `Ticker`, `CIK`, `IndustryId`. |
| Industry metadata | SimFin `industries` + `simfin_industry_exclusions.csv` | Sector/industry names for audit. |
| Bank/insurance sanity | SimFin `income-banks` / `income-insurance` ticker index | Secondary exclusion signal. |
| Historical S&P 500 constituents | `data/reference/sp500_constituents.csv` | Phase 2 only. |
| SIC codes | SEC EDGAR submissions | Phase 2 only. |
| Daily prices and volume | `curated/prices` | For ADV dedup and floors (phase 2). |
| Market cap | `curated/fundamentals` join `curated/prices` | Tie-break and optional floors. |
| Run date | Pipeline parameter | PIT universe slice. |

## Outputs

| Dataset | Path | Schema |
| --- | --- | --- |
| Daily universe | `s3://smartwealthai-data-lake/curated/universe/run_date=<YYYY-MM-DD>/universe.parquet` | `run_date, ticker, cik, industry_id, sector, market_cap_usd, exclusion_reasons` (demo schema; `sic_code` added in phase 2) |
| Exclusion log | `s3://smartwealthai-data-lake/curated/universe/run_date=<YYYY-MM-DD>/exclusions.parquet` | One row per excluded ticker with the triggered rule(s). |
| DuckDB view | `v_universe` | Latest universe view, partitioned on `run_date`. |

## Mermaid diagram (demo)

```mermaid
flowchart TD
    Companies["SimFin companies (market=us)"] --> Seed["Seed universe at run_date"]
    ExclCSV["simfin_industry_exclusions.csv"] --> SectorFilter{"IndustryId excluded?"}
    BankSanity["Bank / insurance statement indices"] --> SanityFilter{"Bank or insurer ticker?"}
    Seed --> SectorFilter
    SectorFilter -->|Yes| Excluded["exclusions.parquet"]
    SectorFilter -->|No| SanityFilter
    SanityFilter -->|Yes| Excluded
    SanityFilter -->|No| Universe["universe.parquet"]
    Universe --> DuckDBView["v_universe"]
    Excluded --> ExclusionLog["exclusions.parquet"]
```

## Mermaid diagram (full MVP — phase 2)

```mermaid
flowchart TD
    SP500["data/reference/sp500_constituents.csv"] --> Seed["Build seed universe at run_date"]
    Curated["curated/fundamentals + curated/prices"] --> Enrich["Enrich with SIC, market cap, ADV"]
    Seed --> Enrich

    Enrich --> CommonOnly{"Common stock?"}
    CommonOnly -->|No| Excluded["Excluded: non-common-stock"]
    CommonOnly -->|Yes| SectorFilter{"SIC in banks / insurers / utilities?"}

    SectorFilter -->|Yes| Excluded2["Excluded: sector"]
    SectorFilter -->|No| Dedup["Deduplicate share classes by ADV"]
    Dedup --> Floors{"Market cap and volume floors"}
    Floors -->|Below| Excluded3["Excluded: too small / illiquid"]
    Floors -->|Above| Universe["Daily universe (curated/universe)"]

    Excluded --> ExclusionLog["exclusions.parquet"]
    Excluded2 --> ExclusionLog
    Excluded3 --> ExclusionLog

    Universe --> DuckDBView["v_universe"]
```

## Expected flow (demo)

1. Load SimFin `companies` for `market=us` from curated or raw snapshot.
2. Join `IndustryId` to `simfin_industry_exclusions.csv`; excluded rows → `exclusions.parquet` with reason `sector`.
3. Drop tickers found in bank/insurance SimFin statement indices (sanity check).
4. Persist `universe.parquet` for `run_date`.

## Expected flow (full MVP — phase 2)

1. Read `data/reference/sp500_constituents.csv` and compute historical membership through `run_date`.
2. Map each ticker to its CIK and `sic_code` via the curated EDGAR submissions table.
3. Filter to common stocks. The MVP keeps only issuers whose SEC form types include `10-K` and `10-Q` filed on a standard schedule, and excludes:
   - ETFs and ETN issuers (form `N-CSR`, `N-Q`, fund-specific filings).
   - REITs (`SIC 6798`).
   - BDCs (`SIC 6770` and explicit BDC registrants).
   - Preferred-only listings.
   - Foreign private issuers filing `20-F` instead of `10-K` (ADRs).
4. Exclude sectors by SIC code range:
   - Banks: `6020-6199`.
   - Insurers: `6311-6411`.
   - Utilities: `4900-4999`.
   The full SIC-to-bucket mapping table is materialized in the spec for review.
5. For each issuer with multiple share classes, compute the trailing-90-day average daily volume per class and keep the class with the highest figure. All other classes go to `exclusions.parquet` with reason `share_class_lower_liquidity`.
6. Apply optional floors:
   - `market_cap_usd >= market_cap_floor` (parameter, default off in the MVP).
   - `avg_daily_volume_usd_90d >= adv_floor` (parameter, default `1_000_000` USD).
7. Persist the universe and exclusion log for `run_date`, alongside the parameter values used.

## Acceptance criteria

### Demo

- [x] `data/reference/simfin_industry_exclusions.csv` versioned with banks, insurers, utilities (`industry_id`, `industry_name`, `sector`, `exclusion_reason`).
- [x] Same `run_date` → byte-identical `universe.parquet`.
- [x] No excluded `IndustryId` appears in the universe.
- [x] No bank/insurance sanity-check ticker appears in the universe.
- [x] Module consumes only curated/raw SimFin snapshots (no network).

**Code:** `src/smartwealthai/universe_builder.py`, CLI `poetry run build-universe`.

### Full MVP (phase 2)

- Bankrupt companies that were once in the index appear in past universe snapshots up to their delisting date and are excluded only after that date with reason `delisted`.
- No company whose SIC code is in the excluded sector ranges appears in any universe snapshot.
- Share class deduplication is reversible from the exclusion log.
- The schema of `universe.parquet` is versioned and documented.

## Open questions

- Source of the historical constituents file. Proposed: `github.com/fja05680/sp500` snapshot pinned in `data/reference/sp500_constituents.csv`. Need user confirmation.
- How do we handle additions / removals on the same day a ticker is also evaluated for inclusion? Recommendation: include the ticker if it was in the index at the close of the prior trading day.
- Do we want a manual override list (`data/reference/universe_overrides.csv`) so the user can pin or blacklist tickers for testing? Recommendation: yes, but only honored when an explicit flag is set on the run.
- For dual-class issuers, do we collapse activity from both classes for the personal portfolio module, or do we keep them separate? Recommendation: keep separate in `portfolio-evolution`, deduplicate only in the investment universe.
- Do we want to record, in the universe snapshot, the SIC code reclassifications that happen mid-history? Recommendation: yes, store both the current and the as-of-date SIC code.

## Risks

- The community S&P 500 constituents dataset can have errors (missing additions, wrong dates). Mitigation: pin a snapshot and add a smoke test that asserts a known set of historical events (e.g., Lehman removal 2008, Tesla addition 2020).
- SIC codes are not a perfect sector classifier. Some banks file under non-bank SIC codes and vice versa. Mitigation: keep an explicit override list per CIK and review it during exclusions analysis.
- Survivorship bias still creeps in if the constituents file is built from "currently listed" companies. Mitigation: verify a sample of known-bankrupt companies (Lehman, Enron, WorldCom) are present in the historical file.
- Share class deduplication based on liquidity can flip the kept class across days for low-liquidity issuers. Mitigation: smooth the volume metric over 90 days and require a margin before flipping.
- Excluding banks, insurers, and utilities removes a sizable chunk of the index. Documented as an MVP trade-off.
