"""Decimation must not alias the retained passband."""

from __future__ import annotations

from pathlib import Path

import mne
import numpy as np
import pytest

from bigp3_als.edf import SHARED_EEG_CHANNELS
from bigp3_als.features import (
    BANDPASS_HZ,
    DECIMATION_FACTOR,
    _downsampled_epoch_features,
    _extract_file_epochs,
    minimum_sampling_frequency,
)

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


def test_minimum_sampling_frequency_tracks_the_configured_factor_and_passband() -> None:
    """The threshold is derived, so it stays correct if the factor or the band edge changes."""
    assert minimum_sampling_frequency() == 2.0 * BANDPASS_HZ[1] * DECIMATION_FACTOR
    assert minimum_sampling_frequency(1) == 2.0 * BANDPASS_HZ[1]
    assert minimum_sampling_frequency(8) == 2.0 * minimum_sampling_frequency(4)
    assert minimum_sampling_frequency() <= SAMPLING_HZ

    for factor in (1, 2, 4, 8):
        nyquist = minimum_sampling_frequency(factor) / factor / 2.0
        assert nyquist >= BANDPASS_HZ[1]


class _ReachedTheRead(Exception):
    """Signals that control flow got past the sampling-rate guard and started reading data."""


class _StubRaw:
    """The smallest object `_extract_file_epochs` needs before it checks the sampling rate."""

    def __init__(self, sampling_frequency: float) -> None:
        self.ch_names = [
            *SHARED_EEG_CHANNELS,
            "StimulusBegin",
            "StimulusType",
            "PhaseInSequence",
        ]
        self.info = {"sfreq": sampling_frequency}

    def get_data(self, *args: object, **kwargs: object) -> np.ndarray:
        raise _ReachedTheRead


def test_extraction_refuses_a_file_whose_sampling_rate_would_fold_the_passband(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mne.io, "read_raw_edf", lambda *args, **kwargs: _StubRaw(128.0))
    edf_path = Path("StudyX/participant01/session01/Train/low_rate.edf")

    with pytest.raises(ValueError) as failure:
        _extract_file_epochs(edf_path)

    message = str(failure.value)
    assert "128" in message
    assert "240" in message
    assert "low_rate.edf" in message


def test_extraction_accepts_the_256_hz_rate_the_archive_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The guard must not fire on the rate every source study is documented to use."""
    monkeypatch.setattr(mne.io, "read_raw_edf", lambda *args, **kwargs: _StubRaw(SAMPLING_HZ))

    with pytest.raises(_ReachedTheRead):
        _extract_file_epochs(Path("StudyX/participant01/session01/Train/ok.edf"))
