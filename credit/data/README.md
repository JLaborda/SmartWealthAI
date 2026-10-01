# Credit demo data (local / LFS)

Public demo data only — not live bank BFSI data.

## Book sample (AMEX-shaped) — smoke / hermetic

| Path | Notes |
| --- | --- |
| `credit/data/train_df_sample.pkl` | Sample from *Financial AI in Practice* ch.5; Git LFS (~319 MiB). Jorge: AMEX-derived, not Home Credit. |

**Schema (inspected):** 100 000 rows × 919 columns. Application id is the DataFrame index `customer_ID` (hex string). Target column is `target` (`int8`): **1 = bad (default)**, **0 = good** — same convention as [AMEX Default Prediction](https://www.kaggle.com/competitions/amex-default-prediction) (default = no payment within 120 days after the latest statement in the performance window). Features are aggregated AMEX-style (`P_*`, `D_*`, `B_*`, `R_*`, `S_*` mean/std/min/max/last, etc.).

**Operator:** after clone, run `git lfs pull` (or `git lfs pull --include="credit/data/*"`) so the pickle materializes locally.

## Competition raw extracts — priority path (#151)

Official Kaggle downloads only (accept competition terms; configure Kaggle CLI). **Do not commit** full dumps. Layout (under gitignored `data/*`):

```text
data/credit/raw/amex/
data/credit/raw/home_credit/
```

| Source | Competition / dataset | Notes |
| --- | --- | --- |
| AMEX | [American Express - Default Prediction](https://www.kaggle.com/competitions/amex-default-prediction) | Official archive via Kaggle CLI; then **local** CSV→parquet conversion (controlled dtypes). Do **not** treat community parquet/feather mirrors as source of truth (many re-encode NAs/categories). |
| Home Credit | [Home Credit Default Risk](https://www.kaggle.com/c/home-credit-default-risk) | Official archive via Kaggle CLI into `data/credit/raw/home_credit/`. |
| FICO HELOC | **Later** (not in #151) | [Kaggle HELOC mirror](https://www.kaggle.com/datasets/averkiyoliabev/home-equity-line-of-creditheloc); [Hugging Face `mstz/heloc`](https://huggingface.co/datasets/mstz/heloc); official [FICO Explainable ML Challenge](https://community.fico.com/s/explainable-machine-learning-challenge) form (often flaky). |

Operator download/convert steps land in #151. Downstream: raw → **application mart** (#152), competition EDA (#153), then scratch scoring (#145).

Hermetic CI continues to use `tests/credit/fixtures/application_source/applications.csv`.

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

EDA notebook (book-sample smoke): `credit/notebooks/eda_application_mart.ipynb`.

Mart artifacts under `data/credit/` stay gitignored (`data/*`).
