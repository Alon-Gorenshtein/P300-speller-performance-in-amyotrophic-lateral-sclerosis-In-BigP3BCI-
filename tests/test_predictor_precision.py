"""Predictor precision differs between cohorts and must be measured, because
measurement error in a predictor flattens a fitted slope.

A rank correlation between precision and slope has no units and cannot say how much of the
heterogeneity measurement error could explain; the reliability ratio and the disattenuated slope
can, and are tested here alongside the guards against three ways the rank correlation itself can be
computed wrong: mixing three standard-error specifications together, summarising over sessions that
never entered a fit, and mistaking a confound with cohort discrimination for measurement error.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from bigp3_als.predictor_precision import (
    disattenuated_heterogeneity,
    partial_correlation_controlling_for_auc_level,
    precision_table,
    precision_versus_slope,
    reliability_ratio,
    weighted_slope_versus_reliability,
)


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


def test_precision_versus_slope_filters_to_the_primary_se_method_by_default() -> None:
    """cohort_calibration.csv stacks three se_method rows per cohort; an unfiltered merge would
    triple the sample and understate the p-value by treating 18 cohorts thrice over as 54."""
    precision = pd.DataFrame({"study": ["StudyA", "StudyB", "StudyC"],
                              "auc_standard_error": [0.01, 0.05, 0.10]})
    calibration = pd.DataFrame({
        "held_out_study": ["StudyA", "StudyB", "StudyC"] * 3,
        "slope": [1.5, 1.0, 0.5] * 3,
        "se_method": ["cluster"] * 3 + ["model"] * 3 + ["quasibinomial"] * 3,
    })

    result = precision_versus_slope(precision, calibration)

    assert result["n_studies"] == 3
    assert result["spearman_rho"] == pytest.approx(-1.0, abs=1e-9)


def test_precision_versus_slope_raises_on_a_genuine_duplicate_cohort_key() -> None:
    """The guard is a property of the function, not of whoever calls it: even without an
    se_method column to filter on, a cohort appearing twice must not be merged silently."""
    precision = pd.DataFrame({"study": ["StudyA", "StudyB"], "auc_standard_error": [0.01, 0.05]})
    calibration = pd.DataFrame({"held_out_study": ["StudyA", "StudyA", "StudyB"], "slope": [1.0, 2.0, 3.0]})

    with pytest.raises(ValueError, match="duplicate cohort keys"):
        precision_versus_slope(precision, calibration)


def _analysis_predictions() -> pd.DataFrame:
    """Only two of StudyA's three feature sessions, and none of StudyB's, entered a cohort fit."""
    return pd.DataFrame({
        "study": ["StudyA", "StudyA"],
        "study_participant_id": ["P0", "P1"],
        "session_id": ["SE001", "SE001"],
        "held_out_study": ["StudyA", "StudyA"],
        "model_role": ["primary", "primary"],
    })


def test_precision_table_restricts_to_sessions_that_actually_entered_a_cohort_fit() -> None:
    table = precision_table(_features(), predictions=_analysis_predictions())

    assert list(table["study"]) == ["StudyA"]
    assert table.loc[table["study"] == "StudyA", "n_sessions"].iloc[0] == 2


def _reliability_predictions() -> pd.DataFrame:
    """Identical AUC values, hence identical observed variance, in both cohorts; StudyB has a
    tenth of the epochs, so any reliability gap between them is due to that alone."""
    return pd.DataFrame({
        "held_out_study": ["StudyA"] * 3 + ["StudyB"] * 3,
        "study_participant_id": [f"P{i}" for i in range(6)],
        "session_id": ["SE001"] * 6,
        "calibration_auc": [0.80, 0.85, 0.75, 0.80, 0.85, 0.75],
        "n_target_epochs": [600] * 3 + [60] * 3,
        "n_nontarget_epochs": [6000] * 3 + [600] * 3,
        "model_role": ["primary"] * 6,
    })


def test_reliability_ratio_is_lower_for_the_cohort_with_fewer_epochs() -> None:
    table = reliability_ratio(_reliability_predictions()).set_index("study")

    assert 0.0 < table.loc["StudyB", "reliability"] < table.loc["StudyA", "reliability"] < 1.0


def test_reliability_ratio_returns_nan_when_error_variance_swamps_observed_variance() -> None:
    """A tenfold inflation of the error term pushes StudyB's assumed error past its entire
    observed spread; that cohort's reliability is undefined, not a small positive number."""
    table = reliability_ratio(_reliability_predictions(), error_variance_inflation=10.0).set_index("study")

    assert np.isnan(table.loc["StudyB", "reliability"])


