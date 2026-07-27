"""Recoverable protocol differences are candidate explanations for heterogeneity."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bigp3_als.protocol import (
    _holm,
    explains_heterogeneity,
    joint_moderator_fit,
    leave_one_cohort_out,
    protocol_covariates,
    protocol_report,
)


def _trials() -> pd.DataFrame:
    return pd.DataFrame({
        "study": ["StudyA"] * 4 + ["StudyB"] * 4,
        "condition": ["CB", "CB", "RC", "RC", "Dry", "Dry", "Dry", "Wet"],
        "eligible": [True] * 8,
    })


def _records() -> pd.DataFrame:
    return pd.DataFrame({
        "study": ["StudyA"] * 3 + ["StudyB"] * 3,
        "n": [20, 20, 20, 10, 10, 10],
        "correct": [20, 18, 16, 5, 7, 9],
    })


def test_protocol_covariates_counts_conditions_per_study() -> None:
    table = protocol_covariates(_trials(), _records()).set_index("study")

    assert table.loc["StudyA", "n_conditions"] == 2
    assert table.loc["StudyB", "n_conditions"] == 2


def test_ceiling_fraction_is_reported() -> None:
    table = protocol_covariates(_trials(), _records()).set_index("study")

    assert table.loc["StudyA", "fraction_at_ceiling"] == pytest.approx(1 / 3)
    assert table.loc["StudyB", "fraction_at_ceiling"] == pytest.approx(0.0)


def test_explains_heterogeneity_returns_one_row_per_covariate() -> None:
    covariates = pd.DataFrame({
        "study": ["A", "B", "C", "D"],
        "mean_accuracy": [0.6, 0.7, 0.8, 0.9],
        "accuracy_sd": [0.3, 0.2, 0.1, 0.05],
        "fraction_at_ceiling": [0.0, 0.1, 0.4, 0.8],
        "median_selections_per_record": [10, 12, 14, 16],
        "n_conditions": [1, 2, 2, 3],
    })
    calibration = pd.DataFrame({
        "held_out_study": ["A", "B", "C", "D"], "slope": [0.5, 0.9, 1.4, 2.0]
    })

    result = explains_heterogeneity(covariates, calibration)

    assert set(result["covariate"]) >= {"mean_accuracy", "accuracy_sd", "fraction_at_ceiling"}
    assert result["spearman_rho"].abs().max() <= 1.0


def _cohort_covariates(n_studies: int) -> pd.DataFrame:
    """One row per cohort, with a moderator that varies and one that does not."""
    return pd.DataFrame({
        "study": [f"Study{index:02d}" for index in range(n_studies)],
        "mean_accuracy": np.linspace(0.55, 0.95, n_studies),
        "accuracy_sd": np.linspace(0.30, 0.05, n_studies),
        "fraction_at_ceiling": np.linspace(0.0, 0.8, n_studies),
        "median_selections_per_record": np.arange(10, 10 + n_studies),
        "n_conditions": [1 + index % 3 for index in range(n_studies)],
    })


def _cohort_calibration(n_studies: int, slope: np.ndarray, slope_se: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({
        "held_out_study": [f"Study{index:02d}" for index in range(n_studies)],
        "slope": slope,
        "slope_se": slope_se,
        "se_method": ["cluster"] * n_studies,
    })


def test_stacked_standard_error_blocks_are_not_counted_as_extra_cohorts() -> None:
    """The frozen per-cohort file stacks three specifications, so 18 cohorts arrive as 54 rows.

    Taking it whole would triple every cohort, which leaves a rank correlation's coefficient
    untouched and shrinks its p value towards zero on evidence that does not exist.
    """
    n_studies = 8
    covariates = _cohort_covariates(n_studies)
    cluster = _cohort_calibration(
        n_studies,
        np.linspace(0.5, 2.0, n_studies),
        np.full(n_studies, 0.2),
    )
    other = cluster.copy()
    other["slope"] = np.linspace(2.0, 0.5, n_studies)  # the opposite ordering, to be sure it is unused
    other["se_method"] = "model"
    third = other.copy()
    third["se_method"] = "quasibinomial"
    stacked = pd.concat([cluster, other, third], ignore_index=True)

    from_stacked = explains_heterogeneity(covariates, stacked)
    from_cluster = explains_heterogeneity(covariates, cluster)

    assert (from_stacked["n_studies"] == n_studies).all()
    pd.testing.assert_frame_equal(from_stacked, from_cluster)


def test_a_cohort_repeated_within_one_specification_is_refused() -> None:
    covariates = _cohort_covariates(4)
    calibration = _cohort_calibration(4, np.linspace(0.5, 2.0, 4), np.full(4, 0.2))
    duplicated = pd.concat([calibration, calibration.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="one row per cohort"):
        explains_heterogeneity(covariates, duplicated)


def test_meta_regression_recovers_a_moderator_the_slopes_follow_exactly() -> None:
    """An exactly fitting moderator is reported without a p value rather than with a perfect one.

    Its residuals come back as floating-point dust rather than zero, and a Knapp and Hartung scale
    built from dust would return a standard error near 1e-15 and a p value of zero.
    """
    n_studies = 8
    covariates = _cohort_covariates(n_studies)
    moderator = covariates["median_selections_per_record"].to_numpy(dtype=float)
    calibration = _cohort_calibration(
        n_studies, 0.5 + 0.4 * moderator, np.full(n_studies, 0.1)
    )

    row = (
        explains_heterogeneity(covariates, calibration)
        .set_index("covariate")
        .loc["median_selections_per_record"]
    )

    assert row["coefficient_per_sd"] == pytest.approx(0.4 * moderator.std(ddof=1))
    assert row["between_cohort_variance_explained"] == pytest.approx(1.0)
    assert row["tau_squared"] == pytest.approx(0.0, abs=1e-12)
    assert np.isnan(row["meta_p_value"])
    assert np.isnan(row["coefficient_se"])


def test_two_descriptors_that_agree_exactly_are_refused_rather_than_inverted() -> None:
    n_studies = 8
    covariates = _cohort_covariates(n_studies)
    covariates["accuracy_sd"] = covariates["mean_accuracy"] * 2.0
    rng = np.random.default_rng(2)
    calibration = _cohort_calibration(
        n_studies, 1.0 + rng.normal(0, 0.4, n_studies), np.full(n_studies, 0.2)
    )

    fit = joint_moderator_fit(covariates, calibration, ("mean_accuracy", "accuracy_sd"))

    assert np.isnan(fit["joint_p_value"])
    assert fit["n_studies"] == n_studies


def test_meta_regression_downweights_an_imprecisely_estimated_cohort() -> None:
    """A cohort measured in 16 records must not move the fit as one measured in 89 does."""
    n_studies = 9
    covariates = _cohort_covariates(n_studies)
    moderator = covariates["median_selections_per_record"].to_numpy(dtype=float)
    slope = 0.5 + 0.4 * moderator
    slope[-1] = 20.0  # a wild cohort, and the standard error below says it is barely measured
    standard_error = np.full(n_studies, 0.05)
    standard_error[-1] = 8.0
    calibration = _cohort_calibration(n_studies, slope, standard_error)

    row = (
        explains_heterogeneity(covariates, calibration)
        .set_index("covariate")
        .loc["median_selections_per_record"]
    )
    unweighted = np.polyfit(moderator, slope, 1)[0] * moderator.std(ddof=1)

    assert row["coefficient_per_sd"] == pytest.approx(0.4 * moderator.std(ddof=1), rel=0.02)
    assert abs(unweighted - row["coefficient_per_sd"]) > 1.0


def test_a_cohort_without_a_usable_standard_error_is_named_not_silently_dropped() -> None:
    n_studies = 8
    covariates = _cohort_covariates(n_studies)
    standard_error = np.full(n_studies, 0.2)
    standard_error[2] = np.nan
    standard_error[5] = 0.0
    calibration = _cohort_calibration(n_studies, np.linspace(0.5, 2.0, n_studies), standard_error)

    row = explains_heterogeneity(covariates, calibration).set_index("covariate").loc["mean_accuracy"]

    assert row["n_studies"] == n_studies
    assert row["n_studies_meta"] == n_studies - 2
    assert row["n_dropped"] == 2
    assert set(str(row["dropped_labels"]).split(",")) == {"Study02", "Study05"}


def test_holm_multiplies_the_smallest_p_value_by_the_number_of_tests() -> None:
    adjusted = _holm(np.array([0.01, 0.02, 0.30, 0.60, 0.90]))

    assert adjusted[0] == pytest.approx(0.05)
    assert adjusted[1] == pytest.approx(0.08)
    assert np.all(np.diff(adjusted) >= 0)
    assert np.all(adjusted <= 1.0)


def test_holm_counts_only_the_tests_that_were_performed() -> None:
    adjusted = _holm(np.array([0.01, np.nan, 0.30]))

    assert adjusted[0] == pytest.approx(0.02)
    assert np.isnan(adjusted[1])


def test_report_carries_the_unmoderated_heterogeneity_and_what_it_dropped() -> None:
    n_studies = 8
    covariates = _cohort_covariates(n_studies)
    calibration = _cohort_calibration(
        n_studies, np.linspace(0.5, 2.0, n_studies), np.full(n_studies, 0.2)
    )

    report = protocol_report(covariates, calibration)

    assert report["baseline_heterogeneity"]["n_studies"] == n_studies
    assert report["baseline_heterogeneity"]["n_dropped"] == 0.0
    assert report["baseline_heterogeneity"]["dropped_labels"] == []
    assert len(report["descriptors"]) == 5
    assert len(report["joint_fits"]) == 2
    assert len(report["leave_one_cohort_out"]) == 5


def test_the_joint_test_of_one_moderator_agrees_with_its_own_t_test() -> None:
    n_studies = 10
    covariates = _cohort_covariates(n_studies)
    rng = np.random.default_rng(0)
    calibration = _cohort_calibration(
        n_studies,
        0.5 + 0.1 * covariates["median_selections_per_record"].to_numpy(float) + rng.normal(0, 0.3, n_studies),
        np.full(n_studies, 0.2),
    )

    single = joint_moderator_fit(covariates, calibration, ("median_selections_per_record",))
    row = (
        explains_heterogeneity(covariates, calibration)
        .set_index("covariate")
        .loc["median_selections_per_record"]
    )

    assert single["joint_p_value"] == pytest.approx(row["meta_p_value"])
    assert single["f_statistic"] == pytest.approx(row["t_statistic"] ** 2)


def test_a_joint_fit_too_large_for_the_cohorts_returns_nothing_rather_than_a_number() -> None:
    n_studies = 6
    covariates = _cohort_covariates(n_studies)
    calibration = _cohort_calibration(
        n_studies, np.linspace(0.5, 2.0, n_studies), np.full(n_studies, 0.2)
    )

    fit = joint_moderator_fit(
        covariates,
        calibration,
        ("mean_accuracy", "accuracy_sd", "fraction_at_ceiling", "median_selections_per_record",
         "n_conditions"),
    )

    assert np.isnan(fit["joint_p_value"])
    assert np.isnan(fit["between_cohort_variance_explained"])


def test_leave_one_cohort_out_brackets_the_full_sample_result() -> None:
    n_studies = 8
    covariates = _cohort_covariates(n_studies)
    rng = np.random.default_rng(1)
    calibration = _cohort_calibration(
        n_studies,
        0.5 + 0.05 * covariates["median_selections_per_record"].to_numpy(float) + rng.normal(0, 0.4, n_studies),
        np.full(n_studies, 0.25),
    )

    full = explains_heterogeneity(covariates, calibration).set_index("covariate")
    influence = leave_one_cohort_out(covariates, calibration).set_index("covariate")

    assert (influence["n_refits"] == n_studies).all()
    for name in influence.index:
        assert influence.loc[name, "meta_p_value_min"] <= influence.loc[name, "meta_p_value_max"]
        assert influence.loc[name, "variance_explained_max"] >= 0.0
        assert influence.loc[name, "withheld_at_min_meta_p"] in set(covariates["study"])
    # A refit on 7 cohorts is not required to bracket the 8-cohort fit, but the recorded extremes
    # must be reachable: the full-sample p value sits inside the range for at least one descriptor.
    assert any(
        influence.loc[name, "meta_p_value_min"]
        <= full.loc[name, "meta_p_value"]
        <= influence.loc[name, "meta_p_value_max"]
        for name in influence.index
    )
