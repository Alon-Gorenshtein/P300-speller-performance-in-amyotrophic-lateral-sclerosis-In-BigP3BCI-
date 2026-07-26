"""Separate genuine between-cohort variation from sampling error.

Reporting the spread of cohort-specific calibration slopes as evidence of heterogeneity assumes
each slope is measured precisely. Cohorts here differ several-fold in participants and selections,
and some sit near ceiling, so part of the observed spread is sampling error. A random-effects
summary estimates the between-cohort variance after the within-cohort variance is accounted for,
which is the quantity the transportability claim actually needs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

PROBABILITY_FLOOR = 1e-6


def cohort_calibration(predictions: pd.DataFrame) -> pd.DataFrame:
    """Fit calibration intercept and slope, with standard errors, inside each withheld cohort."""
    required = {"held_out_study", "correct", "n", "predicted_probability"}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"predictions missing columns: {missing}")

    if "model_role" in predictions.columns:
        predictions = predictions.loc[predictions["model_role"] == "primary"]
        if predictions.empty:
            raise ValueError("no primary-model predictions found")

    rows: list[dict[str, object]] = []
    for study, group in predictions.groupby("held_out_study", sort=True):
        if str(study).startswith("Pooled"):
            continue
        probability = np.clip(
            group["predicted_probability"].to_numpy(dtype=float), PROBABILITY_FLOOR, 1 - PROBABILITY_FLOOR
        )
        design = sm.add_constant(np.log(probability / (1 - probability)), has_constant="add")
        successes = group["correct"].to_numpy(dtype=float)
        trials = group["n"].to_numpy(dtype=float)
        entry: dict[str, object] = {
            "held_out_study": study,
            "n_records": int(len(group)),
            "n_selections": int(trials.sum()),
            "intercept": np.nan, "intercept_se": np.nan,
            "slope": np.nan, "slope_se": np.nan,
        }
        try:
            model = sm.GLM(
                np.column_stack([successes, trials - successes]), design, family=sm.families.Binomial()
            ).fit()
            entry.update(
                intercept=float(model.params[0]), intercept_se=float(model.bse[0]),
                slope=float(model.params[1]), slope_se=float(model.bse[1]),
            )
        except (ValueError, IndexError, np.linalg.LinAlgError,
                sm.tools.sm_exceptions.PerfectSeparationError):
            pass
        rows.append(entry)
    return pd.DataFrame(rows)


def random_effects(estimates: pd.Series, standard_errors: pd.Series) -> dict[str, float]:
    """Summarise cohort estimates by DerSimonian and Laird random-effects pooling."""
    frame = pd.DataFrame({"y": pd.to_numeric(estimates, errors="coerce"),
                          "se": pd.to_numeric(standard_errors, errors="coerce")}).dropna()
    frame = frame.loc[frame["se"] > 0]
    k = len(frame)
    if k < 2:
        raise ValueError("random-effects pooling needs at least two studies")

    y = frame["y"].to_numpy(dtype=float)
    variance = frame["se"].to_numpy(dtype=float) ** 2
    fixed_weight = 1.0 / variance
    fixed_mean = float((fixed_weight * y).sum() / fixed_weight.sum())

    q = float((fixed_weight * (y - fixed_mean) ** 2).sum())
    c = float(fixed_weight.sum() - (fixed_weight**2).sum() / fixed_weight.sum())
    tau_squared = max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0

    weight = 1.0 / (variance + tau_squared)
    pooled = float((weight * y).sum() / weight.sum())
    pooled_se = float(np.sqrt(1.0 / weight.sum()))
    critical = float(stats.t.ppf(0.975, df=k - 1))
    spread = float(np.sqrt(tau_squared + pooled_se**2))

    return {
        "n_studies": float(k),
        "pooled": pooled,
        "pooled_se": pooled_se,
        "tau_squared": tau_squared,
        "tau": float(np.sqrt(tau_squared)),
        "i_squared": float(max(0.0, 100.0 * (q - (k - 1)) / q)) if q > 0 else 0.0,
        "q_statistic": q,
        "q_p_value": float(stats.chi2.sf(q, df=k - 1)),
        "prediction_interval_low": pooled - critical * spread,
        "prediction_interval_high": pooled + critical * spread,
    }
