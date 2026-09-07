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
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

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


def recalibration_summary(draws: pd.DataFrame) -> pd.DataFrame:
    """Summarise the paired improvement over the transported mapping, per method and local size."""
    rows: list[dict[str, object]] = []
    for (method, size), block in draws.groupby(["method", "n_local_participants"], sort=True):
        identified = block.loc[block["identified"]]
        paired = (
            identified["transported_mean_absolute_error"] - identified["mean_absolute_error"]
        ).to_numpy(dtype=float)
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
                "mean_improvement": float(paired.mean()) if len(paired) else np.nan,
                "improvement_low": float(np.percentile(paired, 2.5)) if len(paired) else np.nan,
                "improvement_high": float(np.percentile(paired, 97.5)) if len(paired) else np.nan,
                "win_fraction": float(np.mean(paired > 0)) if len(paired) else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["method", "n_local_participants"], ignore_index=True)
