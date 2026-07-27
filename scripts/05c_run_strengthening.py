"""Establish what the calibration score adds beyond trivial alternatives.

Run after the primary analysis is frozen. Produces the reference points a reader needs in order to
judge the primary estimation error, plus the across-session ordering that matches how a calibration
recording would actually be used.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from bigp3_als.strengthening import (
    across_session_association,
    null_benchmark,
    participant_level_association,
    session_accuracy_icc,
    within_study_association,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, default=Path("output/final/analysis_records.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/final"))
    parser.add_argument("--feature", default="calibration_auc")
    arguments = parser.parse_args()

    records = pd.read_csv(arguments.records)
    arguments.output_directory.mkdir(parents=True, exist_ok=True)

    benchmark = null_benchmark(records)
    benchmark.to_csv(arguments.output_directory / "null_benchmark.csv", index=False)

    within = within_study_association(records, feature=arguments.feature)
    within.to_csv(arguments.output_directory / "within_study_association.csv", index=False)

    participant = participant_level_association(records, feature=arguments.feature)
    participant.to_csv(arguments.output_directory / "participant_level_association.csv", index=False)

    pairs, across = across_session_association(records, feature=arguments.feature)
    pairs.to_csv(arguments.output_directory / "across_session_pairs.csv", index=False)
    across.to_csv(arguments.output_directory / "across_session_association.csv", index=False)

    clustering = session_accuracy_icc(records, feature=arguments.feature)
    (arguments.output_directory / "session_clustering.json").write_text(json.dumps(clustering, indent=2) + "\n")

    pooled = benchmark.loc[benchmark["held_out_study"] == "Pooled held-out records"].iloc[0]
    centred = within.loc[within["analysis"] == "pooled_study_centred"].iloc[0]
    print(f"development-mean benchmark MAE {pooled['development_mean_benchmark_mae']:.4f}")
    print(f"held-out-cohort-mean benchmark MAE {pooled['held_out_cohort_mean_benchmark_mae']:.4f}")
    print(f"pooled study-centred r {centred['pearson_r']:.3f}")
    print(f"participant-level r {participant['pearson_r'].iloc[0]:.3f} (n={participant['n_participants'].iloc[0]})")
    across_row = across.loc[across["analysis"] == "across_session_prior_to_later"]
    if not across_row.empty:
        row = across_row.iloc[0]
        print(f"across-session r {row['pearson_r']:.3f} (n_pairs={row['n_pairs']})")
    print(f"intraclass correlation {clustering['intraclass_correlation']:.3f}")
    print("wrote strengthening outputs")


if __name__ == "__main__":
    main()
