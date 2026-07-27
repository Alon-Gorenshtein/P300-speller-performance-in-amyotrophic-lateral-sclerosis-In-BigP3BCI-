"""Export the fitted coefficients of each development fold so any estimate can be recomputed.

The Methods promise that fitted values for every fold are reported, which is a reproducibility
claim a reader will test by taking a session's calibration score and arriving at the estimate the
paper reports. Four numbers per fold are enough: the two logistic coefficients a and b, and the
development mean m and standard deviation d that standardise the score.

The coefficients are not refitted here. Refitting would duplicate the model code and could drift
from it silently. They are recovered from the fitted model itself by asking it for the estimate at
two scores, the development mean and one development standard deviation above it, which standardise
to 0 and 1. The log odds at those two points are a and a + b, because the model is linear in the
standardised score and has one predictor.

Every fold is then reconstructed from its four exported numbers and compared against the model's own
predictions for that fold's records. The script fails if any fold disagrees by more than a tolerance
at the level of floating-point noise, so an exported table that would not let a reader recompute an
estimate cannot be written.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from bigp3_als.validation import MODEL_SPECS, _fit_probability_model, leave_one_study_out

RECONSTRUCTION_TOLERANCE = 1e-10


def _logit(probability: np.ndarray) -> np.ndarray:
    return np.log(probability / (1.0 - probability))


def build_fold_coefficients(records: pd.DataFrame) -> pd.DataFrame:
    """Return one row per development fold with the four numbers that reproduce its estimates."""
    specification = next(spec for spec in MODEL_SPECS if spec.role == "primary")
    feature = specification.features[0]
    modeled = records.dropna(subset=list(specification.features)).copy()

    rows: list[dict[str, object]] = []
    for held_out, development, validation in leave_one_study_out(modeled):
        scores = development[feature].to_numpy(dtype=float)
        location = float(scores.mean())
        scale = float(scores.std(ddof=0))
        probe = pd.DataFrame({feature: [location, location + scale]})
        probe_log_odds = _logit(_fit_probability_model(development, probe, specification.features))
        intercept = float(probe_log_odds[0])
        slope = float(probe_log_odds[1] - probe_log_odds[0])

        held_out_scores = validation[feature].to_numpy(dtype=float)
        reconstructed = 1.0 / (1.0 + np.exp(-(intercept + slope * (held_out_scores - location) / scale)))
        fitted = _fit_probability_model(development, validation, specification.features)
        error = float(np.max(np.abs(reconstructed - fitted)))
        if error > RECONSTRUCTION_TOLERANCE:
            raise ValueError(f"{held_out}: exported coefficients reproduce the fold to only {error:.3e}")

        rows.append(
            {
                "held_out_study": held_out,
                "n_development_records": int(len(development)),
                "n_development_selections": int(development["n"].sum()),
                "intercept_a": intercept,
                "slope_b": slope,
                "development_mean_m": location,
                "development_sd_d": scale,
                "max_reconstruction_error": error,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, default=Path("output/expanded/analysis_records.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    arguments = parser.parse_args()

    table = build_fold_coefficients(pd.read_csv(arguments.records))
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    table.to_csv(arguments.output_directory / "fold_coefficients.csv", index=False)
    print(table.round(6).to_string(index=False))
    print(f"worst reconstruction error across {len(table)} folds: {table['max_reconstruction_error'].max():.3e}")
    print("wrote fold_coefficients.csv")


if __name__ == "__main__":
    main()
