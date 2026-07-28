"""Test the protocol descriptors the archive supports against the calibration heterogeneity.

The cohorts disagree about the calibration mapping by more than sampling error explains, and the
first objection to reading that as a transportability limit is that the source studies also differ
in stimulus paradigm, matrix design, electrode type and stopping rule. The stopping rule and the
electrode configuration are not recorded as fields, but ten descriptors are available: eight
recoverable from the reconstructed trials and the analysis records, and two (grid size and
stimulus paradigm) transcribed directly from the archive's own data descriptor. This script tests
each of them as a moderator of the cohort calibration slope.

The primary analysis is a precision-weighted random-effects meta-regression, corrected across the
ten descriptors by Holm. The rank correlations are reported beside it. The joint fits and the
leave-one-cohort-out refits are there so that a null is not read as more solid than 18 cohorts can
make it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from bigp3_als.protocol import protocol_covariates, protocol_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=Path,
                        default=Path("output/intermediate/online_trials_all20.csv"))
    parser.add_argument("--records", type=Path,
                        default=Path("output/expanded/analysis_records.csv"))
    parser.add_argument("--calibration", type=Path,
                        default=Path("output/expanded/cohort_calibration.csv"))
    parser.add_argument("--se-method", default="cluster")
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    arguments = parser.parse_args()

    covariates = protocol_covariates(
        pd.read_csv(arguments.trials), pd.read_csv(arguments.records)
    )
    covariates.to_csv(arguments.output_directory / "protocol_covariates.csv", index=False)

    report = protocol_report(
        covariates, pd.read_csv(arguments.calibration), arguments.se_method
    )
    (arguments.output_directory / "protocol_meta_regression.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )

    baseline = report["baseline_heterogeneity"]
    print(covariates.drop(columns=["condition_list"]).to_string(index=False))
    print()
    print(f"unmoderated between-cohort variance: tau squared {baseline['tau_squared']:.4f}, "
          f"tau {baseline['tau']:.4f}, I2 {baseline['i_squared']:.1f}%, "
          f"pooled over {baseline['n_studies']:.0f} cohorts, "
          f"dropped {baseline['n_dropped']:.0f} {list(baseline['dropped_labels'])}")
    print()
    descriptors = pd.DataFrame(report["descriptors"])
    print(descriptors[["covariate", "kind", "n_studies_meta", "n_dropped", "coefficient_per_sd",
                       "ci_low", "ci_high", "meta_p_value", "meta_p_value_holm",
                       "between_cohort_variance_explained"]].round(4).to_string(index=False))
    print()
    print(descriptors[["covariate", "spearman_rho", "p_value", "p_value_holm"]]
          .round(4).to_string(index=False))
    print()
    for fit in report["joint_fits"]:
        print(f"joint fit on {len(fit['moderators'])} descriptors "
              f"({', '.join(fit['moderators'])}): variance explained "
              f"{fit['between_cohort_variance_explained']:.3f}, "
              f"F {fit['f_statistic']:.2f} on {len(fit['moderators'])} and "
              f"{fit['degrees_of_freedom']:.0f} df, p {fit['joint_p_value']:.3f}, "
              f"dropped {fit['n_dropped']} {fit['dropped_labels']}")
    print()
    print("leave one cohort out, uncorrected p values")
    print(pd.DataFrame(report["leave_one_cohort_out"]).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
