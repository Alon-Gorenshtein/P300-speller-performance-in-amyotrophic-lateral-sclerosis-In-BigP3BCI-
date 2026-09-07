"""Quantify what local recalibration costs, in participants and in character selections."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from bigp3_als.recalibration import recalibration_draws, recalibration_summary

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

    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    draws.to_csv(arguments.output_directory / "recalibration_draws.csv", index=False)
    summary.to_csv(arguments.output_directory / "recalibration_summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
