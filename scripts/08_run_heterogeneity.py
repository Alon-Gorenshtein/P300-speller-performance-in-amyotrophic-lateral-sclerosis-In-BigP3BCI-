"""Report calibration heterogeneity across withheld cohorts with sampling error removed.

The spread of the eighteen cohort-specific calibration slopes mixes real between-cohort variation
with the sampling error of each slope, and the cohorts differ several-fold in size, so the raw
standard deviation of those slopes cannot support a transportability claim on its own. This script
refits every cohort with its own standard error, pools the slopes and intercepts by
DerSimonian and Laird, and writes tau, I-squared, the Q test and the prediction interval beside the
naive standard deviation the manuscript previously reported.

Every standard-error specification the estimator offers is run. Cluster-robust is primary because
the 739 records come from 271 participants and conditions recorded within one session share an
identical predicted probability, so model-based standard errors understate the within-cohort
variance and inflate tau squared. The model-based and quasi-binomial specifications are reported
beside it, because three corrections that disagree about the within-cohort variance but agree about
I-squared say more than any one of them alone.

Two further quantities are reported because the I-squared point estimate lands within a few points
of the conventional 75 percent threshold and the threshold call cannot be made on the point estimate
alone: a test-based confidence interval for I-squared, and the effect on tau and I-squared of
inflating every within-cohort variance by a fixed factor. The second answers directly how much
downward bias in the within-cohort standard errors, the known failure mode of a cluster-robust
variance with fewer than thirty clusters, would be needed to change the conclusion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from bigp3_als.heterogeneity import SE_METHODS, cohort_calibration, random_effects

# How far the within-cohort variances are inflated in the sensitivity. A cluster-robust variance
# with 5 to 24 clusters is biased downward even under the CR1 correction statsmodels applies, and an
# understated within-cohort variance inflates tau squared, so the question is how large that bias
# would have to be to matter. Factors below 1 are not run: no argument has been made that the within
# cohort variance is overstated.
VARIANCE_INFLATION_FACTORS = (1.0, 1.1, 1.2, 1.5, 2.0, 3.0, 5.0)


def i_squared_interval(q_statistic: float, n_studies: int) -> tuple[float, float]:
    """Test-based 95 percent confidence interval for I-squared, Higgins and Thompson 2002.

    The interval is built on H = sqrt(Q / (k-1)), whose logarithm is treated as normal, and then
    mapped through I-squared = (H squared - 1) / H squared. H is truncated below at 1 because a Q
    smaller than its degrees of freedom carries no evidence of heterogeneity, which puts the
    corresponding I-squared endpoint at 0.

    This is the only interval available from the pooled quantities alone, and it is approximate. It
    is reported because at eighteen studies the sampling distribution of I-squared is wide, and a
    point estimate a few points from a threshold cannot be compared with that threshold without it.
    """
    degrees = n_studies - 1
    if q_statistic <= 0 or degrees < 2:
        return (0.0, 0.0)

    log_h = 0.5 * (np.log(q_statistic) - np.log(degrees))
    if q_statistic > n_studies:
        standard_error = 0.5 * (np.log(q_statistic) - np.log(degrees)) / (
            np.sqrt(2.0 * q_statistic) - np.sqrt(2.0 * n_studies - 3.0)
        )
    else:
        standard_error = np.sqrt(
            1.0 / (2.0 * (n_studies - 2)) * (1.0 - 1.0 / (3.0 * (n_studies - 2) ** 2))
        )

    critical = stats.norm.ppf(0.975)
    bounds = [max(1.0, float(np.exp(log_h + sign * critical * standard_error))) for sign in (-1, 1)]
    return tuple(100.0 * (h**2 - 1.0) / h**2 for h in bounds)


def variance_inflation_sensitivity(
    estimates: pd.Series, standard_errors: pd.Series
) -> list[dict[str, float]]:
    """Repool with every within-cohort variance multiplied by a factor, to bound the threshold call.

    The multiplication is applied to the standard errors and the verified pooling is rerun, rather
    than the effect being derived algebraically, so the numbers reported here come from the same
    estimator as everything else.
    """
    rows = []
    for factor in VARIANCE_INFLATION_FACTORS:
        pooled = random_effects(estimates, standard_errors * np.sqrt(factor))
        rows.append({
            "variance_inflation_factor": float(factor),
            "tau": pooled["tau"],
            "i_squared": pooled["i_squared"],
            "q_statistic": pooled["q_statistic"],
            "q_p_value": pooled["q_p_value"],
            "prediction_interval_low": pooled["prediction_interval_low"],
            "prediction_interval_high": pooled["prediction_interval_high"],
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path,
                        default=Path("output/expanded/external_validation_predictions.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    arguments = parser.parse_args()

    predictions = pd.read_csv(arguments.predictions)
    critical = stats.norm.ppf(0.975)
    summary: dict[str, object] = {}
    tables = []

    for specification in SE_METHODS:
        calibration = cohort_calibration(predictions, se_method=specification)
        for column in ("slope", "intercept"):
            calibration[f"{column}_ci_low"] = calibration[column] - critical * calibration[f"{column}_se"]
            calibration[f"{column}_ci_high"] = calibration[column] + critical * calibration[f"{column}_se"]
        tables.append(calibration)

        # Labelled by cohort, so that a cohort dropped from the pooling comes back by name rather
        # than as a row number.
        labelled = calibration.set_index("held_out_study")
        entry: dict[str, object] = {
            "slope": random_effects(labelled["slope"], labelled["slope_se"]),
            "intercept": random_effects(labelled["intercept"], labelled["intercept_se"]),
            "naive_slope_sd": float(calibration["slope"].std(ddof=1)),
            "naive_intercept_sd": float(calibration["intercept"].std(ddof=1)),
            "n_cohorts_total": int(len(calibration)),
            "n_cohorts_fitted": int(calibration["slope"].notna().sum()),
        }
        for name in ("slope", "intercept"):
            low, high = i_squared_interval(entry[name]["q_statistic"], int(entry[name]["n_studies"]))
            entry[name]["i_squared_ci_low"] = low
            entry[name]["i_squared_ci_high"] = high
        entry["slope_variance_inflation"] = variance_inflation_sensitivity(
            labelled["slope"], labelled["slope_se"]
        )
        summary[specification] = entry

    pd.concat(tables, ignore_index=True).to_csv(
        arguments.output_directory / "cohort_calibration.csv", index=False
    )
    (arguments.output_directory / "heterogeneity_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )

    for specification in SE_METHODS:
        for name in ("slope", "intercept"):
            s = summary[specification][name]
            print(f"{specification:14s} {name:9s} pooled {s['pooled']:.3f}, tau {s['tau']:.4f}, "
                  f"I2 {s['i_squared']:.1f}% [{s['i_squared_ci_low']:.1f}, {s['i_squared_ci_high']:.1f}], "
                  f"Q {s['q_statistic']:.1f} on {s['n_studies']:.0f}-1 df, Q p {s['q_p_value']:.2e}, "
                  f"PI [{s['prediction_interval_low']:.3f}, {s['prediction_interval_high']:.3f}], "
                  f"dropped {s['n_dropped']:.0f} {list(s['dropped_labels'])}")
        print(f"{specification:14s} cohorts fitted {summary[specification]['n_cohorts_fitted']}"
              f"/{summary[specification]['n_cohorts_total']}, "
              f"naive slope SD {summary[specification]['naive_slope_sd']:.4f}, "
              f"naive intercept SD {summary[specification]['naive_intercept_sd']:.4f}")

    print("\nslope, within-cohort variances inflated by a common factor")
    for specification in SE_METHODS:
        for row in summary[specification]["slope_variance_inflation"]:
            print(f"{specification:14s} x{row['variance_inflation_factor']:<4} "
                  f"tau {row['tau']:.4f}, I2 {row['i_squared']:.1f}%, Q p {row['q_p_value']:.2e}, "
                  f"PI [{row['prediction_interval_low']:.3f}, {row['prediction_interval_high']:.3f}]")

    primary = tables[list(SE_METHODS).index("cluster")]
    print("\nper-cohort calibration, cluster-robust")
    print(primary[["held_out_study", "n_records", "n_selections", "slope", "slope_se",
                   "slope_ci_low", "slope_ci_high", "intercept", "intercept_se"]]
          .round(3).to_string(index=False))


if __name__ == "__main__":
    main()
