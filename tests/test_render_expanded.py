"""Tests for the widened-design figures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bigp3_als.render_expanded import render_skill_by_cohort
from bigp3_als.strengthening import null_benchmark
from tests.test_strengthening import _records


def _metrics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"held_out_study": "StudyF", "session_mean_absolute_error": 0.05},
            {"held_out_study": "StudyL", "session_mean_absolute_error": 0.20},
            {"held_out_study": "Pooled held-out records", "session_mean_absolute_error": 0.12},
        ]
    )


def test_skill_figure_reads_the_benchmark_column_null_benchmark_writes(tmp_path: Path) -> None:
    # Guards the column name across the module boundary: null_benchmark writes it and this figure
    # reads it, so a rename on one side and not the other would only surface at figure-build time.
    render_skill_by_cohort(_metrics(), null_benchmark(_records()), ("StudyF",), tmp_path)

    assert (tmp_path / "figure_skill_by_cohort.png").exists()
