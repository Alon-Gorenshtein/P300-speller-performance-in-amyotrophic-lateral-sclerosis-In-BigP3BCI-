"""Measure how precisely the calibration score itself was estimated in each cohort.

The score is a cross-validated area under the curve computed from that session's calibration files.
Sessions differ several-fold in files, folds and surviving epochs, so the score is not measured
equally well everywhere. Measurement error in a predictor attenuates a fitted slope, which is an
alternative explanation for between-cohort differences in calibration.

A rank correlation between a cohort's predictor noise and its fitted slope cannot answer how much
of the heterogeneity that noise could explain, because a rank correlation carries no units. The
quantity that does is the reliability ratio, lambda: the fraction of the observed between-session
variance in the calibration score that is true signal rather than measurement error. Classical
attenuation theory says the fitted slope is biased toward zero by a factor of lambda, so dividing
each cohort's slope by its own lambda estimates what the slope would have been had the predictor
been measured without error. That correction, not the rank correlation, is what tells a reader
whether measurement error can explain away the heterogeneity Task 5 reported.

The Hanley and McNeil standard error this module builds on assumes the epochs behind an area under
the curve are independent draws. They are not: they come from repeated stimulus sequences within a
cross-validated session. The true standard error of each session's score is therefore larger than
what is computed here, every reliability ratio in this module is an overestimate, and every
disattenuated slope is a lower bound on how far attenuation could be pushing it. This is the same
direction of error the module's stress test is built to probe.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from bigp3_als.heterogeneity import random_effects

MAX_FOLDS = 5
PRIMARY_SE_METHOD = "cluster"
SESSION_KEY = ("study", "study_participant_id", "session_id")


def _auc_standard_error(auc: float, n_target: float, n_nontarget: float) -> float:
    """Hanley and McNeil approximate standard error of an area under the curve.

    Assumes independent target and non-target epochs; see the module docstring for why that
    assumption is optimistic here and what that implies for everything built on this function.
    """
    if n_target < 1 or n_nontarget < 1:
        return float("nan")
    q1 = auc / (2 - auc)
    q2 = 2 * auc**2 / (1 + auc)
    variance = (
        auc * (1 - auc) + (n_target - 1) * (q1 - auc**2) + (n_nontarget - 1) * (q2 - auc**2)
    ) / (n_target * n_nontarget)
    return float(np.sqrt(max(variance, 0.0)))


def _deduplicated_analysis_sessions(predictions: pd.DataFrame) -> pd.DataFrame:
    """One row per session that actually entered a cohort's calibration fit.

    `external_validation_predictions.csv` carries one row per condition, so a session with the
    usual two conditions appears twice with an identical predicted probability. It also carries a
    null-model comparator alongside the primary model when both are present. Neither repeat should
    count as a second session of evidence.
    """
    frame = predictions
    if "model_role" in frame.columns:
        frame = frame.loc[frame["model_role"] == "primary"]
    key = [column for column in ("study_participant_id", "session_id") if column in frame.columns]
    return frame.drop_duplicates(subset=key).copy()


def _filter_to_primary_specification(calibration: pd.DataFrame, se_method: str) -> pd.DataFrame:
    """Rename to `study` and keep one row per cohort, raising rather than merging duplicates.

    `cohort_calibration.csv` stacks three standard-error specifications for the same eighteen
    cohorts under an `se_method` column. Merging against it unfiltered triples every row, and a
    rank correlation or regression computed over the result understates its own p-value by
    treating eighteen cohorts counted three times as fifty-four independent observations. This is
    the guard against that, applied once here rather than trusted to whoever calls in.
    """
    frame = calibration.rename(columns={"held_out_study": "study"})
    if "se_method" in frame.columns:
        frame = frame.loc[frame["se_method"] == se_method]
    duplicate_keys = sorted(set(frame["study"][frame["study"].duplicated()]))
    if duplicate_keys:
        raise ValueError(
            f"calibration has duplicate cohort keys after filtering to se_method={se_method!r}: "
            f"{duplicate_keys}; pass a single standard-error specification"
        )
    return frame


def precision_table(features: pd.DataFrame, predictions: pd.DataFrame | None = None) -> pd.DataFrame:
    """Summarise, per study, how much data supported each session's calibration score.

    `n_nontarget_epochs` is read directly from the features file rather than derived as
    `n_calibration_epochs - n_target_epochs`: on the real data the two agree exactly, but the
    stored column is what the pipeline actually counted, and reading it directly does not depend
    on that agreement continuing to hold.

    `auc_standard_error` is the root-mean-square of the per-session Hanley and McNeil standard
    error, not the median. Attenuation depends on the mean of the error *variance*, and the RMS of
    a set of standard errors is exactly the square root of that mean; the median has no such
    relationship to it and is reported alongside only as a robustness check
    (`auc_standard_error_median`, `auc_standard_error_mean`).

    If `predictions` is given (`external_validation_predictions.csv` or equivalent, with the
    columns in `SESSION_KEY` plus `model_role`), the table is restricted to the sessions that
    actually entered a cohort's fit rather than every session with an evaluable calibration score.
    The two sets differ severalfold for some cohorts: StudyQ contributes 107 feature sessions but
    only 53 entered a fit, and StudyC and StudyP contribute feature sessions but no cohort fit at
    all, so they carry no row once this restriction is applied. `n_sessions` reports how many
    sessions actually informed each row so this is never silent.
    """
    frame = features.dropna(subset=["calibration_auc"]).copy()
    if predictions is not None:
        sessions = _deduplicated_analysis_sessions(predictions)
        key = list(SESSION_KEY)
        frame = frame.merge(sessions[key], on=key, how="inner")
    frame["folds"] = frame["train_file_count"].clip(upper=MAX_FOLDS)
    if "n_nontarget_epochs" not in frame.columns:
        frame["n_nontarget_epochs"] = frame["n_calibration_epochs"] - frame["n_target_epochs"]
    frame["auc_se"] = [
        _auc_standard_error(a, t, nt)
        for a, t, nt in zip(frame["calibration_auc"], frame["n_target_epochs"], frame["n_nontarget_epochs"])
    ]
    return (
        frame.groupby("study", sort=True)
        .agg(
            n_sessions=("calibration_auc", "size"),
            median_train_files=("train_file_count", "median"),
            median_folds=("folds", "median"),
            median_calibration_epochs=("n_calibration_epochs", "median"),
            median_target_epochs=("n_target_epochs", "median"),
            median_calibration_auc=("calibration_auc", "median"),
            auc_standard_error=("auc_se", lambda s: float(np.sqrt(np.mean(np.square(s))))),
            auc_standard_error_mean=("auc_se", "mean"),
            auc_standard_error_median=("auc_se", "median"),
        )
        .reset_index()
    )


def precision_versus_slope(
    precision: pd.DataFrame, calibration: pd.DataFrame, se_method: str = PRIMARY_SE_METHOD
) -> dict[str, float]:
    """Test whether cohorts with a noisier predictor show flatter calibration slopes.

    `calibration` is filtered to `se_method` (cluster-robust by default, the paper's primary
    specification) before merging; see `_filter_to_primary_specification` for why an unfiltered
    frame is refused rather than silently tripling the sample.
    """
    calibration = _filter_to_primary_specification(calibration, se_method)
    merged = precision.merge(calibration[["study", "slope"]], on="study").dropna(
        subset=["auc_standard_error", "slope"]
    )
    if len(merged) < 3:
        return {"n_studies": float(len(merged)), "spearman_rho": float("nan"), "p_value": float("nan")}
    rho, p_value = stats.spearmanr(merged["auc_standard_error"], merged["slope"])
    return {"n_studies": float(len(merged)), "spearman_rho": float(rho), "p_value": float(p_value)}


def partial_correlation_controlling_for_auc_level(
    precision: pd.DataFrame, calibration: pd.DataFrame, se_method: str = PRIMARY_SE_METHOD
) -> dict[str, float]:
    """Test whether the rank correlation survives controlling for how well a cohort discriminates.

    The Hanley and McNeil standard error is itself a function of the area under the curve, largest
    near 0.5, so a cohort's predictor precision and its predictor's discrimination are not
    independent measurements: a cohort that discriminates poorly gets a noisier standard error for
    the same reason it may get a flatter slope, a real cohort difference rather than measurement
    error. Partialling out the cohort's median calibration area under the curve separates the two
    explanations.
    """
    calibration = _filter_to_primary_specification(calibration, se_method)
    merged = precision.merge(calibration[["study", "slope"]], on="study").dropna(
        subset=["auc_standard_error", "slope", "median_calibration_auc"]
    )
    n_studies = len(merged)
    if n_studies < 4:
        return {"n_studies": float(n_studies), "partial_rho": float("nan"), "p_value": float("nan")}

    rho_precision_slope, _ = stats.spearmanr(merged["auc_standard_error"], merged["slope"])
    rho_precision_auc, _ = stats.spearmanr(merged["auc_standard_error"], merged["median_calibration_auc"])
    rho_auc_slope, _ = stats.spearmanr(merged["median_calibration_auc"], merged["slope"])

    denominator = np.sqrt((1.0 - rho_precision_auc**2) * (1.0 - rho_auc_slope**2))
    partial_rho = (
        (rho_precision_slope - rho_precision_auc * rho_auc_slope) / denominator
        if denominator > 0
        else float("nan")
    )
    degrees_of_freedom = n_studies - 3
    if np.isfinite(partial_rho) and abs(partial_rho) < 1 and degrees_of_freedom > 0:
        t_statistic = partial_rho * np.sqrt(degrees_of_freedom / (1.0 - partial_rho**2))
        p_value = float(2.0 * stats.t.sf(abs(t_statistic), df=degrees_of_freedom))
    else:
        p_value = float("nan")

    return {
        "n_studies": float(n_studies),
        "rho_precision_vs_slope": float(rho_precision_slope),
        "rho_precision_vs_auc_level": float(rho_precision_auc),
        "rho_auc_level_vs_slope": float(rho_auc_slope),
        "partial_rho": float(partial_rho),
        "p_value": p_value,
    }


def reliability_ratio(predictions: pd.DataFrame, error_variance_inflation: float = 1.0) -> pd.DataFrame:
    """Per-cohort reliability of the calibration score, over the sessions that entered a fit.

    lambda = 1 - E[error variance] / Var(observed AUC within cohort), formed from the sessions in
    `predictions` after `_deduplicated_analysis_sessions`. E[error variance] is the mean of the
    per-session Hanley and McNeil variance; Var(observed AUC) is the between-session variance of
    `calibration_auc` within the same cohort. `error_variance_inflation` multiplies the error term
    before the ratio is formed, to stress-test how large the true measurement error would have to
    be, relative to what Hanley and McNeil implies, before disattenuation would matter.

    A cohort whose observed variance is not defined (fewer than two sessions) or whose inflated
    error variance meets or exceeds its observed variance returns NaN: a reliability of zero or
    below is not a small predictor, it is a predictor about which this method has nothing left to
    say, and is treated as missing rather than clipped to a number that would still support a
    division.
    """
    sessions = _deduplicated_analysis_sessions(predictions).copy()
    sessions["auc_se"] = [
        _auc_standard_error(a, t, nt)
        for a, t, nt in zip(sessions["calibration_auc"], sessions["n_target_epochs"], sessions["n_nontarget_epochs"])
    ]
    rows: list[dict[str, object]] = []
    for study, group in sessions.groupby("held_out_study", sort=True):
        error_variance = float(np.mean(np.square(group["auc_se"]))) * error_variance_inflation
        observed_variance = float(group["calibration_auc"].var(ddof=1)) if len(group) > 1 else float("nan")
        if observed_variance and observed_variance > 0 and error_variance < observed_variance:
            reliability = 1.0 - error_variance / observed_variance
        else:
            reliability = float("nan")
        rows.append({
            "study": study,
            "n_sessions": int(len(group)),
            "error_variance": error_variance,
            "observed_variance": observed_variance,
            "reliability": reliability,
        })
    return pd.DataFrame(rows)


def disattenuated_heterogeneity(
    reliability: pd.DataFrame, calibration: pd.DataFrame, se_method: str = PRIMARY_SE_METHOD
) -> dict[str, object]:
    """Correct each cohort's slope for attenuation by its own reliability, then re-pool.

    With lambda treated as known, classical attenuation correction gives
    beta_true = beta_obs / lambda, and by the delta method Var(beta_true) = Var(beta_obs) / lambda
    squared: the standard error is scaled by the same factor as the point estimate, not left at its
    observed value. An earlier version of this function scaled only the point estimate, reasoning
    that the standard error reflects sampling variability of the regression coefficient rather than
    predictor reliability; that reasoning was wrong, and wrong in a checkable way. Measurement error
    that is identical across every cohort carries no information about between-cohort
    heterogeneity, so a correct convention must leave Q unchanged when the same lambda is applied to
    every cohort alike. Scaling both the estimate and its standard error by 1/lambda satisfies that
    invariance exactly: the lambda factors cancel in the inverse-variance weights and therefore in
    Q. Scaling only the estimate does not, and instead multiplies Q by 1/lambda squared, an artifact
    of the convention rather than a change in the underlying heterogeneity.
    `test_disattenuated_heterogeneity_is_invariant_to_a_uniform_reliability` pins this property so
    the error cannot be reintroduced silently.

    Re-pooling uses `bigp3_als.heterogeneity.random_effects`, the same estimator behind the
    headline heterogeneity result, so a change here is directly comparable to that result.
    """
    calibration = _filter_to_primary_specification(calibration, se_method)
    merged = reliability.merge(calibration[["study", "slope", "slope_se"]], on="study").dropna(
        subset=["slope", "slope_se"]
    )
    usable_reliability = merged["reliability"].where(merged["reliability"] > 0)
    merged = merged.assign(
        slope_disattenuated=merged["slope"] / usable_reliability,
        slope_se_disattenuated=merged["slope_se"] / usable_reliability,
    )

    indexed = merged.set_index("study")
    observed = random_effects(indexed["slope"], indexed["slope_se"])
    disattenuated = random_effects(indexed["slope_disattenuated"], indexed["slope_se_disattenuated"])

    finite_reliability = merged["reliability"].dropna()
    finite_disattenuated_slope = merged["slope_disattenuated"].dropna()
    return {
        "n_studies": float(len(merged)),
        "reliability_min": float(finite_reliability.min()) if len(finite_reliability) else float("nan"),
        "reliability_max": float(finite_reliability.max()) if len(finite_reliability) else float("nan"),
        "reliability_median": float(finite_reliability.median()) if len(finite_reliability) else float("nan"),
        "observed_slope_min": float(merged["slope"].min()),
        "observed_slope_max": float(merged["slope"].max()),
        "disattenuated_slope_min": (
            float(finite_disattenuated_slope.min()) if len(finite_disattenuated_slope) else float("nan")
        ),
        "disattenuated_slope_max": (
            float(finite_disattenuated_slope.max()) if len(finite_disattenuated_slope) else float("nan")
        ),
        "observed": observed,
        "disattenuated": disattenuated,
    }


def identifiability_limit(predictions: pd.DataFrame) -> float:
    """Largest error-variance inflation factor at which every cohort keeps an identifiable reliability.

    Per cohort, the reliability ratio hits zero once the assumed error variance reaches the
    cohort's observed between-session variance, at inflation factor `observed_variance /
    error_variance`. The smallest such factor across cohorts is where the sensitivity analysis in
    `reliability_inflation_sensitivity` must stop: past it, at least one cohort's assumed
    measurement error would exceed its entire observed spread in calibration area under the curve,
    which amounts to declaring that cohort's calibration score pure noise. That is not a value a
    floor or a dropped-cohort convention can stand in for; it is a fact about the data, reported
    here so the sensitivity analysis can refuse to go past it rather than inventing what happens
    there.
    """
    sessions = _deduplicated_analysis_sessions(predictions).copy()
    sessions["auc_se"] = [
        _auc_standard_error(a, t, nt)
        for a, t, nt in zip(sessions["calibration_auc"], sessions["n_target_epochs"], sessions["n_nontarget_epochs"])
    ]
    limits = []
    for _, group in sessions.groupby("held_out_study", sort=True):
        error_variance = float(np.mean(np.square(group["auc_se"])))
        observed_variance = float(group["calibration_auc"].var(ddof=1)) if len(group) > 1 else float("nan")
        if error_variance > 0 and observed_variance and observed_variance > 0:
            limits.append(observed_variance / error_variance)
    return float(min(limits)) if limits else float("nan")


def reliability_inflation_sensitivity(
    predictions: pd.DataFrame,
    calibration: pd.DataFrame,
    factors: tuple[float, ...] = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
    se_method: str = PRIMARY_SE_METHOD,
) -> pd.DataFrame:
    """Repeat the disattenuation at increasing multiples of the assumed error variance.

    Answers how much larger the true measurement error would have to be, relative to what Hanley
    and McNeil implies, before the disattenuated heterogeneity moves meaningfully. Every cohort
    keeps its own reliability at every factor tried here; none is floored, clipped, or dropped,
    because either of those inserts a value nobody derived. Instead, every requested factor is
    checked against `identifiability_limit` before anything is fit, and the call is refused if any
    factor would push a cohort's reliability to zero or below. The caller who wants to see past that
    factor has to reckon with what it means first: this method has nothing left to say about a
    cohort whose reliability is not identified, so a sensitivity analysis is not the place to invent
    an answer for it.
    """
    limit = identifiability_limit(predictions)
    unsafe_factors = sorted(factor for factor in factors if factor >= limit)
    if unsafe_factors:
        raise ValueError(
            f"error-variance inflation factor(s) {unsafe_factors} are at or beyond the "
            f"identifiability limit ({limit:.4f}): at least one cohort's assumed measurement error "
            "would meet or exceed its entire observed spread in calibration area under the curve, "
            "so its reliability is not identified. Choose factors strictly below this limit."
        )
    rows = []
    for factor in factors:
        reliability = reliability_ratio(predictions, error_variance_inflation=factor)
        result = disattenuated_heterogeneity(reliability, calibration, se_method=se_method)
        rows.append({
            "error_variance_inflation_factor": float(factor),
            "identifiability_limit": limit,
            "n_studies": result["n_studies"],
            "reliability_min": result["reliability_min"],
            "tau": result["disattenuated"]["tau"],
            "i_squared": result["disattenuated"]["i_squared"],
            "q_statistic": result["disattenuated"]["q_statistic"],
            "q_p_value": result["disattenuated"]["q_p_value"],
        })
    return pd.DataFrame(rows)


def weighted_slope_versus_reliability(
    reliability: pd.DataFrame, calibration: pd.DataFrame, se_method: str = PRIMARY_SE_METHOD
) -> dict[str, float]:
    """Precision-weighted least squares of the cohort slope on its reliability.

    `precision_versus_slope` treats every cohort's slope as equally informative, but the cohorts'
    own slope standard errors span a sevenfold range, so an unweighted rank correlation lets a
    barely-identified slope count exactly as much as a tightly estimated one. Weighting each cohort
    by the inverse variance of its own slope estimate asks the sharper question: among the slopes
    that are actually well measured, does reliability predict the slope.
    """
    calibration = _filter_to_primary_specification(calibration, se_method)
    merged = reliability.merge(calibration[["study", "slope", "slope_se"]], on="study").dropna(
        subset=["slope", "slope_se", "reliability"]
    )
    n_studies = len(merged)
    if n_studies < 3:
        return {
            "n_studies": float(n_studies),
            "beta": float("nan"),
            "beta_se": float("nan"),
            "p_value": float("nan"),
            "r_squared": float("nan"),
        }
    weights = 1.0 / merged["slope_se"].to_numpy(dtype=float) ** 2
    design = sm.add_constant(merged["reliability"].to_numpy(dtype=float))
    model = sm.WLS(merged["slope"].to_numpy(dtype=float), design, weights=weights).fit()
    return {
        "n_studies": float(n_studies),
        "beta": float(model.params[1]),
        "beta_se": float(model.bse[1]),
        "p_value": float(model.pvalues[1]),
        "r_squared": float(model.rsquared),
    }
