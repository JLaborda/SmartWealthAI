# SmartWealthAI Documentation Planning Summary

Use this summary to brief a local agent about the current documentation and planning context.

## Project context

SmartWealthAI is a Python-based financial screener and portfolio management project focused on quantitative value investing.

The current workflow is spec-driven development:

- First create and iterate Markdown specification documents.
- Ask many questions before deciding implementation details.
- Define architecture, feature boundaries, risks, and acceptance criteria.
- Only design and implement code after the specs are refined.

Important constraint: do not implement application code yet. The current work is documentation/specification only.

## MVP vision

The MVP should be a modular quantitative value investing system that can:

1. Retrieve financial data from multiple providers.
2. Store raw and normalized data in a data lake.
3. Filter companies with high risk of permanent capital loss.
4. Identify high-quality companies.
5. Identify cheap companies.
6. Use corroborative signals to strengthen or weaken investment theses.
7. Analyze unstructured financial data.
8. Prepare broker orders, starting with paper trading or simulation only.

## Documentation language

The user originally described the desired documentation in Spanish, then clarified that all documentation must be in English.

All specs should therefore be written in English.

## Documentation structure created

The documentation structure created so far is:

```text
docs/
  arquitecture.md
  features/
    etl-data-lake.md
    permanent-loss-filter.md
    high-quality-stocks.md
    cheap-stocks.md
    corroborative-signals.md
    unstructured-financial-data.md
    broker-execution.md
```

Note: `docs/arquitecture.md` intentionally uses the filename requested by the user, even though "architecture" is normally spelled differently.

## Feature modules

### ETL + Data Lake

Responsibilities:

- Download financial data from sources such as Yahoo Finance, Financial Modeling Prep, EODHD, SEC filings, and future providers.
- Store raw provider responses before transformation.
- Normalize data into shared schemas.
- Validate completeness, freshness, consistency, and lineage.
- Expose curated datasets to downstream scoring modules.

### Permanent Loss Filter

Responsibilities:

- Identify companies with elevated risk of permanent capital loss.
- Cover three core risk areas:
  - financial statement manipulation
  - fraud indicators
  - bankruptcy or financial distress
- Decide whether risks should exclude a company, penalize it, or flag it for review.
- Preserve explanations for every exclusion or penalty.

### High-Quality Stocks

Responsibilities:

- Identify companies with strong economic quality.
- Score profitability, balance sheet strength, earnings quality, and capital allocation.
- Produce explainable quality scores that can be combined with valuation scores.

### Cheap Stocks

Responsibilities:

- Identify undervalued companies.
- Use valuation ratios such as earnings yield, free cash flow yield, EV/EBIT, EV/EBITDA, price/book, price/sales, dividend yield, and shareholder yield.
- Flag unreliable ratios, especially when denominators are negative or distorted.
- Avoid blindly ranking value traps as attractive.

### Corroborative Signals

Responsibilities:

- Capture signals that support or challenge the main quality and valuation ranking.
- Candidate signals include buybacks, insider buying, insider selling, dividends, shareholder yield, short interest, institutional ownership changes, activist involvement, and corporate events.
- These signals should not replace the core value framework.

### Unstructured Financial Data

Responsibilities:

- Analyze financial text such as annual reports, 10-Ks, 10-Qs, earnings call transcripts, press releases, news, and regulatory documents.
- Store raw documents or immutable references.
- Extract metadata, text flags, summaries, and future RAG/ML-ready artifacts.
- Support future fraud analysis and qualitative risk review.

### Broker Execution

Responsibilities:

- Convert portfolio decisions into controlled order proposals.
- Start with paper trading or simulation.
- Validate orders using risk and operational checks.
- Store order proposals, approvals, submissions, status events, and reconciliation reports.
- Keep live trading out of scope for the MVP.

## Common spec structure

Each Markdown spec should include:

- Objective
- MVP scope
- Out of scope
- Candidate metrics, signals, or data
- Mermaid diagram
- Expected flow
- Questions to answer together
- Outputs
- Acceptance criteria
- Risks

The architecture spec includes:

- MVP vision
- Architecture principles
- Mermaid architecture diagram
- Module table linking to each feature spec
- Proposed functional flow
- Cross-cutting questions
- Pending decisions
- Architecture acceptance criteria

## Key architectural principles

- Modularity: modules should evolve independently.
- Traceability: every score or decision should be explainable from input data.
- Reproducibility: a run over a given universe and date should be repeatable.
- Raw data first: store raw provider responses before transformations.
- Provider abstraction: data sources should be wrapped behind connectors.
- Paper trading first: broker integration must start in simulation or paper mode.
- Specs before code: refine Markdown specs before implementation.
- Explainability: investment decisions should be auditable from versioned data and rules.

## Important open questions

The specs intentionally contain many open questions for iterative planning. Key areas still requiring user decisions include:

- Initial investment universe: US, Europe, global, common stocks only, ADRs, REITs, ETFs, etc.
- Liquidity and market cap thresholds.
- Treatment of banks, insurers, utilities, REITs, and other sectors with special accounting.
- Primary financial data provider and fallback providers.
- Data lake format and location: local filesystem, DuckDB, S3-compatible storage, database, etc.
- Whether point-in-time data is required in the MVP.
- Handling of missing, stale, or conflicting data.
- Scoring approach: Greenblatt-style ranking, weighted multifactor ranking, or staged rules.
- Whether the permanent loss filter is a hard exclusion or a score penalty.
- Rebalancing frequency and target portfolio size.
- Whether backtesting is part of the MVP or a follow-up milestone.
- Which unstructured data sources should be processed first.
- Which broker or paper trading simulator should be supported first.

## Verification already performed

- Only Markdown documentation files were created.
- No application code was implemented.
- Each architecture/feature spec includes one Mermaid diagram.
- Documentation was searched for obvious leftover Spanish headings or terms after translation.

## Git context

Work was performed on branch:

```text
cursor/spec-driven-docs-b818
```

Documentation commit:

```text
0f53a54 Add spec-driven MVP documentation
```

The branch was pushed to the remote repository.

## Recommended next step

Continue the spec-driven process by reviewing the architecture and feature documents with the user. Ask clarifying questions, record decisions in the Markdown specs, and avoid implementation until the user explicitly moves from documentation planning to code design or coding.
