# Universe reference files

Versioned ticker lists used by `download-fundamentals` and future universe modules.

## Format

Each file is a CSV with **exactly** these columns:

| Column | Type | Description |
| --- | --- | --- |
| `ticker` | string | Trading symbol (uppercase). Passed to `edgartools.Company(ticker)`. |
| `cik` | string | SEC CIK, zero-padded to 10 digits. Used for `companyfacts` REST URLs. |

Example:

```csv
ticker,cik
AAPL,0000320193
MSFT,0000789019
```

## Why include CIK?

Ticker symbols change, split across share classes, or map to multiple listings. A fixed
`ticker,cik` pair makes downloads reproducible and avoids runtime lookups against SEC
`company_tickers.json` for every run.

Resolve CIKs once when creating or refreshing a universe file:

```bash
# Example: look up CIKs from SEC company_tickers.json
curl -H "User-Agent: $SEC_IDENTITY" https://www.sec.gov/files/company_tickers.json
```

## Presets

| Preset | File | Issuers | Notes |
| --- | --- | --- | --- |
| `dow30` | `dow30.csv` | 30 | Current Dow Jones Industrial Average components. |

Register new presets in `UNIVERSE_PRESETS` (`src/smartwealthai/universe.py`).

## Maintenance

- Update the CSV when index membership changes (e.g. Dow constituent swap).
- Commit changes via PR so universe history is reviewable.
- Do not store raw lake data here — only small reference lists belong in `data/reference/`.
