"""Quantify what local recalibration costs, in participants and in character selections."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from bigp3_als.recalibration import common_cohorts, recalibration_draws, recalibration_summary

PRIMARY_MODEL = "calibration_auc"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path,
                        default=Path("output/expanded/external_validation_predictions.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    parser.add_argument("--draws", type=int, default=200)
    arguments = parser.parse_args()

    predictions = pd.read_csv(arguments.predictions)
    predictions = predictions.loc[predictions["model"] == PRIMARY_MODEL].copy()
    if predictions.empty:
        raise SystemExit(f"no rows for model {PRIMARY_MODEL}")

    draws = recalibration_draws(predictions, draws=arguments.draws)
    summary = recalibration_summary(draws)

    # The all-available summary above uses more data at each size on its own, but its cohort mix
    # shrinks and gets easier as the size grows (see common_cohorts docstring). This second summary
    # is restricted to the cohorts large enough to appear at every size, so it is the one that
    # actually traces a learning curve rather than a curve confounded with cohort composition.
    balanced_cohorts = common_cohorts(draws)
    balanced_summary = recalibration_summary(draws, cohorts=balanced_cohorts)

    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    draws.to_csv(arguments.output_directory / "recalibration_draws.csv", index=False)
    summary.to_csv(arguments.output_directory / "recalibration_summary.csv", index=False)
    balanced_summary.to_csv(arguments.output_directory / "recalibration_summary_balanced.csv", index=False)

    print("All-available cohorts at each size:")
    print(summary.to_string(index=False))
    print(f"\nBalanced ladder ({len(balanced_cohorts)} cohorts present at every tested size):")
    print(balanced_summary.to_string(index=False))


if __name__ == "__main__":
    main()
