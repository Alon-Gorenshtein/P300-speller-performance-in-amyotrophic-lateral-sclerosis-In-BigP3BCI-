"""Cohort calibration must carry its own uncertainty, and pooling must separate
true between-cohort variation from sampling error."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bigp3_als.heterogeneity import (
    MINIMUM_STANDARD_ERROR,
    SE_METHODS,
    cohort_calibration,
    random_effects,
)


def _predictions(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for study in ("StudyA", "StudyB"):
        for index in range(40):
            p = float(np.clip(rng.uniform(0.3, 0.95), 0.01, 0.99))
            n = 20
            rows.append({"held_out_study": study,
                         "study_participant_id": f"{study}:P{index % 10:02d}", "n": n,
                         "correct": rng.binomial(n, p), "predicted_probability": p})
    return pd.DataFrame(rows)


def _repeated_within_participant(seed: int = 3) -> pd.DataFrame:
    """One cohort where every participant contributes eight records at one predicted probability.

    Each participant also carries a persistent accuracy offset, so residuals correlate inside a
    participant. This is the structure of the real predictions file, where conditions recorded in
    one session share an identical predicted probability.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for participant in range(12):
        p = float(rng.uniform(0.35, 0.9))
        truth = float(np.clip(p + (0.08 if participant % 2 else -0.08), 0.02, 0.98))
        for _ in range(8):
            rows.append({"held_out_study": "StudyA",
                         "study_participant_id": f"StudyA:P{participant:02d}", "n": 20,
                         "correct": int(rng.binomial(20, truth)), "predicted_probability": p})
    return pd.DataFrame(rows)


def _cohort(**columns: object) -> pd.DataFrame:
    return pd.DataFrame(columns)


def test_cohort_calibration_returns_one_row_per_cohort_with_standard_errors() -> None:
    result = cohort_calibration(_predictions())

    assert list(result["held_out_study"]) == ["StudyA", "StudyB"]
    assert (result["slope_se"] > 0).all()
    assert (result["intercept_se"] > 0).all()
    assert set(result["se_method"]) == {"cluster"}


def test_calibration_slope_is_near_one_when_predictions_are_correct() -> None:
    result = cohort_calibration(_predictions())

    for _, row in result.iterrows():
        assert row["slope"] == pytest.approx(1.0, abs=0.15)


def test_random_effects_reports_no_heterogeneity_for_identical_estimates() -> None:
    summary = random_effects(pd.Series([1.0, 1.0, 1.0, 1.0]), pd.Series([0.1, 0.1, 0.1, 0.1]))

    assert summary["tau_squared"] == pytest.approx(0.0, abs=1e-9)
    assert summary["i_squared"] == pytest.approx(0.0, abs=1e-6)
    assert summary["pooled"] == pytest.approx(1.0, abs=1e-9)


def test_random_effects_attributes_small_spread_to_sampling_error() -> None:
    """Spread the same size as the standard errors is not evidence of heterogeneity."""
    summary = random_effects(pd.Series([0.9, 1.0, 1.1]), pd.Series([0.3, 0.3, 0.3]))

    assert summary["tau_squared"] == pytest.approx(0.0, abs=1e-6)
    assert summary["i_squared"] < 10.0


def test_random_effects_detects_spread_far_larger_than_the_standard_errors() -> None:
    summary = random_effects(pd.Series([0.1, 1.0, 2.2]), pd.Series([0.05, 0.05, 0.05]))

    assert summary["tau_squared"] > 0.3
    assert summary["i_squared"] > 90.0
    assert summary["q_p_value"] < 0.01


def test_prediction_interval_is_wider_than_the_confidence_interval() -> None:
    summary = random_effects(pd.Series([0.1, 1.0, 2.2]), pd.Series([0.05, 0.05, 0.05]))
    width = summary["prediction_interval_high"] - summary["prediction_interval_low"]
    assert width > 2 * 1.96 * summary["pooled_se"]


def test_random_effects_refuses_a_single_study() -> None:
    with pytest.raises(ValueError, match="at least two"):
        random_effects(pd.Series([1.0]), pd.Series([0.1]))


