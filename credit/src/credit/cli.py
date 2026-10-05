"""Credit Scoring System (CSS) CLI — composable stages (#143–#152, #145)."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import click

from credit import __version__
from credit.amex_parquet import convert_amex_extract_to_parquet
from credit.application_mart import build_application_mart
from credit.competition_mart import SourceKind, build_competition_mart
from credit.competition_raw import stage_competition_extract
from credit.scoring_pipeline import (
    ARTIFACT_NAME,
    fit_scoring_pipeline,
    score_applications,
)


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
    help=(
        "Credit Scoring System (CSS) CLI. "
        "Stages: build-application-mart, build-competition-mart, "
        "stage-competition-extract, convert-amex-extract, fit, score."
    ),
)
@click.version_option(__version__, prog_name="credit-css")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Entry point for the ``credit-css`` console script."""
    if ctx.invoked_subcommand is None:
        click.echo(
            "Credit Scoring System (CSS) CLI.\n"
            "Stages: build-application-mart, build-competition-mart, "
            "stage-competition-extract, convert-amex-extract, fit, score\n"
            "See credit/docs/features/css-chapter5-mart-and-scoring.md."
        )


@main.command("build-application-mart")
@click.option(
    "--source",
    "source_path",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help="Local application source table (.csv, .pkl, or .pickle).",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Directory for the application mart artifact and README sidecar.",
)
@click.option(
    "--application-id-column",
    default="SK_ID_CURR",
    show_default=True,
    help="Application id column (or index name for AMEX-shaped pickles).",
)
@click.option(
    "--target-column",
    default="TARGET",
    show_default=True,
    help="Binary target column name.",
)
@click.option(
    "--bad-value",
    default="1",
    show_default=True,
    help="Target value that means bad (default / positive class).",
)
@click.option(
    "--good-value",
    default="0",
    show_default=True,
    help="Target value that means good (negative class).",
)
@click.option(
    "--decision-date-column",
    default=None,
    help="Optional application/decision date column for time-based split docs.",
)
def build_application_mart_cmd(
    source_path: Path,
    output_dir: Path,
    application_id_column: str,
    target_column: str,
    bad_value: str,
    good_value: str,
    decision_date_column: str | None,
) -> None:
    """Build a validated application mart from local demo source data."""
    result = build_application_mart(
        source_path,
        output_dir,
        application_id_column=application_id_column,
        target_column=target_column,
        bad_value=_parse_label_value(bad_value),
        good_value=_parse_label_value(good_value),
        decision_date_column=decision_date_column,
    )
    click.echo(
        f"Application mart written: {result.mart_path} "
        f"({result.retained_rows} retained, {result.rejected_rows} rejected). "
        f"Target `{result.target_column}`: bad={result.bad_value}, "
        f"good={result.good_value}. Split policy: {result.split_policy}. "
        f"Sidecar: {result.readme_path}"
    )


def _parse_label_value(raw: str) -> object:
    """Parse CLI label tokens; prefer ints when the token is integral."""
    try:
        as_float = float(raw)
    except ValueError:
        return raw
    if as_float == int(as_float):
        return int(as_float)
    return as_float


@main.command("build-competition-mart")
@click.option(
    "--source-kind",
    type=click.Choice(["amex", "home_credit"], case_sensitive=False),
    required=True,
    help="Competition raw source: amex or home_credit.",
)
@click.option(
    "--raw-dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    required=True,
    help="Local raw extract dir (e.g. data/credit/raw/amex).",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Directory for the application mart artifact and README sidecar.",
)
def build_competition_mart_cmd(
    source_kind: str,
    raw_dir: Path,
    output_dir: Path,
) -> None:
    """Prepare competition raw → validated application mart."""
    kind = cast(SourceKind, source_kind.lower())
    result = build_competition_mart(
        source_kind=kind,
        raw_dir=raw_dir,
        output_dir=output_dir,
    )
    click.echo(
        f"Competition mart written: {result.mart_path} "
        f"({result.retained_rows} retained, {result.rejected_rows} rejected). "
        f"Target `{result.target_column}`: bad={result.bad_value}, "
        f"good={result.good_value}. Split policy: {result.split_policy}. "
        f"Sidecar: {result.readme_path}"
    )


