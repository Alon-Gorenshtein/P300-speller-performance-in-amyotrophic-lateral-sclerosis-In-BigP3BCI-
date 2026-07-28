"""Tests for study-held-out clinical validation."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import bigp3_als.validation as validation_module
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


def test_joint_bootstrap_resamples_once_per_replicate_not_once_per_fold(monkeypatch: pytest.MonkeyPatch) -> None:
    """The naive mutant resamples inside the fold loop, the way ``_bootstrap_intervals`` legitimately
    does for its own, independent purpose. That calls ``_resample_clusters`` once per fold per
    replicate (``repetitions * n_studies`` times) and cannot preserve the fact that a cohort shared
    between two folds should see the identical draw within one replicate. The correct joint-bootstrap
    design resamples once per replicate, before the fold loop, so it must call ``_resample_clusters``
    exactly ``repetitions`` times. A prior version of this test suite (4 tests, none of which counted
    calls) passed unchanged against the naive mutant, so this test exists specifically to fail against
    it.
    """
    records = _toy_records()
    spec = next(s for s in MODEL_SPECS if s.role == "primary")
    original_resample_clusters = validation_module._resample_clusters
    calls = {"count": 0}

    def _counting_resample_clusters(*args: object, **kwargs: object):
        calls["count"] += 1
        return original_resample_clusters(*args, **kwargs)

    monkeypatch.setattr(validation_module, "_resample_clusters", _counting_resample_clusters)
    repetitions = 10
    joint_bootstrap_fold_covariance(records, spec, repetitions=repetitions)
    assert calls["count"] == repetitions


def test_joint_bootstrap_gives_every_fold_in_one_replicate_the_identical_shared_cohort_draw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Within one replicate, any two folds that both develop on a shared cohort must see the exact
    same resampled rows for it (same participants, same bootstrap draw labels) — that identity is
    the entire point of resampling once per replicate rather than once per fold. Captured directly
    from the function under test, by spying on ``_fit_probability_model`` (the first thing every fold
    does with its ``development`` frame), rather than re-deriving the property from
    ``_resample_clusters``/``leave_one_study_out`` composed by hand, which would pass even if the
    function under test resampled independently per fold instead of once per replicate. With
    ``repetitions=1`` every one of the 4 toy studies is held out exactly once, so all captured
    development frames necessarily come from the same single replicate.
    """
    records = _toy_records()
    spec = next(s for s in MODEL_SPECS if s.role == "primary")
    all_studies = set(records["study"].unique())
    original_fit_probability_model = validation_module._fit_probability_model
    captured_development: dict[str, pd.DataFrame] = {}

    def _capturing_fit_probability_model(development, validation, features):
        (held_out,) = all_studies - set(development["study"].unique())
        captured_development[held_out] = development.copy()
        return original_fit_probability_model(development, validation, features)

    monkeypatch.setattr(validation_module, "_fit_probability_model", _capturing_fit_probability_model)
    joint_bootstrap_fold_covariance(records, spec, repetitions=1)

    assert set(captured_development) == all_studies
    # StudyA is a shared (non-held-out) cohort in both the StudyB-held-out and StudyC-held-out folds.
    shared_cohort = "StudyA"
    shared_in_b = (
        captured_development["StudyB"].loc[lambda frame: frame["study"] == shared_cohort].reset_index(drop=True)
    )
    shared_in_c = (
        captured_development["StudyC"].loc[lambda frame: frame["study"] == shared_cohort].reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(shared_in_b, shared_in_c)
