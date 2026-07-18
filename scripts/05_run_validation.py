"""Run prespecified external-study validation models."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from bigp3_als.validation import MODEL_SPECS, build_analysis_records, run_external_validation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=Path, default=Path("output/intermediate/online_trials.csv"))
    parser.add_argument("--features", type=Path, default=Path("output/intermediate/calibration_features.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("output/intermediate/file_metadata.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/final"))
    arguments = parser.parse_args()
    records = build_analysis_records(
        pd.read_csv(arguments.trials), pd.read_csv(arguments.features), pd.read_csv(arguments.metadata)
    )
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    records.to_csv(arguments.output_directory / "analysis_records.csv", index=False)
    predictions, metrics = zip(*(run_external_validation(records, specification) for specification in MODEL_SPECS))
    pd.concat(predictions, ignore_index=True).to_csv(
        arguments.output_directory / "external_validation_predictions.csv", index=False
    )
    pd.concat(metrics, ignore_index=True).to_csv(
        arguments.output_directory / "external_validation_metrics.csv", index=False
    )
    print(f"validated {len(MODEL_SPECS)} models across {len(records)} session-condition records")


if __name__ == "__main__":
    main()
