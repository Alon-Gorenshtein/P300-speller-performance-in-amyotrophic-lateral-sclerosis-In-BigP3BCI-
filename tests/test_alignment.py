"""Tests for Euclidean Alignment of calibration epochs."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bigp3_als.alignment import (
    ALIGNMENT_SPECS,
    cohort_standardised,
    euclidean_align,
    inverse_square_root,
    pooled_reference,
    reference_covariance,
)


def test_reference_covariance_is_the_mean_epoch_covariance() -> None:
    rng = np.random.default_rng(11)
    epochs = rng.normal(size=(7, 3, 20))

    reference = reference_covariance(epochs)

    expected = np.mean([epoch @ epoch.T / epoch.shape[1] for epoch in epochs], axis=0)
    assert reference.shape == (3, 3)
    assert np.allclose(reference, expected)


def test_aligning_a_recording_to_its_own_reference_whitens_it() -> None:
    rng = np.random.default_rng(12)
    mixing = rng.normal(size=(4, 4))
    epochs = np.einsum("cd,tds->tcs", mixing, rng.normal(size=(200, 4, 64)))

    aligned = euclidean_align(epochs, reference_covariance(epochs))

    assert np.allclose(reference_covariance(aligned), np.eye(4), atol=1e-8)


def test_alignment_removes_a_per_channel_gain_difference() -> None:
    rng = np.random.default_rng(13)
    epochs = rng.normal(size=(120, 4, 40))
    gains = np.diag([1.0, 5.0, 0.2, 3.0])
    rescaled = np.einsum("cd,tds->tcs", gains, epochs)

    aligned = euclidean_align(epochs, reference_covariance(epochs))
    aligned_rescaled = euclidean_align(rescaled, reference_covariance(rescaled))

    # Whitening is unique only up to rotation, so compare the invariant the classifier sees:
    # the Gram matrix of the flattened trials.
    left = aligned.reshape(len(aligned), -1)
    right = aligned_rescaled.reshape(len(aligned_rescaled), -1)
    assert np.allclose(left @ left.T, right @ right.T, rtol=1e-6, atol=1e-8)


def test_inverse_square_root_floors_a_singular_direction_instead_of_exploding() -> None:
    matrix = np.diag([4.0, 1.0, 0.0])

    whitener = inverse_square_root(matrix, relative_floor=1e-6)

    assert np.isfinite(whitener).all()
    assert whitener[2, 2] == pytest.approx(1.0 / np.sqrt(4.0 * 1e-6))


def test_inverse_square_root_rejects_a_matrix_with_no_positive_eigenvalue() -> None:
    with pytest.raises(ValueError, match="positive"):
        inverse_square_root(np.zeros((3, 3)))


def test_pooled_reference_weights_recordings_by_their_epoch_count() -> None:
    first = np.eye(2)
    second = np.diag([3.0, 3.0])

    pooled = pooled_reference([first, second], [1.0, 3.0])

    assert np.allclose(pooled, np.diag([2.5, 2.5]))


def test_cohort_standardisation_uses_session_values_not_repeated_records() -> None:
    # Two sessions per cohort, one of which was run under three conditions and the other under one.
    # Standardising over records would centre on the repeated session; standardising over sessions
    # centres on the midpoint of the two.
    records = pd.DataFrame(
        {
            "study": ["A"] * 4,
            "study_participant_id": ["A:1", "A:1", "A:1", "A:2"],
            "session_id": ["S1", "S1", "S1", "S2"],
            "condition": ["CB", "RC", "CBcol", "CB"],
            "calibration_auc": [0.9, 0.9, 0.9, 0.7],
        }
    )

    standardised = cohort_standardised(records, "calibration_auc", method="z")

    assert standardised.iloc[0] == pytest.approx(1.0)
    assert standardised.iloc[3] == pytest.approx(-1.0)


def test_cohort_standardisation_is_computed_within_each_cohort_separately() -> None:
    records = pd.DataFrame(
        {
            "study": ["A", "A", "B", "B"],
            "study_participant_id": ["A:1", "A:2", "B:1", "B:2"],
            "session_id": ["S1", "S2", "S1", "S2"],
            "condition": ["CB"] * 4,
            "calibration_auc": [0.60, 0.70, 0.85, 0.95],
        }
    )

    standardised = cohort_standardised(records, "calibration_auc", method="z")

    assert standardised.tolist() == pytest.approx([-1.0, 1.0, -1.0, 1.0])


def test_cohort_standardisation_rank_method_is_monotone_and_finite() -> None:
    records = pd.DataFrame(
        {
            "study": ["A"] * 5,
            "study_participant_id": [f"A:{i}" for i in range(5)],
            "session_id": [f"S{i}" for i in range(5)],
            "condition": ["CB"] * 5,
            "calibration_auc": [0.5, 0.6, 0.7, 0.8, 0.9],
        }
    )

    standardised = cohort_standardised(records, "calibration_auc", method="rank")

    assert np.isfinite(standardised).all()
    assert standardised.is_monotonic_increasing


def test_cohort_standardisation_returns_missing_for_a_single_session_cohort() -> None:
    records = pd.DataFrame(
        {
            "study": ["A"],
            "study_participant_id": ["A:1"],
            "session_id": ["S1"],
            "condition": ["CB"],
            "calibration_auc": [0.8],
        }
    )

    assert cohort_standardised(records, "calibration_auc", method="z").isna().all()


def test_every_alignment_specification_names_one_feature_and_a_role() -> None:
    names = [spec.name for spec in ALIGNMENT_SPECS]

    assert len(names) == len(set(names))
    assert all(len(spec.features) == 1 for spec in ALIGNMENT_SPECS)
    assert all(spec.role in {"alignment", "nonlinear"} for spec in ALIGNMENT_SPECS)
