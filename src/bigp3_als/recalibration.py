"""How much local data a site needs before recalibrating beats transporting the fitted mapping.

The paper's conclusion tells a reader not to report expected accuracy in a cohort where the mapping
was not developed without local recalibration, and then says nothing about what that costs. This
module answers the question the recommendation raises: inside each withheld cohort, draw a small
number of participants whose online accuracy is known, refit the mapping on them alone, and score
the refit on the participants who were not drawn. The transported mapping is scored on the identical
participants in the same draw, so every comparison is paired and the two never differ by which
sessions happened to be easy.

Two refits are reported and they cost different amounts of local data. An intercept-only refit moves
the whole mapping up or down and is identified from a single participant. A refit of both intercept
and slope also changes how steeply estimated accuracy tracks the score, needs at least two
participants, and pays for the extra flexibility in variance. Which of the two wins first, and at
what local sample size, is the operational answer a site needs.

A local draw can separate: if every drawn participant spelled perfectly there is no finite
maximum-likelihood fit, and statsmodels 0.14 does not raise on this, it converges at maxiter to a
huge-but-finite coefficient with a fitted probability on the boundary. That is the same failure mode
`heterogeneity._bootstrap_standard_errors` guards, and the same guard is applied here: a draw that
fails it is flagged rather than scored, and the flagged fraction is reported, because silently
dropping the hardest draws would make recalibration look cheaper than it is.

`recalibration_summary` reports two different kinds of interval and they answer different
questions. The draw-level `improvement_low`/`improvement_high` describe how much one site's own
experience can vary from draw to draw; they are a percentile range, not a confidence interval for
a mean. The cohort-level `cohort_improvement_ci_low`/`cohort_improvement_ci_high` average within
each cohort first and pool across cohorts, matching the unit of replication used everywhere else in
this package, and that is the interval that answers whether the mean improvement is real.
`common_cohorts` restricts a summary to the cohorts present at every tested size, because otherwise
the ladder confounds the recalibration effect with a cohort mix that gets smaller and easier at
larger local sizes.

Mean absolute error is not the only outcome that matters here. The paper's transportability failure
is stated in terms of the calibration intercept and slope (tau 0.87 and 0.43), and a refit only ever
touches those two parameters directly. If recalibration corrects the intercept and slope but MAE
stays flat, the honest conclusion is that the mapping's systematic bias is fixable while MAE is
dominated by irreducible within-cohort variance no refit can touch, not that recalibration "does not
work". `recalibration_draws` therefore also fits the same guarded logistic-calibration model the
rest of the codebase uses (`validation._fit_calibration_model_guarded`) on the transported and on
the recalibrated evaluation-set probabilities, and `recalibration_summary` reports both directly
(so a reader can see whether either mapping's intercept sits near 0 and slope near 1) and as a
paired distance-from-ideal improvement, pooled at the cohort level like everything else.

A null result at a given size is only informative if it states what effect size it could have ruled
out. `recalibration_summary` also reports a minimum detectable effect for the MAE, intercept and
slope improvements: the true mean improvement that would have put the cohort-level CI's lower bound
exactly at zero, given the between-cohort SD and cohort count actually observed at that size. Because
`n_cohorts_contributing` falls across the ladder, this bound is tightest in the middle of the range
and loosest at the top; a null at n=16, where only 6 cohorts contribute, rules out a much larger
effect than the same null at n=6 does, and the two must not be read as equally informative.

The recalibrated calibration slope for `intercept_and_slope` is heavy-tailed, not merely noisy: its
mean at some sizes sits far outside any plausible slope (for example, deep negative), while its
median stays close to 1. `recalibration_summary` reports the median alongside the mean for exactly
this reason, and separately reports the fraction of identified draws whose recalibrated slope falls
outside a stated sane range and the fraction that come back negative, since a negative slope is a
qualitatively different failure (the local refit inverted the mapping) from a merely imprecise one.
The mechanism, confirmed by hand on several of the most extreme draws: the two-parameter local refit
itself is well-behaved and passes its own identification guard with a slope near zero, which makes
the recalibrated probability nearly constant across the whole evaluation set; fitting a SECOND
calibration model to diagnose a near-constant predictor is an ill-conditioned regression regardless
of evaluation sample size, and it converges to a huge-but-finite intercept/slope pair whose fitted
values stay comfortably inside the identification guard's boundary. `_fit_calibration_model_guarded`
guards against complete separation (fitted values driven to the 0/1 boundary) and exact design-rank
deficiency; it does not and is not extended here to guard against near-zero predictor variance short
of exact singularity, so these draws are correctly identified by the letter of the guard and reported
as such. The instability is real and belongs in the fraction columns, not filtered out of them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from bigp3_als.validation import (
    RANDOM_SEED,
    _expanded_binary,
    _fit_calibration_model_guarded,
    _FITTED_BOUNDARY,
)

# Local sample sizes, in participants. The ladder is dense at the bottom because that is where the
# answer lies: a site deciding whether to recalibrate cares about the difference between one
# participant and six, not between twenty and twenty-four. Extended to 14 and 16 to see whether the
# curve settles within a realistic local-calibration effort; stopped at 16 because only 6 of the 18
# cohorts keep 3 evaluation participants in reserve at that size, and at 18 only 2 would (below the
# floor for a cohort-level CI at all).
LOCAL_SIZES = (1, 2, 3, 4, 6, 8, 12, 14, 16)

# A cohort must keep at least this many participants outside the local draw, so that the evaluation
# is not itself a two-participant estimate. Cohorts range from 5 to 24 participants, so this floor
# excludes the largest sizes in the smallest cohorts rather than excluding cohorts.
MINIMUM_EVALUATION_PARTICIPANTS = 3

DRAWS = 200
PROBABILITY_FLOOR = 1e-6
PARTICIPANT_COLUMN = "study_participant_id"

# A plainly stated range a calibration slope has no business leaving: below 0 the mapping is
# inverted (higher predicted accuracy tracks lower observed accuracy), above 3 predicted accuracy is
# amplified far past what transportability's own tau=0.43 heterogeneity in this parameter has ever
# shown. Used only to report how often a draw's recalibrated slope leaves it, never to reject a fit.
_SANE_SLOPE_RANGE = (0.0, 3.0)


def _logit(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=float), PROBABILITY_FLOOR, 1 - PROBABILITY_FLOOR)
    return np.log(clipped / (1 - clipped))


def _mean_absolute_error(records: pd.DataFrame, probabilities: np.ndarray) -> float:
    observed = records["correct"].to_numpy(dtype=float) / records["n"].to_numpy(dtype=float)
    return float(np.mean(np.abs(observed - probabilities)))


def _calibration_fit(evaluation: pd.DataFrame, probability_column: str) -> tuple[float, float, bool]:
    """Guarded logistic-calibration intercept and slope on the expanded evaluation observations.

    Reuses `validation._fit_calibration_model_guarded` rather than a second recomputation of the
    same fit, so these numbers sit on the same scale, with the same identification guard, as the
    paper's own headline transportability estimates (tau 0.87 intercept, tau 0.43 slope).
    """
    labels, probabilities = _expanded_binary(evaluation, probability_column=probability_column)
    return _fit_calibration_model_guarded(labels, probabilities)


def _fit_local(local: pd.DataFrame, with_slope: bool) -> tuple[float, float, bool]:
    """Return the local intercept, slope and whether the fit was identified."""
    labels, probabilities = _expanded_binary(local)
    eta = _logit(probabilities)
    design = np.column_stack([np.ones_like(eta), eta]) if with_slope else np.ones((len(eta), 1))
    if np.linalg.matrix_rank(design) < design.shape[1]:
        return np.nan, np.nan, False
    offset = None if with_slope else eta
    try:
        model = sm.GLM(labels, design, family=sm.families.Binomial(), offset=offset).fit()
    except Exception:
        return np.nan, np.nan, False
    fitted = np.asarray(model.fittedvalues, dtype=float)
    if not np.all(np.isfinite(model.params)):
        return np.nan, np.nan, False
    if np.any(fitted < _FITTED_BOUNDARY) or np.any(fitted > 1 - _FITTED_BOUNDARY):
        return np.nan, np.nan, False
    if with_slope:
        return float(model.params[0]), float(model.params[1]), True
    return float(model.params[0]), 1.0, True


def recalibration_draws(
    predictions: pd.DataFrame,
    sizes: tuple[int, ...] = LOCAL_SIZES,
    draws: int = DRAWS,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Return one row per cohort, local size, draw and refit method."""
    required = {"held_out_study", PARTICIPANT_COLUMN, "correct", "n", "predicted_probability"}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"predictions missing columns: {', '.join(missing)}")
    rows: list[dict[str, object]] = []
    rng = np.random.default_rng(seed)
    for cohort, block in predictions.groupby("held_out_study", sort=True):
        participants = np.array(sorted(block[PARTICIPANT_COLUMN].unique()))
        for size in sizes:
            if size < 1 or len(participants) - size < MINIMUM_EVALUATION_PARTICIPANTS:
                continue
            methods = ("intercept_only",) if size < 2 else ("intercept_only", "intercept_and_slope")
            for draw in range(draws):
                chosen = rng.choice(participants, size=size, replace=False)
                is_local = block[PARTICIPANT_COLUMN].isin(chosen)
                local, evaluation = block.loc[is_local], block.loc[~is_local]
                transported = evaluation["predicted_probability"].to_numpy(dtype=float)
                transported_error = _mean_absolute_error(evaluation, transported)
                eta_evaluation = _logit(transported)
                # Depends only on the evaluation split for this draw, not on the refit method, so it
                # is computed once and shared by every method row below rather than refit per method.
                transported_intercept, transported_slope, transported_calibration_ok = _calibration_fit(
                    evaluation, "predicted_probability"
                )
                for method in methods:
                    intercept, slope, identified = _fit_local(local, method == "intercept_and_slope")
                    error = np.nan
                    recalibrated_intercept = recalibrated_slope = np.nan
                    calibration_identified = False
                    if identified:
                        recalibrated_probability = 1.0 / (1.0 + np.exp(-(intercept + slope * eta_evaluation)))
                        error = _mean_absolute_error(evaluation, recalibrated_probability)
                        recalibrated_intercept, recalibrated_slope, recalibrated_calibration_ok = _calibration_fit(
                            evaluation.assign(_recalibrated_probability=recalibrated_probability),
                            "_recalibrated_probability",
                        )
                        calibration_identified = bool(transported_calibration_ok and recalibrated_calibration_ok)
                    rows.append(
                        {
                            "held_out_study": cohort,
                            "n_local_participants": int(size),
                            "n_local_selections": int(local["n"].sum()),
                            "n_evaluation_participants": int(len(participants) - size),
                            "draw": int(draw),
                            "method": method,
                            "identified": bool(identified),
                            "mean_absolute_error": float(error) if identified else np.nan,
                            "transported_mean_absolute_error": transported_error,
                            # Calibration parameters are reported only when both the transported and
                            # the recalibrated fit are identified, so the pair is always comparable
                            # rather than one side silently defaulting to a fit that did not converge.
                            "calibration_identified": calibration_identified,
                            "transported_calibration_intercept": float(transported_intercept)
                            if calibration_identified else np.nan,
                            "transported_calibration_slope": float(transported_slope)
                            if calibration_identified else np.nan,
                            "recalibrated_calibration_intercept": float(recalibrated_intercept)
                            if calibration_identified else np.nan,
                            "recalibrated_calibration_slope": float(recalibrated_slope)
                            if calibration_identified else np.nan,
                        }
                    )
    return pd.DataFrame(rows)


