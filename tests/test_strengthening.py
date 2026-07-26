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


def test_null_benchmark_oracle_never_exceeds_the_null_within_a_study() -> None:
    result = null_benchmark(_records())
    per_study = result.loc[result["held_out_study"] != "Pooled held-out records"]

    # Estimating a study at its own mean cannot be worse than estimating it at another mean.
    assert (
        per_study["same_study_oracle_mean_absolute_error"] <= per_study["null_mean_absolute_error"] + 1e-12
    ).all()


def test_null_benchmark_is_zero_when_every_record_sits_at_the_common_mean() -> None:
    records = _records()
    records["correct"] = 8  # every record 0.8 accuracy, so no variation anywhere
    result = null_benchmark(records)

    assert result["null_mean_absolute_error"].iloc[-1] == pytest.approx(0.0)


def test_within_study_association_recovers_a_planted_positive_association() -> None:
    result = within_study_association(_records())
    centred = result.loc[result["analysis"] == "pooled_study_centred"].iloc[0]

    assert centred["pearson_r"] > 0.9
    assert centred["n_sessions"] == 12


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


def test_across_session_predictor_is_never_taken_from_the_outcome_session() -> None:
    records = _records()
    # Make the second session's score distinctive so leakage would be visible.
    records.loc[records["session_id"] == "SE002", "calibration_auc"] = 0.123
    pairs, _ = across_session_association(records)

    assert (pairs["prior_session_feature"] != 0.123).all()
    assert (pairs["same_session_feature"] == 0.123).all()
