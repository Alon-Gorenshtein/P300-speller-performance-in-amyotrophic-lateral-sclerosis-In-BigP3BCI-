"""Decimation must not alias the retained passband."""

from __future__ import annotations

import numpy as np

from bigp3_als.features import DECIMATION_FACTOR, _downsampled_epoch_features

SAMPLING_HZ = 256.0
BANDPASS_EDGE_HZ = 30.0


def test_decimation_factor_keeps_nyquist_above_the_passband() -> None:
    nyquist = SAMPLING_HZ / DECIMATION_FACTOR / 2.0
    assert nyquist >= BANDPASS_EDGE_HZ


def test_feature_width_matches_the_decimation_factor() -> None:
    epochs = np.zeros((5, 16, 256))
    features = _downsampled_epoch_features(epochs)
    expected_samples = int(np.ceil(256 / DECIMATION_FACTOR))
    assert features.shape == (5, 16 * expected_samples)


def test_a_25_hz_tone_is_not_folded_to_a_lower_frequency() -> None:
    """At the old factor a 25 Hz tone aliased to 3.7 Hz. It must survive as itself."""
    time = np.arange(256) / SAMPLING_HZ
    tone = np.sin(2 * np.pi * 25.0 * time)
    epochs = np.tile(tone, (1, 1, 1))

    features = _downsampled_epoch_features(epochs).reshape(1, 1, -1)[0, 0]

    decimated_rate = SAMPLING_HZ / DECIMATION_FACTOR
    spectrum = np.abs(np.fft.rfft(features - features.mean()))
    peak_hz = np.fft.rfftfreq(len(features), 1.0 / decimated_rate)[spectrum.argmax()]
    assert abs(peak_hz - 25.0) < 2.0