def common_cohorts(draws: pd.DataFrame) -> set[str]:
    """Cohorts present at every local size the draws table covers.

    `n_cohorts` in the summary falls across the ladder as small cohorts stop being large enough to
    keep `MINIMUM_EVALUATION_PARTICIPANTS` in reserve, and the surviving cohorts are systematically
    the larger, easier ones. A curve read across sizes without restricting to this set is not a
    learning curve, it is a learning curve confounded with a shrinking, easier cohort mix. Pass the
    result to `recalibration_summary`'s `cohorts` argument to trace the curve on a fixed cohort set
    instead.
    """
    sizes = sorted(draws["n_local_participants"].unique())
    cohorts_by_size = (
        set(draws.loc[draws["n_local_participants"] == size, "held_out_study"].unique())
        for size in sizes
    )
    return set.intersection(*cohorts_by_size)


def _pool_across_cohorts(cohort_labels: pd.Series, values: pd.Series) -> tuple[float, float, float, int]:
    """Mean, 95% CI bounds and cohort count for a paired quantity, cohort as the unit.

    This is inference on whether a mean effect is real, at the level the rest of the paper treats as
    the unit of replication (one estimate per cohort, per `heterogeneity.py`'s pooling). It is a
    different question from the draw-level percentile columns in `recalibration_summary`, which
    describe how much one site's own draw-to-draw experience varies and are not a stand-in for this.
    Averaging within cohort before pooling across cohorts also stops a cohort that happened to
    contribute many draws from outweighing one that contributed few. Used for the paired MAE
    improvement and, identically, for the calibration intercept, slope and their distance-from-ideal
    improvements, so all of them are judged by the same standard.
    """
    per_cohort = values.groupby(cohort_labels).mean()
    n_cohorts = int(per_cohort.shape[0])
    if n_cohorts == 0:
        return np.nan, np.nan, np.nan, 0
    mean = float(per_cohort.mean())
    if n_cohorts < 2:
        return mean, np.nan, np.nan, n_cohorts
    standard_error = float(per_cohort.std(ddof=1) / np.sqrt(n_cohorts))
    margin = float(stats.t.ppf(0.975, df=n_cohorts - 1) * standard_error)
    return mean, mean - margin, mean + margin, n_cohorts