def test_disattenuated_slope_divides_by_the_cohorts_own_reliability() -> None:
    reliability = pd.DataFrame({"study": ["StudyA", "StudyB"], "reliability": [0.5, 0.8]})
    calibration = pd.DataFrame({
        "held_out_study": ["StudyA", "StudyB"],
        "slope": [1.0, 1.0],
        "slope_se": [0.2, 0.2],
        "se_method": ["cluster"] * 2,
    })

    result = disattenuated_heterogeneity(reliability, calibration)

    assert result["disattenuated_slope_max"] == pytest.approx(1.0 / 0.5, abs=1e-9)
    assert result["disattenuated_slope_min"] == pytest.approx(1.0 / 0.8, abs=1e-9)


def test_disattenuated_heterogeneity_drops_a_cohort_with_no_identifiable_reliability() -> None:
    """A cohort whose reliability came back NaN keeps its place in the observed pooling but is
    dropped, not divided by a near-zero number, from the disattenuated one."""
    reliability = pd.DataFrame({"study": ["S1", "S2", "S3"], "reliability": [0.5, 0.8, float("nan")]})
    calibration = pd.DataFrame({
        "held_out_study": ["S1", "S2", "S3"],
        "slope": [1.0, 1.0, 1.0],
        "slope_se": [0.2, 0.2, 0.2],
        "se_method": ["cluster"] * 3,
    })

    result = disattenuated_heterogeneity(reliability, calibration)

    assert result["observed"]["n_studies"] == 3
    assert result["disattenuated"]["n_studies"] == 2
    assert "S3" in result["disattenuated"]["dropped_labels"]


def test_partial_correlation_attenuates_a_confound_with_cohort_discrimination() -> None:
    """Precision and slope are both driven here by a shared cohort-discrimination level; the raw
    rank correlation is strong, but partialling that level out should attenuate it substantially,
    because the raw correlation is standing in for the confound rather than for measurement error."""
    rng = np.random.default_rng(7)
    n = 12
    auc_level = np.linspace(0.60, 0.90, n)
    se = (0.95 - auc_level) * 0.3 + rng.normal(0, 0.01, n)
    slope = 2.0 * auc_level - 0.6 + rng.normal(0, 0.08, n)
    studies = [f"S{i}" for i in range(n)]

    precision = pd.DataFrame({"study": studies, "auc_standard_error": se, "median_calibration_auc": auc_level})
    calibration = pd.DataFrame({"held_out_study": studies, "slope": slope, "se_method": ["cluster"] * n})

    result = partial_correlation_controlling_for_auc_level(precision, calibration)

    assert result["n_studies"] == n
    assert abs(result["rho_precision_vs_slope"]) > 0.9
    assert abs(result["partial_rho"]) < abs(result["rho_precision_vs_slope"]) / 2


def test_weighted_regression_is_not_dragged_off_by_a_barely_identified_outlier_cohort() -> None:
    """Four cohorts sit exactly on slope = 2 * reliability - 0.5 with tiny standard errors; a
    fifth cohort is wildly discordant but carries a standard error 400 times larger. An unweighted
    fit lets that outlier set the slope; the precision-weighted fit should not."""
    reliability = pd.DataFrame({
        "study": ["S1", "S2", "S3", "S4", "Outlier"],
        "reliability": [0.5, 0.7, 0.85, 0.95, 0.6],
    })
    calibration = pd.DataFrame({
        "held_out_study": ["S1", "S2", "S3", "S4", "Outlier"],
        "slope": [0.5, 0.9, 1.2, 1.4, -5.0],
        "slope_se": [0.05, 0.05, 0.05, 0.05, 20.0],
        "se_method": ["cluster"] * 5,
    })

    weighted = weighted_slope_versus_reliability(reliability, calibration)

    merged = reliability.merge(
        calibration.rename(columns={"held_out_study": "study"})[["study", "slope"]], on="study"
    )
    unweighted = sm.OLS(merged["slope"].to_numpy(), sm.add_constant(merged["reliability"].to_numpy())).fit()

    assert weighted["beta"] == pytest.approx(2.0, abs=0.05)
    assert weighted["p_value"] < 0.001
    assert abs(weighted["beta"] - 2.0) < abs(float(unweighted.params[1]) - 2.0)