def test_random_effects_matches_values_computed_by_hand() -> None:
    """Estimates 1, 2 and 6 with standard errors 1, 1 and 2, worked through in exact fractions.

    Inverse-variance weights 1, 1 and 1/4 sum to 9/4 and give a fixed-effect mean of exactly 2, so
    Q = 1 + 0 + 4 = 5. With squared weights summing to 33/16, C = 9/4 - (33/16)/(9/4) = 4/3, and
    tau squared = (5 - 2)/(4/3) = 9/4. Random-effects weights 4/13, 4/13 and 4/25 then give a
    pooled estimate of 17/7 and a pooled variance of 325/252. The unequal weights are what make
    this discriminating: the fixed-effect mean is 2 while the random-effects mean is 17/7, so a
    summary that centres Q on the wrong mean, or that pools with fixed-effect weights, fails here.
    """
    summary = random_effects(pd.Series([1.0, 2.0, 6.0]), pd.Series([1.0, 1.0, 2.0]))

    assert summary["q_statistic"] == pytest.approx(5.0, abs=1e-9)
    assert summary["tau_squared"] == pytest.approx(2.25, abs=1e-9)
    assert summary["tau"] == pytest.approx(1.5, abs=1e-9)
    assert summary["i_squared"] == pytest.approx(60.0, abs=1e-9)
    assert summary["pooled"] == pytest.approx(17.0 / 7.0, abs=1e-9)
    assert summary["pooled_se"] == pytest.approx(1.1356419064487449, abs=1e-9)
    assert summary["q_p_value"] == pytest.approx(np.exp(-2.5), abs=1e-9)
    assert summary["n_studies"] == 3.0


def test_prediction_interval_half_width_is_exactly_the_published_formula() -> None:
    """Pinned exactly, because a one-sided comparison against the confidence interval gets easier
    to satisfy as the pooled standard error shrinks, which is the case it looks like it guards.

    On the fixture above, t(0.975, df=2) has the closed form sqrt(722/39), because the t
    distribution with two degrees of freedom has cumulative distribution
    1/2 + t / (2 sqrt(2 + t squared)). The half-width is that critical value times
    sqrt(tau squared + pooled variance) = sqrt(223/63), so it equals
    sqrt(722/39 * 223/63) = sqrt(161006/2457) = 8.095029804114835.
    """
    summary = random_effects(pd.Series([1.0, 2.0, 6.0]), pd.Series([1.0, 1.0, 2.0]))

    expected_half_width = float(np.sqrt(161006.0 / 2457.0))
    assert expected_half_width == pytest.approx(8.095029804114835, abs=1e-9)
    assert summary["prediction_interval_high"] - summary["pooled"] == pytest.approx(
        expected_half_width, abs=1e-9
    )
    assert summary["pooled"] - summary["prediction_interval_low"] == pytest.approx(
        expected_half_width, abs=1e-9
    )
    assert summary["prediction_interval_low"] == pytest.approx(-5.666458375543407, abs=1e-9)
    assert summary["prediction_interval_high"] == pytest.approx(10.523601232686264, abs=1e-9)


def test_random_effects_reports_the_cohorts_it_dropped() -> None:
    labels = ["StudyA", "StudyB", "StudyC", "StudyD"]
    summary = random_effects(
        pd.Series([1.0, 1.2, np.nan, 0.9], index=labels),
        pd.Series([0.1, 0.2, 0.3, 0.0], index=labels),
    )

    assert summary["dropped_labels"] == ("StudyC", "StudyD")
    assert summary["n_dropped"] == 2.0
    assert summary["n_studies"] == 2.0


def test_counts_enter_as_grouped_binomial_trials_not_as_proportions() -> None:
    """Quadrupling every count must leave the slope alone and halve the standard errors.

    A proportion endog would carry no information about how many selections each record summarises,
    so the standard errors would not move at all.
    """
    records = _cohort(
        held_out_study=["S"] * 6, study_participant_id=[f"S:P{index}" for index in range(6)],
        n=[10] * 6, correct=[2, 5, 4, 7, 6, 9],
        predicted_probability=[0.3, 0.4, 0.5, 0.6, 0.7, 0.9],
    )
    quadrupled = records.assign(n=records["n"] * 4, correct=records["correct"] * 4)

    base = cohort_calibration(records, se_method="model").iloc[0]
    scaled = cohort_calibration(quadrupled, se_method="model").iloc[0]

    assert scaled["slope"] == pytest.approx(base["slope"], abs=1e-10)
    assert scaled["intercept"] == pytest.approx(base["intercept"], abs=1e-10)
    assert scaled["slope_se"] == pytest.approx(base["slope_se"] / 2.0, rel=1e-9)
    assert scaled["intercept_se"] == pytest.approx(base["intercept_se"] / 2.0, rel=1e-9)


