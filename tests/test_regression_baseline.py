"""The four-cohort result is frozen. Any change to shared code must not move it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

BASELINE = {
    "session_mean_absolute_error": 0.095282,
    "character_brier_score": 0.110083,
    "character_brier_skill_score": 0.287339,
    "predicted_probability_character_auc": 0.827604,
    "calibration_intercept": 0.021516,
    "calibration_slope": 0.991029,
}


@pytest.mark.slow
def test_four_cohort_primary_is_unchanged(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, "scripts/05_run_validation.py",
         "--trials", "output/intermediate/online_trials_with_b.csv",
         "--features", "output/intermediate/calibration_features_with_b.csv",
         "--metadata", "output/intermediate/file_metadata_with_b.csv",
         "--output-directory", str(tmp_path)],
        check=True,
    )
    metrics = pd.read_csv(tmp_path / "external_validation_metrics.csv")
    pooled = metrics.loc[metrics["held_out_study"].str.startswith("Pooled")].iloc[0]
    for name, expected in BASELINE.items():
        assert pooled[name] == pytest.approx(expected, abs=1e-6), name
