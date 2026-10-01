# Credit demo data (local / LFS)

Public demo data only — not live bank BFSI data.

## Book sample (AMEX-shaped) — smoke / hermetic

| Path | Notes |
| --- | --- |
| `credit/data/train_df_sample.pkl` | Sample from *Financial AI in Practice* ch.5; Git LFS (~319 MiB). Jorge: AMEX-derived, not Home Credit. |

**Schema (inspected):** 100 000 rows × 919 columns. Application id is the DataFrame index `customer_ID` (hex string). Target column is `target` (`int8`): **1 = bad (default)**, **0 = good** — same convention as [AMEX Default Prediction](https://www.kaggle.com/competitions/amex-default-prediction) (default = no payment within 120 days after the latest statement in the performance window). Features are aggregated AMEX-style (`P_*`, `D_*`, `B_*`, `R_*`, `S_*` mean/std/min/max/last, etc.).

**Operator:** after clone, run `git lfs pull` (or `git lfs pull --include="credit/data/*"`) so the pickle materializes locally.

## Competition raw extracts — priority path (#151)

Official Kaggle downloads only (accept competition terms; configure Kaggle CLI / `~/.kaggle/kaggle.json`). **Do not commit** full dumps. Layout (under gitignored `data/*`):

```text
data/credit/raw/amex/
data/credit/raw/home_credit/
```

| Source | Competition / dataset | Notes |
| --- | --- | --- |
| AMEX | [American Express - Default Prediction](https://www.kaggle.com/competitions/amex-default-prediction) | **DATA ACCESS: Competition Use Only** — read Rules before download. Official archive via Kaggle CLI; then **local** CSV→parquet (`credit-css convert-amex-extract`). float64→float32 only; missing values stay missing (no community NA→`-127` tricks). |
| Home Credit | [Home Credit Default Risk](https://www.kaggle.com/c/home-credit-default-risk) | Official archive via Kaggle CLI → `stage-competition-extract`. Multi-table raw (application / bureau / previous / balances). Application mart via `build-competition-mart` (#152); bureau joins deferred. Keys: `SK_ID_CURR`, `SK_ID_PREV`, `SK_ID_BUREAU`. |
| FICO HELOC | **Later** (not in #151) | [Kaggle HELOC mirror](https://www.kaggle.com/datasets/averkiyoliabev/home-equity-line-of-creditheloc); [Hugging Face `mstz/heloc`](https://huggingface.co/datasets/mstz/heloc); official [FICO Explainable ML Challenge](https://community.fico.com/s/explainable-machine-learning-challenge) form (often flaky). |

### Operator steps (local)

Prereq: Poetry installs the `kaggle` CLI (`poetry run kaggle`). Credentials: `~/.kaggle/kaggle.json` or `KAGGLE_USERNAME` / `KAGGLE_KEY`. Accept each competition’s Rules on the website first. Disk: AMEX raw zip is ~20 GB before unzip/parquet.

```bash
# Home Credit
mkdir -p data/credit/raw/home_credit
poetry run kaggle competitions download -c home-credit-default-risk -p data/credit/raw/home_credit
poetry run credit-css stage-competition-extract \
  --source data/credit/raw/home_credit/home-credit-default-risk.zip \
  --dest-dir data/credit/raw/home_credit

# AMEX (Competition Use Only — local private use; do not redistribute)
mkdir -p data/credit/raw/amex
poetry run kaggle competitions download -c amex-default-prediction -p data/credit/raw/amex
poetry run credit-css stage-competition-extract \
  --source data/credit/raw/amex/amex-default-prediction.zip \
  --dest-dir data/credit/raw/amex
# After unzip, convert large CSVs (paths may vary if nested):
poetry run credit-css convert-amex-extract \
  --source data/credit/raw/amex/train_data.csv \
  --output data/credit/raw/amex/train_data.parquet
poetry run credit-css convert-amex-extract \
  --source data/credit/raw/amex/test_data.csv \
  --output data/credit/raw/amex/test_data.parquet
```

If the zip extracts nested folders, point `--source` at the CSV path that actually exists. Labels file (`train_labels.csv`) can stay CSV.

### Competition → application mart (#152)

Given raw extracts above, build validated application marts (one row per applicant/application + **target** → **bad**/**good**):

```bash
# AMEX: statement parquet + train_labels → customer-level mart
poetry run credit-css build-competition-mart \
  --source-kind amex \
  --raw-dir data/credit/raw/amex \
  --output-dir data/credit/application_mart/amex

# Home Credit: application_train pass-through (bureau joins later)
poetry run credit-css build-competition-mart \
  --source-kind home_credit \
  --raw-dir data/credit/raw/home_credit \
  --output-dir data/credit/application_mart/home_credit
```

**AMEX contract:** numeric features aggregated per `customer_ID` (ordered by `S_2`) as mean/std/min/max/last; inner join `train_labels.csv`; `target` 1=bad, 0=good.  
**Home Credit contract (v1):** `application_train.csv` already application-grain; bureau/previous/balance joins deferred.

Downstream: competition EDA (#153), then scratch scoring (#145).

Hermetic CI uses `tests/credit/fixtures/` (tiny AMEX statements + Home Credit application rows).

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
