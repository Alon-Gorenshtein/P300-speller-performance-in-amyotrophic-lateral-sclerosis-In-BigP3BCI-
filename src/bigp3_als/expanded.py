"""Analyses that become available once every BigP3BCI source study is included.

The four-study version of this work could not quantify uncertainty over source studies, because a
between-study variance estimated on three degrees of freedom is not usable. Widening the design to
every source study that yields eligible online outcomes turns the study into the unit of replication
and makes three further questions answerable.

``ALS_STUDIES`` records which cohorts the archive documentation identifies as amyotrophic lateral
sclerosis populations. They remain the prespecified primary subgroup; the remaining cohorts are what
makes the transportability statement estimable.

``random_effects_pooling`` treats the per-study estimates as exchangeable draws and reports the
interval that matters for a reader deciding whether to expect this performance in their own cohort:
not the confidence interval for the mean across the observed studies, but the prediction interval for
a study that was not observed.

``transfer_to_als`` withholds every ALS cohort from development at once, which is the situation a
group faces when it has only neurotypical calibration data and wants to apply the mapping to a
patient.

``als_meta_regression`` asks whether the calibration-to-accuracy mapping itself differs by cohort
type, rather than whether the two cohort types differ in accuracy. Cohort type is a property of a
source study, so the study is the unit of that comparison: an earlier record-level interaction
treated 18 study-level observations as 739 and reported a precision the design cannot support.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

# Studies the BigP3BCI v1.0.0 documentation identifies as ALS populations.
ALS_STUDIES = ("StudyB", "StudyF", "StudyL", "StudyN")


def label_cohort_type(records: pd.DataFrame) -> pd.DataFrame:
    """Add an ``als_cohort`` flag without altering any existing column."""
    if "study" not in records.columns:
        raise ValueError("records must carry a 'study' column")
    labelled = records.copy()
    labelled["als_cohort"] = labelled["study"].isin(ALS_STUDIES)
    return labelled


def random_effects_pooling(estimates: pd.Series, label: str = "estimate") -> dict[str, float]:
    """Summarise per-study estimates with a mean interval and a new-study prediction interval.

    The confidence interval describes the average across the source studies that were observed. The
    prediction interval describes the value a single new source study would be expected to produce,
    and is the quantity a reader should use. With few studies the two differ substantially, and
    reporting only the first overstates precision.
    """
    values = pd.Series(estimates).dropna().to_numpy(dtype=float)
    n_studies = len(values)
    if n_studies < 2:
        raise ValueError("random-effects pooling needs at least two studies")

    mean = float(values.mean())
    between_sd = float(values.std(ddof=1))
    standard_error = between_sd / np.sqrt(n_studies)
    critical = float(stats.t.ppf(0.975, df=n_studies - 1))

    return {
        "quantity": label,
        "n_studies": float(n_studies),
        "mean": mean,
        "between_study_sd": between_sd,
        "confidence_interval_low": mean - critical * standard_error,
        "confidence_interval_high": mean + critical * standard_error,
        "prediction_interval_low": mean - critical * between_sd * np.sqrt(1.0 + 1.0 / n_studies),
        "prediction_interval_high": mean + critical * between_sd * np.sqrt(1.0 + 1.0 / n_studies),
    }


def pool_held_out_metrics(metrics: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    """Apply :func:`random_effects_pooling` to each held-out-study metric column."""
    per_study = metrics.loc[~metrics["held_out_study"].str.startswith("Pooled")]
    rows = [random_effects_pooling(per_study[column], label=column) for column in columns if column in per_study]
    return pd.DataFrame(rows)


def _accuracy(records: pd.DataFrame) -> pd.Series:
    return records["correct"] / records["n"]


def transfer_to_als(
    records: pd.DataFrame,
    fit_predictions,
    feature: str = "calibration_auc",
) -> pd.DataFrame:
    """Develop the mapping on non-ALS cohorts only, then evaluate it on each ALS cohort.

    ``fit_predictions`` is injected so this function does not duplicate the primary model code. It
    receives development and validation frames and returns predicted probabilities for the
    validation frame.
    """
    labelled = label_cohort_type(records)
    development = labelled.loc[~labelled["als_cohort"]]
    if development.empty:
        raise ValueError("no non-ALS records available for development")

    rows: list[dict[str, object]] = []
    for study in sorted(set(ALS_STUDIES) & set(labelled["study"].unique())):
        held_out = labelled.loc[labelled["study"] == study].copy()
        held_out["predicted_probability"] = fit_predictions(development, held_out, (feature,))
        observed = _accuracy(held_out)
        error = (observed - held_out["predicted_probability"]).abs()
        rows.append(
            {
                "held_out_study": study,
                "development": "non-ALS cohorts only",
                "n_records": int(len(held_out)),
                "n_selections": int(held_out["n"].sum()),
                "mean_absolute_error": float(error.mean()),
                "signed_bias": float((observed - held_out["predicted_probability"]).mean()),
                "observed_mean_accuracy": float(observed.mean()),
            }
        )
    return pd.DataFrame(rows)


def _cohort_slopes(cohort_calibration: pd.DataFrame, se_method: str) -> pd.DataFrame:
    """Return one usable calibration slope per cohort, under a single standard-error specification.

    The frozen per-cohort file stacks every standard-error specification, so it carries three rows
    per cohort. Taking it whole would treat each cohort as three, which is the same unit-of-analysis
    error at one level down, so the specification is selected here and any remaining repetition is
    refused rather than silently averaged.
    """
    frame = cohort_calibration.copy()
    if "se_method" in frame.columns:
        available = sorted(str(value) for value in frame["se_method"].dropna().unique())
        if se_method not in available:
            raise ValueError(f"cohort calibration carries no {se_method!r} rows; found {available}")
        frame = frame.loc[frame["se_method"] == se_method]
    frame = frame.dropna(subset=["slope"])
    if frame["held_out_study"].duplicated().any():
        raise ValueError("cohort calibration must carry one row per cohort after selecting se_method")
    return frame


def als_meta_regression(
    cohort_calibration: pd.DataFrame,
    als_studies: tuple[str, ...] = ALS_STUDIES,
    se_method: str = "cluster",
) -> dict[str, object]:
    """Compare calibration slopes between cohort types with the study as the unit of analysis.

    Cohort type varies between studies, not between records, so a record-level interaction test
    would treat a study-level exposure as if it had been measured hundreds of times. With a small
    number of studies per group this comparison is exploratory.

    Welch's two-sample t-test is used rather than a precision-weighted contrast, because with four
    studies in one group the unweighted comparison rests on the fewest assumptions. It ignores the
    per-cohort standard errors; :func:`als_random_effects_meta_regression` uses them, and the two
    are reported together.
    """
    frame = _cohort_slopes(cohort_calibration, se_method)
    is_als = frame["held_out_study"].isin(als_studies)
    als = frame.loc[is_als, "slope"].to_numpy(dtype=float)
    other = frame.loc[~is_als, "slope"].to_numpy(dtype=float)
    if len(als) < 3 or len(other) < 3:
        raise ValueError("meta-regression needs at least three studies in each group")

    statistic, p_value = stats.ttest_ind(als, other, equal_var=False)
    als_term = als.var(ddof=1) / len(als)
    other_term = other.var(ddof=1) / len(other)
    pooled_se = float(np.sqrt(als_term + other_term))
    # Welch-Satterthwaite: with 4 studies against 14 this sits well below the 16 a pooled-variance
    # test would claim, and the interval widens accordingly.
    degrees = float(
        (als_term + other_term) ** 2
        / (als_term**2 / (len(als) - 1) + other_term**2 / (len(other) - 1))
    )
    difference = float(als.mean() - other.mean())
    critical = float(stats.t.ppf(0.975, df=degrees))
    return {
        "n_als_studies": float(len(als)),
        "n_other_studies": float(len(other)),
        "mean_slope_als": float(als.mean()),
        "mean_slope_other": float(other.mean()),
        "sd_slope_als": float(np.sqrt(als.var(ddof=1))),
        "sd_slope_other": float(np.sqrt(other.var(ddof=1))),
        "difference": difference,
        "difference_se": pooled_se,
        "difference_ci_low": difference - critical * pooled_se,
        "difference_ci_high": difference + critical * pooled_se,
        "t_statistic": float(statistic),
        "degrees_of_freedom": degrees,
        "p_value": float(p_value),
        "se_method": se_method,
    }


def _weighted_least_squares(
    design: np.ndarray, y: np.ndarray, weights: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return coefficients, their unscaled covariance, and residuals."""
    weighted = design.T * weights
    covariance = np.linalg.inv(weighted @ design)
    coefficients = covariance @ (weighted @ y)
    return coefficients, covariance, y - design @ coefficients


