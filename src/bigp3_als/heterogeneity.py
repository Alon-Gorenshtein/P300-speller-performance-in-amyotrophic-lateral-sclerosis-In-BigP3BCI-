"""Separate genuine between-cohort variation from sampling error.

Reporting the spread of cohort-specific calibration slopes as evidence of heterogeneity assumes
each slope is measured precisely. Cohorts here differ several-fold in participants and selections,
and some sit near ceiling, so part of the observed spread is sampling error. A random-effects
summary estimates the between-cohort variance after the within-cohort variance is accounted for,
which is the quantity the transportability claim actually needs.

Two properties of the input decide whether that separation is honest.

First, the records are not independent. Each cohort contributes several records per participant,
and conditions recorded within one session share an identical predicted probability, so a binomial
likelihood that treats every record as its own draw understates the within-cohort variance. Because
tau squared is (Q - (k-1)) / C, understating the within-cohort variance inflates Q and therefore
inflates the between-cohort variance, in the direction that makes transportability look worse than
it is. Standard errors are therefore clustered by participant by default, with the model-based
version retained and selectable so the difference can be reported as a sensitivity analysis rather
than assumed away.

Second, a cohort can fail to identify a calibration slope at all: too few records, a predicted
probability that never varies, or outcomes that are perfectly separated. Every one of those returns
a finite, plausible-looking estimate from the fitter, with a standard error tight enough to earn
real weight in the pooling. Each is detected explicitly and returned as NaN, because a fabricated
slope with a tight standard error does more damage to the pooled estimate than a missing one. The
converse case is guarded the same way: a cohort the model reproduces exactly has residuals of zero,
which collapses the clustered sandwich and the quasi-binomial dispersion to floating-point dust
rather than to zero, so a positivity check alone would let through a standard error of 4e-16 and let
one cohort set the pooled estimate by itself.

A third standard-error option scales the model-based errors by the square root of the Pearson
dispersion, the quasi-binomial correction. It absorbs excess variance without needing to know where
that variance came from, so unlike clustering it does not depend on the participant being the right
unit and it does not need many clusters to behave. The two corrections therefore fail differently,
and agreement between them says more than either alone. Neither is a bound: clustering is
downward-biased below roughly thirty clusters, which every cohort here is, and quasi-binomial
scaling absorbs marginal overdispersion but not correlation within a participant, so both can leave
the within-cohort variance too small and tau squared too large.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.tools.sm_exceptions import PerfectSeparationError, PerfectSeparationWarning

PROBABILITY_FLOOR = 1e-6
CLUSTER_COLUMN = "study_participant_id"
SE_METHODS = ("cluster", "model", "quasibinomial")

# Intercept and slope. Named because the identification guards below are stated against it.
N_CALIBRATION_PARAMETERS = 2

# How close a fitted probability may come to 0 or 1 before the fit counts as separated. Under
# separation the maximum likelihood estimate diverges and the fitted values are driven onto the
# boundary: an all-correct cohort lands 2.1e-11 from 1. Across the eighteen real cohorts the
# closest any fitted value comes to a boundary is 1.2e-3, so this threshold sits three orders of
# magnitude clear of real data and four clear of a separated fit.
FITTED_BOUNDARY = 1e-6

# Smallest quasi-binomial dispersion that can come from real counts rather than from a fit that
# reproduces its data exactly. Under no overdispersion the Pearson statistic is about its residual
# degrees of freedom, so the dispersion sits near 1; across the eighteen real cohorts the smallest
# is 0.74 and the largest 8.79. A cohort the model reproduces exactly returns 1e-32 or so and would
# otherwise be handed a standard error of 2e-16, which is not zero and so survives the positivity
# check while taking essentially the entire weight in the pooling. This threshold sits seven orders
# of magnitude below the smallest real value and more than twenty above the degenerate one.
MINIMUM_DISPERSION = 1e-8

# Smallest standard error that can come from a real fit rather than a degenerate one. A cohort whose
# fitted proportions reproduce the observed ones has residuals of zero, and the clustered sandwich is
# a sum of one outer product of cluster scores, so it collapses: the slope standard error comes back
# at 4e-16 rather than at 0, which passes a positivity check while carrying weight 8e30 in an
# inverse-variance pooling and setting the pooled estimate by itself. The same collapse is possible
# under the model-based specification. Across the eighteen real cohorts the smallest standard error
# of any parameter under any specification is 0.058, so this floor sits six orders of magnitude below
# real data and seven above the degenerate case. It does not fire on the current predictions file;
# it exists because analyses that subset within a cohort make an exactly fitting cohort reachable.
MINIMUM_STANDARD_ERROR = 1e-8

# statsmodels 0.14 does not raise on a non-identified binomial fit, it warns, so PerfectSeparationError
# is retained only for older versions and for the discrete models that do still raise. The warning
# itself is not a usable signal: statsmodels emits it whenever the fitted proportions reproduce the
# observed ones exactly (generalized_linear_model.py, `np.allclose(mu - endog, 0)`), which is true
# under separation but equally true of a small cohort the model happens to fit perfectly well.
# Identification is therefore judged from the fitted values, not from the warning.
_FIT_FAILURES = (
    ValueError,
    IndexError,
    np.linalg.LinAlgError,
    PerfectSeparationError,
)


def cohort_calibration(predictions: pd.DataFrame, se_method: str = "cluster") -> pd.DataFrame:
    """Fit calibration intercept and slope, with standard errors, inside each withheld cohort.

    `se_method` is "cluster" for standard errors clustered on `study_participant_id`, the default
    because records repeat within participant, "model" for the model-based binomial standard
    errors, which are correct only if every record is an independent draw, or "quasibinomial" for
    the model-based errors scaled by the square root of the Pearson dispersion. The method used is
    returned as a column, so a downstream table cannot mix them without it being visible.
    """
    if se_method not in SE_METHODS:
        raise ValueError(f"se_method must be one of {list(SE_METHODS)}, got {se_method!r}")

    required = {"held_out_study", "correct", "n", "predicted_probability"}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"predictions missing columns: {missing}")
    if se_method == "cluster" and CLUSTER_COLUMN not in predictions.columns:
        raise ValueError(
            f"cluster-robust standard errors need a {CLUSTER_COLUMN!r} column; "
            "pass se_method='model' to fit without clustering"
        )

    if "model_role" in predictions.columns:
        predictions = predictions.loc[predictions["model_role"] == "primary"]
        if predictions.empty:
            raise ValueError("no primary-model predictions found")

    rows: list[dict[str, object]] = []
    for study, group in predictions.groupby("held_out_study", sort=True):
        if str(study).startswith("Pooled"):
            continue
        rows.append(_fit_cohort(study, group, se_method))
    return pd.DataFrame(rows)


def _fit_cohort(study: object, group: pd.DataFrame, se_method: str) -> dict[str, object]:
    """Fit one cohort, returning NaN estimates whenever the calibration slope is not identified."""
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
        "se_method": se_method,
    }

    # A cohort with no residual degrees of freedom still returns two finite parameters, and one
    # whose predicted probability never varies returns an arbitrary split of a sum that is the only
    # identified quantity. Both look like ordinary estimates, so both are ruled out before fitting.
    if len(group) - N_CALIBRATION_PARAMETERS < 1:
        return entry
    if np.linalg.matrix_rank(design) < N_CALIBRATION_PARAMETERS:
        return entry

    fit_kwargs: dict[str, object] = {}
    if se_method == "cluster":
        cluster_codes = pd.factorize(group[CLUSTER_COLUMN].to_numpy())[0]
        # The clustered covariance is a sum of one outer product per cluster, so with fewer clusters
        # than parameters it is rank deficient and its standard errors are not usable.
        if len(np.unique(cluster_codes)) < N_CALIBRATION_PARAMETERS:
            return entry
        fit_kwargs = {"cov_type": "cluster", "cov_kwds": {"groups": cluster_codes}}

    try:
        with warnings.catch_warnings():
            # Neutralised rather than escalated, so that an ambient -W error cannot abort a whole
            # run over a warning this function deliberately does not act on. Other warning
            # categories are left under whatever filter the caller has set.
            warnings.simplefilter("ignore", PerfectSeparationWarning)
            model = sm.GLM(
                np.column_stack([successes, trials - successes]), design, family=sm.families.Binomial()
            ).fit(**fit_kwargs)
        parameters = np.asarray(model.params, dtype=float)
        errors = np.asarray(model.bse, dtype=float)
        fitted = np.asarray(model.fittedvalues, dtype=float)
        if se_method == "quasibinomial":
            # The dispersion is formed here rather than by fitting with scale="X2", which is wrong
            # for a two-column binomial endog: statsmodels 0.14 weights the Pearson sum by the trial
            # counts when it reports pearson_chi2 but not when it estimates the X2 scale, so the
            # scale it returns is that of the proportions and understates the dispersion of the
            # counts by roughly the trials per record. That would divide these standard errors by
            # the square root of the selections per record, between three and seven across these
            # cohorts, and inflate tau squared, the opposite of what this specification is for. Note
            # also that a dispersion below one shrinks the standard errors instead of widening them,
            # so this specification is not uniformly conservative either.
            dispersion = float(model.pearson_chi2) / float(model.df_resid)
            if not np.isfinite(dispersion) or dispersion <= MINIMUM_DISPERSION:
                return entry
            errors = errors * np.sqrt(dispersion)
    except _FIT_FAILURES:
        return entry

    # A separated fit returns finite numbers, so finiteness alone would let one through: the
    # all-correct cohort reports a slope of 4e-15 with a standard error of 21929, which carries no
    # weight in the pooling but does add one to k, and k enters tau squared through (Q - (k-1)).
    if fitted.min() <= FITTED_BOUNDARY or fitted.max() >= 1.0 - FITTED_BOUNDARY:
        return entry
    if not np.all(np.isfinite(parameters)) or not np.all(np.isfinite(errors)):
        return entry
    if not np.all(errors > MINIMUM_STANDARD_ERROR):
        return entry

    entry.update(
        intercept=float(parameters[0]), intercept_se=float(errors[0]),
        slope=float(parameters[1]), slope_se=float(errors[1]),
    )
    return entry


def random_effects(estimates: pd.Series, standard_errors: pd.Series) -> dict[str, object]:
    """Summarise cohort estimates by DerSimonian and Laird random-effects pooling.

    A cohort whose estimate or standard error is missing or non-positive cannot be pooled. Those
    labels, taken from the index of `estimates`, come back in `dropped_labels`, so a summary can
    never be reported over fewer cohorts than the surrounding text claims. Every other value is a
    float.
    """
    frame = pd.DataFrame({"y": pd.to_numeric(estimates, errors="coerce"),
                          "se": pd.to_numeric(standard_errors, errors="coerce")})
    usable = frame["y"].notna() & frame["se"].notna() & (frame["se"] > 0)
    dropped_labels = tuple(frame.index[~usable])
    frame = frame.loc[usable]
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

    # The prediction interval uses k-1 degrees of freedom. The Higgins, Thompson and Spiegelhalter
    # convention is k-2; at k=18 the two critical values are 2.1098 and 2.1199, a difference that
    # cannot change a conclusion, and k-1 keeps the interval defined at k=2. Either choice
    # undercovers, because tau squared enters as though it were known rather than estimated, and
    # that understatement grows with the heterogeneity, so it bites hardest in the range seen here.
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
        "n_dropped": float(len(dropped_labels)),
        "dropped_labels": dropped_labels,
    }
