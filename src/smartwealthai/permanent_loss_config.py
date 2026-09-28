"""Load versioned permanent-loss / forensic YAML configuration."""

from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "permanent_loss"


def load_yaml_config(path: Path) -> dict:
    """Load one YAML config file."""
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_distress_rules_config(
    config_dir: Path = DEFAULT_CONFIG_DIR,
    *,
    filename: str = "distress_rules_v1.yaml",
) -> dict:
    """Return distress rule thresholds keyed by ``rule_id``."""
    return load_yaml_config(config_dir / filename)


def load_beneish_config(
    config_dir: Path = DEFAULT_CONFIG_DIR,
    *,
    filename: str = "beneish_v1.yaml",
) -> dict:
    """Return Beneish M-Score coefficients and intercept."""
    return load_yaml_config(config_dir / filename)


def load_forensic_gate_config(
    config_dir: Path = DEFAULT_CONFIG_DIR,
    *,
    filename: str = "forensic_gate_v1.yaml",
) -> dict:
    """Return cross-sectional forensic percentile gate settings."""
    return load_yaml_config(config_dir / filename)


def load_accrual_config(
    config_dir: Path = DEFAULT_CONFIG_DIR,
    *,
    filename: str = "accrual_v1.yaml",
) -> dict:
    """Return STA / SNOA accrual metric version metadata."""
    return load_yaml_config(config_dir / filename)


def load_comboaccrual_gate_config(
    config_dir: Path = DEFAULT_CONFIG_DIR,
    *,
    filename: str = "comboaccrual_gate_v1.yaml",
) -> dict:
    """Return COMBOACCRUAL bottom-percentile gate settings."""
    return load_yaml_config(config_dir / filename)
