"""Tests for sensitivity analysis boundaries."""

from __future__ import annotations

import pandas as pd

from bigp3_als.sensitivity import leave_one_participant_out


def test_leave_one_participant_out_never_uses_that_participant_for_training() -> None:
    records = pd.DataFrame(
        {
            "study": ["StudyF", "StudyF", "StudyF"],
            "study_participant_id": ["StudyF:F_01", "StudyF:F_02", "StudyF:F_03"],
        }
    )

    splits = list(leave_one_participant_out(records))

    assert len(splits) == 3
    for participant, development, validation in splits:
        assert participant not in set(development.study_participant_id)
        assert set(validation.study_participant_id) == {participant}
