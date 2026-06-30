"""Tracer bullet: quantitative-value.md spec structure (issue #86)."""

from pathlib import Path

SPEC_PATH = Path("docs/mvp/features/quantitative-value.md")

REQUIRED_HEADINGS = (
    "## Objective",
    "## MVP scope",
    "## Acceptance criteria",
)


def test_quantitative_value_spec_exists_with_required_sections() -> None:
  assert SPEC_PATH.is_file(), f"missing spec: {SPEC_PATH}"

  text = SPEC_PATH.read_text(encoding="utf-8")

  for heading in REQUIRED_HEADINGS:
    assert heading in text, f"missing heading: {heading}"

  assert "```mermaid" in text, "spec must include at least one Mermaid diagram"
