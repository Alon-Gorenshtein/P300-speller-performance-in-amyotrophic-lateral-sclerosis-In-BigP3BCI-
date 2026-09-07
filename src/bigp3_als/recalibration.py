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
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from bigp3_als.validation import RANDOM_SEED, _expanded_binary, _FITTED_BOUNDARY

# Local sample sizes, in participants. The ladder is dense at the bottom because that is where the
# answer lies: a site deciding whether to recalibrate cares about the difference between one
# participant and six, not between twenty and twenty-four.
LOCAL_SIZES = (1, 2, 3, 4, 6, 8, 12)

# A cohort must keep at least this many participants outside the local draw, so that the evaluation
# is not itself a two-participant estimate. Cohorts range from 5 to 24 participants, so this floor
# excludes the largest sizes in the smallest cohorts rather than excluding cohorts.
MINIMUM_EVALUATION_PARTICIPANTS = 3

DRAWS = 200
PROBABILITY_FLOOR = 1e-6
PARTICIPANT_COLUMN = "study_participant_id"


def _logit(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=float), PROBABILITY_FLOOR, 1 - PROBABILITY_FLOOR)
    return np.log(clipped / (1 - clipped))


def _mean_absolute_error(records: pd.DataFrame, probabilities: np.ndarray) -> float:
    observed = records["correct"].to_numpy(dtype=float) / records["n"].to_numpy(dtype=float)
    return float(np.mean(np.abs(observed - probabilities)))


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
                for method in methods:
                    intercept, slope, identified = _fit_local(local, method == "intercept_and_slope")
                    error = np.nan
                    if identified:
                        error = _mean_absolute_error(
                            evaluation, 1.0 / (1.0 + np.exp(-(intercept + slope * eta_evaluation)))
                        )
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


def _pool_across_cohorts(identified: pd.DataFrame) -> tuple[float, float, float, int]:
    """Mean, 95% CI bounds and cohort count for the paired improvement, cohort as the unit.

    This is inference on whether the mean improvement is real, at the level the rest of the paper
    treats as the unit of replication (one estimate per cohort, per `heterogeneity.py`'s pooling).
    It is a different question from `improvement_low`/`improvement_high` in `recalibration_summary`,
    which describe how much one site's own draw-to-draw experience varies and are not a stand-in for
    this. Averaging within cohort before pooling across cohorts also stops a cohort that happened to
    contribute many draws from outweighing one that contributed few.
    """
    per_cohort = (
        identified["transported_mean_absolute_error"] - identified["mean_absolute_error"]
    ).groupby(identified["held_out_study"]).mean()
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
        cohort_mean, cohort_low, cohort_high, n_cohorts_contributing = _pool_across_cohorts(identified)
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
            }
        )
    return pd.DataFrame(rows).sort_values(["method", "n_local_participants"], ignore_index=True)