def recalibration_summary(draws: pd.DataFrame, cohorts: set[str] | None = None) -> pd.DataFrame:
    """Summarise the paired improvement over the transported mapping, per method and local size.

    Pass `cohorts` (for example, `common_cohorts(draws)`) to restrict the summary to a fixed set of
    cohorts, so a curve traced across `n_local_participants` is not also tracing a change in which
    cohorts were large enough to contribute at each size.
    """
    if cohorts is not None:
        draws = draws.loc[draws["held_out_study"].isin(cohorts)]
    rows: list[dict[str, object]] = []
    for (method, size), block in draws.groupby(["method", "n_local_participants"], sort=True):
        identified = block.loc[block["identified"]]
        paired = (
            identified["transported_mean_absolute_error"] - identified["mean_absolute_error"]
        ).to_numpy(dtype=float)
        cohort_mean, cohort_low, cohort_high, n_cohorts_contributing = _pool_across_cohorts(
            identified["held_out_study"], identified["transported_mean_absolute_error"] - identified["mean_absolute_error"]
        )

        # A refit only ever touches the intercept and slope directly; MAE can stay flat even when
        # calibration is fixed, if MAE is dominated by within-cohort variance no refit can reach.
        # These columns let a reader tell the two apart instead of reading a flat MAE curve as
        # "recalibration does not work".
        calibrated = block.loc[block["calibration_identified"]]
        cohort_labels = calibrated["held_out_study"]
        transported_intercept_mean, transported_intercept_low, transported_intercept_high, n_cohorts_calibration = (
            _pool_across_cohorts(cohort_labels, calibrated["transported_calibration_intercept"])
        )
        recalibrated_intercept_mean, recalibrated_intercept_low, recalibrated_intercept_high, _ = (
            _pool_across_cohorts(cohort_labels, calibrated["recalibrated_calibration_intercept"])
        )
        transported_slope_mean, transported_slope_low, transported_slope_high, _ = _pool_across_cohorts(
            cohort_labels, calibrated["transported_calibration_slope"]
        )
        recalibrated_slope_mean, recalibrated_slope_low, recalibrated_slope_high, _ = _pool_across_cohorts(
            cohort_labels, calibrated["recalibrated_calibration_slope"]
        )
        # The recalibrated slope for intercept_and_slope is heavy-tailed, not merely noisy (verified
        # by hand: see module docstring). Its mean can sit far outside any plausible slope while its
        # median stays near 1; report the median for both mappings so the comparison stays paired.
        transported_intercept_median = float(calibrated["transported_calibration_intercept"].median())
        recalibrated_intercept_median = float(calibrated["recalibrated_calibration_intercept"].median())
        transported_slope_median = float(calibrated["transported_calibration_slope"].median())
        recalibrated_slope_median = float(calibrated["recalibrated_calibration_slope"].median())
        # How often the recalibrated slope leaves a plainly sane range, and how often it is negative
        # outright (the local refit inverted the mapping, a qualitatively different failure from a
        # merely imprecise slope). Draw-level fractions, like identified_fraction and win_fraction,
        # not cohort-pooled. For intercept_only these equal the transported slope's own fractions,
        # since its recalibrated slope is identical to the transported one by construction.
        recalibrated_slope_values = calibrated["recalibrated_calibration_slope"]
        recalibrated_slope_negative_fraction = float((recalibrated_slope_values < 0).mean())
        recalibrated_slope_out_of_range_fraction = float(
            (
                (recalibrated_slope_values < _SANE_SLOPE_RANGE[0])
                | (recalibrated_slope_values > _SANE_SLOPE_RANGE[1])
            ).mean()
        )
        # Perfect calibration is intercept 0, slope 1. A positive value here means the recalibrated
        # mapping sits closer to that target than the transported one did, on the same draw.
        intercept_improvement = (
            calibrated["transported_calibration_intercept"].abs()
            - calibrated["recalibrated_calibration_intercept"].abs()
        )
        intercept_improvement_mean, intercept_improvement_low, intercept_improvement_high, _ = (
            _pool_across_cohorts(cohort_labels, intercept_improvement)
        )
        slope_improvement = (calibrated["transported_calibration_slope"] - 1.0).abs() - (
            calibrated["recalibrated_calibration_slope"] - 1.0
        ).abs()
        slope_improvement_mean, slope_improvement_low, slope_improvement_high, _ = _pool_across_cohorts(
            cohort_labels, slope_improvement
        )

        # Minimum detectable effect: the true mean improvement that would put the CI's lower bound
        # exactly at zero, given the between-cohort SD and cohort count actually observed here. It is
        # the same margin already added and subtracted to build the CI (ci_high - mean, equivalently
        # mean - ci_low), named and reported on its own so a null result states what it could have
        # ruled out rather than just that nothing crossed zero. A wide bound at a given size does not
        # mean the true effect is small, it means this size could not have detected anything smaller
        # than the bound.
        mae_minimum_detectable_effect = cohort_high - cohort_mean
        intercept_minimum_detectable_effect = intercept_improvement_high - intercept_improvement_mean
        slope_minimum_detectable_effect = slope_improvement_high - slope_improvement_mean

        rows.append(
            {
                "method": method,
                "n_local_participants": int(size),
                "n_draws": int(len(block)),
                "identified_fraction": float(block["identified"].mean()),
                "n_cohorts": int(block["held_out_study"].nunique()),
                "median_local_selections": float(block["n_local_selections"].median()),
                "transported_mae": float(identified["transported_mean_absolute_error"].mean()),
                "recalibrated_mae": float(identified["mean_absolute_error"].mean()),
                # Draw-level spread: how variable one site's own experience is, across draws and
                # cohorts pooled together. NOT a confidence interval for the mean, anywhere it is used.
                "mean_improvement": float(paired.mean()) if len(paired) else np.nan,
                "improvement_low": float(np.percentile(paired, 2.5)) if len(paired) else np.nan,
                "improvement_high": float(np.percentile(paired, 97.5)) if len(paired) else np.nan,
                "win_fraction": float(np.mean(paired > 0)) if len(paired) else np.nan,
                # Cohort-level inference: whether the mean improvement is distinguishable from zero,
                # with the cohort as the unit of replication. This IS the confidence interval.
                "cohort_mean_improvement": cohort_mean,
                "cohort_improvement_ci_low": cohort_low,
                "cohort_improvement_ci_high": cohort_high,
                "n_cohorts_contributing": n_cohorts_contributing,
                "mae_minimum_detectable_effect": mae_minimum_detectable_effect,
                # Calibration parameters, transported versus recalibrated, each with its own
                # cohort-level 95% CI, plus the paired distance-from-ideal improvement.
                "calibration_identified_fraction": float(block["calibration_identified"].mean()),
                "n_cohorts_calibration": n_cohorts_calibration,
                "transported_calibration_intercept_mean": transported_intercept_mean,
                "transported_calibration_intercept_median": transported_intercept_median,
                "transported_calibration_intercept_ci_low": transported_intercept_low,
                "transported_calibration_intercept_ci_high": transported_intercept_high,
                "recalibrated_calibration_intercept_mean": recalibrated_intercept_mean,
                "recalibrated_calibration_intercept_median": recalibrated_intercept_median,
                "recalibrated_calibration_intercept_ci_low": recalibrated_intercept_low,
                "recalibrated_calibration_intercept_ci_high": recalibrated_intercept_high,
                "transported_calibration_slope_mean": transported_slope_mean,
                "transported_calibration_slope_median": transported_slope_median,
                "transported_calibration_slope_ci_low": transported_slope_low,
                "transported_calibration_slope_ci_high": transported_slope_high,
                "recalibrated_calibration_slope_mean": recalibrated_slope_mean,
                "recalibrated_calibration_slope_median": recalibrated_slope_median,
                "recalibrated_calibration_slope_ci_low": recalibrated_slope_low,
                "recalibrated_calibration_slope_ci_high": recalibrated_slope_high,
                # Draw-level instability, not a cohort-pooled statistic: how often the recalibrated
                # slope leaves a plainly sane range, and how often it inverts the mapping outright.
                "recalibrated_slope_out_of_range_fraction": recalibrated_slope_out_of_range_fraction,
                "recalibrated_slope_negative_fraction": recalibrated_slope_negative_fraction,
                "cohort_mean_intercept_improvement": intercept_improvement_mean,
                "cohort_intercept_improvement_ci_low": intercept_improvement_low,
                "cohort_intercept_improvement_ci_high": intercept_improvement_high,
                "intercept_minimum_detectable_effect": intercept_minimum_detectable_effect,
                "cohort_mean_slope_improvement": slope_improvement_mean,
                "cohort_slope_improvement_ci_low": slope_improvement_low,
                "cohort_slope_improvement_ci_high": slope_improvement_high,
                "slope_minimum_detectable_effect": slope_minimum_detectable_effect,
            }
        )
    return pd.DataFrame(rows).sort_values(["method", "n_local_participants"], ignore_index=True)


