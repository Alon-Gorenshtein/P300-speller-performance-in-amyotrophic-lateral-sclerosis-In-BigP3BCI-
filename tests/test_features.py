"""Tests for leakage-free calibration P300 feature construction."""

from __future__ import annotations

import numpy as np

from bigp3_als.features import (
    calibration_discriminability,
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
