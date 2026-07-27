"""Tests for the widened-design figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from bigp3_als.expanded import ALS_STUDIES
from bigp3_als.render_expanded import (
    _build_cohort_type_relationship,
    render_calibration_curves,
    render_calibration_forest,
    render_cohort_type_relationship,
    render_skill_by_cohort,
)
from bigp3_als.strengthening import null_benchmark
from tests.test_strengthening import _records


def _metrics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"held_out_study": "StudyF", "session_mean_absolute_error": 0.05},
            {"held_out_study": "StudyL", "session_mean_absolute_error": 0.20},
            {"held_out_study": "Pooled held-out records", "session_mean_absolute_error": 0.12},
        ]
    )


def _calibration() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "held_out_study": ["StudyA", "StudyB", "StudyF"],
            "slope": [0.5, 1.0, 1.8],
            "slope_se": [0.2, 0.1, 0.3],
            "intercept": [0.4, 0.0, -0.6],
            "intercept_se": [0.3, 0.2, 0.4],
        }
    )


def _summary() -> dict[str, dict[str, float]]:
    return {
        "slope": {
            "pooled": 1.1,
            "prediction_interval_low": 0.2,
            "prediction_interval_high": 2.0,
            "tau": 0.5,
            "i_squared": 80.0,
        }
    }


def test_skill_figure_reads_the_benchmark_column_null_benchmark_writes(tmp_path: Path) -> None:
    # Guards the column name across the module boundary: null_benchmark writes it and this figure
    # reads it, so a rename on one side and not the other would only surface at figure-build time.
    render_skill_by_cohort(_metrics(), null_benchmark(_records()), ("StudyF",), tmp_path)

    assert (tmp_path / "figure_skill_by_cohort.png").exists()


def test_calibration_forest_writes_both_formats(tmp_path: Path) -> None:
    render_calibration_forest(_calibration(), _summary(), ALS_STUDIES, tmp_path)

    assert (tmp_path / "figure_calibration_forest.pdf").exists()
    assert (tmp_path / "figure_calibration_forest.png").exists()


def test_calibration_curves_write_both_formats(tmp_path: Path) -> None:
    predictions = pd.DataFrame({
        "held_out_study": ["StudyA"] * 30 + ["StudyB"] * 30,
        "n": [20] * 60,
        "correct": list(range(10, 20)) * 6,
        "predicted_probability": [0.4 + 0.02 * i for i in range(30)] * 2,
    })

    render_calibration_curves(predictions, ALS_STUDIES, tmp_path)

    assert (tmp_path / "figure_calibration_curves.pdf").exists()
    assert (tmp_path / "figure_calibration_curves.png").exists()


def test_calibration_forest_rejects_a_frame_without_standard_errors(tmp_path: Path) -> None:
    # The interval is the point of the figure, so a frame carrying only point estimates must fail
    # rather than render bare dots that a reader would take for precise estimates.
    calibration = _calibration().drop(columns=["slope_se"])

    with pytest.raises(ValueError, match="slope_se"):
        render_calibration_forest(calibration, _summary(), ALS_STUDIES, tmp_path)


def test_calibration_forest_checks_the_intervals_it_derives_against_the_supplied_ones(
    tmp_path: Path,
) -> None:
    # The analysis writes both the standard error and the interval. Deriving the interval here and
    # silently disagreeing with the written one would put a figure and a table out of step.
    calibration = _calibration()
    calibration["slope_ci_low"] = calibration["slope"] - 1.959963984540054 * calibration["slope_se"]
    calibration["slope_ci_high"] = calibration["slope"] + 1.959963984540054 * calibration["slope_se"]
    render_calibration_forest(calibration, _summary(), ALS_STUDIES, tmp_path)

    calibration.loc[0, "slope_ci_high"] = 99.0
    with pytest.raises(ValueError, match="slope"):
        render_calibration_forest(calibration, _summary(), ALS_STUDIES, tmp_path)


def test_calibration_curves_use_the_primary_model_when_several_are_present(tmp_path: Path) -> None:
    # The prediction table can carry comparator models. A curve mixing model families would be a
    # calibration statement about no model in particular.
    primary = pd.DataFrame({
        "held_out_study": ["StudyA"] * 20,
        "n": [20] * 20,
        "correct": list(range(10, 20)) * 2,
        "predicted_probability": [0.5 + 0.02 * i for i in range(20)],
        "model_role": ["primary"] * 20,
    })
    comparator = primary.assign(model_role="comparator", predicted_probability=0.1)

    render_calibration_curves(pd.concat([primary, comparator]), ALS_STUDIES, tmp_path)

    assert (tmp_path / "figure_calibration_curves.pdf").exists()


def test_cohort_type_figure_draws_no_fitted_line(tmp_path: Path) -> None:
    # The record-level interaction was demoted to a study-level test because the record-level fit
    # overstates precision. A straight-line fit per cohort type is the visual form of that claim and
    # must not come back into the figure.
    figure = _build_cohort_type_relationship(_records(), ("StudyF",), "calibration_auc")
    try:
        # Nothing at all is drawn as a line, so a fit reduced to its two endpoints fails too.
        assert [line for axis in figure.axes for line in axis.lines] == []
    finally:
        plt.close(figure)

    render_cohort_type_relationship(_records(), ("StudyF",), tmp_path)
    assert (tmp_path / "figure_cohort_type_relationship.png").exists()