def test_clustering_widens_standard_errors_without_moving_the_estimates() -> None:
    """Repeated records from one participant are not independent draws, and treating them as
    independent understates the within-cohort variance, which inflates tau squared."""
    records = _repeated_within_participant()

    clustered = cohort_calibration(records, se_method="cluster").iloc[0]
    model_based = cohort_calibration(records, se_method="model").iloc[0]

    assert clustered["slope"] == pytest.approx(model_based["slope"], abs=1e-12)
    assert clustered["intercept"] == pytest.approx(model_based["intercept"], abs=1e-12)
    assert clustered["slope_se"] > 1.5 * model_based["slope_se"]
    assert clustered["intercept_se"] > 1.5 * model_based["intercept_se"]
    assert clustered["se_method"] == "cluster"
    assert model_based["se_method"] == "model"


def test_clustering_requires_a_participant_column() -> None:
    records = _predictions().drop(columns=["study_participant_id"])

    with pytest.raises(ValueError, match="study_participant_id"):
        cohort_calibration(records)

    assert not cohort_calibration(records, se_method="model")["slope"].isna().any()


def test_unknown_standard_error_method_is_rejected() -> None:
    with pytest.raises(ValueError, match="se_method"):
        cohort_calibration(_predictions(), se_method="robust")


def test_quasibinomial_scales_standard_errors_by_the_pearson_dispersion() -> None:
    """The quasi-binomial fit is the binomial fit with its standard errors multiplied by the square
    root of the Pearson dispersion, so the estimates cannot move and the ratio of the standard
    errors is pinned. The dispersion is recomputed here from the fitted probabilities alone, so the
    test does not simply repeat whatever scaling statsmodels applied."""
    records = _repeated_within_participant()

    model_based = cohort_calibration(records, se_method="model").iloc[0]
    quasi = cohort_calibration(records, se_method="quasibinomial").iloc[0]

    probability = records["predicted_probability"].to_numpy(dtype=float)
    linear = model_based["intercept"] + model_based["slope"] * np.log(probability / (1 - probability))
    fitted = 1.0 / (1.0 + np.exp(-linear))
    trials = records["n"].to_numpy(dtype=float)
    successes = records["correct"].to_numpy(dtype=float)
    pearson = float((((successes - trials * fitted) ** 2) / (trials * fitted * (1 - fitted))).sum())
    dispersion = pearson / (len(records) - 2)

    assert dispersion > 1.0
    assert quasi["se_method"] == "quasibinomial"
    assert quasi["slope"] == pytest.approx(model_based["slope"], abs=1e-12)
    assert quasi["intercept"] == pytest.approx(model_based["intercept"], abs=1e-12)
    assert quasi["slope_se"] == pytest.approx(
        model_based["slope_se"] * np.sqrt(dispersion), rel=1e-9
    )
    assert quasi["intercept_se"] == pytest.approx(
        model_based["intercept_se"] * np.sqrt(dispersion), rel=1e-9
    )


def test_quasibinomial_needs_no_participant_column() -> None:
    """Only the clustered specification reads the participant identifier."""
    records = _predictions().drop(columns=["study_participant_id"])

    result = cohort_calibration(records, se_method="quasibinomial")

    assert not result["slope"].isna().any()
    assert (result["slope_se"] > 0).all()


def test_quasibinomial_yields_no_estimate_for_a_cohort_it_fits_exactly() -> None:
    """A cohort whose observed proportions the model reproduces exactly has a Pearson dispersion of
    zero, so its quasi-binomial standard errors collapse. They do not collapse to exactly zero:
    floating point leaves a slope standard error of about 2e-16, which passes a positivity check
    and would then carry weight 2e31 in an inverse-variance pooling, so the estimate would set the
    pooled slope by itself. The cohort is dropped instead. It is still estimable under the other two
    specifications, which is why dropped labels are reported per specification rather than once."""
    records = _cohort(
        held_out_study=["S"] * 6, study_participant_id=[f"S:P{index}" for index in range(6)],
        n=[10] * 6, correct=[3, 4, 5, 6, 7, 9],
        predicted_probability=[0.3, 0.4, 0.5, 0.6, 0.7, 0.9],
    )

    row = cohort_calibration(records, se_method="quasibinomial").iloc[0]
    assert np.isnan(row["slope"]) and np.isnan(row["slope_se"])

    assert np.isfinite(cohort_calibration(records, se_method="model").iloc[0]["slope_se"])


