"""Tests for study-held-out clinical validation."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bigp3_als.validation import MODEL_SPECS, joint_bootstrap_fold_covariance, leave_one_study_out


def test_leave_one_study_out_never_mixes_the_held_out_study_into_development() -> None:
    records = pd.DataFrame(
        {
            "study": ["StudyF", "StudyF", "StudyL", "StudyN"],
            "study_participant_id": ["StudyF:F_01", "StudyF:F_02", "StudyL:L_01", "StudyN:N_01"],
            "correct": [5, 4, 3, 2],
            "n": [6, 6, 6, 6],
            "calibration_auc": [0.9, 0.8, 0.7, 0.6],
        }
    )

    splits = list(leave_one_study_out(records))

    assert {held_out for held_out, _, _ in splits} == {"StudyF", "StudyL", "StudyN"}
    for held_out, development, validation in splits:
        assert set(development.study) == set(records.study) - {held_out}
        assert set(validation.study) == {held_out}
        assert not set(development.study_participant_id) & set(validation.study_participant_id)


def _toy_records(n_studies: int = 4, n_participants: int = 6, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(n_studies):
        study = f"Study{chr(ord('A') + s)}"
        for p in range(n_participants):
            score = rng.normal(0.6 + 0.1 * s, 0.15)
            n = 10
            correct = int(rng.binomial(n, min(max(score, 0.05), 0.95)))
            rows.append({
                "study": study, "study_participant_id": f"{study}_{p}", "session_id": "S1",
                "calibration_auc": score, "correct": correct, "n": n,
            })
    return pd.DataFrame(rows)


def test_joint_bootstrap_returns_a_covariance_matrix_indexed_by_every_study() -> None:
    records = _toy_records()
    spec = next(s for s in MODEL_SPECS if s.role == "primary")
    result = joint_bootstrap_fold_covariance(records, spec, repetitions=25)
    assert result["n_replicates"] == 25
    assert set(result["studies"]) == {"StudyA", "StudyB", "StudyC", "StudyD"}
    expected_columns = {f"{s}_intercept" for s in result["studies"]} | {f"{s}_slope" for s in result["studies"]}
    assert set(result["covariance_matrix"].columns) == expected_columns
    assert set(result["covariance_matrix"].index) == expected_columns
    # A covariance matrix is symmetric.
    assert result["covariance_matrix"].to_numpy() == pytest.approx(
        result["covariance_matrix"].to_numpy().T, abs=1e-9
    )


def test_joint_bootstrap_replicate_spread_intervals_are_ordered() -> None:
    records = _toy_records()
    spec = next(s for s in MODEL_SPECS if s.role == "primary")
    result = joint_bootstrap_fold_covariance(records, spec, repetitions=25)
    for key in ("replicate_between_cohort_sd_intercept", "replicate_between_cohort_sd_slope"):
        block = result[key]
        assert block["ci_low"] <= block["mean"] <= block["ci_high"]


def test_joint_bootstrap_is_deterministic_across_repeated_calls() -> None:
    records = _toy_records()
    spec = next(s for s in MODEL_SPECS if s.role == "primary")
    first = joint_bootstrap_fold_covariance(records, spec, repetitions=10)
    second = joint_bootstrap_fold_covariance(records, spec, repetitions=10)
    assert first["covariance_matrix"].to_numpy() == pytest.approx(
        second["covariance_matrix"].to_numpy(), nan_ok=True
    )


def test_joint_bootstrap_reports_finite_replicate_counts_per_study() -> None:
    records = _toy_records()
    spec = next(s for s in MODEL_SPECS if s.role == "primary")
    result = joint_bootstrap_fold_covariance(records, spec, repetitions=25)
    for study in result["studies"]:
        assert 0 <= result["n_finite_per_study"][study] <= 25
