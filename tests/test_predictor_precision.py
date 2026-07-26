"""Predictor precision differs between cohorts and must be measured, because
measurement error in a predictor flattens a fitted slope."""

from __future__ import annotations

import pandas as pd
import pytest

from bigp3_als.predictor_precision import precision_table, precision_versus_slope


def _features() -> pd.DataFrame:
    return pd.DataFrame({
        "study": ["StudyA"] * 3 + ["StudyB"] * 3,
        "study_participant_id": [f"P{i}" for i in range(6)],
        "session_id": ["SE001"] * 6,
        "train_file_count": [10, 10, 10, 2, 2, 2],
        "n_calibration_epochs": [4000, 4000, 4000, 400, 400, 400],
        "n_target_epochs": [600, 600, 600, 60, 60, 60],
        "calibration_auc": [0.80, 0.82, 0.78, 0.70, 0.60, 0.85],
    })


def test_precision_table_reports_one_row_per_study() -> None:
    table = precision_table(_features())

    assert list(table["study"]) == ["StudyA", "StudyB"]
    assert table.loc[table["study"] == "StudyA", "median_train_files"].iloc[0] == 10


def test_fold_count_is_capped_at_five_by_the_pipeline() -> None:
    table = precision_table(_features())

    assert table.loc[table["study"] == "StudyA", "median_folds"].iloc[0] == 5
    assert table.loc[table["study"] == "StudyB", "median_folds"].iloc[0] == 2


def test_cohort_with_fewer_epochs_has_the_larger_auc_standard_error() -> None:
    table = precision_table(_features()).set_index("study")

    assert table.loc["StudyB", "auc_standard_error"] > table.loc["StudyA", "auc_standard_error"]


def test_precision_versus_slope_returns_a_rank_correlation() -> None:
    precision = pd.DataFrame({"study": ["StudyA", "StudyB", "StudyC"],
                              "auc_standard_error": [0.01, 0.05, 0.10]})
    calibration = pd.DataFrame({"held_out_study": ["StudyA", "StudyB", "StudyC"],
                                "slope": [1.5, 1.0, 0.5]})

    result = precision_versus_slope(precision, calibration)

    assert result["n_studies"] == 3
    assert result["spearman_rho"] == pytest.approx(-1.0, abs=1e-9)
