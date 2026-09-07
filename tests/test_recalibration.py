"""Tests for the local-recalibration learning curve."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bigp3_als.recalibration import (
    LOCAL_SIZES,
    MINIMUM_EVALUATION_PARTICIPANTS,
    recalibration_draws,
    recalibration_summary,
)


def _cohort(n_participants: int, offset: float, seed: int) -> pd.DataFrame:
    """One cohort whose transported probabilities are shifted by a constant on the log-odds scale."""
    rng = np.random.default_rng(seed)
    truth = rng.uniform(0.35, 0.9, size=n_participants)
    transported = 1.0 / (1.0 + np.exp(-(np.log(truth / (1 - truth)) - offset)))
    return pd.DataFrame(
        {
            "held_out_study": "StudyX",
            "study_participant_id": [f"StudyX:{i:02d}" for i in range(n_participants)],
            "session_id": "S1",
            "condition": "CB",
            "n": 40,
            "correct": rng.binomial(40, truth),
            "predicted_probability": transported,
        }
    )


def test_intercept_only_recalibration_removes_a_pure_offset() -> None:
    predictions = _cohort(16, offset=1.2, seed=3)

    draws = recalibration_draws(predictions, sizes=(6,), draws=40, seed=11)
    summary = recalibration_summary(draws)
    row = summary.set_index(["method", "n_local_participants"]).loc[("intercept_only", 6)]

    assert row["mean_improvement"] > 0.05
    assert row["win_fraction"] > 0.9


def test_recalibration_is_evaluated_only_on_participants_outside_the_local_draw() -> None:
    predictions = _cohort(12, offset=0.8, seed=4)

    draws = recalibration_draws(predictions, sizes=(4,), draws=5, seed=12)

    # 12 participants, 4 drawn locally, so every row must have been scored on the other 8.
    assert (draws["n_evaluation_participants"] == 8).all()


def test_a_cohort_too_small_for_a_size_contributes_no_rows_at_that_size() -> None:
    predictions = _cohort(5, offset=0.5, seed=5)

    draws = recalibration_draws(predictions, sizes=(1, 3, 4), draws=5, seed=13)

    # 5 participants and a floor of 3 evaluation participants leaves size 1 only, since 5 - 3 = 2
    # and 5 - 4 = 1 both fall below the floor.
    assert sorted(draws["n_local_participants"].unique()) == [1]


def test_slope_recalibration_is_not_attempted_on_a_single_local_participant() -> None:
    predictions = _cohort(10, offset=0.6, seed=6)

    draws = recalibration_draws(predictions, sizes=(1,), draws=5, seed=14)

    assert set(draws["method"]) == {"intercept_only"}


def test_a_non_identified_draw_is_flagged_rather_than_scored() -> None:
    # Every local participant at 100% accuracy separates the fit perfectly.
    predictions = _cohort(12, offset=0.0, seed=7)
    predictions.loc[predictions.index[:4], "correct"] = predictions.loc[predictions.index[:4], "n"]

    draws = recalibration_draws(predictions, sizes=(4,), draws=30, seed=15)

    assert draws["identified"].dtype == bool
    assert draws.loc[~draws["identified"], "mean_absolute_error"].isna().all()


def test_summary_reports_the_paired_difference_not_two_independent_means() -> None:
    predictions = _cohort(14, offset=1.0, seed=8)

    draws = recalibration_draws(predictions, sizes=(5,), draws=30, seed=16)
    summary = recalibration_summary(draws)
    row = summary.set_index(["method", "n_local_participants"]).loc[("intercept_only", 5)]

    identified = draws.loc[draws["identified"] & (draws["method"] == "intercept_only")]
    paired = identified["transported_mean_absolute_error"] - identified["mean_absolute_error"]
    assert row["mean_improvement"] == pytest.approx(float(paired.mean()))


def test_local_sizes_are_ascending_and_start_at_one() -> None:
    assert LOCAL_SIZES[0] == 1
    assert list(LOCAL_SIZES) == sorted(LOCAL_SIZES)
    assert MINIMUM_EVALUATION_PARTICIPANTS >= 3
