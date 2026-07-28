"""Recoverable protocol differences are candidate explanations for heterogeneity."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bigp3_als.protocol import (
    COVARIATES,
    DESCRIPTOR_KIND,
    PROTOCOL_DESCRIPTORS,
    _holm,
    documented_protocol_metadata,
    explains_heterogeneity,
    family_composition_sensitivity,
    joint_moderator_fit,
    leave_one_cohort_out,
    protocol_covariates,
    protocol_report,
    stopping_rule_subgroups,
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


def _timed_trials() -> pd.DataFrame:
    """Two studies, two files each, with the selection timestamps a stopping rule leaves behind.

    StudyA is paced at exactly 20 s in one file and 30 s in the other, so its per-file medians are
    20 and 30 and its study median is 25. StudyB runs at 10 s throughout. The first trial of each
    file has no predecessor and contributes no interval.
    """
    rows = []
    for study, path, start, gap, count in [
        ("StudyA", "a/one.edf", 5.0, 20.0, 4),
        ("StudyA", "a/two.edf", 7.0, 30.0, 4),
        ("StudyB", "b/one.edf", 3.0, 10.0, 4),
        ("StudyB", "b/two.edf", 9.0, 10.0, 4),
    ]:
        for index in range(count):
            rows.append({
                "study": study,
                "relative_path": path,
                "trial_number": index + 1,
                "phase3_time_seconds": start + gap * index,
                "condition": "CB",
                "target": float(1 + index),
                "eligible": True,
            })
    return pd.DataFrame(rows)


def test_inter_selection_interval_is_the_within_file_gap() -> None:
    table = protocol_covariates(_timed_trials(), _records()).set_index("study")

    assert table.loc["StudyA", "median_inter_selection_interval"] == pytest.approx(25.0)
    assert table.loc["StudyB", "median_inter_selection_interval"] == pytest.approx(10.0)


def test_the_gap_between_two_files_is_never_counted_as_a_selection_interval() -> None:
    """Files are separate recordings, so the elapsed time between them is not a pacing measurement.

    Without the within-file grouping, StudyB's second file starting at 9 s after a first file ending
    at 33 s would enter as an interval of -24 s and move the median.
    """
    trials = _timed_trials()
    trials.loc[trials["relative_path"] == "b/two.edf", "phase3_time_seconds"] += 1000.0

    table = protocol_covariates(trials, _records()).set_index("study")

    assert table.loc["StudyB", "median_inter_selection_interval"] == pytest.approx(10.0)


def test_a_constant_interval_survives_timestamp_dust_but_not_a_real_change() -> None:
    """Fixed-repetition pacing arrives as 18.499993 s, not as 18.5, because timestamps come from
    sample indices. An equality test would call every cohort data-dependent."""
    trials = _timed_trials()
    dusty = trials["relative_path"] == "a/one.edf"
    trials.loc[dusty, "phase3_time_seconds"] += np.array([0.0, 1e-13, 0.0, 1e-13])[: dusty.sum()]

    table = protocol_covariates(trials, _records()).set_index("study")
    assert bool(table.loc["StudyA", "constant_within_file_interval"])

    varying = trials.copy()
    changed = varying["relative_path"] == "a/one.edf"
    varying.loc[changed, "phase3_time_seconds"] = [5.0, 25.0, 40.0, 75.0]

    assert not bool(
        protocol_covariates(varying, _records())
        .set_index("study")
        .loc["StudyA", "constant_within_file_interval"]
    )


def test_matrix_proxies_come_from_the_target_index() -> None:
    trials = _timed_trials()
    trials.loc[trials["study"] == "StudyB", "target"] = [1.0, 4.0, 4.0, 9.0, 1.0, 1.0, 2.0, 2.0]

    table = protocol_covariates(trials, _records()).set_index("study")

    assert table.loc["StudyA", "max_target_index"] == 4
    assert table.loc["StudyA", "n_distinct_targets"] == 4
    assert table.loc["StudyB", "max_target_index"] == 9
    assert table.loc["StudyB", "n_distinct_targets"] == 4


def test_documented_protocol_metadata_covers_all_eighteen_contributing_cohorts() -> None:
    metadata = documented_protocol_metadata()
    expected_studies = {
        "StudyA", "StudyB", "StudyD", "StudyE", "StudyF", "StudyG", "StudyH", "StudyI",
        "StudyJ", "StudyK", "StudyL", "StudyM", "StudyN", "StudyO", "StudyQ", "StudyR",
        "StudyS1", "StudyS2",
    }
    assert set(metadata["study"]) == expected_studies


def test_documented_grid_size_matches_the_archive_table() -> None:
    metadata = documented_protocol_metadata().set_index("study")
    assert metadata.loc["StudyB", "grid_size"] == 36
    assert metadata.loc["StudyJ", "grid_size"] == 36
    assert metadata.loc["StudyL", "grid_size"] == 36
    assert metadata.loc["StudyN", "grid_size"] == 36
    assert metadata.loc["StudyA", "grid_size"] == 72
    assert metadata.loc["StudyF", "grid_size"] == 72


def test_checkerboard_indicator_is_false_only_for_the_two_row_column_only_studies() -> None:
    metadata = documented_protocol_metadata().set_index("study")
    assert metadata.loc["StudyD", "has_checkerboard_paradigm"] == False  # noqa: E712
    assert metadata.loc["StudyJ", "has_checkerboard_paradigm"] == False  # noqa: E712
    non_checkerboard = metadata.loc[~metadata["has_checkerboard_paradigm"]]
    assert set(non_checkerboard.index) == {"StudyD", "StudyJ"}


def test_grid_size_and_checkerboard_are_registered_as_protocol_descriptors() -> None:
    assert "grid_size" in COVARIATES
    assert "has_checkerboard_paradigm" in COVARIATES
    assert DESCRIPTOR_KIND["grid_size"] == "protocol descriptor"
    assert DESCRIPTOR_KIND["has_checkerboard_paradigm"] == "protocol descriptor"
    assert "grid_size" in PROTOCOL_DESCRIPTORS
    assert "has_checkerboard_paradigm" in PROTOCOL_DESCRIPTORS


def test_protocol_covariates_merges_documented_metadata_onto_the_empirical_covariates() -> None:
    # A minimal trials/records pair with two studies, enough for protocol_covariates() to run.
    # protocol_covariates is already imported at the top of this file.
    trials = pd.DataFrame({
        "study": ["StudyA", "StudyA", "StudyD", "StudyD"],
        "eligible": [True, True, True, True],
        "condition": ["c1", "c1", "c1", "c1"],
        "relative_path": ["a1", "a1", "d1", "d1"],
        "trial_number": [1, 2, 1, 2],
        "phase3_time_seconds": [0.0, 5.0, 0.0, 6.0],
        "target": [1, 2, 1, 2],
    })
    records = pd.DataFrame({
        "study": ["StudyA", "StudyD"],
        "correct": [8, 9],
        "n": [10, 10],
    })
    covariates = protocol_covariates(trials, records)
    merged = covariates.set_index("study")
    assert merged.loc["StudyA", "grid_size"] == 72
    assert merged.loc["StudyD", "grid_size"] == 72
    assert merged.loc["StudyA", "has_checkerboard_paradigm"] == True  # noqa: E712
    assert merged.loc["StudyD", "has_checkerboard_paradigm"] == False  # noqa: E712


def test_covariates_without_timing_columns_still_produce_the_rest() -> None:
    """The archive's trial file carries timestamps; a caller's need not, and must not crash."""
    table = protocol_covariates(_trials(), _records())

    assert "median_inter_selection_interval" not in table
    assert set(table["study"]) == {"StudyA", "StudyB"}


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


def test_a_constant_moderator_reports_the_cohorts_it_had_and_why_it_could_not_use_them() -> None:
    """Zero cohorts fitted beside zero dropped is self-contradictory, and the contract forbids it."""
    n_studies = 8
    covariates = _cohort_covariates(n_studies)
    covariates["n_conditions"] = 2
    calibration = _cohort_calibration(
        n_studies, np.linspace(0.5, 2.0, n_studies), np.full(n_studies, 0.2)
    )

    row = explains_heterogeneity(covariates, calibration).set_index("covariate").loc["n_conditions"]

    assert row["n_studies_meta"] == n_studies
    assert row["n_dropped"] == 0
    assert np.isnan(row["meta_p_value"])
    assert "does not vary" in str(row["unidentified_reason"])


def test_family_composition_sensitivity_reports_every_definition() -> None:
    descriptors = pd.DataFrame({
        "covariate": ["a", "b", "c"],
        "kind": ["protocol descriptor", "protocol descriptor", "outcome summary"],
        "meta_p_value": [0.01, 0.40, 0.02],
        "p_value": [0.03, 0.50, 0.04],
    })

    sensitivity = family_composition_sensitivity(descriptors)

    everything = next(row for row in sensitivity if row["family"] == "all descriptors")
    protocol = next(row for row in sensitivity if row["family"] == "protocol descriptors")
    assert everything["n_tests"] == 3
    assert everything["meta_p_holm"]["a"] == pytest.approx(0.03)
    assert protocol["n_tests"] == 2
    assert protocol["meta_p_holm"]["a"] == pytest.approx(0.02)
    # Pooling the two analyses is the least favourable definition, and must be the largest.
    pooled = next(row for row in sensitivity if row["family"] == "both analyses pooled")
    assert pooled["n_tests"] == 6
    assert pooled["meta_p_holm"]["a"] >= everything["meta_p_holm"]["a"]


def test_stopping_rule_subgroups_split_on_whether_the_interval_was_data_dependent() -> None:
    n_studies = 12
    covariates = _cohort_covariates(n_studies)
    covariates["median_inter_selection_interval"] = np.linspace(8.0, 40.0, n_studies)
    covariates["constant_within_file_interval"] = [True] * 6 + [False] * 6
    rng = np.random.default_rng(3)
    calibration = _cohort_calibration(
        n_studies,
        0.4 + 0.03 * covariates["median_inter_selection_interval"].to_numpy(float)
        + rng.normal(0, 0.2, n_studies),
        np.full(n_studies, 0.2),
    )

    subgroups = stopping_rule_subgroups(covariates, calibration)

    assert {row["subgroup"] for row in subgroups} == {"constant interval", "variable interval"}
    assert all(row["n_studies_meta"] == 6 for row in subgroups)
    assert all(row["coefficients_per_sd"][0] > 0 for row in subgroups)


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
    assert len(report["joint_fits"]) == 4
    assert len(report["leave_one_cohort_out"]) == 5
    assert {row["family"] for row in report["family_composition"]} == {
        "all descriptors", "protocol descriptors", "outcome summaries", "both analyses pooled"
    }


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
