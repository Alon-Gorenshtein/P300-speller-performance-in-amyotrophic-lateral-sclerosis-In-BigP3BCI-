"""Tests for Euclidean Alignment of calibration epochs."""

from __future__ import annotations

import numpy as np
import pytest

from bigp3_als.alignment import (
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