def instability_by_smaller_side(
    draws: pd.DataFrame,
    method: str = "intercept_and_slope",
    cohorts: set[str] | None = None,
) -> pd.DataFrame:
    """Tabulate recalibrated-slope instability by whichever side of the local/evaluation split is
    smaller, rather than by `n_local_participants` alone.

    The instability in the recalibrated calibration slope is U-shaped in `n_local_participants`
    (high at small local sizes, low in the middle, high again near the top of the ladder). The
    naive read is two different findings: small local samples destabilise the refit, and separately,
    large local samples somehow do too. That is wrong. `n_local_participants` and
    `n_evaluation_participants` trade off along a fixed-size cohort, so tabulating by one alone
    conflates two populations. Direct evidence this conflation is real: at a fixed
    `n_evaluation_participants` of 18 in the balanced 6-cohort ladder, draws with
    `n_local_participants=2` have a 29.4% out-of-range fraction (n=703) while draws with
    `n_local_participants=6` at that SAME evaluation size have 7.1% (n=169). Same evaluation-set
    size, very different instability, so evaluation size alone does not determine it (confirmed:
    tabulating by `n_evaluation_participants` alone is not a clean decreasing function either, it
    falls through n_evaluation=7-13 then rises again through 14-19).

    What does produce a clean, essentially monotonic decrease is `min(n_local_participants,
    n_evaluation_participants)`: the diagnostic calibration fit (see module docstring) is
    ill-conditioned whenever EITHER side of the local/evaluation split is starved, because either a
    starved local side or a starved evaluation side can leave the recalibrated probability with too
    little effective variance to fit a second slope through reliably. The instability at
    `n_local_participants=2` and the instability at `n_local_participants=16` are therefore one
    mechanism observed from two sides of the same resampling design, not two separate findings about
    recalibration itself.
    """
    if cohorts is not None:
        draws = draws.loc[draws["held_out_study"].isin(cohorts)]
    calibrated = draws.loc[(draws["method"] == method) & draws["calibration_identified"]]
    smaller_side = calibrated[["n_local_participants", "n_evaluation_participants"]].min(axis=1)
    slope = calibrated["recalibrated_calibration_slope"]
    labelled = pd.DataFrame(
        {
            "smaller_side": smaller_side,
            "negative": slope < 0,
            "out_of_range": (slope < _SANE_SLOPE_RANGE[0]) | (slope > _SANE_SLOPE_RANGE[1]),
        }
    )
    summary = labelled.groupby("smaller_side").agg(
        n_draws=("negative", "size"),
        negative_fraction=("negative", "mean"),
        out_of_range_fraction=("out_of_range", "mean"),
    )
    return summary.reset_index().sort_values("smaller_side", ignore_index=True)
