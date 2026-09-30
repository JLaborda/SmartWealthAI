# Credit demo data (local / LFS)

Public demo data only — not live bank BFSI data.

## Book sample (AMEX-shaped)

| Path | Notes |
| --- | --- |
| `credit/data/train_df_sample.pkl` | Sample from *Financial AI in Practice* ch.5; Git LFS (~319 MiB). Jorge: AMEX-derived, not Home Credit. |

**Schema (inspected):** 100 000 rows × 919 columns. Application id is the DataFrame index `customer_ID` (hex string). Target column is `target` (`int8`): **1 = bad (default)**, **0 = good** — same convention as [AMEX Default Prediction](https://www.kaggle.com/competitions/amex-default-prediction) (default = no payment within 120 days after the latest statement in the performance window). Features are aggregated AMEX-style (`P_*`, `D_*`, `B_*`, `R_*`, `S_*` mean/std/min/max/last, etc.).

**Operator:** after clone, run `git lfs pull` (or `git lfs pull --include="credit/data/*"`) so the pickle materializes locally.

## Later sources (out of this hotfix)

- Full AMEX: https://www.kaggle.com/competitions/amex-default-prediction
- Home Credit: https://www.kaggle.com/c/home-credit-default-risk

Do not commit full Kaggle dumps. Hermetic CI continues to use `tests/credit/fixtures/application_source/applications.csv`.

## Mart regeneration (book sample)

```bash
git lfs pull --include="credit/data/*"
poetry run credit-css build-application-mart \
  --source credit/data/train_df_sample.pkl \
  --output-dir data/credit/application_mart \
  --application-id-column customer_ID \
  --target-column target \
  --bad-value 1 \
  --good-value 0
```

EDA notebook (reads the mart): `credit/notebooks/eda_application_mart.ipynb`.

Mart artifacts under `data/credit/` stay gitignored (`data/*`).
