"""Leakage-free calibration P300 feature extraction for clinical BigP3 sessions."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import mne
import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from bigp3_als.edf import REQUIRED_EVENT_CHANNELS, SHARED_EEG_CHANNELS, parse_source_path, select_edf_paths


EPOCH_START_SECONDS = -0.2
EPOCH_END_SECONDS = 0.8
P300_WINDOW_SECONDS = (0.25, 0.5)
ARTIFACT_THRESHOLD_UV = 150.0
MIN_TARGET_EPOCHS = 10
MIN_NONTARGET_EPOCHS = 40


def sampling_frequencies_compatible(first: float, second: float) -> bool:
    """Allow only negligible EDF rounding differences around a nominal rate."""
    return bool(np.isclose(first, second, rtol=0.0, atol=1e-3))


def select_calibration_events(
    stimulus_begin: np.ndarray, phase: np.ndarray, stimulus_type: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Return phase-2 rising stimulus onsets and their target/non-target labels."""
    stimulus = np.rint(np.asarray(stimulus_begin)).astype(int)
    phase_values = np.rint(np.asarray(phase)).astype(int)
    labels = np.rint(np.asarray(stimulus_type)).astype(int)
    if not (len(stimulus) == len(phase_values) == len(labels)):
        raise ValueError("calibration state streams have unequal lengths")
    rising = (stimulus == 1) & np.r_[True, stimulus[:-1] != 1]
    samples = np.flatnonzero(rising & (phase_values == 2))
    event_labels = labels[samples]
    valid = np.isin(event_labels, [0, 1])
    return samples[valid], event_labels[valid]


def calibration_discriminability(
    epochs: np.ndarray, labels: np.ndarray, groups: np.ndarray
) -> float:
    """Estimate inner grouped-CV target discrimination AUC from calibration epochs only."""
    labels = np.asarray(labels, dtype=int)
    groups = np.asarray(groups)
    if epochs.ndim != 3 or len(epochs) != len(labels) or len(labels) != len(groups):
        raise ValueError("epochs, labels, and groups must align")
    if set(np.unique(labels)) != {0, 1}:
        raise ValueError("calibration labels must contain target and non-target epochs")
    unique_groups = np.unique(groups)
    if len(unique_groups) < 2:
        raise ValueError("at least two calibration files are required for grouped validation")
    n_splits = min(5, len(unique_groups))
    downsample_step = max(1, epochs.shape[-1] // 20)
    features = epochs[:, :, ::downsample_step].reshape(len(epochs), -1)
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=20260718)
    predictions = np.full(len(labels), np.nan)
    for train_indices, test_indices in splitter.split(features, labels, groups):
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=20260718),
        )
        model.fit(features[train_indices], labels[train_indices])
        predictions[test_indices] = model.predict_proba(features[test_indices])[:, 1]
    if np.isnan(predictions).any():
        raise ValueError("grouped cross-validation did not predict every calibration epoch")
    return float(roc_auc_score(labels, predictions))


def _bandpass(data: np.ndarray, sampling_frequency: float) -> np.ndarray:
    sos = butter(4, [0.5, 30.0], btype="bandpass", fs=sampling_frequency, output="sos")
    return sosfiltfilt(sos, data, axis=-1)


def _extract_file_epochs(edf_path: Path) -> tuple[np.ndarray, np.ndarray, float]:
    raw = mne.io.read_raw_edf(edf_path, preload=False, verbose="ERROR")
    required = set(SHARED_EEG_CHANNELS) | {"StimulusBegin", "StimulusType", "PhaseInSequence"}
    missing = sorted(required - set(raw.ch_names))
    if missing:
        raise ValueError(f"missing calibration channels in {edf_path}: {', '.join(missing)}")
    sampling_frequency = float(raw.info["sfreq"])
    eeg = _bandpass(raw.get_data(picks=list(SHARED_EEG_CHANNELS)), sampling_frequency)
    stimulus_begin, stimulus_type, phase = raw.get_data(
        picks=["StimulusBegin", "StimulusType", "PhaseInSequence"]
    )
    samples, labels = select_calibration_events(stimulus_begin, phase, stimulus_type)
    pre_samples = round(-EPOCH_START_SECONDS * sampling_frequency)
    post_samples = round(EPOCH_END_SECONDS * sampling_frequency)
    valid = (samples >= pre_samples) & (samples + post_samples <= eeg.shape[1])
    samples, labels = samples[valid], labels[valid]
    epochs = np.stack([eeg[:, sample - pre_samples : sample + post_samples] for sample in samples])
    epochs = epochs - epochs[:, :, :pre_samples].mean(axis=2, keepdims=True)
    artifact_free = np.max(np.abs(epochs), axis=(1, 2)) * 1e6 <= ARTIFACT_THRESHOLD_UV
    return epochs[artifact_free], labels[artifact_free], sampling_frequency


