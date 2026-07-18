"""Tests for transparent reconstruction of online P300 spelling outcomes."""

from __future__ import annotations

import numpy as np

from bigp3_als.trials import reconstruct_online_trials


def _streams(*, selected: int = 5, fake_feedback: int = 0) -> dict[str, np.ndarray]:
    return {
        "PhaseInSequence": np.array([0, 1, 2, 2, 2, 3, 3, 0]),
        "CurrentTarget": np.array([0, 0, 5, 5, 5, 0, 0, 0]),
        "SelectedTarget": np.array([0, 0, 0, 0, 0, selected, selected, 0]),
        "DisplayResults": np.array([0, 0, 0, 0, 0, 1, 1, 0]),
        "FakeFeedback": np.array([0, 0, 0, 0, 0, fake_feedback, fake_feedback, 0]),
    }


def test_reconstruction_marks_a_non_overridden_matching_selection_correct() -> None:
    trials = reconstruct_online_trials(_streams())

    assert trials[0].target == 5
    assert trials[0].selected == 5
    assert trials[0].correct is True
    assert trials[0].eligible is True
    assert trials[0].exclusion_reason is None


def test_reconstruction_marks_a_nonmatching_selection_incorrect() -> None:
    trials = reconstruct_online_trials(_streams(selected=4))

    assert trials[0].correct is False
    assert trials[0].eligible is True


def test_reconstruction_excludes_missing_selected_target() -> None:
    trials = reconstruct_online_trials(_streams(selected=0))

    assert trials[0].eligible is False
    assert trials[0].exclusion_reason == "missing_selected_target"


def test_reconstruction_excludes_fake_feedback_override() -> None:
    trials = reconstruct_online_trials(_streams(fake_feedback=5))

    assert trials[0].eligible is False
    assert trials[0].exclusion_reason == "fake_feedback_override"
