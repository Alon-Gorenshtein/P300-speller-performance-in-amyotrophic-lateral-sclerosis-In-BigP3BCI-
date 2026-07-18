"""Tests for study-held-out clinical validation."""

from __future__ import annotations

import pandas as pd

from bigp3_als.validation import leave_one_study_out


def test_leave_one_study_out_never_mixes_the_held_out_study_into_development() -> None:
    records = pd.DataFrame(
        {
            "study": ["StudyF", "StudyF", "StudyL", "StudyN"],
            "study_participant_id": ["StudyF:F_01", "StudyF:F_02", "StudyL:L_01", "StudyN:N_01"],
            "correct": [5, 4, 3, 2],
            "n": [6, 6, 6, 6],
            "calibration_auc": [0.9, 0.8, 0.7, 0.6],
        }
    )

    splits = list(leave_one_study_out(records))

    assert {held_out for held_out, _, _ in splits} == {"StudyF", "StudyL", "StudyN"}
    for held_out, development, validation in splits:
        assert set(development.study) == set(records.study) - {held_out}
        assert set(validation.study) == {held_out}
        assert not set(development.study_participant_id) & set(validation.study_participant_id)
