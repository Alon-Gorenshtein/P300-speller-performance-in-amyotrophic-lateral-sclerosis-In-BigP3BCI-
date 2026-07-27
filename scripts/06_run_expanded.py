"""Run the source-study-held-out design across every BigP3BCI cohort that yields online outcomes.

The four-cohort version of this analysis could not put an interval on transportability, because a
between-study variance estimated on three degrees of freedom is not usable. This script widens the
design to every source study with eligible feedback outcomes, keeps the documented ALS cohorts as the
originally targeted primary subgroup, and adds the transfer and moderation questions that only become
answerable once non-ALS cohorts are present.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from bigp3_als.expanded import (
    ALS_STUDIES,
    als_leave_one_cohort_out,
    als_meta_regression,
    als_permutation_test,
    als_random_effects_meta_regression,
    label_cohort_type,
    pool_held_out_metrics,
    study_inventory,
    transfer_to_als,
)
from bigp3_als.heterogeneity import cohort_calibration
from bigp3_als.strengthening import (
    across_session_association,
    null_benchmark,
    participant_level_association,
    session_accuracy_icc,
    within_study_association,
)
from bigp3_als.validation import (
    MODEL_SPECS,
    _fit_probability_model,
    build_analysis_records,
    run_source_study_held_out_validation,
)

POOLED_COLUMNS = (
    "session_mean_absolute_error",
    "character_brier_skill_score",
    "predicted_probability_character_auc",
    "calibration_intercept",
    "calibration_slope",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=Path, default=Path("output/intermediate/online_trials_all20.csv"))
    parser.add_argument("--features", type=Path, default=Path("output/intermediate/calibration_features_all20.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("output/intermediate/file_metadata_all20.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    parser.add_argument("--bootstrap-repetitions", type=int, default=2000)
    arguments = parser.parse_args()

    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    trials = pd.read_csv(arguments.trials)
    features = pd.read_csv(arguments.features)
    metadata = pd.read_csv(arguments.metadata)

    inventory = study_inventory(trials)
    inventory.to_csv(arguments.output_directory / "study_inventory.csv", index=False)
    contributing = inventory.loc[inventory["contributes_outcomes"], "study"].tolist()
    print(f"source studies contributing eligible outcomes: {len(contributing)} of {len(inventory)}")

    records = label_cohort_type(build_analysis_records(trials, features, metadata))
    records.to_csv(arguments.output_directory / "analysis_records.csv", index=False)
    print(
        f"records {len(records)} | participants {records['study_participant_id'].nunique()} "
        f"| studies {records['study'].nunique()} | selections {int(records['n'].sum())}"
    )

    primary = next(spec for spec in MODEL_SPECS if spec.role == "primary")

    predictions, metrics = run_source_study_held_out_validation(
        records, primary, bootstrap_repetitions=arguments.bootstrap_repetitions
    )
    metrics.to_csv(arguments.output_directory / "external_validation_metrics.csv", index=False)
    predictions.to_csv(arguments.output_directory / "external_validation_predictions.csv", index=False)

    pooled = pool_held_out_metrics(metrics, POOLED_COLUMNS)
    pooled.to_csv(arguments.output_directory / "random_effects_pooling.csv", index=False)

    als_records = records.loc[records["als_cohort"]]
    _, als_metrics = run_source_study_held_out_validation(
        als_records, primary, bootstrap_repetitions=arguments.bootstrap_repetitions
    )
    als_metrics.to_csv(arguments.output_directory / "als_subgroup_metrics.csv", index=False)

    transfer = transfer_to_als(records, _fit_probability_model)
    transfer.to_csv(arguments.output_directory / "transfer_to_als.csv", index=False)

    # Cohort type is a study-level attribute, so the cohort is the unit of this comparison. The
    # per-cohort calibration slopes are refitted here from the predictions just produced rather than
    # read back from the heterogeneity script, which runs later and would make the ordering circular.
    calibration = cohort_calibration(predictions, se_method="cluster")
    moderation = {
        "quantity": "cohort calibration slope, cluster-robust",
        "welch_t_test": als_meta_regression(calibration, ALS_STUDIES),
        "exact_permutation_test": als_permutation_test(calibration, ALS_STUDIES),
        "random_effects_meta_regression": als_random_effects_meta_regression(calibration, ALS_STUDIES),
        "leave_one_cohort_out": als_leave_one_cohort_out(calibration, ALS_STUDIES).to_dict(orient="records"),
    }
    (arguments.output_directory / "als_meta_regression.json").write_text(
        json.dumps(moderation, indent=2) + "\n"
    )

    null_benchmark(records).to_csv(arguments.output_directory / "null_benchmark.csv", index=False)
    within_study_association(records).to_csv(arguments.output_directory / "within_study_association.csv", index=False)
    participant_level_association(records).to_csv(
        arguments.output_directory / "participant_level_association.csv", index=False
    )
    pairs, across = across_session_association(records)
    pairs.to_csv(arguments.output_directory / "across_session_pairs.csv", index=False)
    across.to_csv(arguments.output_directory / "across_session_association.csv", index=False)
    (arguments.output_directory / "session_clustering.json").write_text(
        json.dumps(session_accuracy_icc(records), indent=2) + "\n"
    )

    mae = pooled.loc[pooled["quantity"] == "session_mean_absolute_error"]
    if not mae.empty:
        row = mae.iloc[0]
        print(
            f"\nMAE across {int(row['n_studies'])} held-out studies: mean {row['mean']:.4f}, "
            f"between-study SD {row['between_study_sd']:.4f}"
        )
        print(f"  95% CI for the mean      {row['confidence_interval_low']:.4f} to {row['confidence_interval_high']:.4f}")
        print(f"  95% PI for a new study   {row['prediction_interval_low']:.4f} to {row['prediction_interval_high']:.4f}")
    print(f"\nALS cohorts present: {sorted(set(ALS_STUDIES) & set(records['study'].unique()))}")
    print("wrote expanded outputs")


if __name__ == "__main__":
    main()
