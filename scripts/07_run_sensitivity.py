"""Prespecified sensitivity analyses for the widened design.

Each analysis removes one explanation for the primary result and re-runs the whole withheld-cohort
procedure on what remains. The reported quantity is the study-level summary rather than the
participant bootstrap, because the question each sensitivity asks is whether the spread across
cohorts changes, not whether the mean shifts within the observed cohorts.
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from bigp3_als.expanded import label_cohort_type, pool_held_out_metrics, random_effects_pooling
from bigp3_als.validation import (
    MODEL_SPECS,
    _expanded_binary,
    _fit_calibration_model,
    _fit_probability_model,
    build_analysis_records,
    run_source_study_held_out_validation,
)

METRIC = "session_mean_absolute_error"
CALIBRATION = "calibration_slope"


def _summarise(records: pd.DataFrame, label: str, replicates: int) -> dict[str, object]:
    primary = next(spec for spec in MODEL_SPECS if spec.role == "primary")
    if records["study"].nunique() < 3:
        return {"analysis": label, "n_studies": records["study"].nunique(), "note": "too few cohorts"}
    _, metrics = run_source_study_held_out_validation(records, primary, bootstrap_repetitions=replicates)
    pooled = pool_held_out_metrics(metrics, (METRIC, CALIBRATION))
    mae = pooled.loc[pooled["quantity"] == METRIC].iloc[0]
    slope = pooled.loc[pooled["quantity"] == CALIBRATION].iloc[0]
    return {
        "analysis": label,
        "n_studies": int(mae["n_studies"]),
        "n_records": int(len(records)),
        "n_selections": int(records["n"].sum()),
        "mae_mean": mae["mean"],
        "mae_between_study_sd": mae["between_study_sd"],
        "mae_prediction_low": mae["prediction_interval_low"],
        "mae_prediction_high": mae["prediction_interval_high"],
        "slope_mean": slope["mean"],
        "slope_between_study_sd": slope["between_study_sd"],
        "slope_prediction_low": slope["prediction_interval_low"],
        "slope_prediction_high": slope["prediction_interval_high"],
    }


def _leave_two_studies_out(records: pd.DataFrame, label: str) -> dict[str, object]:
    """Withhold every pair of cohorts at once, so development runs on 16 cohorts rather than 17.

    The primary analysis withholds one cohort and develops on the other 17. This asks whether the
    result depends on having that many, which is the question a reader with sixteen cohorts of their
    own would ask.

    Each cohort sits in 17 of the pairs, so it collects 17 estimates; those are averaged into one
    value per cohort before pooling. The row is therefore summarised over 18 cohort-level values by
    the same random-effects pooling as every other row, and its between-cohort standard deviation and
    interval carry the same meaning. Summarising the pairs themselves would not: a pair shares a
    cohort with 32 other pairs, so their spread is not a spread over independent units.

    No bootstrap is run here. The comparison of interest is against the primary row of this same
    table, computed on the same records, and the between-cohort spread is what the comparison turns
    on.
    """
    primary = next(spec for spec in MODEL_SPECS if spec.role == "primary")
    studies = sorted(records["study"].unique())
    collected: dict[str, dict[str, list[float]]] = {study: {"mae": [], "slope": []} for study in studies}
    n_splits = 0
    for held_out in itertools.combinations(studies, 2):
        development = records.loc[~records["study"].isin(held_out)]
        validation = records.loc[records["study"].isin(held_out)]
        if development["study"].nunique() < 3 or validation.empty:
            continue
        n_splits += 1
        evaluated = validation.assign(
            predicted_probability=_fit_probability_model(development, validation, primary.features)
        )
        for study in held_out:
            cohort = evaluated.loc[evaluated["study"] == study]
            observed = cohort["correct"] / cohort["n"]
            collected[study]["mae"].append(float((observed - cohort["predicted_probability"]).abs().mean()))
            labels, probabilities = _expanded_binary(cohort)
            collected[study]["slope"].append(_fit_calibration_model(labels, probabilities)[1])

    if n_splits == 0:
        # Below five cohorts no pair leaves three to develop on, so the analysis has nothing to
        # report. Say so in the same shape the other rows use rather than raise inside the pooling.
        return {"analysis": label, "n_studies": len(studies), "note": "too few cohorts"}

    per_cohort_mae = pd.Series({study: float(np.mean(values["mae"])) for study, values in collected.items()})
    per_cohort_slope = pd.Series({study: float(np.nanmean(values["slope"])) for study, values in collected.items()})
    mae = random_effects_pooling(per_cohort_mae, label=METRIC)
    slope = random_effects_pooling(per_cohort_slope, label=CALIBRATION)
    return {
        "analysis": f"{label} ({n_splits} splits)",
        "n_studies": int(mae["n_studies"]),
        "n_records": int(len(records)),
        "n_selections": int(records["n"].sum()),
        "mae_mean": mae["mean"],
        "mae_between_study_sd": mae["between_study_sd"],
        "mae_prediction_low": mae["prediction_interval_low"],
        "mae_prediction_high": mae["prediction_interval_high"],
        "slope_mean": slope["mean"],
        "slope_between_study_sd": slope["between_study_sd"],
        "slope_prediction_low": slope["prediction_interval_low"],
        "slope_prediction_high": slope["prediction_interval_high"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=Path, default=Path("output/intermediate/online_trials_all20.csv"))
    parser.add_argument("--features", type=Path, default=Path("output/intermediate/calibration_features_all20.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("output/intermediate/file_metadata_all20.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    parser.add_argument("--bootstrap-repetitions", type=int, default=50)
    arguments = parser.parse_args()

    records = label_cohort_type(
        build_analysis_records(
            pd.read_csv(arguments.trials), pd.read_csv(arguments.features), pd.read_csv(arguments.metadata)
        )
    )
    records = records.dropna(subset=["calibration_auc"]).copy()
    records["accuracy"] = records["correct"] / records["n"]

    rows = [_summarise(records, "primary (all contributing cohorts)", arguments.bootstrap_repetitions)]

    # Cohorts where almost every session is at ceiling leave little to estimate, so the error is
    # small for reasons unrelated to the predictor.
    spread = records.groupby("study")["accuracy"].std()
    informative = spread.loc[spread >= 0.10].index
    rows.append(
        _summarise(
            records.loc[records["study"].isin(informative)],
            "cohorts with outcome standard deviation at least 0.10",
            arguments.bootstrap_repetitions,
        )
    )

    rows.append(
        _summarise(
            records.loc[records["artifact_rejection_fraction"] <= 0.20],
            "records with artifact rejection at most 20 percent",
            arguments.bootstrap_repetitions,
        )
    )

    rows.append(
        _summarise(
            records.loc[records["n"] >= 10],
            "records with at least 10 eligible selections",
            arguments.bootstrap_repetitions,
        )
    )

    rows.append(
        _summarise(
            records.loc[~records["als_cohort"]],
            "other cohorts only",
            arguments.bootstrap_repetitions,
        )
    )
    rows.append(
        _summarise(
            records.loc[records["als_cohort"]],
            "ALS cohorts only (prespecified primary subgroup)",
            arguments.bootstrap_repetitions,
        )
    )

    rows.append(_leave_two_studies_out(records, "leave-two-studies-out development"))

    table = pd.DataFrame(rows)
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    table.to_csv(arguments.output_directory / "sensitivity_analyses.csv", index=False)
    for _, row in table.iterrows():
        if "note" in row and isinstance(row.get("note"), str):
            print(f"{row['analysis']:52s} {row['note']}")
            continue
        print(
            f"{row['analysis']:52s} studies {int(row['n_studies']):2d}  "
            f"MAE {row['mae_mean']:.4f} (SD {row['mae_between_study_sd']:.4f}) "
            f"PI [{row['mae_prediction_low']:.4f}, {row['mae_prediction_high']:.4f}]  "
            f"slope SD {row['slope_between_study_sd']:.3f}"
        )
    print("wrote sensitivity_analyses.csv")


if __name__ == "__main__":
    main()
