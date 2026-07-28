"""Jointly bootstrap all 18 leave-one-study-out folds to measure their shared-development covariance.

The primary random-effects pooling in ``scripts/06_run_expanded.py`` treats the 18 held-out
calibration-intercept and calibration-slope estimates as statistically independent draws. They are
not: any two leave-one-study-out folds share up to 16 of 17 development cohorts, so a bootstrap that
resamples each held-out cohort's participants independently per fold (as ``_bootstrap_intervals`` in
``validation.py`` and ``_bootstrap_standard_errors`` in ``heterogeneity.py`` both do) cannot see that
shared-development correlation. This script instead draws one joint resample of every cohort's
participants per replicate and refits all 18 folds from that same resampled dataset, so the
correlation the shared development data induces between folds shows up directly in the resulting
empirical covariance matrix.

The two summary quantities this script prints, ``replicate_between_cohort_sd_intercept`` and
``_slope``, are not a dependence-aware substitute for the meta-analytic tau reported elsewhere in
this codebase: studies are never resampled here, only the participants within each fixed cohort, so
the spread across the 18 held-out estimates within one replicate mixes genuine between-cohort
heterogeneity with each fold's own within-cohort sampling noise (see
``joint_bootstrap_fold_covariance``'s docstring in ``validation.py`` for the full argument). Report it
as an empirical, assumption-light quantity that combines both sources of spread, not as a corrected
tau.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from bigp3_als.expanded import label_cohort_type
from bigp3_als.validation import (
    BOOTSTRAP_REPETITIONS,
    MODEL_SPECS,
    build_analysis_records,
    joint_bootstrap_fold_covariance,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=Path, default=Path("output/intermediate/online_trials_all20.csv"))
    parser.add_argument("--features", type=Path, default=Path("output/intermediate/calibration_features_all20.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("output/intermediate/file_metadata_all20.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    parser.add_argument("--bootstrap-repetitions", type=int, default=BOOTSTRAP_REPETITIONS)
    arguments = parser.parse_args()

    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    trials = pd.read_csv(arguments.trials)
    features = pd.read_csv(arguments.features)
    metadata = pd.read_csv(arguments.metadata)

    records = label_cohort_type(build_analysis_records(trials, features, metadata))
    print(
        f"records {len(records)} | participants {records['study_participant_id'].nunique()} "
        f"| studies {records['study'].nunique()}"
    )

    primary_spec = next(spec for spec in MODEL_SPECS if spec.role == "primary")

    result = joint_bootstrap_fold_covariance(
        records, primary_spec, repetitions=arguments.bootstrap_repetitions
    )

    covariance = result["covariance_matrix"].copy()
    covariance.index.name = "term"
    covariance.reset_index().to_csv(arguments.output_directory / "joint_bootstrap_covariance.csv", index=False)

    correlation = result["correlation_matrix"].copy()
    correlation.index.name = "term"
    correlation.reset_index().to_csv(arguments.output_directory / "joint_bootstrap_correlation.csv", index=False)

    # Per-cohort replicate diagnostics: how many of the `repetitions` joint replicates produced a
    # fit for this cohort that survived the separation guards in `_fit_calibration_model_guarded`,
    # alongside the `repetitions // 2` threshold that decides whether the cohort is reported as
    # identified under this method. Same columns and the same convention as
    # `scripts/08_run_heterogeneity.py`'s `bootstrap_replicate_diagnostics.csv`, so the two are
    # directly comparable.
    diagnostics = pd.DataFrame(
        {
            "held_out_study": result["studies"],
            "n_finite_replicates": [result["n_finite_per_study"][study] for study in result["studies"]],
            "repetitions": result["n_replicates"],
            "discard_threshold": result["discard_threshold"],
            "identified": [result["identified_per_study"][study] for study in result["studies"]],
        }
    )
    diagnostics.to_csv(arguments.output_directory / "joint_bootstrap_replicate_diagnostics.csv", index=False)

    summary = {
        "n_replicates": result["n_replicates"],
        "n_finite_per_study": result["n_finite_per_study"],
        "discard_threshold": result["discard_threshold"],
        "identified_per_study": result["identified_per_study"],
        "replicate_between_cohort_sd_intercept": result["replicate_between_cohort_sd_intercept"],
        "replicate_between_cohort_sd_slope": result["replicate_between_cohort_sd_slope"],
    }
    (arguments.output_directory / "joint_bootstrap_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )

    print(f"n_replicates: {result['n_replicates']}")
    print(f"n_finite_per_study: {result['n_finite_per_study']}")
    print(
        f"identified (>= {result['discard_threshold']} of {result['n_replicates']} replicates): "
        f"{result['identified_per_study']}"
    )
    print(f"replicate_between_cohort_sd_intercept: {result['replicate_between_cohort_sd_intercept']}")
    print(f"replicate_between_cohort_sd_slope: {result['replicate_between_cohort_sd_slope']}")
    print("wrote joint bootstrap outputs")


if __name__ == "__main__":
    main()
