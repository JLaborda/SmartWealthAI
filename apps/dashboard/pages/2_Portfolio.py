"""Top equal-weight model portfolio with per-name explainability."""

from __future__ import annotations

import streamlit as st

from apps.dashboard.common import load_snapshot, render_empty_state, render_footer

st.set_page_config(page_title="Portfolio", page_icon="💼", layout="wide")

st.title("Model portfolio")
st.caption("Top names by combined rank, equal-weighted.")

snapshot = load_snapshot()

if not snapshot.has_portfolio:
    render_empty_state("portfolio")
else:
    explain = snapshot.portfolio.sort_values(["combined_rank", "market_cap"], ascending=[True, True])
    if snapshot.has_ranking:
        explain = explain.merge(
            snapshot.ranking[
                ["ticker", "roc", "ey", "roc_rank", "ey_rank", "ebit", "market_cap", "as_of_date"]
            ],
            on="ticker",
            how="left",
            suffixes=("", "_rank"),
        )
        columns = [
            "ticker",
            "combined_rank",
            "weight",
            "roc",
            "ey",
            "roc_rank",
            "ey_rank",
            "ebit",
            "market_cap",
            "as_of_date",
        ]
    else:
        columns = ["ticker", "combined_rank", "weight", "market_cap"]
    st.dataframe(explain[columns], use_container_width=True, hide_index=True)

render_footer(snapshot)
