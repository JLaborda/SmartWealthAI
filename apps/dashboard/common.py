"""Shared helpers for the demo Streamlit dashboard."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import streamlit as st

from smartwealthai.dashboard_data import (
    DashboardSnapshot,
    discover_latest_run_date,
    load_dashboard_snapshot,
    resolve_data_dir,
)


def data_dir() -> Path:
    return resolve_data_dir()


def selected_run_date() -> date:
    """Resolve run date from query params, env, or latest scored partition."""
    params = st.query_params
    if "run_date" in params:
        return date.fromisoformat(str(params["run_date"]))

    env_run_date = os.environ.get("SMARTWEALTHAI_RUN_DATE")
    if env_run_date:
        return date.fromisoformat(env_run_date)

    latest = discover_latest_run_date(data_dir())
    if latest is None:
        return date.today()
    return latest


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