def test_a_constant_predictor_yields_no_estimate() -> None:
    """The slope is not identified when the predicted probability never varies, yet the fitter
    still returns an arbitrary split of the one quantity that is identified, their sum."""
    records = _cohort(
        held_out_study=["S"] * 4, study_participant_id=[f"S:P{index}" for index in range(4)],
        n=[20] * 4, correct=[16, 15, 17, 16], predicted_probability=[0.8] * 4,
    )

    for method in SE_METHODS:
        row = cohort_calibration(records, se_method=method).iloc[0]
        assert np.isnan(row["slope"]) and np.isnan(row["slope_se"])
        assert np.isnan(row["intercept"]) and np.isnan(row["intercept_se"])
        assert row["n_records"] == 4


def test_a_cohort_without_residual_degrees_of_freedom_yields_no_estimate() -> None:
    single = _cohort(held_out_study=["S"], study_participant_id=["S:P0"], n=[20], correct=[15],
                     predicted_probability=[0.8])
    saturated = _cohort(held_out_study=["S"] * 2, study_participant_id=["S:P0", "S:P1"],
                        n=[20, 20], correct=[15, 18], predicted_probability=[0.7, 0.9])

    for records in (single, saturated):
        for method in SE_METHODS:
            row = cohort_calibration(records, se_method=method).iloc[0]
            assert np.isnan(row["slope"]) and np.isnan(row["slope_se"])
            assert np.isnan(row["intercept"]) and np.isnan(row["intercept_se"])


def test_a_cohort_with_one_participant_yields_no_clustered_estimate() -> None:
    """A clustered covariance is a sum of one outer product per participant, so a single
    participant cannot support it. statsmodels divides by the number of clusters minus one and
    raises ZeroDivisionError, which would otherwise abort the whole pass. The same cohort is still
    estimable without clustering, which is what the model-based sensitivity is for.
    """
    records = _cohort(
        held_out_study=["S"] * 4, study_participant_id=["S:P0"] * 4, n=[20] * 4,
        correct=[12, 13, 17, 16], predicted_probability=[0.6, 0.6, 0.85, 0.85],
    )

    clustered = cohort_calibration(records, se_method="cluster").iloc[0]
    assert np.isnan(clustered["slope"]) and np.isnan(clustered["slope_se"])

    model_based = cohort_calibration(records, se_method="model").iloc[0]
    assert np.isfinite(model_based["slope"]) and model_based["slope_se"] > 0


def test_a_separated_cohort_yields_no_estimate() -> None:
    """Every selection correct drives the estimate to the boundary. The fitter returns a slope of
    about zero with a standard error in the tens of thousands, which carries no weight but would
    still add one to k, and k enters tau squared through (Q - (k-1))."""
    records = _cohort(
        held_out_study=["S"] * 5, study_participant_id=[f"S:P{index}" for index in range(5)],
        n=[20] * 5, correct=[20] * 5, predicted_probability=[0.6, 0.7, 0.8, 0.9, 0.75],
    )

    for method in SE_METHODS:
        row = cohort_calibration(records, se_method=method).iloc[0]
        assert np.isnan(row["slope"]) and np.isnan(row["slope_se"])


def test_a_cohort_the_model_fits_exactly_yields_no_clustered_estimate() -> None:
    """The clustered sandwich is a sum of one outer product of cluster scores, and an exact fit has
    residuals of zero, so every score is zero and the sandwich collapses. It collapses to
    floating-point dust rather than to zero, a slope standard error of 4e-16 carrying weight 8e30,
    which a positivity check would pass and which would then set the pooled slope by itself. This is
    the same pathology as the quasi-binomial zero dispersion but on the primary specification, so it
    reaches the pooled numbers the paper reports rather than only a sensitivity.
    """
    records = _cohort(
        held_out_study=["S"] * 6, study_participant_id=[f"S:P{index}" for index in range(6)],
        n=[10] * 6, correct=[3, 4, 5, 6, 7, 9],
        predicted_probability=[0.3, 0.4, 0.5, 0.6, 0.7, 0.9],
    )

    clustered = cohort_calibration(records, se_method="cluster").iloc[0]
    assert np.isnan(clustered["slope"]) and np.isnan(clustered["slope_se"])
    assert np.isnan(clustered["intercept"]) and np.isnan(clustered["intercept_se"])


