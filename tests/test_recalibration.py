"""Tests for the local-recalibration learning curve."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from bigp3_als.recalibration import (
    LOCAL_SIZES,
    MINIMUM_EVALUATION_PARTICIPANTS,
    common_cohorts,
    instability_by_smaller_side,
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


# recalibration_summary always reads the calibration columns, even from a block where none of the
# fits were identified, so a fixture built only to exercise the MAE columns still needs them present
# (as NaN / not identified) rather than omitted.
_NO_CALIBRATION = {
    "calibration_identified": False,
    "transported_calibration_intercept": np.nan,
    "transported_calibration_slope": np.nan,
    "recalibrated_calibration_intercept": np.nan,
    "recalibrated_calibration_slope": np.nan,
}


def test_cohort_level_mean_averages_within_cohort_before_pooling_across_cohorts() -> None:
    # StudyA contributes a single identified draw at improvement 10; StudyB contributes nine
    # identified draws at improvement 0. A flat, draw-level mean is dominated by StudyB's nine rows
    # (1.0). Averaging within cohort first, then pooling the two cohort means, weights the cohorts
    # equally (5.0). The two orders must give different numbers, and each must land in its own column.
    rows = [
        {
            "held_out_study": "StudyA",
            "n_local_participants": 5,
            "n_local_selections": 100,
            "draw": 0,
            "method": "intercept_only",
            "identified": True,
            "mean_absolute_error": 0.0,
            "transported_mean_absolute_error": 10.0,
            **_NO_CALIBRATION,
        }
    ]
    rows += [
        {
            "held_out_study": "StudyB",
            "n_local_participants": 5,
            "n_local_selections": 100,
            "draw": draw,
            "method": "intercept_only",
            "identified": True,
            "mean_absolute_error": 0.0,
            "transported_mean_absolute_error": 0.0,
            **_NO_CALIBRATION,
        }
        for draw in range(9)
    ]
    draws = pd.DataFrame(rows)

    summary = recalibration_summary(draws)
    row = summary.set_index(["method", "n_local_participants"]).loc[("intercept_only", 5)]

    assert row["mean_improvement"] == pytest.approx(1.0)
    assert row["cohort_mean_improvement"] == pytest.approx(5.0)
    assert row["n_cohorts_contributing"] == 2


def test_common_cohorts_are_exactly_those_present_at_every_size() -> None:
    # StudyA and StudyB both reach size 4; StudyC is only large enough to appear at size 1.
    draws = pd.DataFrame(
        {
            "held_out_study": ["StudyA", "StudyA", "StudyB", "StudyB", "StudyC"],
            "n_local_participants": [1, 4, 1, 4, 1],
            "n_local_selections": [10, 10, 10, 10, 10],
            "draw": [0, 0, 0, 0, 0],
            "method": "intercept_only",
            "identified": True,
            "mean_absolute_error": 0.05,
            "transported_mean_absolute_error": 0.10,
            **{key: value for key, value in _NO_CALIBRATION.items()},
        }
    )

    assert common_cohorts(draws) == {"StudyA", "StudyB"}

    full = recalibration_summary(draws)
    restricted = recalibration_summary(draws, cohorts=common_cohorts(draws))

    # At size 1 all three cohorts are present, so restricting to the common set must drop StudyC.
    assert full.set_index("n_local_participants").loc[1, "n_cohorts"] == 3
    assert restricted.set_index("n_local_participants").loc[1, "n_cohorts"] == 2


def test_perfectly_transported_probabilities_calibrate_near_intercept_zero_slope_one() -> None:
    # offset=0.0 means the transported probability equals the true probability used to generate
    # outcomes, so its own calibration fit on the evaluation set should recover intercept near 0 and
    # slope near 1, up to finite-sample noise.
    predictions = _cohort(18, offset=0.0, seed=21)

    draws = recalibration_draws(predictions, sizes=(4,), draws=100, seed=31)
    summary = recalibration_summary(draws)
    row = summary.set_index(["method", "n_local_participants"]).loc[("intercept_only", 4)]

    assert row["transported_calibration_intercept_mean"] == pytest.approx(0.0, abs=0.3)
    assert row["transported_calibration_slope_mean"] == pytest.approx(1.0, abs=0.5)


def test_recalibrated_intercept_moves_closer_to_zero_than_the_transported_intercept() -> None:
    # A known +1.2 log-odds offset (same fixture as the pure-offset MAE test) should leave the
    # transported intercept far from 0, and the recalibrated intercept, refit on local data, closer.
    predictions = _cohort(18, offset=1.2, seed=22)

    draws = recalibration_draws(predictions, sizes=(6,), draws=100, seed=32)
    summary = recalibration_summary(draws)
    row = summary.set_index(["method", "n_local_participants"]).loc[("intercept_only", 6)]

    assert abs(row["recalibrated_calibration_intercept_mean"]) < abs(row["transported_calibration_intercept_mean"])
    assert row["cohort_mean_intercept_improvement"] > 0


def _mae_fixture(cohort_values: dict[str, float], n_local_participants: int = 5) -> pd.DataFrame:
    """One identified draw per cohort. Holding mean_absolute_error at 0 makes the paired improvement
    (transported minus recalibrated) equal to the given value directly, so a fixture can specify the
    per-cohort improvement to be pooled without going through a real local refit."""
    return pd.DataFrame(
        [
            {
                "held_out_study": cohort,
                "n_local_participants": n_local_participants,
                "n_local_selections": 100,
                "draw": 0,
                "method": "intercept_only",
                "identified": True,
                "mean_absolute_error": 0.0,
                "transported_mean_absolute_error": value,
                **_NO_CALIBRATION,
            }
            for cohort, value in cohort_values.items()
        ]
    )


def test_minimum_detectable_effect_scales_with_cohort_spread_and_cohort_count() -> None:
    # Scaling every cohort's improvement by a constant factor scales its between-cohort SD by the
    # same factor; the cohort count and degrees of freedom are unchanged, so the minimum detectable
    # effect (t-critical times standard error) must scale by exactly the same factor.
    modest = _mae_fixture({"StudyA": 1.0, "StudyB": 2.0, "StudyC": 3.0})
    scaled = _mae_fixture({"StudyA": 3.0, "StudyB": 6.0, "StudyC": 9.0})

    modest_row = recalibration_summary(modest).iloc[0]
    scaled_row = recalibration_summary(scaled).iloc[0]

    assert scaled_row["mae_minimum_detectable_effect"] == pytest.approx(
        3.0 * modest_row["mae_minimum_detectable_effect"]
    )

    # Repeating the same three values to reach six cohorts adds degrees of freedom and averages the
    # standard error over more cohorts, so the bound must shrink even though the underlying spread of
    # any one value is unchanged.
    doubled = _mae_fixture(
        {"StudyA": 1.0, "StudyB": 2.0, "StudyC": 3.0, "StudyD": 1.0, "StudyE": 2.0, "StudyF": 3.0}
    )
    doubled_row = recalibration_summary(doubled).iloc[0]

    assert doubled_row["mae_minimum_detectable_effect"] < modest_row["mae_minimum_detectable_effect"]


def test_an_improvement_exactly_at_the_minimum_detectable_effect_gives_a_ci_touching_zero() -> None:
    # The between-cohort SD, and so the minimum detectable effect, is unchanged by adding the same
    # constant to every cohort's value. Shift an arbitrary fixture so its mean lands exactly on its
    # own (unchanged) minimum detectable effect; the resulting CI's lower bound must be exactly zero,
    # since ci_low = mean - minimum_detectable_effect by construction.
    baseline = _mae_fixture({"StudyA": 1.0, "StudyB": 2.0, "StudyC": 3.0, "StudyD": 10.0})
    baseline_row = recalibration_summary(baseline).iloc[0]
    shift = baseline_row["mae_minimum_detectable_effect"] - baseline_row["cohort_mean_improvement"]

    shifted = _mae_fixture(
        {"StudyA": 1.0 + shift, "StudyB": 2.0 + shift, "StudyC": 3.0 + shift, "StudyD": 10.0 + shift}
    )
    shifted_row = recalibration_summary(shifted).iloc[0]

    assert shifted_row["mae_minimum_detectable_effect"] == pytest.approx(
        baseline_row["mae_minimum_detectable_effect"]
    )
    assert shifted_row["cohort_mean_improvement"] == pytest.approx(shifted_row["mae_minimum_detectable_effect"])
    assert shifted_row["cohort_improvement_ci_low"] == pytest.approx(0.0, abs=1e-9)


def test_minimum_detectable_effect_80_exceeds_the_50_percent_column_for_mae_intercept_and_slope() -> None:
    # 80% power needs a larger true effect than 50% power to detect reliably, for every one of the
    # three quantities the module reports a minimum detectable effect for.
    mae_fixture = _mae_fixture({"StudyA": 1.0, "StudyB": 2.0, "StudyC": 3.0, "StudyD": 10.0})
    mae_row = recalibration_summary(mae_fixture).iloc[0]
    assert mae_row["mae_minimum_detectable_effect_80"] > mae_row["mae_minimum_detectable_effect"]

    calibration_fixture = _calibration_fixture(
        [
            {"held_out_study": "StudyA", "recalibrated_calibration_intercept": 0.1, "recalibrated_calibration_slope": 0.9},
            {"held_out_study": "StudyB", "recalibrated_calibration_intercept": -0.2, "recalibrated_calibration_slope": 1.2},
            {"held_out_study": "StudyC", "recalibrated_calibration_intercept": 0.3, "recalibrated_calibration_slope": 0.8},
            {"held_out_study": "StudyD", "recalibrated_calibration_intercept": -0.1, "recalibrated_calibration_slope": 1.1},
        ]
    )
    calibration_row = recalibration_summary(calibration_fixture).iloc[0]
    assert (
        calibration_row["intercept_minimum_detectable_effect_80"]
        > calibration_row["intercept_minimum_detectable_effect"]
    )
    assert (
        calibration_row["slope_minimum_detectable_effect_80"] > calibration_row["slope_minimum_detectable_effect"]
    )


def test_minimum_detectable_effect_80_ratio_matches_the_t_based_conversion_factor() -> None:
    # The 80%-power bound is derived by scaling the 50%-power bound by
    # (t(0.975, df) + t(0.80, df)) / t(0.975, df); the ratio of the two committed columns must equal
    # that factor exactly, at the degrees of freedom the fixture's own cohort count implies.
    fixture = _mae_fixture(
        {"StudyA": 1.0, "StudyB": 2.0, "StudyC": 3.0, "StudyD": 10.0, "StudyE": 4.0, "StudyF": 6.0}
    )
    row = recalibration_summary(fixture).iloc[0]
    df = int(row["n_cohorts_contributing"]) - 1
    expected_factor = (stats.t.ppf(0.975, df) + stats.t.ppf(0.80, df)) / stats.t.ppf(0.975, df)

    ratio = row["mae_minimum_detectable_effect_80"] / row["mae_minimum_detectable_effect"]
    assert ratio == pytest.approx(expected_factor)

    # The df=5 case named in the review: six cohorts contributing gives the 1.3577 conversion factor.
    assert expected_factor == pytest.approx(1.3577, abs=0.0005)


def test_minimum_detectable_effect_80_is_nan_when_the_50_percent_column_is_nan() -> None:
    # A single cohort has no between-cohort SD, so both the 50% and 80% bounds are undefined.
    single_cohort = _mae_fixture({"StudyA": 1.0})
    row = recalibration_summary(single_cohort).iloc[0]

    assert np.isnan(row["mae_minimum_detectable_effect"])
    assert np.isnan(row["mae_minimum_detectable_effect_80"])


def _calibration_fixture(rows: list[dict]) -> pd.DataFrame:
    """One identified, calibration_identified draw per given row. MAE columns are held at 0 (unused
    by the assertions these fixtures support); only the calibration columns given per row vary."""
    return pd.DataFrame(
        [
            {
                "n_local_participants": 5,
                "n_local_selections": 100,
                "draw": index,
                "method": "intercept_and_slope",
                "identified": True,
                "mean_absolute_error": 0.0,
                "transported_mean_absolute_error": 0.0,
                "calibration_identified": True,
                "transported_calibration_intercept": 0.0,
                "transported_calibration_slope": 1.0,
                **row,
            }
            for index, row in enumerate(rows)
        ]
    )


def test_recalibrated_slope_median_is_robust_to_a_heavy_tailed_mean() -> None:
    # Three ordinary slopes near 1 and one extreme outlier at -10000, the same order of magnitude of
    # pathology seen in the real intercept_and_slope draws (a near-zero local slope makes the
    # recalibrated probability nearly constant, which makes the downstream calibration fit
    # ill-conditioned). The mean is dragged far from 1 by the single outlier; the median should not be.
    rows = _calibration_fixture(
        [
            {"held_out_study": "StudyA", "recalibrated_calibration_intercept": 0.1, "recalibrated_calibration_slope": 0.9},
            {"held_out_study": "StudyA", "recalibrated_calibration_intercept": 0.2, "recalibrated_calibration_slope": 1.1},
            {"held_out_study": "StudyB", "recalibrated_calibration_intercept": 0.0, "recalibrated_calibration_slope": 1.0},
            {"held_out_study": "StudyB", "recalibrated_calibration_intercept": 20000.0, "recalibrated_calibration_slope": -10000.0},
        ]
    )

    summary = recalibration_summary(rows)
    row = summary.iloc[0]

    assert row["recalibrated_calibration_slope_median"] == pytest.approx(0.95, abs=0.2)
    assert row["recalibrated_calibration_slope_mean"] < -2000


def test_negative_and_out_of_range_slope_fractions_count_the_right_draws() -> None:
    # Four draws: two sane (0.9, 1.1), one negative (-0.5, an inverted mapping), one positive but
    # outside the stated [0, 3] sane range (5.0).
    rows = _calibration_fixture(
        [
            {"held_out_study": "StudyA", "recalibrated_calibration_intercept": 0.0, "recalibrated_calibration_slope": 0.9},
            {"held_out_study": "StudyA", "recalibrated_calibration_intercept": 0.0, "recalibrated_calibration_slope": 1.1},
            {"held_out_study": "StudyB", "recalibrated_calibration_intercept": 0.0, "recalibrated_calibration_slope": -0.5},
            {"held_out_study": "StudyB", "recalibrated_calibration_intercept": 0.0, "recalibrated_calibration_slope": 5.0},
        ]
    )

    summary = recalibration_summary(rows)
    row = summary.iloc[0]

    assert row["recalibrated_slope_negative_fraction"] == pytest.approx(0.25)
    assert row["recalibrated_slope_out_of_range_fraction"] == pytest.approx(0.5)


def test_smaller_side_grouping_is_the_union_of_local_smaller_and_evaluation_smaller_with_no_double_counting() -> None:
    # smaller_side=4 must collect exactly the rows where the local side is 4 and no larger than the
    # evaluation side, PLUS the rows where the evaluation side is 4 and strictly smaller than the
    # local side (avoiding double-counting a tie, where the two sides are equal, at 5). No draw may
    # be counted twice or dropped: the sizes across every smaller_side group must sum to the input.
    rows = pd.DataFrame(
        [
            # local=4 is the smaller (or tied) side -> smaller_side 4, twice.
            {"n_local_participants": 4, "n_evaluation_participants": 10, "method": "intercept_and_slope",
             "calibration_identified": True, "recalibrated_calibration_slope": 0.9},
            {"n_local_participants": 4, "n_evaluation_participants": 10, "method": "intercept_and_slope",
             "calibration_identified": True, "recalibrated_calibration_slope": -0.1},
            # evaluation=4 is the strictly smaller side -> also smaller_side 4.
            {"n_local_participants": 12, "n_evaluation_participants": 4, "method": "intercept_and_slope",
             "calibration_identified": True, "recalibrated_calibration_slope": 1.2},
            # a tie: both sides equal 5 -> smaller_side 5, counted once, not twice.
            {"n_local_participants": 5, "n_evaluation_participants": 5, "method": "intercept_and_slope",
             "calibration_identified": True, "recalibrated_calibration_slope": 0.7},
            # evaluation=3 is the smaller side -> smaller_side 3, unrelated to the size-4 group.
            {"n_local_participants": 8, "n_evaluation_participants": 3, "method": "intercept_and_slope",
             "calibration_identified": True, "recalibrated_calibration_slope": -2.0},
        ]
    )

    result = instability_by_smaller_side(rows)
    counts = dict(zip(result["smaller_side"], result["n_draws"]))

    assert counts == {3: 1, 4: 3, 5: 1}
    assert result["n_draws"].sum() == len(rows)
