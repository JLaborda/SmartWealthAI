"""Combined Greenblatt ranking with ROC/EY explainability."""

from __future__ import annotations

import streamlit as st

from apps.dashboard.common import load_snapshot, render_empty_state, render_footer

st.set_page_config(page_title="Ranking", page_icon="📊", layout="wide")

st.title("Ranking")
st.caption("Combined rank = ROC rank + EY rank (lower is better). Tie-break: ascending market cap.")

snapshot = load_snapshot()

if not snapshot.has_ranking:
    render_empty_state("ranking")
else:
    display = snapshot.ranking[
        [
            "ticker",
            "combined_rank",
            "roc_rank",
            "ey_rank",
            "roc",
            "ey",
            "ebit",
            "market_cap",
            "as_of_date",
        ]
    ].copy()
    display = display.sort_values(["combined_rank", "market_cap"], ascending=[True, True])
    st.dataframe(display, use_container_width=True, hide_index=True)

render_footer(snapshot)
