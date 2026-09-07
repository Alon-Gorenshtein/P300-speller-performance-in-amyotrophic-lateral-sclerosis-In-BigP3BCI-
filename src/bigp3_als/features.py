"""Leakage-free calibration P300 feature extraction for clinical BigP3 sessions."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import mne
import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.kernel_approximation import Nystroem
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from bigp3_als.edf import REQUIRED_EVENT_CHANNELS, SHARED_EEG_CHANNELS, parse_source_path, select_edf_paths


EPOCH_START_SECONDS = -0.2
EPOCH_END_SECONDS = 0.8
BANDPASS_HZ = (0.5, 30.0)
P300_WINDOW_SECONDS = (0.25, 0.5)
POSTERIOR_CHANNELS = ("EEG_P3", "EEG_Pz", "EEG_P4", "EEG_PO7", "EEG_PO8", "EEG_Oz")
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


DECIMATION_FACTOR = 4


def minimum_sampling_frequency(decimation_factor: int = DECIMATION_FACTOR) -> float:
    """Return the lowest sampling frequency at which decimation still spans the passband.

    Decimating by n leaves a Nyquist frequency of sampling_frequency / n / 2, which has to stay at
    or above the upper bandpass edge for the retained band to survive.
    """
    if decimation_factor < 1:
        raise ValueError("decimation factor must be at least 1")
    return 2.0 * BANDPASS_HZ[1] * decimation_factor


def _downsampled_epoch_features(epochs: np.ndarray, decimation_factor: int = DECIMATION_FACTOR) -> np.ndarray:
    """Return a compact epoch representation that does not fold the retained passband.

    Subsampling preserves a band only when the resulting Nyquist frequency stays above it. At
    256 Hz a factor of four leaves Nyquist at 32 Hz, above the 30 Hz bandpass edge, so no part of
    the retained band folds; the earlier factor of twelve left Nyquist at 10.7 Hz and folded
    everything from 10.7 to 30 Hz onto lower frequencies. The bandpass is a fourth-order
    zero-phase Butterworth rather than a brick wall, so attenuated shoulder content above 32 Hz
    does still fold onto 24 to 32 Hz: the response is 8.9 dB down at 32 Hz, that shoulder carries
    about 1.2 percent of output power for a white input, and mains at 60 Hz arrives about 60 dB
    down.
    """
    if decimation_factor < 1:
        raise ValueError("decimation factor must be at least 1")
    return epochs[:, :, ::decimation_factor].reshape(len(epochs), -1)


def _grouped_cv_predictions(
    epochs: np.ndarray, labels: np.ndarray, groups: np.ndarray, classifier: str
) -> np.ndarray:
    """Return grouped out-of-fold calibration probabilities for one classifier."""
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
    features = _downsampled_epoch_features(epochs)
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=20260718)
    predictions = np.full(len(labels), np.nan)
    for train_indices, test_indices in splitter.split(features, labels, groups):
        if classifier == "logistic":
            model = make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    C=1.0, class_weight="balanced", max_iter=1000, random_state=20260718
                ),
            )
        elif classifier == "shrinkage_lda":
            model = make_pipeline(
                StandardScaler(), LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
            )
        elif classifier == "rbf":
            # A radial-basis kernel boundary, reached through a Nystroem approximation rather than
            # an exact support-vector machine. A session carries on the order of ten thousand
            # calibration epochs and an exact kernel machine is quadratic in that count, which would
            # put the extraction pass into days. The approximation is fitted inside the training
            # fold only, so the grouped split still holds.
            model = make_pipeline(
                StandardScaler(),
                # gamma=None resolves to 1 / n_features, the RBF-approximation default; Nystroem
                # does not accept SVC's "scale" string in this scikit-learn version.
                Nystroem(kernel="rbf", gamma=None, n_components=300, random_state=20260718),
                LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=20260718),
            )
        elif classifier == "gradient_boosting":
            # A tree ensemble on a principal-component reduction of the same epoch features. The
            # reduction is what makes the arm affordable: boosting bins every feature, and binning
            # a thousand of them per fold costs more than the whole rest of the pass. Both stages
            # are fitted inside the training fold.
            model = make_pipeline(
                StandardScaler(),
                PCA(n_components=40, svd_solver="randomized", random_state=20260718),
                HistGradientBoostingClassifier(
                    max_iter=100,
                    max_leaf_nodes=15,
                    learning_rate=0.1,
                    l2_regularization=1.0,
                    early_stopping=False,
                    random_state=20260718,
                ),
            )
        else:
            raise ValueError(f"unknown calibration classifier: {classifier}")
        model.fit(features[train_indices], labels[train_indices])
        predictions[test_indices] = model.predict_proba(features[test_indices])[:, 1]
    if np.isnan(predictions).any():
        raise ValueError("grouped cross-validation did not predict every calibration epoch")
    return predictions


def calibration_discriminability(
    epochs: np.ndarray, labels: np.ndarray, groups: np.ndarray
) -> float:
    """Estimate inner grouped-CV target discrimination AUC from calibration epochs only."""
    return float(roc_auc_score(labels, _grouped_cv_predictions(epochs, labels, groups, "logistic")))


def calibration_classification_accuracy(
    epochs: np.ndarray, labels: np.ndarray, groups: np.ndarray
) -> float:
    """Estimate grouped-CV calibration classification accuracy at a fixed 0.5 threshold."""
    predictions = _grouped_cv_predictions(epochs, labels, groups, "logistic")
    return float(np.mean((predictions >= 0.5) == np.asarray(labels, dtype=int)))


def shrinkage_lda_discriminability(
    epochs: np.ndarray, labels: np.ndarray, groups: np.ndarray
) -> float:
    """Estimate grouped-CV AUC of a conventional regularized LDA comparator."""
    return float(roc_auc_score(labels, _grouped_cv_predictions(epochs, labels, groups, "shrinkage_lda")))


def nonlinear_discriminability(
    epochs: np.ndarray, labels: np.ndarray, groups: np.ndarray, classifier: str = "rbf"
) -> float:
    """Estimate grouped-CV AUC of a nonlinear decision boundary on the same calibration epochs.

    Both scores the study reports so far come from linear decoders, so a mapping that fails to
    transport could in principle be a property of linear boundaries rather than of the
    calibration-to-accuracy relationship. This arm holds the epochs, the grouped split and the
    metric fixed and varies only the boundary.
    """
    return float(roc_auc_score(labels, _grouped_cv_predictions(epochs, labels, groups, classifier)))


def _bandpass(data: np.ndarray, sampling_frequency: float) -> np.ndarray:
    sos = butter(4, list(BANDPASS_HZ), btype="bandpass", fs=sampling_frequency, output="sos")
    return sosfiltfilt(sos, data, axis=-1)


def _extract_file_epochs(edf_path: Path) -> tuple[np.ndarray, np.ndarray, float, int]:
    raw = mne.io.read_raw_edf(edf_path, preload=False, verbose="ERROR")
    required = set(SHARED_EEG_CHANNELS) | {"StimulusBegin", "StimulusType", "PhaseInSequence"}
    missing = sorted(required - set(raw.ch_names))
    if missing:
        raise ValueError(f"missing calibration channels in {edf_path}: {', '.join(missing)}")
    sampling_frequency = float(raw.info["sfreq"])
    required_rate = minimum_sampling_frequency()
    if sampling_frequency < required_rate:
        raise ValueError(
            f"sampling frequency {sampling_frequency:g} Hz in {edf_path} is below the "
            f"{required_rate:g} Hz required to decimate by {DECIMATION_FACTOR} without folding "
            f"the {BANDPASS_HZ[1]:g} Hz passband"
        )
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
    n_pre_artifact = int(len(labels))
    artifact_free = np.max(np.abs(epochs), axis=(1, 2)) * 1e6 <= ARTIFACT_THRESHOLD_UV
    return epochs[artifact_free], labels[artifact_free], sampling_frequency, n_pre_artifact


def _session_feature_row(session_paths: list[Path], cache_path: Path) -> dict[str, object]:
    source = parse_source_path(session_paths[0].relative_to(cache_path).as_posix())
    epochs_list: list[np.ndarray] = []
    labels_list: list[np.ndarray] = []
    groups_list: list[np.ndarray] = []
    sampling_frequency: float | None = None
    n_pre_artifact = 0
    for group_index, path in enumerate(session_paths):
        epochs, labels, file_sampling_frequency, file_pre_artifact = _extract_file_epochs(path)
        if sampling_frequency is None:
            sampling_frequency = file_sampling_frequency
        elif not sampling_frequencies_compatible(sampling_frequency, file_sampling_frequency):
            raise ValueError(f"inconsistent sampling frequency in {source.study_participant_id}")
        epochs_list.append(epochs)
        labels_list.append(labels)
        groups_list.append(np.repeat(group_index, len(labels)))
        n_pre_artifact += file_pre_artifact
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
        "n_calibration_epochs": int(len(labels)),
        "n_calibration_epochs_pre_artifact": n_pre_artifact,
        "artifact_rejection_fraction": float(1.0 - len(labels) / n_pre_artifact) if n_pre_artifact else np.nan,
        "feature_exclusion_reason": None,
    }
    if target_count < MIN_TARGET_EPOCHS or nontarget_count < MIN_NONTARGET_EPOCHS:
        return {
            **base,
            "calibration_auc": np.nan,
            "calibration_accuracy": np.nan,
            "shrinkage_lda_auc": np.nan,
            "pz_difference_uv": np.nan,
            "posterior_difference_uv": np.nan,
            "posterior_signed_r2_max": np.nan,
            "feature_exclusion_reason": "insufficient_epochs",
        }
    try:
        auc = calibration_discriminability(epochs, labels, groups)
        accuracy = calibration_classification_accuracy(epochs, labels, groups)
        lda_auc = shrinkage_lda_discriminability(epochs, labels, groups)
    except ValueError as error:
        return {
            **base,
            "calibration_auc": np.nan,
            "calibration_accuracy": np.nan,
            "shrinkage_lda_auc": np.nan,
            "pz_difference_uv": np.nan,
            "posterior_difference_uv": np.nan,
            "posterior_signed_r2_max": np.nan,
            "feature_exclusion_reason": str(error),
        }
    assert sampling_frequency is not None
    times = np.arange(epochs.shape[-1]) / sampling_frequency + EPOCH_START_SECONDS
    p300_window = (times >= P300_WINDOW_SECONDS[0]) & (times <= P300_WINDOW_SECONDS[1])
    pz_index = SHARED_EEG_CHANNELS.index("EEG_Pz")
    pz_difference_uv = float(
        (epochs[labels == 1, pz_index, :][:, p300_window].mean()
         - epochs[labels == 0, pz_index, :][:, p300_window].mean())
        * 1e6
    )
    posterior_indices = [SHARED_EEG_CHANNELS.index(channel) for channel in POSTERIOR_CHANNELS]
    target_window = epochs[labels == 1, :, :][:, posterior_indices, :][:, :, p300_window]
    nontarget_window = epochs[labels == 0, :, :][:, posterior_indices, :][:, :, p300_window]
    posterior_difference_uv = float((target_window.mean() - nontarget_window.mean()) * 1e6)
    target_mean = target_window.mean(axis=0)
    nontarget_mean = nontarget_window.mean(axis=0)
    pooled_variance = (
        target_window.var(axis=0, ddof=1) + nontarget_window.var(axis=0, ddof=1)
    ) / 2
    signed_r2 = np.sign(target_mean - nontarget_mean) * (target_mean - nontarget_mean) ** 2 / (
        pooled_variance + np.finfo(float).eps
    )
    posterior_signed_r2_max = float(np.max(signed_r2))
    return {
        **base,
        "calibration_auc": auc,
        "calibration_accuracy": accuracy,
        "shrinkage_lda_auc": lda_auc,
        "pz_difference_uv": pz_difference_uv,
        "posterior_difference_uv": posterior_difference_uv,
        "posterior_signed_r2_max": posterior_signed_r2_max,
    }


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
