"""Tests for the analyses that establish what the calibration score adds."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bigp3_als.strengthening import (
    across_session_association,
    collapse_to_sessions,
    null_benchmark,
    participant_level_association,
    session_accuracy_icc,
    within_study_association,
)


def _records() -> pd.DataFrame:
    """Two studies, three participants each, two sessions each, one or two conditions."""
    rows = []
    for study, base in (("StudyF", 0.60), ("StudyL", 0.80)):
        for participant_index in range(3):
            score = 0.60 + 0.10 * participant_index
            for session_index in range(2):
                accuracy = min(0.99, base + 0.10 * participant_index + 0.02 * session_index)
                for condition in ("CB", "RC"):
                    rows.append(
                        {
                            "study": study,
                            "study_participant_id": f"{study}:P_{participant_index:02d}",
                            "session_id": f"SE{session_index + 1:03d}",
                            "condition": condition,
                            "n": 10,
                            "correct": round(accuracy * 10),
                            "calibration_auc": score,
                        }
                    )
    return pd.DataFrame(rows)


def test_collapse_to_sessions_gives_one_row_per_participant_session() -> None:
    sessions = collapse_to_sessions(_records())

    assert len(sessions) == 12
    assert sessions["selections"].eq(20).all()
    assert set(sessions.columns) >= {"study", "study_participant_id", "session_id", "accuracy"}


def test_collapse_to_sessions_rejects_a_predictor_that_varies_within_a_session() -> None:
    records = _records()
    records.loc[0, "calibration_auc"] = 0.99

    with pytest.raises(ValueError, match="varies within participant-session"):
        collapse_to_sessions(records)


def test_null_benchmark_reports_one_row_per_study_plus_a_pooled_row() -> None:
    result = null_benchmark(_records())

    assert list(result["held_out_study"]) == ["StudyF", "StudyL", "Pooled held-out records"]
    assert result["n_records"].iloc[-1] == 24


def test_benchmark_columns_are_named_for_the_comparison_they_make() -> None:
    result = null_benchmark(_records())

    assert "development_mean_benchmark_mae" in result.columns
    assert "held_out_cohort_mean_benchmark_mae" in result.columns
    assert "null_mean_absolute_error" not in result.columns
    assert not any("oracle" in c for c in result.columns)


def test_a_cohorts_own_mean_can_be_the_worse_absolute_error_benchmark() -> None:
    """The own-mean benchmark is not guaranteed to beat the development mean.

    Mean absolute error is minimised by the median, not the mean, so estimating a cohort at its own
    mean can be worse than estimating it at some other constant. A skewed held-out cohort shows this
    directly, and the production data behaves the same way in 7 of its 18 cohorts, so no test here
    may assert the ordering as an invariant.
    """
    rows = []
    for correct in (5, 9, 9, 9):  # accuracies 0.5, 0.9, 0.9, 0.9: mean 0.8, median 0.9
        rows.append({"study": "StudyF", "n": 10, "correct": correct, "calibration_auc": 0.7})
    for _ in range(4):  # development cohort sits at 0.9, which is the held-out cohort's median
        rows.append({"study": "StudyL", "n": 10, "correct": 9, "calibration_auc": 0.7})

    held_out = null_benchmark(pd.DataFrame(rows)).set_index("held_out_study").loc["StudyF"]

    assert held_out["development_mean_benchmark_mae"] == pytest.approx(0.10)
    assert held_out["held_out_cohort_mean_benchmark_mae"] == pytest.approx(0.15)
    assert (
        held_out["held_out_cohort_mean_benchmark_mae"] > held_out["development_mean_benchmark_mae"]
    )


def test_null_benchmark_is_zero_when_every_record_sits_at_the_common_mean() -> None:
    records = _records()
    records["correct"] = 8  # every record 0.8 accuracy, so no variation anywhere
    result = null_benchmark(records)

    assert result["development_mean_benchmark_mae"].iloc[-1] == pytest.approx(0.0)


def test_within_study_association_recovers_a_planted_positive_association() -> None:
    result = within_study_association(_records())
    centred = result.loc[result["analysis"] == "pooled_study_centred"].iloc[0]

    assert centred["pearson_r"] > 0.9
    assert centred["n_sessions"] == 12


def _noisy_records(n_participants: int, seed: int = 0) -> pd.DataFrame:
    """One study, one session each, with a positive association blurred by noise."""
    generator = np.random.default_rng(seed)
    rows = []
    for index in range(n_participants):
        score = float(generator.uniform(0.55, 0.95))
        accuracy = float(np.clip(score + generator.normal(0.0, 0.15), 0.05, 0.95))
        rows.append(
            {
                "study": "StudyF",
                "study_participant_id": f"StudyF:P_{index:03d}",
                "session_id": "SE001",
                "condition": "CB",
                "n": 100,
                "correct": round(accuracy * 100),
                "calibration_auc": score,
            }
        )
    return pd.DataFrame(rows)


def test_correlation_interval_contains_the_estimate_and_narrows_as_the_cohort_grows() -> None:
    small = within_study_association(_noisy_records(12)).iloc[0]
    large = within_study_association(_noisy_records(200)).iloc[0]

    for row in (small, large):
        assert row["pearson_ci_low"] <= row["pearson_r"] <= row["pearson_ci_high"]
        assert -1.0 <= row["pearson_ci_low"] and row["pearson_ci_high"] <= 1.0

    small_width = small["pearson_ci_high"] - small["pearson_ci_low"]
    large_width = large["pearson_ci_high"] - large["pearson_ci_low"]
    assert large_width < small_width


def test_correlation_interval_is_missing_when_three_observations_leave_no_variance() -> None:
    # The variance of the Fisher z transform is 1 / (n - 3), so three sessions carry a coefficient
    # but no interval. Reporting a width there would invent precision the data cannot supply.
    result = within_study_association(_noisy_records(3)).iloc[0]

    assert result["n_sessions"] == 3
    assert np.isnan(result["pearson_ci_low"])
    assert np.isnan(result["pearson_ci_high"])


def test_participant_level_association_uses_one_row_per_participant() -> None:
    result = participant_level_association(_records()).iloc[0]

    assert result["n_participants"] == 6
    assert result["pearson_r"] > 0.5


def test_session_accuracy_icc_is_high_when_sessions_repeat_within_participant() -> None:
    summary = session_accuracy_icc(_records())

    assert summary["n_participants"] == 6
    assert summary["mean_sessions_per_participant"] == pytest.approx(2.0)
    assert summary["intraclass_correlation"] > 0.5
    assert summary["effective_independent_sessions"] < summary["n_sessions"]


def test_across_session_pairs_always_put_the_predictor_before_the_outcome() -> None:
    pairs, summary = across_session_association(_records())

    assert len(pairs) == 6  # six participants, two sessions each, one consecutive pair apiece
    assert (pairs["predictor_session"] < pairs["outcome_session"]).all()
    assert summary.loc[summary["analysis"] == "across_session_prior_to_later", "n_pairs"].iloc[0] == 6


def test_across_session_returns_a_stub_when_no_participant_has_two_sessions() -> None:
    records = _records()
    single = records.loc[records["session_id"] == "SE001"].copy()

    pairs, summary = across_session_association(single)

    assert pairs.empty
    assert summary["n_pairs"].iloc[0] == 0


def test_across_session_refuses_identifiers_whose_lexical_order_is_the_wrong_order() -> None:
    """Unpadded identifiers sort lexically into an order that is not the recording order.

    SE10 precedes SE2 lexically, so pairing on that order would take the later session's calibration
    recording as the predictor for the earlier session's accuracy. The analysis has no timestamp with
    which to notice that, so the function refuses the input rather than silently reversing the pair.
    """
    records = _records()
    records["session_id"] = records["session_id"].replace({"SE001": "SE2", "SE002": "SE10"})

    with pytest.raises(ValueError, match="contradicts their numeric"):
        across_session_association(records)


def test_across_session_refuses_identifiers_that_carry_no_strict_order() -> None:
    """SE1 and SE01 name the same position, so no ordering of them can be the recording order."""
    records = _records()
    records["session_id"] = records["session_id"].replace({"SE001": "SE1", "SE002": "SE01"})

    with pytest.raises(ValueError, match="do not form a strict order"):
        across_session_association(records)


def test_across_session_accepts_the_zero_padded_identifiers_this_archive_uses() -> None:
    """The guard must not reject the format the analysis actually runs on."""
    records = _records()
    records["session_id"] = records["session_id"].replace({"SE002": "SE012"})

    pairs, _ = across_session_association(records)

    assert (pairs["predictor_session"] == "SE001").all()
    assert (pairs["outcome_session"] == "SE012").all()


def test_across_session_predictor_is_never_taken_from_the_outcome_session() -> None:
    records = _records()
    # Make the second session's score distinctive so leakage would be visible.
    records.loc[records["session_id"] == "SE002", "calibration_auc"] = 0.123
    pairs, _ = across_session_association(records)

    assert (pairs["prior_session_feature"] != 0.123).all()
    assert (pairs["same_session_feature"] == 0.123).all()
