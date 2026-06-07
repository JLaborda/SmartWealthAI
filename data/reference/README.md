# Reference data (versioned in git)

Small, reviewable datasets that seed the data lake. The lake mirror lives under `data/lake/curated/reference/` (gitignored) or S3 in production.

| Path | Source | Updated by |
| --- | --- | --- |
| `universes/dow30.csv` | Dow Jones 30 constituents + SEC CIKs | Hand-edited / PR review |
| `universes/*.csv` | Future presets (S&P 500, Russell 3000, …) | Hand-edited or import scripts |
| `sp500_constituents.csv` | [fja05680/sp500](https://github.com/fja05680/sp500) | `scripts/import_sp500_reference.py` |
| `ticker_mapping.csv` | Manual / broker overrides | Hand-edited |
| `ticker_cik_overrides.csv` | Delisted / renamed tickers → CIK | Hand-edited |

### Universe files

Download presets for `download-fundamentals` live under [`universes/`](universes/README.md).
Each file lists `ticker,cik` pairs. The `dow30` preset is the initial pilot universe for
the fundamentals download spike.

Run `poetry run python scripts/import_sp500_reference.py` to refresh the S&P 500 snapshot.
