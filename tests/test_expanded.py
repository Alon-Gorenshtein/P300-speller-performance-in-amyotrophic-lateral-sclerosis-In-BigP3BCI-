"""Tests for the analyses that the all-source-study design makes possible."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from bigp3_als.expanded import (
    ALS_STUDIES,
    als_leave_one_cohort_out,
    als_meta_regression,
    als_permutation_test,
    als_random_effects_meta_regression,
    label_cohort_type,
    pool_held_out_metrics,
    random_effects_pooling,
    study_inventory,
    transfer_to_als,
)
from bigp3_als.heterogeneity import random_effects


def _records() -> pd.DataFrame:
    """Six studies, four of them the documented ALS cohorts, three participants each."""
    rows = []
    studies = [*ALS_STUDIES, "StudyA", "StudyG"]
    for study in studies:
        for participant_index in range(3):
            score = 0.60 + 0.10 * participant_index
            accuracy = 0.55 + 0.15 * participant_index
            rows.append(
                {
                    "study": study,
                    "study_participant_id": f"{study}:P_{participant_index:02d}",
                    "session_id": "SE001",
                    "condition": "CB",
                    "n": 20,
                    "correct": round(accuracy * 20),
                    "calibration_auc": score,
                }
            )
    return pd.DataFrame(rows)


def _fit_predictions(development: pd.DataFrame, validation: pd.DataFrame, features: tuple[str, ...]):
    """Stand-in for the primary model: a straight line fit on development records."""
    x = development[list(features)[0]].to_numpy(dtype=float)
    y = (development["correct"] / development["n"]).to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    return np.clip(intercept + slope * validation[list(features)[0]].to_numpy(dtype=float), 0.0, 1.0)


def test_label_cohort_type_flags_only_the_documented_als_studies() -> None:
    labelled = label_cohort_type(_records())

    assert set(labelled.loc[labelled["als_cohort"], "study"]) == set(ALS_STUDIES)
    assert set(labelled.loc[~labelled["als_cohort"], "study"]) == {"StudyA", "StudyG"}


def test_label_cohort_type_does_not_mutate_the_input() -> None:
    records = _records()
    label_cohort_type(records)

    assert "als_cohort" not in records.columns


def test_prediction_interval_is_always_wider_than_the_confidence_interval() -> None:
    summary = random_effects_pooling(pd.Series([0.11, 0.08, 0.076, 0.13, 0.10]))

    confidence_width = summary["confidence_interval_high"] - summary["confidence_interval_low"]
    prediction_width = summary["prediction_interval_high"] - summary["prediction_interval_low"]
    assert prediction_width > confidence_width


def test_pooling_reproduces_the_four_study_hand_calculation() -> None:
    # The four held-out MAEs of the original design, recomputed by the review panel.
    summary = random_effects_pooling(pd.Series([0.1136, 0.0848, 0.0760, 0.1289]))

    assert summary["mean"] == pytest.approx(0.100825, abs=1e-6)
    assert summary["between_study_sd"] == pytest.approx(0.0247, abs=5e-4)
    # The panel reported a new-study prediction interval of roughly 0.013 to 0.189.
    assert summary["prediction_interval_low"] == pytest.approx(0.013, abs=0.01)
    assert summary["prediction_interval_high"] == pytest.approx(0.189, abs=0.01)


def test_pooling_refuses_a_single_study() -> None:
    with pytest.raises(ValueError, match="at least two studies"):
        random_effects_pooling(pd.Series([0.1]))


def test_pool_held_out_metrics_ignores_the_pooled_row() -> None:
    metrics = pd.DataFrame(
        {
            "held_out_study": ["StudyA", "StudyB", "StudyF", "Pooled held-out predictions"],
            "session_mean_absolute_error": [0.10, 0.12, 0.08, 0.099],
        }
    )

    pooled = pool_held_out_metrics(metrics, ("session_mean_absolute_error",))

    assert pooled["n_studies"].iloc[0] == 3


def test_log_scale_prediction_interval_is_never_negative_for_a_right_skewed_error_metric() -> None:
    """MAE cannot be negative. A log-scale interval must respect that even when the raw-scale
    interval would not."""
    # Chosen so the raw-scale (identity) interval crosses zero, reproducing the reviewer's finding.
    # (Last value lowered from the task brief's 0.043 to 0.020: at 0.043 the raw-scale
    # prediction_interval_low computes to +0.000255, which does not actually reproduce the
    # zero-crossing defect this test exists to demonstrate.)
    values = pd.Series([0.056, 0.058, 0.063, 0.066, 0.067, 0.084, 0.101, 0.108, 0.121, 0.124,
                        0.126, 0.153, 0.058, 0.059, 0.172, 0.173, 0.186, 0.020])
    raw = random_effects_pooling(values, label="mae")
    assert raw["prediction_interval_low"] < 0.0  # reproduces the defect on the raw scale

    logged = random_effects_pooling(values, label="mae", transform="log")
    assert logged["prediction_interval_low"] > 0.0
    assert logged["prediction_interval_high"] > logged["prediction_interval_low"]
    # The point estimate should be recognisably the same quantity, not a different mean.
    assert logged["mean"] == pytest.approx(raw["mean"], rel=0.15)


def test_log_scale_transform_rejects_a_series_with_a_non_positive_value() -> None:
    with pytest.raises(ValueError, match="positive"):
        random_effects_pooling(pd.Series([0.05, -0.01, 0.03]), transform="log")


def test_log_scale_between_study_sd_is_reported_on_the_log_scale() -> None:
    """The mean and the interval under transform="log" are reported on the original scale, but the
    between-study standard deviation must stay on the log scale that produced them - otherwise a
    summary sentence pairs a log-derived mean with a raw-scale spread on the same line, mixing two
    scales without saying so. This should differ from the raw-scale SD on the same input, not
    coincide with it."""
    values = pd.Series([0.056, 0.058, 0.063, 0.066, 0.067, 0.084, 0.101, 0.108, 0.121, 0.124,
                        0.126, 0.153, 0.058, 0.059, 0.172, 0.173, 0.186, 0.020])

    identity = random_effects_pooling(values, transform="identity")
    logged = random_effects_pooling(values, transform="log")

    assert logged["between_study_sd"] == pytest.approx(float(np.log(values).std(ddof=1)))
    assert logged["between_study_sd"] != pytest.approx(identity["between_study_sd"])


def test_pool_held_out_metrics_applies_log_scale_only_to_named_columns() -> None:
    metrics = pd.DataFrame({
        "held_out_study": ["A", "B", "C", "D"],
        "session_mean_absolute_error": [0.09, 0.10, 0.12, 0.08],
        "character_brier_skill_score": [-0.05, 0.10, 0.20, -0.02],
    })
    pooled = pool_held_out_metrics(
        metrics, ("session_mean_absolute_error", "character_brier_skill_score"),
        log_scale_columns=frozenset({"session_mean_absolute_error"}),
    )
    mae_row = pooled.loc[pooled["quantity"] == "session_mean_absolute_error"].iloc[0]
    skill_row = pooled.loc[pooled["quantity"] == "character_brier_skill_score"].iloc[0]
    assert mae_row["prediction_interval_low"] > 0.0
    assert skill_row["prediction_interval_low"] < 0.0  # skill is legitimately negative; must be untouched


def test_transfer_to_als_never_trains_on_an_als_cohort() -> None:
    seen: list[set[str]] = []

    def spy(development, validation, features):
        seen.append(set(development["study"]))
        return _fit_predictions(development, validation, features)

    result = transfer_to_als(_records(), spy)

    assert len(result) == 4
    for development_studies in seen:
        assert development_studies.isdisjoint(ALS_STUDIES)
    assert set(result["held_out_study"]) == set(ALS_STUDIES)


def test_transfer_to_als_reports_one_row_per_als_cohort_present() -> None:
    records = _records()
    records = records.loc[records["study"] != "StudyN"]

    result = transfer_to_als(records, _fit_predictions)

    assert set(result["held_out_study"]) == {"StudyB", "StudyF", "StudyL"}


def _cohort_slopes() -> pd.DataFrame:
    """Seven cohorts, four of them the documented ALS cohorts, with a planted 0.5 difference."""
    return pd.DataFrame(
        {
            "held_out_study": ["StudyB", "StudyF", "StudyL", "StudyN", "StudyA", "StudyG", "StudyM"],
            "slope": [1.6, 1.5, 1.7, 1.2, 1.0, 0.9, 1.1],
            "slope_se": [0.2] * 7,
        }
    )


def test_als_meta_regression_uses_studies_not_records_as_the_unit() -> None:
    result = als_meta_regression(_cohort_slopes(), ALS_STUDIES)

    assert result["n_als_studies"] == 4
    assert result["n_other_studies"] == 3
    assert result["difference"] == pytest.approx(1.5 - 1.0, abs=0.01)
    assert result["p_value"] > 0.001  # seven studies cannot support a tiny p value


def test_als_meta_regression_refuses_fewer_than_three_studies_per_group() -> None:
    calibration = pd.DataFrame(
        {"held_out_study": ["StudyB", "StudyA"], "slope": [1.6, 1.0], "slope_se": [0.2, 0.2]}
    )

    with pytest.raises(ValueError, match="at least three"):
        als_meta_regression(calibration, ALS_STUDIES)


def test_als_meta_regression_counts_each_cohort_once_when_the_file_carries_every_se_method() -> None:
    """The frozen file stacks three standard-error specifications, so it holds 3 rows per cohort."""
    stacked = pd.concat(
        [_cohort_slopes().assign(se_method=method) for method in ("cluster", "model", "quasibinomial")],
        ignore_index=True,
    )

    result = als_meta_regression(stacked, ALS_STUDIES)

    assert result["n_als_studies"] == 4
    assert result["n_other_studies"] == 3


def test_als_meta_regression_rejects_repeated_cohorts_it_cannot_disambiguate() -> None:
    doubled = pd.concat([_cohort_slopes(), _cohort_slopes()], ignore_index=True)

    with pytest.raises(ValueError, match="one row per cohort"):
        als_meta_regression(doubled, ALS_STUDIES)


def test_als_meta_regression_rejects_an_unavailable_standard_error_method() -> None:
    stacked = _cohort_slopes().assign(se_method="model")

    with pytest.raises(ValueError, match="cluster"):
        als_meta_regression(stacked, ALS_STUDIES)


def test_welch_p_value_still_agrees_with_scipy_after_the_statistic_was_factored_out() -> None:
    """The t-test is hand-rolled so the permutation can studentise with the identical statistic."""
    calibration = _cohort_slopes()
    result = als_meta_regression(calibration, ALS_STUDIES)
    reference = stats.ttest_ind([1.6, 1.5, 1.7, 1.2], [1.0, 0.9, 1.1], equal_var=False)

    assert result["t_statistic"] == pytest.approx(reference.statistic, rel=1e-12)
    assert result["p_value"] == pytest.approx(reference.pvalue, rel=1e-12)


def test_permutation_test_enumerates_every_assignment_exactly() -> None:
    result = als_permutation_test(_cohort_slopes(), ALS_STUDIES)

    # Seven cohorts, four of them ALS: 35 ways to choose which four carry the label.
    assert result["exact"] is True
    assert result["n_assignments"] == 35
    assert result["p_value"] >= 1 / 35


def test_permutation_test_reproduces_an_independent_enumeration() -> None:
    """Recount the permutation distribution here, from the slopes, without touching the module."""
    calibration = _cohort_slopes()
    slopes = [1.6, 1.5, 1.7, 1.2, 1.0, 0.9, 1.1]

    def welch_t(als: list[float], other: list[float]) -> float:
        return float(stats.ttest_ind(als, other, equal_var=False).statistic)

    observed = welch_t(slopes[:4], slopes[4:])
    counted = 0
    total = 0
    for indices in itertools.combinations(range(7), 4):
        als = [slopes[i] for i in indices]
        other = [slopes[i] for i in range(7) if i not in indices]
        total += 1
        if abs(welch_t(als, other)) >= abs(observed) - 1e-12:
            counted += 1

    result = als_permutation_test(calibration, ALS_STUDIES)

    assert result["n_assignments"] == total
    assert result["p_value"] == pytest.approx(counted / total, rel=1e-12)


def test_permutation_test_sits_at_its_floor_when_the_groups_do_not_overlap() -> None:
    calibration = _cohort_slopes()
    # Push every ALS slope above every other slope, and keep the spreads equal so that no
    # relabelling can produce a larger studentised contrast than the true one.
    calibration.loc[calibration["held_out_study"].isin(ALS_STUDIES), "slope"] = [5.0, 5.1, 5.2, 5.3]
    calibration.loc[~calibration["held_out_study"].isin(ALS_STUDIES), "slope"] = [1.0, 1.1, 1.2]

    result = als_permutation_test(calibration, ALS_STUDIES)

    assert result["p_value"] == pytest.approx(1 / 35, abs=1e-12)


def test_permutation_test_samples_when_enumeration_would_be_too_large() -> None:
    result = als_permutation_test(_cohort_slopes(), ALS_STUDIES, max_enumerated=10)

    assert result["exact"] is False
    assert result["n_assignments"] == 10
    assert result["n_possible_assignments"] == 35
    # The observed labelling is always in the reference set, so the p value cannot be zero.
    assert result["p_value"] > 0


def test_leave_one_cohort_out_keeps_every_cohort_and_marks_the_ones_it_cannot_refit() -> None:
    result = als_leave_one_cohort_out(_cohort_slopes(), ALS_STUDIES)

    assert len(result) == 7
    assert set(result.loc[result["dropped_is_als"], "dropped_study"]) == set(ALS_STUDIES)
    # Four ALS and three other cohorts: dropping one of the three leaves too few to compare.
    assert result.loc[result["dropped_is_als"], "p_value"].notna().all()
    assert result.loc[~result["dropped_is_als"], "p_value"].isna().all()


def test_leave_one_cohort_out_reproduces_the_full_test_on_the_reduced_frame() -> None:
    calibration = _cohort_slopes()
    result = als_leave_one_cohort_out(calibration, ALS_STUDIES)

    row = result.loc[result["dropped_study"] == "StudyN"].iloc[0]
    direct = als_meta_regression(calibration.loc[calibration["held_out_study"] != "StudyN"], ALS_STUDIES)
    assert row["p_value"] == pytest.approx(direct["p_value"], rel=1e-12)


def test_random_effects_meta_regression_matches_the_group_means_when_precision_is_equal() -> None:
    # Equal standard errors give equal weights, so the weighted contrast is the difference in means.
    result = als_random_effects_meta_regression(_cohort_slopes(), ALS_STUDIES)

    assert result["n_studies"] == 7
    assert result["difference"] == pytest.approx(0.5, abs=1e-8)
    assert result["p_value"] > 0.001


def test_random_effects_meta_regression_reproduces_the_pooling_estimator_without_a_moderator() -> None:
    """With cohort type removed the moment estimator must be the one the pooling analysis uses."""
    calibration = _cohort_slopes()
    calibration["slope_se"] = [0.2, 0.5, 0.15, 0.3, 0.25, 0.4, 0.18]

    result = als_random_effects_meta_regression(calibration, ALS_STUDIES)
    pooled = random_effects(calibration["slope"], calibration["slope_se"])

    assert result["tau_squared_without_moderator"] == pytest.approx(pooled["tau_squared"], rel=1e-12)


def test_random_effects_meta_regression_down_weights_an_imprecise_cohort() -> None:
    calibration = _cohort_slopes()
    # Move one ALS cohort far away but measure it badly; it should barely move the contrast.
    calibration.loc[calibration["held_out_study"] == "StudyN", ["slope", "slope_se"]] = [5.0, 20.0]

    result = als_random_effects_meta_regression(calibration, ALS_STUDIES)
    unweighted = als_meta_regression(calibration, ALS_STUDIES)

    assert result["difference"] < 0.7
    assert unweighted["difference"] > 1.0


def test_study_inventory_keeps_studies_that_contribute_no_outcomes() -> None:
    trials = pd.DataFrame(
        {
            "study": ["StudyB"] * 3 + ["StudyC"] * 4,
            "eligible": [True, True, False, False, False, False, False],
            "exclusion_reason": [None, None, "feedback_not_displayed"] + ["fake_feedback_override"] * 4,
        }
    )

    inventory = study_inventory(trials)

    study_c = inventory.loc[inventory["study"] == "StudyC"].iloc[0]
    assert study_c["eligible"] == 0
    assert study_c["contributes_outcomes"] is np.False_ or not study_c["contributes_outcomes"]
    assert study_c["dominant_exclusion_reason"] == "fake_feedback_override"
