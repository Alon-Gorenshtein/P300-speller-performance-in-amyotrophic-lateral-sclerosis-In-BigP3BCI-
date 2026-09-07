"""Tests for leakage-free calibration P300 feature construction."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from bigp3_als.alignment import pooled_reference
from bigp3_als.features import (
    _alignment_feature_row,
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


# The cohort-level Euclidean Alignment path in `_alignment_feature_row` never touches a real EDF
# file: only `_extract_file_epochs` reads one, so monkeypatching that one function lets these tests
# exercise the row-building and cohort-whitening wiring directly, in milliseconds, instead of only
# through the 9-minute real-data extraction pass.
_FAKE_CACHE = Path("/fake/cache")


def _synthetic_session_epochs(
    seed: int,
    mixing: np.ndarray,
    n_target: int,
    n_nontarget: int,
    *,
    signal: float = 0.6,
    n_channels: int = 4,
    n_samples: int = 24,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a P300-like session: a step in channel 0 for targets, passed through a channel mix.

    Different mixing matrices give two sessions genuinely different covariance structures, which
    is what the pooled-cohort-reference test below needs in order to tell "whitened by the
    session's own reference" apart from "whitened by a pooled cohort reference."
    """
    rng = np.random.default_rng(seed)
    n = n_target + n_nontarget
    labels = np.array([1] * n_target + [0] * n_nontarget)
    labels = labels[rng.permutation(n)]
    base = rng.normal(size=(n, n_channels, n_samples))
    base[labels == 1, 0, :] += signal
    epochs = np.einsum("cd,tds->tcs", mixing, base)
    return epochs, labels


def _split_two_files(
    epochs: np.ndarray, labels: np.ndarray
) -> tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]:
    """Split one session's epochs across two files: grouped CV needs at least two groups."""
    half = len(labels) // 2
    return (epochs[:half], labels[:half]), (epochs[half:], labels[half:])


def _session_paths(study: str, participant: str, session: str) -> list[Path]:
    """Two file paths for one session, matching the schema `parse_source_path` requires."""
    return [
        _FAKE_CACHE / "bigP3BCI-data" / study / participant / session / "Train" / "CB" / f"run{i}.edf"
        for i in range(2)
    ]


def _install_synthetic_extraction(
    monkeypatch: pytest.MonkeyPatch, lookup: dict[Path, tuple[np.ndarray, np.ndarray]]
) -> None:
    """Replace real EDF reading with a lookup, so a test controls its epochs and labels exactly."""

    def fake_extract(path: Path) -> tuple[np.ndarray, np.ndarray, float, int]:
        epochs, labels = lookup[path]
        return epochs, labels, 256.0, len(labels)

    monkeypatch.setattr("bigp3_als.features._extract_file_epochs", fake_extract)


def _reference_only(paths: list[Path]) -> tuple[np.ndarray, int]:
    """Fetch one session's reference covariance and epoch count without paying for any CV fit."""
    row = _alignment_feature_row(paths, _FAKE_CACHE, (), cohort_references={})
    return row["reference_covariance"], row["n_calibration_epochs"]


def test_cohort_reference_path_skips_the_session_level_and_nonlinear_arms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The cheap cohort pass must not also pay for the arms Task 3 already extracted."""
    epochs, labels = _synthetic_session_epochs(1, np.eye(4), n_target=15, n_nontarget=50)
    paths = _session_paths("StudyZ", "P1", "S1")
    _install_synthetic_extraction(monkeypatch, dict(zip(paths, _split_two_files(epochs, labels))))

    row = _alignment_feature_row(
        paths,
        _FAKE_CACHE,
        (
            "calibration_auc_ea_session",
            "calibration_auc_rbf",
            "calibration_auc_gbm",
            "calibration_auc_ea_cohort",
        ),
        {"StudyZ": np.eye(4)},
    )

    assert np.isfinite(row["calibration_auc_ea_cohort"])
    assert "calibration_auc_reproduced" not in row
    assert "calibration_auc_ea_session" not in row
    assert "calibration_auc_rbf" not in row
    assert "calibration_auc_gbm" not in row


def test_cohort_and_session_level_paths_use_identical_epochs_labels_and_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cohort reference equal to a session's own reference must whiten it identically.

    Both `calibration_discriminability` and `euclidean_align` are deterministic given the same
    epochs, labels, groups and reference matrix, so if either branch pulled a different subset of
    epochs, a different label array or a different grouping, these two calls would disagree even
    though the reference passed in is the same matrix.
    """
    mixing = np.array([[1, 0, 0, 0], [0.6, 1, 0, 0], [0, 0, 1, 0.3], [0, 0, 0, 1]])
    epochs, labels = _synthetic_session_epochs(2, mixing, n_target=15, n_nontarget=50)
    paths = _session_paths("StudyZ", "P1", "S1")
    _install_synthetic_extraction(monkeypatch, dict(zip(paths, _split_two_files(epochs, labels))))

    session_row = _alignment_feature_row(paths, _FAKE_CACHE, ("calibration_auc_ea_session",))
    cohort_row = _alignment_feature_row(
        paths, _FAKE_CACHE, ("calibration_auc_ea_cohort",), {"StudyZ": session_row["reference_covariance"]}
    )

    assert cohort_row["calibration_auc_ea_cohort"] == session_row["calibration_auc_ea_session"]