def _session_feature_row(session_paths: list[Path], cache_path: Path) -> dict[str, object]:
    source = parse_source_path(session_paths[0].relative_to(cache_path).as_posix())
    epochs_list: list[np.ndarray] = []
    labels_list: list[np.ndarray] = []
    groups_list: list[np.ndarray] = []
    sampling_frequency: float | None = None
    for group_index, path in enumerate(session_paths):
        epochs, labels, file_sampling_frequency = _extract_file_epochs(path)
        if sampling_frequency is None:
            sampling_frequency = file_sampling_frequency
        elif not sampling_frequencies_compatible(sampling_frequency, file_sampling_frequency):
            raise ValueError(f"inconsistent sampling frequency in {source.study_participant_id}")
        epochs_list.append(epochs)
        labels_list.append(labels)
        groups_list.append(np.repeat(group_index, len(labels)))
    epochs = np.concatenate(epochs_list)
    labels = np.concatenate(labels_list)
    groups = np.concatenate(groups_list)
    target_count = int((labels == 1).sum())
    nontarget_count = int((labels == 0).sum())
    base = {
        "study": source.study,
        "participant_id": source.participant_id,
        "study_participant_id": source.study_participant_id,
        "session_id": source.session_id,
        "train_file_count": len(session_paths),
        "n_target_epochs": target_count,
        "n_nontarget_epochs": nontarget_count,
        "feature_exclusion_reason": None,
    }
    if target_count < MIN_TARGET_EPOCHS or nontarget_count < MIN_NONTARGET_EPOCHS:
        return {**base, "calibration_auc": np.nan, "pz_difference_uv": np.nan, "feature_exclusion_reason": "insufficient_epochs"}
    try:
        auc = calibration_discriminability(epochs, labels, groups)
    except ValueError as error:
        return {**base, "calibration_auc": np.nan, "pz_difference_uv": np.nan, "feature_exclusion_reason": str(error)}
    assert sampling_frequency is not None
    times = np.arange(epochs.shape[-1]) / sampling_frequency + EPOCH_START_SECONDS
    p300_window = (times >= P300_WINDOW_SECONDS[0]) & (times <= P300_WINDOW_SECONDS[1])
    pz_index = SHARED_EEG_CHANNELS.index("EEG_Pz")
    pz_difference_uv = float(
        (epochs[labels == 1, pz_index, :][:, p300_window].mean()
         - epochs[labels == 0, pz_index, :][:, p300_window].mean())
        * 1e6
    )
    return {**base, "calibration_auc": auc, "pz_difference_uv": pz_difference_uv}


def build_calibration_features(cache_path: Path) -> pd.DataFrame:
    """Return one calibration-only feature row per clinical participant-session."""
    grouped_paths: dict[tuple[str, str, str], list[Path]] = defaultdict(list)
    for edf_path in select_edf_paths(cache_path):
        relative_path = edf_path.relative_to(cache_path).as_posix()
        source = parse_source_path(relative_path)
        if source.phase == "Train":
            grouped_paths[(source.study, source.participant_id, source.session_id)].append(edf_path)
    if not grouped_paths:
        raise ValueError("no Train EDF files found in source cache")
    rows = [_session_feature_row(paths, cache_path) for _, paths in sorted(grouped_paths.items())]
    return pd.DataFrame(rows).sort_values(["study", "participant_id", "session_id"], ignore_index=True)
