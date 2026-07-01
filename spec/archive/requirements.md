> **Superseded.** Historical Sprint 0 spike. Canonical specs live under `spec/`.

# Sprint 0 requirements: Magic Formula screener spike

> **Status:** Historical reference only. The full MVP is defined in [mission.md](../constitution/mission.md) and [features/](../features/). Do not treat this document as the current MVP scope.

## Primary goal

Build a minimal Python pipeline that downloads financial data for a very small set of tickers, computes a simple ranking, and prints the result to the console.

## Functional requirements

### Input

- Start from a **static hardcoded list** of 5–10 known tickers (e.g. `["AAPL", "MSFT", "GOOGL", "JNJ", "KO"]`).
- Do not download the full S&P 500 in this spike (API rate limits and runtime).

### Processing

- Connect to a free API (recommended: `yfinance`).
- Fetch proxy metrics for the Magic Formula:
  - **Return on Capital (ROC)**, or fallback **ROE** / **ROA**
  - **Earnings Yield**, or fallback inverse **P/E**
- Rank each metric from 1 to N across the universe and **sum ranks** for a final Magic Rank.

### Output

- Print the final ranking to the console (plain `print` or a small pandas table), best to worst.

## Technical requirements

- **Language:** Python 3.x (project now standardizes on 3.11+ via Poetry)
- **Libraries:** `yfinance`, `pandas`
- **Version control:** Git with a few local commits

## Explicitly out of scope for Sprint 0

- Databases, GUI, Docker, machine learning
- Downloading thousands of tickers

Those belong to later MVP modules documented under `spec/features/`.
