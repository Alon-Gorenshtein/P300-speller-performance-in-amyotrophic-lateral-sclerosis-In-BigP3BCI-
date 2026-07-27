"""Regenerate the two predictor-precision outputs and report the disattenuated heterogeneity.

`predictor_precision.csv` and `predictor_reliability.csv` are both promised by name in the
supplement's frozen-output inventory, but until this script existed neither had a pipeline stage
behind it: they were produced once from an interactive call and left on disk. A reader who took the
availability statement at its word could not regenerate them, and nothing would have caught them
drifting from the code that made them. This script is that stage. It writes both files from the
frozen inputs and refuses to finish if either has drifted from what is already on disk.

It also prints the quantities the supplement reports but does not store: the per-cohort reliability
range, the heterogeneity of the calibration slope before and after every cohort's slope is corrected
for attenuation by its own reliability, and the stress test that inflates the assumed measurement
error out to the identifiability limit. Those are printed rather than written because they are three
scalars and a seven-row table read once into prose, not an artifact anything downstream consumes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from bigp3_als.predictor_precision import (
    disattenuated_heterogeneity,
    identifiability_limit,
    precision_table,
    reliability_inflation_sensitivity,
    reliability_ratio,
)

# Strictly below the identifiability limit, past which at least one cohort's assumed measurement
# error would exceed its entire observed spread and its reliability would not be identified.
INFLATION_FACTORS = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 6.5)


def _check_against_disk(table: pd.DataFrame, path: Path, tolerance: float = 1e-9) -> None:
    """Fail loudly if a regenerated output disagrees with the frozen one it overwrites."""
    if not path.exists():
        print(f"  {path.name}: no frozen copy on disk, writing a new one")
        return
    frozen = pd.read_csv(path)
    if list(frozen.columns) != list(table.columns) or len(frozen) != len(table):
        raise SystemExit(
            f"{path.name} has changed shape: frozen {frozen.shape} against regenerated {table.shape}"
        )
    numeric = table.select_dtypes("number").columns
    drift = (frozen[numeric] - table[numeric].reset_index(drop=True)).abs().max().max()
    if drift > tolerance:
        raise SystemExit(f"{path.name} drifted from the frozen copy by {drift:.3e}")
    print(f"  {path.name}: reproduces the frozen copy (max drift {drift:.3e})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path,
                        default=Path("output/intermediate/calibration_features_all20.csv"))
    parser.add_argument("--predictions", type=Path,
                        default=Path("output/expanded/external_validation_predictions.csv"))
    parser.add_argument("--calibration", type=Path,
                        default=Path("output/expanded/cohort_calibration.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    arguments = parser.parse_args()

    features = pd.read_csv(arguments.features)
    predictions = pd.read_csv(arguments.predictions)
    calibration = pd.read_csv(arguments.calibration)

    precision = precision_table(features, predictions)
    reliability = reliability_ratio(predictions)

    print("regenerated outputs:")
    _check_against_disk(precision, arguments.output_directory / "predictor_precision.csv")
    _check_against_disk(reliability, arguments.output_directory / "predictor_reliability.csv")
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    precision.to_csv(arguments.output_directory / "predictor_precision.csv", index=False)
    reliability.to_csv(arguments.output_directory / "predictor_reliability.csv", index=False)

    finite = reliability["reliability"].dropna()
    print(f"\nreliability ratio across {len(reliability)} cohorts: "
          f"{finite.min():.4f} to {finite.max():.4f}, median {finite.median():.4f}; "
          f"{int((finite >= 0.95).sum())} of {len(finite)} at or above 0.95")

    result = disattenuated_heterogeneity(reliability, calibration)
    for name in ("observed", "disattenuated"):
        block = result[name]
        print(f"  {name:14s} tau {block['tau']:.4f}  I2 {block['i_squared']:.2f}  "
              f"Q {block['q_statistic']:.2f}  p {block['q_p_value']:.3e}")
    print(f"  slope range {result['observed_slope_min']:.3f} to {result['observed_slope_max']:.3f} "
          f"observed, {result['disattenuated_slope_min']:.3f} to "
          f"{result['disattenuated_slope_max']:.3f} disattenuated")

    limit = identifiability_limit(predictions)
    print(f"\nerror-variance inflation stress test, identifiability limit {limit:.4f}:")
    sensitivity = reliability_inflation_sensitivity(
        predictions, calibration, factors=INFLATION_FACTORS
    )
    print(sensitivity.to_string(index=False))
    print(f"\nI2 never falls below {sensitivity['i_squared'].min():.2f} and the Q p-value never "
          f"rises above {sensitivity['q_p_value'].max():.3e} anywhere in that range")


if __name__ == "__main__":
    main()