@main.command("stage-competition-extract")
@click.option(
    "--source",
    "source_path",
    type=click.Path(path_type=Path, exists=True),
    required=True,
    help="Downloaded competition .zip or an already-extracted directory.",
)
@click.option(
    "--dest-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Destination raw dir (e.g. data/credit/raw/home_credit).",
)
def stage_competition_extract_cmd(source_path: Path, dest_dir: Path) -> None:
    """Stage an official Kaggle extract into the local credit raw layout."""
    result = stage_competition_extract(source_path, dest_dir)
    click.echo(
        f"Staged {len(result.staged_names)} file(s) into {result.dest_dir}: "
        f"{', '.join(result.staged_names)}"
    )


@main.command("convert-amex-extract")
@click.option(
    "--source",
    "source_path",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help="Official AMEX CSV extract (e.g. train_data.csv).",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False),
    required=True,
    help="Destination parquet path.",
)
@click.option(
    "--no-downcast-float64",
    is_flag=True,
    default=False,
    help="Keep float64 (default converts float64→float32 for size only).",
)
def convert_amex_extract_cmd(
    source_path: Path,
    output_path: Path,
    no_downcast_float64: bool,
) -> None:
    """Convert an official AMEX CSV extract to local parquet (no NA sentinels)."""
    result = convert_amex_extract_to_parquet(
        source_path,
        output_path,
        downcast_float64=not no_downcast_float64,
    )
    click.echo(
        f"AMEX parquet written: {result.parquet_path} ({result.row_count} rows) "
        f"from {result.source_path}"
    )


@main.command("fit")
@click.option(
    "--mart",
    "mart_path",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help="Application mart parquet/csv (one row per application).",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help=f"Directory for {ARTIFACT_NAME} (WOE + XGBoost + score scaling).",
)
@click.option(
    "--application-id-column",
    default="customer_ID",
    show_default=True,
    help="Application id column on the mart.",
)
@click.option(
    "--target-column",
    default="target",
    show_default=True,
    help="Binary target column (bad = positive class).",
)
@click.option(
    "--holdout-fraction",
    default=0.3,
    show_default=True,
    type=float,
    help="Stratified holdout fraction (WOE/model fit on develop only).",
)
@click.option(
    "--random-state",
    default=42,
    show_default=True,
    type=int,
    help="RNG seed for develop/holdout split and XGBoost.",
)
@click.option(
    "--skip-mlflow",
    is_flag=True,
    default=False,
    help="Skip MLflow logging (still writes pipeline.joblib).",
)
@click.option(
    "--mlflow-tracking-uri",
    default=None,
    help="MLflow tracking URI (default: $MLFLOW_TRACKING_URI or ./mlruns).",
)
def fit_cmd(
    mart_path: Path,
    output_dir: Path,
    application_id_column: str,
    target_column: str,
    holdout_fraction: float,
    random_state: int,
    skip_mlflow: bool,
    mlflow_tracking_uri: str | None,
) -> None:
    """Fit WOE/IV + XGBoost on develop; export joblib; report holdout AUC + KS."""
    result = fit_scoring_pipeline(
        mart_path,
        output_dir,
        application_id_column=application_id_column,
        target_column=target_column,
        holdout_fraction=holdout_fraction,
        random_state=random_state,
        skip_mlflow=skip_mlflow,
        mlflow_tracking_uri=mlflow_tracking_uri,
    )
    click.echo(
        f"Artifact: {result.artifact_path} "
        f"(features={','.join(result.feature_names)}; "
        f"develop={result.n_develop}, holdout={result.n_holdout}; "
        f"fit_partition={result.fit_partition}). "
        f"Holdout AUC={result.holdout_auc:.4f} KS={result.holdout_ks:.4f} "
        f"(develop AUC={result.develop_auc:.4f} KS={result.develop_ks:.4f})."
    )
    if result.mlflow_run_id:
        click.echo(f"MLflow run id: {result.mlflow_run_id}")


@main.command("score")
@click.option(
    "--artifact",
    "artifact_path",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help=f"Path to {ARTIFACT_NAME} from credit-css fit.",
)
@click.option(
    "--mart",
    "mart_path",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help="Application mart to score (parquet/csv).",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False),
    required=True,
    help="Output parquet with pd, credit_score, rank.",
)
def score_cmd(
    artifact_path: Path,
    mart_path: Path,
    output_path: Path,
) -> None:
    """Load joblib artifact → PD + book-scaled credit score + rank (rank-only)."""
    result = score_applications(artifact_path, mart_path, output_path)
    click.echo(
        f"Scores written: {result.scores_path} ({result.n_scored} applications). "
        "Columns: pd, credit_score, rank (1 = safest = lowest book score)."
    )
