"""Put every alignment and nonlinear arm through the primary transportability procedure.

The question these arms answer is not whether they discriminate better. It is whether a mapping
fitted on 17 cohorts holds in the eighteenth, which is the quantity the paper's conclusion rests on,
so each arm is summarised by the same random-effects tau, the same prediction interval and the same
pooled estimation error as the primary score, computed by the same functions.

No participant bootstrap is run, for the reason `11_run_comparators.py` gives: the primary
predictor's intervals are already reported from 2,000 replicates in the main text, and a second,
slightly different interval for the same quantity does not belong in the same paper.

Predictor-side alignment (all four alignment arms here) can only remove between-cohort differences
in the score's scale and location. It cannot remove between-cohort differences in the accuracy level
itself, which is what the calibration intercept measures. An intercept tau that barely moves against
the primary score's is therefore the expected structural outcome of this class of correction, not
evidence that the alignment was computed wrong; the slope is the parameter these arms can genuinely
move.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from bigp3_als.alignment import ALIGNMENT_SPECS, cohort_standardised
from bigp3_als.expanded import random_effects_pooling
from bigp3_als.heterogeneity import cohort_calibration, random_effects
from bigp3_als.validation import MODEL_SPECS, ModelSpecification, run_source_study_held_out_validation

KEYS = ["study", "study_participant_id", "session_id"]
POOLED_PREFIX = "Pooled"
METRIC = "session_mean_absolute_error"
PRIMARY = next(spec for spec in MODEL_SPECS if spec.name == "calibration_auc")


def _summarise(records: pd.DataFrame, specification: ModelSpecification) -> tuple[dict, pd.DataFrame]:
    modeled = records.dropna(subset=list(specification.features)).copy()
    predictions, metrics = run_source_study_held_out_validation(
        modeled, specification, bootstrap_repetitions=0
    )
    per_cohort = metrics.loc[~metrics["held_out_study"].astype(str).str.startswith(POOLED_PREFIX)]
    pooled = metrics.loc[metrics["held_out_study"].astype(str).str.startswith(POOLED_PREFIX)].iloc[0]
    # cohort_calibration keeps only model_role == "primary" predictions and raises if that leaves
    # nothing (heterogeneity.py:~130). run_source_study_held_out_validation always stamps model_role
    # with this specification's own role, so every non-primary arm would be filtered to empty and
    # raise. That guard protects the frozen primary path's other callers and is not touched here;
    # dropping the column at this call site is the correct place to bypass it for a non-primary arm.
    calibration = cohort_calibration(predictions.drop(columns=["model_role"]), se_method="cluster")
    calibration.insert(0, "arm", specification.name)
    indexed = calibration.set_index("held_out_study")
    slope = random_effects(indexed["slope"], indexed["slope_se"])
    intercept = random_effects(indexed["intercept"], indexed["intercept_se"])
    error = random_effects_pooling(per_cohort[METRIC], label=METRIC, transform="log")
    row = {
        "arm": specification.name,
        "role": specification.role,
        "n_cohorts": int(len(per_cohort)),
        "n_records": int(len(modeled)),
        "n_selections": int(modeled["n"].sum()),
        "mae": float(pooled[METRIC]),
        "brier_skill": float(pooled["character_brier_skill_score"]),
        "character_auc": float(pooled["predicted_probability_character_auc"]),
        "mae_prediction_low": float(error["prediction_interval_low"]),
        "mae_prediction_high": float(error["prediction_interval_high"]),
        "slope_pooled": slope["pooled"],
        "slope_tau": slope["tau"],
        "slope_i_squared": slope["i_squared"],
        "slope_prediction_low": slope["prediction_interval_low"],
        "slope_prediction_high": slope["prediction_interval_high"],
        "intercept_pooled": intercept["pooled"],
        "intercept_tau": intercept["tau"],
        "intercept_i_squared": intercept["i_squared"],
        "intercept_prediction_low": intercept["prediction_interval_low"],
        "intercept_prediction_high": intercept["prediction_interval_high"],
        "n_cohorts_dropped_slope": slope["n_dropped"],
        "n_cohorts_dropped_intercept": intercept["n_dropped"],
    }
    return row, calibration


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, default=Path("output/expanded/analysis_records.csv"))
    parser.add_argument("--alignment-features", type=Path,
                        default=Path("output/intermediate/calibration_features_all20_alignment.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    arguments = parser.parse_args()

    records = pd.read_csv(arguments.records)
    extra = pd.read_csv(arguments.alignment_features)
    columns = [column for column in extra.columns
               if column.startswith("calibration_auc_") and column != "calibration_auc_reproduced"]
    records = records.merge(extra[[*KEYS, *columns]], on=KEYS, how="left", validate="many_to_one")
    records["calibration_auc_cohort_z"] = cohort_standardised(records, "calibration_auc", "z")
    records["calibration_auc_cohort_rank"] = cohort_standardised(records, "calibration_auc", "rank")

    specs = [PRIMARY, *[spec for spec in ALIGNMENT_SPECS if spec.features[0] in records.columns]]
    rows, calibrations = [], []
    for specification in specs:
        available = int(records[specification.features[0]].notna().sum())
        print(f"{specification.name}: {available} of {len(records)} records carry the score")
        if available < len(records):
            print(f"  warning: {len(records) - available} records dropped for this arm")
        row, calibration = _summarise(records, specification)
        rows.append(row)
        calibrations.append(calibration)
        print(f"  tau slope {row['slope_tau']:.3f}  tau intercept {row['intercept_tau']:.3f}  "
              f"MAE {row['mae']:.4f}")

    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(arguments.output_directory / "alignment_transport.csv", index=False)
    pd.concat(calibrations, ignore_index=True).to_csv(
        arguments.output_directory / "alignment_cohort_calibration.csv", index=False
    )
    print(f"wrote {len(rows)} arms")


if __name__ == "__main__":
    main()
