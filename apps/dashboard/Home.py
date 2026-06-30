"""SmartWealthAI demo dashboard — Overview page."""

from __future__ import annotations

import streamlit as st

from apps.dashboard.common import load_snapshot, render_empty_state, render_footer
from smartwealthai.dashboard_data import overview_headline

st.set_page_config(page_title="SmartWealthAI", page_icon="📈", layout="wide")

st.title("SmartWealthAI — Magic Formula Demo")
st.subheader("Overview")

snapshot = load_snapshot()
headline = overview_headline(snapshot)

col1, col2, col3 = st.columns(3)
col1.metric("Run date", headline.run_date.isoformat())
col2.metric("Ranked tickers", headline.ranked_count)
col3.metric("Portfolio holdings", headline.portfolio_count)

if headline.top_ticker:
    st.success(f"Top holding: **{headline.top_ticker}** (best combined rank)")
elif snapshot.has_portfolio:
    st.warning("Portfolio partition exists but has no rows.")
else:
    render_empty_state("portfolio")

st.markdown(
    """
Use the sidebar to open **Ranking** (full Greenblatt table with ROC/EY inputs)
or **Portfolio** (top equal-weight holdings with explainability).
"""
)

render_footer(snapshot)