def _moment_tau_squared(design: np.ndarray, y: np.ndarray, variance: np.ndarray) -> float:
    """DerSimonian and Laird between-study variance for a design that may carry moderators.

    With an intercept-only design this is the estimator :func:`heterogeneity.random_effects` uses.
    With a moderator the residual degrees of freedom fall from k - 1 to k - p and the denominator
    becomes the trace of the residual-projection matrix formed under fixed-effect weights.
    """
    n_studies, n_parameters = design.shape
    weight = 1.0 / variance
    _, covariance, residual = _weighted_least_squares(design, y, weight)
    residual_q = float((weight * residual**2).sum())
    trace = float(weight.sum() - np.trace(covariance @ (design.T * weight**2) @ design))
    if trace <= 0:
        return 0.0
    return max(0.0, (residual_q - (n_studies - n_parameters)) / trace)


def als_random_effects_meta_regression(
    cohort_calibration: pd.DataFrame,
    als_studies: tuple[str, ...] = ALS_STUDIES,
    se_method: str = "cluster",
) -> dict[str, object]:
    """Regress the cohort calibration slope on cohort type, weighting cohorts by their precision.

    The unweighted comparison treats a slope measured in 16 records as it treats one measured in 89.
    This fit weights each cohort by 1 / (its own variance + the residual between-cohort variance),
    with that variance estimated by the DerSimonian and Laird moment estimator applied to the
    residual Q of the two-group fit. It is the same pooling the heterogeneity analysis uses, with
    cohort type entered as a moderator.

    Inference uses the Knapp and Hartung adjustment: the coefficient covariance is scaled by the
    weighted residual mean square and referred to a t distribution on k - 2 degrees of freedom. With
    18 cohorts and a moderator estimated from four of them, a normal test on an assumed-known tau
    squared would understate the uncertainty. The unadjusted Wald p value is returned beside it so
    the two can be compared rather than swapped.
    """
    frame = _cohort_slopes(cohort_calibration, se_method).dropna(subset=["slope_se"])
    frame = frame.loc[pd.to_numeric(frame["slope_se"], errors="coerce") > 0]
    is_als = frame["held_out_study"].isin(als_studies).to_numpy()
    if is_als.sum() < 3 or (~is_als).sum() < 3:
        raise ValueError("meta-regression needs at least three studies in each group")

    y = frame["slope"].to_numpy(dtype=float)
    variance = frame["slope_se"].to_numpy(dtype=float) ** 2
    design = np.column_stack([np.ones(len(y)), is_als.astype(float)])
    n_studies, n_parameters = design.shape

    tau_squared = _moment_tau_squared(design, y, variance)
    # The same estimator with cohort type removed, so that the share of the between-cohort variance
    # the moderator accounts for can be read off rather than assumed to be all of it.
    unconditional = _moment_tau_squared(np.ones((n_studies, 1)), y, variance)

    weight = 1.0 / (variance + tau_squared)
    coefficients, covariance, residual = _weighted_least_squares(design, y, weight)
    difference = float(coefficients[1])
    wald_se = float(np.sqrt(covariance[1, 1]))
    degrees = n_studies - n_parameters
    scale = float((weight * residual**2).sum()) / degrees
    adjusted_se = wald_se * float(np.sqrt(scale))
    critical = float(stats.t.ppf(0.975, df=degrees))
    return {
        "n_studies": float(n_studies),
        "n_als_studies": float(is_als.sum()),
        "n_other_studies": float((~is_als).sum()),
        "tau_squared": tau_squared,
        "tau": float(np.sqrt(tau_squared)),
        "tau_squared_without_moderator": unconditional,
        "tau_without_moderator": float(np.sqrt(unconditional)),
        "between_cohort_variance_explained": float(max(0.0, 1.0 - tau_squared / unconditional))
        if unconditional > 0
        else float("nan"),
        "pooled_slope_other": float(coefficients[0]),
        "pooled_slope_als": float(coefficients[0] + coefficients[1]),
        "difference": difference,
        "difference_se": adjusted_se,
        "difference_ci_low": difference - critical * adjusted_se,
        "difference_ci_high": difference + critical * adjusted_se,
        "t_statistic": difference / adjusted_se if adjusted_se > 0 else float("nan"),
        "degrees_of_freedom": float(degrees),
        "p_value": float(2 * stats.t.sf(abs(difference / adjusted_se), df=degrees))
        if adjusted_se > 0
        else float("nan"),
        "p_value_wald": float(2 * stats.norm.sf(abs(difference / wald_se))) if wald_se > 0 else float("nan"),
        "se_method": se_method,
    }


def study_inventory(trials: pd.DataFrame) -> pd.DataFrame:
    """Report, per source study, how many feedback phases were reconstructed and how many survived.

    Studies that contribute no eligible outcome are kept in the table with their reason, so the
    reader can see that their exclusion is a property of the archive rather than a choice made after
    seeing results.
    """
    reconstructed = trials.groupby("study", sort=True).size().rename("reconstructed")
    eligible = trials.groupby("study", sort=True)["eligible"].sum().rename("eligible")
    reasons = (
        trials.loc[~trials["eligible"]]
        .groupby("study", sort=True)["exclusion_reason"]
        .agg(lambda values: values.value_counts().idxmax() if len(values) else "")
        .rename("dominant_exclusion_reason")
    )
    inventory = pd.concat([reconstructed, eligible, reasons], axis=1).reset_index()
    inventory["eligible"] = inventory["eligible"].fillna(0).astype(int)
    inventory["dominant_exclusion_reason"] = inventory["dominant_exclusion_reason"].fillna("")
    inventory["contributes_outcomes"] = inventory["eligible"] > 0
    inventory["als_cohort"] = inventory["study"].isin(ALS_STUDIES)
    return inventory
