"""Withheld-cohort performance of every comparator predictor named in the Methods.

The comparators were listed in the Methods before they were run on the widened cohort, but
after the primary widened analysis had been fitted, and no analysis plan was registered, so
they are not prespecified in the sense a registered plan would establish.

The Methods name five comparator scores and one exploratory score alongside the primary one, so the
supplement has to report what they did rather than only that they were computed. Each specification
is run through the identical withheld-cohort procedure, and the row reports the pooled held-out
metrics together with the spread of the per-cohort results, because the question a comparator has to
answer in this paper is not only whether it estimates accuracy better but whether its mapping
transports any better.

No participant bootstrap is run. The primary predictor's intervals are reported in the main text
from 2,000 replicates, and rerunning that bootstrap at a smaller replicate count for this sweep
would put a second, slightly different interval for the same primary quantity into the same paper.
The uncertainty this table reports instead is the between-cohort spread, which is the quantity the
paper's argument turns on and which needs no resampling: the per-cohort estimation errors are
summarised by the same random-effects pooling used for the sensitivity table, and the calibration
slope by its uncorrected spread and range across cohorts.

The exploratory ALSFRS-R specification is restricted to the records carrying an observed ALSFRS-R
value, which is 3 of the 18 cohorts. Its row is therefore not comparable with the others, and the
cohort and record counts are reported on every row so that is visible. A final row runs the primary
predictor alone on those same restricted records, because otherwise the exploratory row invites the
reading that adding ALSFRS-R improved the estimate, when the comparison it actually supports is
against a different and much easier set of cohorts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from bigp3_als.expanded import random_effects_pooling
from bigp3_als.validation import MODEL_SPECS, ModelSpecification, run_source_study_held_out_validation

POOLED_PREFIX = "Pooled"
METRIC = "session_mean_absolute_error"


def _comparator_row(records: pd.DataFrame, specification: ModelSpecification) -> dict[str, object]:
    modeled = records.dropna(subset=list(specification.features)).copy()
    _, metrics = run_source_study_held_out_validation(modeled, specification, bootstrap_repetitions=0)
    per_cohort = metrics.loc[~metrics["held_out_study"].astype(str).str.startswith(POOLED_PREFIX)]
    pooled = metrics.loc[metrics["held_out_study"].astype(str).str.startswith(POOLED_PREFIX)].iloc[0]
    error = random_effects_pooling(per_cohort[METRIC], label=METRIC, transform="log")
    slopes = per_cohort["calibration_slope"].to_numpy(dtype=float)
    return {
        "predictor": specification.name,
        "role": specification.role,
        "n_cohorts": int(len(per_cohort)),
        "n_records": int(len(modeled)),
        "n_selections": int(modeled["n"].sum()),
        "mae": float(pooled[METRIC]),
        "brier": float(pooled["character_brier_score"]),
        "brier_skill": float(pooled["character_brier_skill_score"]),
        "auc": float(pooled["predicted_probability_character_auc"]),
        "intercept": float(pooled["calibration_intercept"]),
        "slope": float(pooled["calibration_slope"]),
        "cohort_mae_mean": error["mean"],
        "cohort_mae_sd": error["between_study_sd"],
        "cohort_mae_prediction_low": error["prediction_interval_low"],
        "cohort_mae_prediction_high": error["prediction_interval_high"],
        "cohort_slope_sd": float(np.nanstd(slopes, ddof=1)),
        "cohort_slope_low": float(np.nanmin(slopes)),
        "cohort_slope_high": float(np.nanmax(slopes)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, default=Path("output/expanded/analysis_records.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    arguments = parser.parse_args()

    records = pd.read_csv(arguments.records)
    # No specification is caught and skipped. The supplement claims results for every named
    # predictor, so a specification that silently dropped out would make that claim false while the
    # table still looked complete. A failure here has to stop the run.
    rows = [_comparator_row(records, specification) for specification in MODEL_SPECS]

    exploratory = next((spec for spec in MODEL_SPECS if spec.role == "exploratory"), None)
    if exploratory is not None:
        primary = next(spec for spec in MODEL_SPECS if spec.role == "primary")
        reference = _comparator_row(records.dropna(subset=list(exploratory.features)), primary)
        reference["predictor"] = f"{primary.name} on the same restricted records"
        reference["role"] = "exploratory reference"
        rows.append(reference)

    table = pd.DataFrame(rows)
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    table.to_csv(arguments.output_directory / "comparator_metrics.csv", index=False)
    print(table.round(3).to_string(index=False))
    print("wrote comparator_metrics.csv")


if __name__ == "__main__":
    main()
