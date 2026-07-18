"""Run prespecified external-study validation models."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from bigp3_als.validation import (
    BOOTSTRAP_REPETITIONS,
    MODEL_SPECS,
    build_analysis_records,
    run_source_study_held_out_validation,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=Path, default=Path("output/intermediate/online_trials.csv"))
    parser.add_argument("--features", type=Path, default=Path("output/intermediate/calibration_features.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("output/intermediate/file_metadata.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/final"))
    parser.add_argument(
        "--models",
        nargs="+",
        default=["calibration_auc"],
        help="Prespecified model names. The primary model is the default.",
    )
    parser.add_argument("--bootstrap-repetitions", type=int, default=BOOTSTRAP_REPETITIONS)
    arguments = parser.parse_args()
    records = build_analysis_records(
        pd.read_csv(arguments.trials), pd.read_csv(arguments.features), pd.read_csv(arguments.metadata)
    )
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    records.to_csv(arguments.output_directory / "analysis_records.csv", index=False)
    specifications = [specification for specification in MODEL_SPECS if specification.name in arguments.models]
    if len(specifications) != len(arguments.models):
        known = ", ".join(specification.name for specification in MODEL_SPECS)
        raise ValueError(f"unknown model requested; choose from: {known}")
    predictions, metrics = zip(*(
        run_source_study_held_out_validation(records, specification, arguments.bootstrap_repetitions)
        for specification in specifications
    ))
    pd.concat(predictions, ignore_index=True).to_csv(
        arguments.output_directory / "external_validation_predictions.csv", index=False
    )
    pd.concat(metrics, ignore_index=True).to_csv(
        arguments.output_directory / "external_validation_metrics.csv", index=False
    )
    print(f"validated {len(specifications)} models across {len(records)} session-condition records")


if __name__ == "__main__":
    main()
