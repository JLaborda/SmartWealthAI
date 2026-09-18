"""Shared helpers for the demo Streamlit dashboard."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import streamlit as st

from smartwealthai.dashboard_data import (
    DashboardSnapshot,
    load_dashboard_snapshot,
    resolve_data_dir,
    resolve_run_date,
)


def data_dir() -> Path:
    return resolve_data_dir()


def selected_run_date() -> date:
    """Resolve run date from query params, env, or latest scored partition."""
    params = st.query_params
    query_run_date = str(params["run_date"]) if "run_date" in params else None
    return resolve_run_date(
        query_run_date=query_run_date,
        env_run_date=os.environ.get("SMARTWEALTHAI_RUN_DATE"),
        data_dir=data_dir(),
    )


@st.cache_data(show_spinner=False)
def cached_snapshot(data_dir_str: str, run_date_str: str) -> DashboardSnapshot:
    return load_dashboard_snapshot(Path(data_dir_str), run_date=date.fromisoformat(run_date_str))


def load_snapshot() -> DashboardSnapshot:
    root = data_dir()
    run_date = selected_run_date()
    return cached_snapshot(str(root), run_date.isoformat())


def render_empty_state(module: str) -> None:
    st.info(f"No curated **{module}** data for this run date. Run `score-universe` first.")


def render_footer(snapshot: DashboardSnapshot) -> None:
    st.caption(
        f"Data lake: `{data_dir()}` · run_date={snapshot.run_date.isoformat()} · "
        "MLflow run link available after pipeline logging (#61)."
    )
