"""Render every figure of the widened design from the frozen expanded outputs.

Until this script existed nothing under ``scripts/`` imported ``render_expanded``, so the figures
were rebuilt by hand and could fall silently out of step with the tables beside them, which is how
the skill figure came to plot two negative cohorts against a caption that said one. Every figure the
manuscript embeds is produced here, from one command, so that a regenerated analysis and a stale
figure cannot coexist.

The per-cohort calibration file stacks three standard-error specifications. The cluster-robust one
is primary and is the only one drawn; the heterogeneity summary is keyed the same way and its
matching block is passed rather than the whole file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from bigp3_als.expanded import ALS_STUDIES, _cohort_slopes
from bigp3_als.render_expanded import (
    render_calibration_curves,
    render_calibration_forest,
    render_cohort_type_relationship,
    render_skill_by_cohort,
    render_transportability,
)

PRIMARY_SE_METHOD = "cluster"
EXPECTED_COHORTS = 18
MAIN_TEXT_COHORTS = ALS_STUDIES + ("StudyH", "StudyS2")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("output/expanded"))
    parser.add_argument("--figures", type=Path, default=None)
    parser.add_argument("--se-method", default=PRIMARY_SE_METHOD)
    arguments = parser.parse_args()

    directory = arguments.directory
    figures = arguments.figures or directory / "figures"

    metrics = pd.read_csv(directory / "external_validation_metrics.csv")
    pooling = pd.read_csv(directory / "random_effects_pooling.csv")
    benchmark = pd.read_csv(directory / "null_benchmark.csv")
    records = pd.read_csv(directory / "analysis_records.csv")
    predictions = pd.read_csv(directory / "external_validation_predictions.csv")

    # _cohort_slopes carries the unit-of-analysis guard the analysis uses: one row per cohort under
    # one specification. Reusing it keeps the figure on the same rows every estimate was fitted on.
    calibration = _cohort_slopes(
        pd.read_csv(directory / "cohort_calibration.csv"), arguments.se_method
    )
    if len(calibration) != EXPECTED_COHORTS:
        raise ValueError(
            f"expected {EXPECTED_COHORTS} {arguments.se_method} rows, got {len(calibration)}"
        )
    summary = json.loads((directory / "heterogeneity_summary.json").read_text())[arguments.se_method]

    render_calibration_forest(calibration, summary, ALS_STUDIES, figures)
    render_calibration_curves(predictions, ALS_STUDIES, figures)
    render_calibration_curves(
        predictions, ALS_STUDIES, figures, cohorts=MAIN_TEXT_COHORTS, filename="figure_calibration_curves_main",
        max_columns=3, panel_width=2.3, panel_height=2.5,
    )
    render_transportability(metrics, pooling, ALS_STUDIES, figures)
    render_skill_by_cohort(metrics, benchmark, ALS_STUDIES, figures)
    render_cohort_type_relationship(records, ALS_STUDIES, figures)

    negative = _negative_skill_cohorts(metrics, benchmark)
    print(f"figures written to {figures}")
    print("  figure_calibration_forest        Figure 1")
    print("  figure_calibration_curves        Figure S2 (all 18 cohorts)")
    print("  figure_calibration_curves_main   Figure 2 (6-cohort subset)")
    print("  figure_transportability          Figure 3")
    print("  figure_skill_by_cohort           Figure 4")
    print("  figure_cohort_type_relationship  Figure S1")
    print(f"cohorts below the development-mean benchmark: {len(negative)} ({', '.join(negative)})")


def _negative_skill_cohorts(metrics: pd.DataFrame, benchmark: pd.DataFrame) -> list[str]:
    """Return the cohorts the skill figure draws below zero, so the caption can be checked."""
    per_study = metrics.loc[~metrics["held_out_study"].astype(str).str.startswith("Pooled")]
    merged = per_study.merge(
        benchmark[["held_out_study", "development_mean_benchmark_mae"]], on="held_out_study"
    )
    skill = 1.0 - merged["session_mean_absolute_error"] / merged["development_mean_benchmark_mae"]
    return sorted(merged.loc[skill < 0, "held_out_study"].tolist())


if __name__ == "__main__":
    main()