def test_a_degenerate_standard_error_is_refused_on_every_specification() -> None:
    """Stated against the constant rather than against one fixture, because the floor is what keeps
    a single cohort from taking the entire inverse-variance weight, and it protects all three
    specifications rather than only the two that have a demonstrated collapse."""
    records = _cohort(
        held_out_study=["S"] * 6, study_participant_id=[f"S:P{index}" for index in range(6)],
        n=[10] * 6, correct=[3, 4, 5, 6, 7, 9],
        predicted_probability=[0.3, 0.4, 0.5, 0.6, 0.7, 0.9],
    )

    # Six orders of magnitude below the smallest standard error any of the eighteen real cohorts
    # produces, 0.058, so no real cohort can be caught by it.
    assert MINIMUM_STANDARD_ERROR == 1e-8

    for method in SE_METHODS:
        row = cohort_calibration(records, se_method=method).iloc[0]
        if np.isfinite(row["slope_se"]):
            assert row["slope_se"] > MINIMUM_STANDARD_ERROR
            assert row["intercept_se"] > MINIMUM_STANDARD_ERROR


def test_bootstrap_se_method_is_accepted_and_differs_from_the_cluster_sandwich() -> None:
    """The bootstrap SE is a distinct estimator from the asymptotic cluster sandwich, not an
    alias for it, and it must be finite and positive on a cohort large enough to identify a slope."""
    rng = np.random.default_rng(0)
    n_participants = 12
    records = _cohort(
        held_out_study=["S"] * n_participants,
        study_participant_id=[f"S:P{index}" for index in range(n_participants)],
        n=[20] * n_participants,
        correct=list(rng.binomial(20, 0.7, size=n_participants)),
        predicted_probability=list(np.clip(rng.normal(0.7, 0.1, size=n_participants), 0.05, 0.95)),
    )

    cluster_row = cohort_calibration(records, se_method="cluster").iloc[0]
    bootstrap_row = cohort_calibration(records, se_method="bootstrap").iloc[0]

    assert bootstrap_row["se_method"] == "bootstrap"
    assert np.isfinite(bootstrap_row["slope_se"]) and bootstrap_row["slope_se"] > 0
    assert np.isfinite(bootstrap_row["intercept_se"]) and bootstrap_row["intercept_se"] > 0
    assert bootstrap_row["slope_se"] != pytest.approx(cluster_row["slope_se"])


def test_bootstrap_se_method_is_reproducible_across_calls() -> None:
    """The bootstrap draws must be seeded, or the manuscript's reported SEs would not be
    reproducible from the same input twice."""
    rng = np.random.default_rng(1)
    n_participants = 10
    records = _cohort(
        held_out_study=["S"] * n_participants,
        study_participant_id=[f"S:P{index}" for index in range(n_participants)],
        n=[15] * n_participants,
        correct=list(rng.binomial(15, 0.6, size=n_participants)),
        predicted_probability=list(np.clip(rng.normal(0.6, 0.12, size=n_participants), 0.05, 0.95)),
    )

    first = cohort_calibration(records, se_method="bootstrap").iloc[0]
    second = cohort_calibration(records, se_method="bootstrap").iloc[0]
    assert first["slope_se"] == pytest.approx(second["slope_se"])
    assert first["intercept_se"] == pytest.approx(second["intercept_se"])


def test_bootstrap_se_method_returns_nan_with_fewer_than_two_participants() -> None:
    """A single-participant cohort cannot support a cluster bootstrap for the same reason it
    cannot support the clustered sandwich: resampling one cluster with replacement never varies."""
    records = _cohort(
        held_out_study=["S"] * 4, study_participant_id=["S:P0"] * 4, n=[20] * 4,
        correct=[12, 13, 17, 16], predicted_probability=[0.6, 0.6, 0.85, 0.85],
    )
    row = cohort_calibration(records, se_method="bootstrap").iloc[0]
    assert np.isnan(row["slope"]) and np.isnan(row["slope_se"])


