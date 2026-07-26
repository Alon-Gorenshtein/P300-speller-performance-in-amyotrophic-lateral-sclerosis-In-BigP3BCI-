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

``als_moderation`` asks whether the calibration-to-accuracy mapping itself differs by cohort type,
rather than whether the two cohort types differ in accuracy.
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


def _simple_regression(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float, float]:
    """Return slope, intercept, Pearson r and its two-sided p-value.

    Written out rather than taken from ``scipy.stats.linregress`` because that routine fails on the
    numpy build used here.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), float("nan"), float("nan")

    x_centred = x - x.mean()
    y_centred = y - y.mean()
    denominator = float(x_centred @ x_centred)
    if denominator <= 0:
        return float("nan"), float("nan"), float("nan"), float("nan")

    slope = float((x_centred @ y_centred) / denominator)
    intercept = float(y.mean() - slope * x.mean())
    spread = float(np.sqrt(denominator * (y_centred @ y_centred)))
    r_value = float((x_centred @ y_centred) / spread) if spread > 0 else float("nan")

    p_value = float("nan")
    if np.isfinite(r_value) and abs(r_value) < 1.0:
        t_statistic = r_value * np.sqrt((n - 2) / (1.0 - r_value**2))
        p_value = float(2 * stats.t.sf(abs(t_statistic), df=n - 2))
    elif np.isfinite(r_value):
        p_value = 0.0
    return slope, intercept, r_value, p_value


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


def als_moderation(records: pd.DataFrame, feature: str = "calibration_auc") -> pd.DataFrame:
    """Test whether the calibration-to-accuracy slope differs between ALS and other cohorts.

    A difference in mean accuracy between cohort types is expected and uninteresting. The question
    that matters for transporting a mapping is whether the same score implies the same accuracy, so
    the interaction term is the estimand here.
    """
    labelled = label_cohort_type(records)
    labelled = labelled.assign(accuracy=_accuracy(labelled))
    # A session whose calibration block could not support the estimator carries no score; such
    # records are absent from every model fit and must be absent here too.
    labelled = labelled.dropna(subset=[feature, "accuracy"])
    if labelled.empty:
        raise ValueError(f"no records carry both {feature} and an outcome")

    rows: list[dict[str, object]] = []
    for is_als, group in labelled.groupby("als_cohort", sort=True):
        if len(group) < 3:
            continue
        slope, intercept, r_value, p_value = _simple_regression(group[feature], group["accuracy"])
        rows.append(
            {
                "cohort": "ALS" if is_als else "Other",
                "n_records": int(len(group)),
                "n_studies": int(group["study"].nunique()),
                "slope": float(slope),
                "intercept": float(intercept),
                "pearson_r": float(r_value),
                "p_value": float(p_value),
                "mean_accuracy": float(group["accuracy"].mean()),
                "mean_feature": float(group[feature].mean()),
            }
        )

    interaction = np.nan
    interaction_p = np.nan
    if labelled["als_cohort"].nunique() == 2:
        design = pd.DataFrame(
            {
                "intercept": 1.0,
                "feature": labelled[feature].to_numpy(dtype=float),
                "als": labelled["als_cohort"].to_numpy(dtype=float),
            }
        )
        design["feature_x_als"] = design["feature"] * design["als"]
        outcome = labelled["accuracy"].to_numpy(dtype=float)
        matrix = design.to_numpy(dtype=float)
        coefficients, residuals, rank, _ = np.linalg.lstsq(matrix, outcome, rcond=None)
        if rank == matrix.shape[1]:
            fitted = matrix @ coefficients
            residual = outcome - fitted
            degrees = len(outcome) - matrix.shape[1]
            sigma_squared = float(residual @ residual) / degrees
            covariance = sigma_squared * np.linalg.inv(matrix.T @ matrix)
            interaction = float(coefficients[3])
            standard_error = float(np.sqrt(covariance[3, 3]))
            interaction_p = float(2 * stats.t.sf(abs(interaction / standard_error), df=degrees))

    rows.append(
        {
            "cohort": "Interaction (feature x ALS)",
            "n_records": int(len(labelled)),
            "n_studies": int(labelled["study"].nunique()),
            "slope": interaction,
            "intercept": np.nan,
            "pearson_r": np.nan,
            "p_value": interaction_p,
            "mean_accuracy": np.nan,
            "mean_feature": np.nan,
        }
    )
    return pd.DataFrame(rows)


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