def test_cohort_arm_returns_nan_for_an_underpowered_session_but_keeps_its_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    epochs, labels = _synthetic_session_epochs(3, np.eye(4), n_target=3, n_nontarget=5)
    paths = _session_paths("StudyZ", "P1", "S1")
    _install_synthetic_extraction(monkeypatch, dict(zip(paths, _split_two_files(epochs, labels))))

    row = _alignment_feature_row(paths, _FAKE_CACHE, ("calibration_auc_ea_cohort",), {"StudyZ": np.eye(4)})

    assert np.isnan(row["calibration_auc_ea_cohort"])
    assert row["reference_covariance"] is not None
    assert row["reference_covariance"].shape == (4, 4)


def test_cohort_score_differs_from_the_session_own_reference_score_when_pooled_reference_differs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pins that the cohort branch whitens by the POOLED reference, not the session's own.

    Two sessions in one cohort with deliberately different channel-mixing structures: the pooled
    reference (epoch-count weighted, dominated by the second session's much larger count) is
    materially different from the first session's own reference, so whitening the first session by
    the pooled reference instead of its own must change its discriminability. A refactor that
    silently substituted the session's own reference here would leave every other assertion in
    this module passing; this is the one that would catch it.
    """
    small_epochs, small_labels = _synthetic_session_epochs(11, np.eye(4), n_target=15, n_nontarget=50)
    large_mixing = np.array([[8, 5, 4, 3], [0, 6, 1.5, 0], [0, 0, 0.15, 0], [0, 0, 0, 9]])
    large_epochs, large_labels = _synthetic_session_epochs(
        22, large_mixing, n_target=100, n_nontarget=400
    )
    small_paths = _session_paths("StudyZ", "P1", "S1")
    large_paths = _session_paths("StudyZ", "P2", "S2")
    lookup = {
        **dict(zip(small_paths, _split_two_files(small_epochs, small_labels))),
        **dict(zip(large_paths, _split_two_files(large_epochs, large_labels))),
    }
    _install_synthetic_extraction(monkeypatch, lookup)

    small_own = _alignment_feature_row(small_paths, _FAKE_CACHE, ("calibration_auc_ea_session",))
    large_reference, large_n = _reference_only(large_paths)
    cohort_reference = pooled_reference(
        [small_own["reference_covariance"], large_reference],
        [small_own["n_calibration_epochs"], large_n],
    )

    small_cohort = _alignment_feature_row(
        small_paths, _FAKE_CACHE, ("calibration_auc_ea_cohort",), {"StudyZ": cohort_reference}
    )

    # Empirically 0.012 for this fixed configuration; 0.005 leaves ample margin while still
    # failing hard if a refactor made the two scores coincide.
    assert abs(small_own["calibration_auc_ea_session"] - small_cohort["calibration_auc_ea_cohort"]) > 0.005


def test_cohort_arm_raises_for_a_study_missing_from_the_pooled_reference_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A study absent from `cohort_references` is a caller configuration error, not a per-session
    numerical failure: it must stop the run rather than be swallowed into a NaN row alongside
    genuine underpowered-session and non-convergence failures."""
    epochs, labels = _synthetic_session_epochs(12, np.eye(4), n_target=15, n_nontarget=50)
    paths = _session_paths("StudyZ", "P1", "S1")
    _install_synthetic_extraction(monkeypatch, dict(zip(paths, _split_two_files(epochs, labels))))

    with pytest.raises(ValueError, match="no pooled cohort reference for study StudyZ"):
        _alignment_feature_row(paths, _FAKE_CACHE, ("calibration_auc_ea_cohort",), {"StudyOther": np.eye(4)})


def test_feature_exclusion_reason_distinguishes_underpowered_from_computed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An arm's NaN must be traceable to why it is NaN, the same guarantee `_session_feature_row`
    already gives the published feature table."""
    powered_epochs, powered_labels = _synthetic_session_epochs(13, np.eye(4), n_target=15, n_nontarget=50)
    powered_paths = _session_paths("StudyZ", "P1", "S1")
    underpowered_epochs, underpowered_labels = _synthetic_session_epochs(
        14, np.eye(4), n_target=3, n_nontarget=5
    )
    underpowered_paths = _session_paths("StudyZ", "P2", "S2")
    _install_synthetic_extraction(
        monkeypatch,
        {
            **dict(zip(powered_paths, _split_two_files(powered_epochs, powered_labels))),
            **dict(zip(underpowered_paths, _split_two_files(underpowered_epochs, underpowered_labels))),
        },
    )

    powered_row = _alignment_feature_row(
        powered_paths, _FAKE_CACHE, ("calibration_auc_ea_cohort",), {"StudyZ": np.eye(4)}
    )
    underpowered_row = _alignment_feature_row(
        underpowered_paths, _FAKE_CACHE, ("calibration_auc_ea_cohort",), {"StudyZ": np.eye(4)}
    )

    assert np.isfinite(powered_row["calibration_auc_ea_cohort"])
    assert powered_row["feature_exclusion_reason"] is None
    assert np.isnan(underpowered_row["calibration_auc_ea_cohort"])
    assert underpowered_row["feature_exclusion_reason"] == "insufficient_epochs"
