"""Cohort calibration must carry its own uncertainty, and pooling must separate
true between-cohort variation from sampling error."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bigp3_als.heterogeneity import cohort_calibration, random_effects


def _predictions(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for study, slope in (("StudyA", 1.0), ("StudyB", 1.0)):
        for index in range(40):
            p = float(np.clip(rng.uniform(0.3, 0.95), 0.01, 0.99))
            n = 20
            rows.append({"held_out_study": study, "n": n,
                         "correct": rng.binomial(n, p), "predicted_probability": p})
    return pd.DataFrame(rows)


def test_cohort_calibration_returns_one_row_per_cohort_with_standard_errors() -> None:
    result = cohort_calibration(_predictions())

    assert list(result["held_out_study"]) == ["StudyA", "StudyB"]
    assert (result["slope_se"] > 0).all()
    assert (result["intercept_se"] > 0).all()


def test_calibration_slope_is_near_one_when_predictions_are_correct() -> None:
    result = cohort_calibration(_predictions())

    for _, row in result.iterrows():
        assert row["slope"] == pytest.approx(1.0, abs=0.45)


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
