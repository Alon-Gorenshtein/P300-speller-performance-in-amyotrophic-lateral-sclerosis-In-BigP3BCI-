"""Repeat the withheld-cohort evaluation under each of three explicit estimands.

The mapping from calibration score to online spelling accuracy has been fitted on character
expanded rows, so a session contributing 30 characters moved the fit thirty times as far as one
contributing 4 even though the predictor is identical within a session. That is a choice of
estimand, per character rather than per session or per participant, and it was made silently: a
binomial GLM handed grouped successes and failures already weights each record by its own
denominator. This script states the choice by making it a parameter and reporting all three.

Two slopes are reported per row, and the difference between them is the point. `calibration_slope`
scores every fit on the character scale, which is the scale the manuscript already reports, so the
three rows are directly comparable to the published number and to each other.
`calibration_slope_matched_scale` scores each fit on the scale it was fitted for, which is the
slope that row's estimand actually claims. A fit optimised for one weighting will look miscalibrated
when scored under another, so a reader given only the first column would mistake that mismatch for
poor calibration.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from bigp3_als.estimand import compare_estimands


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path,
                        default=Path("output/expanded/analysis_records.csv"))
    parser.add_argument("--feature", default="calibration_auc")
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    arguments = parser.parse_args()

    records = pd.read_csv(arguments.records)
    comparison = compare_estimands(records, arguments.feature)
    comparison.to_csv(arguments.output_directory / "estimand_comparison.csv", index=False)

    print(f"{len(records)} session-condition records, "
          f"{records.groupby(['study', 'study_participant_id', 'session_id']).ngroups} sessions, "
          f"{records.groupby(['study', 'study_participant_id']).ngroups} participants, "
          f"{int(records['n'].sum())} character selections, "
          f"{records['study'].nunique()} source studies held out one at a time")
    print()
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
