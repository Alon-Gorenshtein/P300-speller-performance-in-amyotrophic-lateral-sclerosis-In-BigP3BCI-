"""Reconstruct feedback-phase P300 spelling outcomes from EDF state streams."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import mne
import numpy as np
import pandas as pd

from bigp3_als.edf import parse_source_path, select_edf_paths


REQUIRED_TRIAL_STREAMS = (
    "PhaseInSequence",
    "CurrentTarget",
    "SelectedTarget",
    "DisplayResults",
    "FakeFeedback",
)


@dataclass(frozen=True)
class OnlineTrial:
    trial_number: int
    phase3_sample: int
    target: int | None
    selected: int | None
    correct: bool | None
    eligible: bool
    exclusion_reason: str | None


def _contiguous_start(values: np.ndarray, index: int, state: int) -> int:
    start = index
    while start > 0 and values[start - 1] == state:
        start -= 1
    return start


def _contiguous_end(values: np.ndarray, index: int, state: int) -> int:
    end = index
    while end < len(values) and values[end] == state:
        end += 1
    return end


def _last_nonzero(values: np.ndarray) -> int | None:
    nonzero = values[values != 0]
    return int(nonzero[-1]) if len(nonzero) else None


def _mode_nonzero(values: np.ndarray) -> int | None:
    nonzero = values[values != 0]
    if not len(nonzero):
        return None
    values_, counts = np.unique(nonzero, return_counts=True)
    return int(values_[np.argmax(counts)])


def reconstruct_online_trials(streams: dict[str, np.ndarray]) -> list[OnlineTrial]:
    """Reconstruct one trial for each feedback-phase transition.

    Target identity is recovered from the immediately preceding contiguous phase-2
    window. The BCI selection is recovered from phase 3. Artificial feedback is
    excluded because it overrides the classifier's output.
    """
    missing = set(REQUIRED_TRIAL_STREAMS) - set(streams)
    if missing:
        raise ValueError(f"missing trial streams: {', '.join(sorted(missing))}")
    arrays = {name: np.rint(np.asarray(values)).astype(int) for name, values in streams.items()}
    lengths = {len(values) for values in arrays.values()}
    if len(lengths) != 1:
        raise ValueError("trial streams have unequal lengths")
    phase = arrays["PhaseInSequence"]
    phase3_starts = np.flatnonzero((phase == 3) & np.r_[True, phase[:-1] != 3])
    trials: list[OnlineTrial] = []
    for trial_number, phase3_start in enumerate(phase3_starts, start=1):
        phase3_end = _contiguous_end(phase, int(phase3_start), 3)
        preceding = phase3_start - 1
        if preceding < 0 or phase[preceding] != 2:
            target = None
        else:
            phase2_start = _contiguous_start(phase, preceding, 2)
            target = _last_nonzero(arrays["CurrentTarget"][phase2_start:phase3_start])
        phase3_selected = arrays["SelectedTarget"][phase3_start:phase3_end]
        selected = _mode_nonzero(phase3_selected)
        displayed_feedback = np.any(arrays["DisplayResults"][phase3_start:phase3_end] != 0)
        fake_feedback = np.any(arrays["FakeFeedback"][phase3_start:phase3_end] != 0)
        if not displayed_feedback:
            eligible, correct, reason = False, None, "feedback_not_displayed"
        elif target is None:
            eligible, correct, reason = False, None, "missing_target"
        elif selected is None:
            eligible, correct, reason = False, None, "missing_selected_target"
        elif fake_feedback:
            eligible, correct, reason = False, None, "fake_feedback_override"
        else:
            eligible, correct, reason = True, target == selected, None
        trials.append(
            OnlineTrial(
                trial_number=trial_number,
                phase3_sample=int(phase3_start),
                target=target,
                selected=selected,
                correct=correct,
                eligible=eligible,
                exclusion_reason=reason,
            )
        )
    return trials


def reconstruct_edf_trials(edf_path: Path, relative_path: str) -> pd.DataFrame:
    """Read required EDF state channels and return trial-level online outcomes."""
    raw = mne.io.read_raw_edf(edf_path, preload=False, verbose="ERROR")
    missing = set(REQUIRED_TRIAL_STREAMS) - set(raw.ch_names)
    if missing:
        raise ValueError(f"missing trial channels in {edf_path}: {', '.join(sorted(missing))}")
    streams = {
        name: raw.get_data(picks=[name])[0]
        for name in REQUIRED_TRIAL_STREAMS
    }
    source = parse_source_path(relative_path)
    trials = reconstruct_online_trials(streams)
    rows: list[dict[str, object]] = []
    for trial in trials:
        row = asdict(trial)
        row.update(
            {
                "study": source.study,
                "participant_id": source.participant_id,
                "study_participant_id": source.study_participant_id,
                "session_id": source.session_id,
                "condition": source.condition,
                "relative_path": relative_path,
                "phase3_time_seconds": trial.phase3_sample / raw.info["sfreq"],
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def build_online_trial_table(cache_path: Path) -> pd.DataFrame:
    """Reconstruct all Test-phase outcomes in the verified clinical source cache."""
    tables: list[pd.DataFrame] = []
    for edf_path in select_edf_paths(cache_path):
        relative_path = edf_path.relative_to(cache_path).as_posix()
        if parse_source_path(relative_path).phase == "Test":
            tables.append(reconstruct_edf_trials(edf_path, relative_path))
    if not tables:
        raise ValueError("no Test EDF files found in source cache")
    return pd.concat(tables, ignore_index=True)
