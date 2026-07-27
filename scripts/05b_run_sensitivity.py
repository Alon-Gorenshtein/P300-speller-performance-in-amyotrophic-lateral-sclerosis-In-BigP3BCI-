"""Run the robustness checks of the original four-cohort design, after the primary analysis is frozen.

These were listed before they were run, but no analysis plan was registered, so they are not
prespecified in the sense a registered plan would establish.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from bigp3_als.sensitivity import run_within_study_lopo, summarize_trial_exclusions
from bigp3_als.validation import MODEL_SPECS, build_analysis_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=Path, default=Path("output/intermediate/online_trials.csv"))
    parser.add_argument("--features", type=Path, default=Path("output/intermediate/calibration_features.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("output/intermediate/file_metadata.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/final"))
    arguments = parser.parse_args()
    trials = pd.read_csv(arguments.trials)
    records = build_analysis_records(trials, pd.read_csv(arguments.features), pd.read_csv(arguments.metadata))
    primary_specification = next(specification for specification in MODEL_SPECS if specification.role == "primary")
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    run_within_study_lopo(records, primary_specification).to_csv(
        arguments.output_directory / "within_study_lopo_sensitivity.csv", index=False
    )
    summarize_trial_exclusions(trials).to_csv(
        arguments.output_directory / "trial_exclusion_summary.csv", index=False
    )
    print("wrote leave-one-participant-out and exclusion robustness outputs")


if __name__ == "__main__":
    main()
