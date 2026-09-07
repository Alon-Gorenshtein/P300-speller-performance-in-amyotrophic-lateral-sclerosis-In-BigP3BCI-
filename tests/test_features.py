"""Tests for leakage-free calibration P300 feature construction."""

from __future__ import annotations

import numpy as np
import pytest

from bigp3_als.features import (
    calibration_discriminability,
    nonlinear_discriminability,
    sampling_frequencies_compatible,
    select_calibration_events,
)


def test_event_selection_uses_only_phase2_stimulus_onsets_and_their_labels() -> None:
    stimulus_begin = np.array([0, 1, 1, 0, 1, 0, 1, 0])
    phase = np.array([1, 2, 2, 2, 3, 2, 2, 2])
    stimulus_type = np.array([0, 1, 1, 0, 0, 0, 1, 0])

    samples, labels = select_calibration_events(stimulus_begin, phase, stimulus_type)

    assert samples.tolist() == [1, 6]
    assert labels.tolist() == [1, 1]


def test_calibration_discriminability_is_computed_from_training_epochs_only() -> None:
    rng = np.random.default_rng(42)
    labels = np.repeat([0, 1], 30)
    epochs = rng.normal(size=(60, 4, 10))
    epochs[labels == 1, 2, 4:7] += 2.0
    groups = np.arange(60) % 3

    score = calibration_discriminability(epochs, labels, groups)

    assert 0.8 < score < 1.0


def test_sampling_frequency_comparison_allows_edf_rounding_not_real_mismatch() -> None:
    assert sampling_frequencies_compatible(256.0000587, 256.0000826)
    assert not sampling_frequencies_compatible(256.0, 128.0)


def test_nonlinear_discriminability_recovers_a_boundary_a_linear_model_cannot() -> None:
    # An exclusive-or arrangement in two channels: no linear boundary separates it, so the linear
    # score sits near chance while a kernel boundary does not. This is the property the arm exists
    # to test, so the test asserts the gap rather than only that the number is finite.
    rng = np.random.default_rng(7)
    epochs = rng.normal(scale=0.2, size=(400, 4, 12))
    corner = rng.integers(0, 2, size=(400, 2)).astype(float)
    epochs[:, 0, :] += corner[:, [0]] * 3.0
    epochs[:, 1, :] += corner[:, [1]] * 3.0
    labels = (corner[:, 0] != corner[:, 1]).astype(int)
    groups = np.arange(400) % 4

    linear = calibration_discriminability(epochs, labels, groups)
    nonlinear = nonlinear_discriminability(epochs, labels, groups)

    assert 0.4 < linear < 0.6
    assert nonlinear > 0.8


def test_nonlinear_discriminability_rejects_an_unknown_classifier() -> None:
    rng = np.random.default_rng(8)
    epochs = rng.normal(size=(40, 3, 8))
    labels = np.repeat([0, 1], 20)
    groups = np.arange(40) % 3

    with pytest.raises(ValueError, match="unknown calibration classifier"):
        nonlinear_discriminability(epochs, labels, groups, classifier="not_a_model")