def test_bootstrap_replicates_on_the_separation_boundary_are_discarded() -> None:
    """A cluster resample that happens to exclude a cohort's only imperfect record is separated:
    every fitted probability sits at the boundary, and the fitter still returns finite, arbitrary
    parameters. Counting those draws as if they carried real information about the standard error is
    the bug this test guards against.

    This fixture is shaped like the real StudyS1 cohort that motivated the guard, and reproduces its
    numbers almost exactly: nine of ten participants answer every selection correctly on both of
    their two records, and the tenth misses one selection on a record whose predicted probability is
    *not* the extreme value in the cohort. That placement is what makes the fixture diagnostic rather
    than a cohort that fails to identify a slope on its own: with the imperfect record away from the
    extreme, the primary, non-resampled fit is comfortably inside the boundary (fitted probabilities
    span [0.990, 0.999], four orders of magnitude clear of FITTED_BOUNDARY) and is confirmed below to
    return a finite estimate under the cluster, model and quasi-binomial specifications, none of which
    resample and so none of which can exercise the guard under test. Swapping in the pre-guard
    `_bootstrap_standard_errors` confirms this fixture actually depends on it: without the guard, this
    test fails (the bootstrap row comes back with finite, absurdly large standard errors instead of
    NaN); with it restored, the test passes.

    It is only the participant-cluster bootstrap that runs into trouble: any resample that happens not
    to draw the tenth participant leaves only perfect records behind, which separates. For this
    fixture that is 1,165 of the 2,000 replicates (58%, verified empirically, matching the real
    StudyS1 cohort's own rate), which exceeds the `len(draws) < repetitions // 2` discard threshold, so
    the cohort correctly comes back not identified under the bootstrap method while every other method
    identifies it. Before the per-replicate guard in `_bootstrap_standard_errors` was added, those
    1,165 separated replicates were counted as real draws and inflated the reported bootstrap standard
    errors from 2.64 to 107 instead of being discarded."""
    n_participants = 10
    # Not monotone in participant index: the imperfect participant (index 1) sits second-lowest in
    # predicted probability, mirroring StudyS1:S1_01, so the covariate alone cannot separate the
    # cohort and the primary fit stays identified.
    probabilities = [0.87, 0.94, 0.95, 0.96, 0.965, 0.968, 0.969, 0.970, 0.972, 0.973]
    imperfect_index = 1
    records = _cohort(
        held_out_study=["S"] * (2 * n_participants),
        study_participant_id=[
            f"S:P{index:02d}" for index in range(n_participants) for _ in range(2)
        ],
        n=[18] * (2 * n_participants),
        correct=[
            17 if index == imperfect_index and condition == 0 else 18
            for index in range(n_participants)
            for condition in range(2)
        ],
        predicted_probability=[
            probabilities[index] for index in range(n_participants) for _ in range(2)
        ],
    )

    bootstrap_row = cohort_calibration(records, se_method="bootstrap").iloc[0]
    assert np.isnan(bootstrap_row["slope"]) and np.isnan(bootstrap_row["slope_se"])
    assert np.isnan(bootstrap_row["intercept"]) and np.isnan(bootstrap_row["intercept_se"])

    # The primary fit is identified under every non-resampling specification, which proves the NaN
    # above comes from the per-replicate bootstrap guard and not from `_fit_cohort`'s own boundary
    # check on the unresampled fit (the failure mode of the fixture this test replaced).
    for se_method in ("cluster", "model", "quasibinomial"):
        row = cohort_calibration(records, se_method=se_method).iloc[0]
        assert np.isfinite(row["slope"]) and np.isfinite(row["slope_se"])
        assert np.isfinite(row["intercept"]) and np.isfinite(row["intercept_se"])


def test_a_cohort_the_model_happens_to_fit_exactly_is_kept() -> None:
    """statsmodels warns about perfect separation whenever the fitted proportions reproduce the
    observed ones, which is also true of a small identified cohort. That warning must not be read
    as a failure to identify."""
    records = _cohort(
        held_out_study=["S"] * 6, study_participant_id=[f"S:P{index}" for index in range(6)],
        n=[10] * 6, correct=[3, 4, 5, 6, 7, 9],
        predicted_probability=[0.3, 0.4, 0.5, 0.6, 0.7, 0.9],
    )

    row = cohort_calibration(records, se_method="model").iloc[0]

    assert row["slope"] == pytest.approx(1.0, abs=1e-9)
    assert row["slope_se"] == pytest.approx(0.3572791652, abs=1e-9)
