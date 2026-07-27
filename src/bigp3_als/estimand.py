"""Fit the calibration-to-accuracy mapping under an explicit choice of estimand.

Expanding each record into one row per character weights the fit by how many characters a session
contributed. That answers a question about a randomly chosen character. Weighting sessions or
participants equally answers different questions. The three are reported together so the reader can
see the mapping does not rest on an unstated choice.

The choice was previously silent rather than absent. A binomial GLM given a two-column endog of
successes and failures already multiplies each record's contribution by its own denominator, so
`sm.GLM(np.column_stack([correct, n - correct]), ...)` with no weights at all reproduces the
character-expanded Bernoulli fit exactly, to machine precision. That is the estimand the pipeline
has been using. `freq_weights` here is therefore divided by the denominators before it is passed:
statsmodels multiplies it back through, and each record ends up contributing exactly the unit
weight asked for. `test_character_weighting_reproduces_the_character_expanded_fit` and
`test_session_weighting_matches_a_one_trial_per_record_fit` pin both halves of that behaviour
against independent constructions, because the whole module is wrong in a silent way if either
half is not what statsmodels does.

Two consequences of that mechanism are worth stating rather than discovering later. First, only
the ratios between the weights matter, so the weight vector is rescaled to mean one before it is
passed; without that rescaling the session and participant weightings leave statsmodels with a
summed frequency weight below one and a negative residual degrees of freedom, which changes no
prediction but makes every standard error and deviance-based test on the fitted object nonsense.
Second, this module returns predictions and never the fitted object, so no inference is drawn from
a fit whose weights are a convention rather than a count of observations.

A session appears once per spelling condition, so one unit per session and one unit per
session-condition record are not the same thing: 410 sessions carry 739 records here, between one
and four each. `session` weighting is strictly per session, at one over the records in that
session, so the row's label, its `n_units` and its weights all name the same unit, and the three
weightings form a ladder in which each level equalises the level below it. The looser convention of
one unit per record was the alternative and it changes little: mean absolute error 0.0968 rather
than 0.0963, character-scale slope 0.8719 rather than 0.8779, matched-scale slope 0.9871 rather
than 0.9816. The stricter one is used because it is the one whose name is true of the fit.

Two calibration slopes are reported per row, and the gap between them is the reason both are here.
`calibration_slope` scores every fit on the character scale. That is the scale the manuscript
already reports, so it puts the three rows on one axis and makes the character row directly
comparable to the published number. But a fit optimised for one weighting will look miscalibrated
when scored under another, and that is exactly what happens: the session-weighted fit scores 0.878
on the character scale. Read alone, that column says the per-session estimand is badly calibrated,
which is false. `calibration_slope_matched_scale` scores each fit on the scale it was fitted for,
which is the slope that row's estimand actually claims, and there the session fit is the better
calibrated of the two, 0.982 against 0.966. The character-scale column measures the mismatch, not
the calibration, for any row other than the character row.

`mean_absolute_error` needs no such pairing. It is an unweighted mean over held-out
session-condition records for every row, which is the manuscript's `session_mean_absolute_error`,
and it moves by less than 0.002 across the three weightings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

WEIGHTINGS = ("character", "session", "participant")
SESSION_KEY = ("study", "study_participant_id", "session_id")
PARTICIPANT_KEY = ("study", "study_participant_id")
PROBABILITY_CLIP = 1e-6


def _unit_weights(records: pd.DataFrame, weighting: str) -> np.ndarray:
    """How much evidence one session-condition record carries under each estimand.

    Under `session` and `participant` the weights of the records belonging to one session or one
    participant sum to exactly one, so the unit named is the unit weighted. Both group on the full
    key rather than on `study_participant_id` alone: the identifiers carry a study prefix on these
    data, so the two agree here, but an unprefixed scheme would silently merge a participant across
    studies and the rest of the codebase groups on the full key for the same reason.
    """
    if weighting == "character":
        return records["n"].to_numpy(dtype=float)
    if weighting == "session":
        counts = records.groupby(list(SESSION_KEY))["n"].transform("size")
        return (1.0 / counts).to_numpy(dtype=float)
    if weighting == "participant":
        counts = records.groupby(list(PARTICIPANT_KEY))["n"].transform("size")
        return (1.0 / counts).to_numpy(dtype=float)
    raise ValueError(f"unknown weighting: {weighting}; expected one of {WEIGHTINGS}")


def _frequency_weights(records: pd.DataFrame, weighting: str) -> np.ndarray:
    """Frequency weights that leave each record contributing exactly its unit weight.

    statsmodels multiplies a frequency weight back through the grouped denominator, so dividing by
    the denominator first cancels that. Rescaling to mean one changes no coefficient and keeps the
    residual degrees of freedom of the fitted object from going negative; see the module docstring.
    """
    trials = records["n"].to_numpy(dtype=float)
    if (trials <= 0).any():
        raise ValueError("every record needs at least one character trial")
    scale = _unit_weights(records, weighting) / trials
    return scale * (len(scale) / scale.sum())


def fit_grouped_binomial(
    development: pd.DataFrame, validation: pd.DataFrame, feature: str, weighting: str
) -> np.ndarray:
    """Fit on grouped successes and trials, then estimate accuracy for the validation records."""
    if weighting not in WEIGHTINGS:
        raise ValueError(f"unknown weighting: {weighting}; expected one of {WEIGHTINGS}")

    development = development.dropna(subset=[feature])
    # A missing predictor in a held-out record would otherwise return a silent NaN probability that
    # travels into a mean absolute error as a dropped record rather than as a refusal. Development
    # rows are dropped because they carry no information; validation rows are refused because the
    # caller asked for a prediction that cannot be made.
    if validation[feature].isna().any():
        raise ValueError(f"validation records carry a missing {feature}; no prediction is defined")
    mean = float(development[feature].mean())
    deviation = float(development[feature].std(ddof=0)) or 1.0

    x_dev = sm.add_constant(
        ((development[feature].to_numpy(dtype=float) - mean) / deviation), has_constant="add"
    )
    successes = development["correct"].to_numpy(dtype=float)
    trials = development["n"].to_numpy(dtype=float)

    model = sm.GLM(
        np.column_stack([successes, trials - successes]),
        x_dev,
        family=sm.families.Binomial(),
        freq_weights=_frequency_weights(development, weighting),
    ).fit()

    x_val = sm.add_constant(
        ((validation[feature].to_numpy(dtype=float) - mean) / deviation), has_constant="add"
    )
    return np.asarray(model.predict(x_val), dtype=float)


def _calibration_slope(
    records: pd.DataFrame, predicted: np.ndarray, weighting: str = "character"
) -> float:
    """Slope of observed accuracy on the predicted log odds, weighted as asked.

    Under `character`, grouped successes and failures against an unweighted binomial GLM is exactly
    the fit `bigp3_als.validation` performs on character-expanded Bernoulli rows, so the default
    reproduces the manuscript's `calibration_slope` rather than defining a second, subtly different
    one. A degenerate design, where every held-out prediction is identical and the slope is
    therefore not recoverable, returns a missing value instead of raising, matching the same
    convention there.
    """
    clipped = np.clip(predicted, PROBABILITY_CLIP, 1 - PROBABILITY_CLIP)
    design = sm.add_constant(np.log(clipped / (1 - clipped)), has_constant="add")
    successes = records["correct"].to_numpy(dtype=float)
    trials = records["n"].to_numpy(dtype=float)
    try:
        model = sm.GLM(
            np.column_stack([successes, trials - successes]),
            design,
            family=sm.families.Binomial(),
            freq_weights=_frequency_weights(records, weighting),
        ).fit()
        return float(model.params[1])
    except (
        ValueError,
        IndexError,
        np.linalg.LinAlgError,
        sm.tools.sm_exceptions.PerfectSeparationError,
    ):
        return float("nan")


def compare_estimands(records: pd.DataFrame, feature: str = "calibration_auc") -> pd.DataFrame:
    """Repeat the withheld-cohort evaluation under each weighting."""
    records = records.dropna(subset=[feature]).copy()
    observed = records["correct"] / records["n"]

    rows: list[dict[str, object]] = []
    for weighting in WEIGHTINGS:
        errors: list[float] = []
        held_out: list[pd.DataFrame] = []
        predictions: list[np.ndarray] = []
        for study in sorted(records["study"].unique()):
            development = records.loc[records["study"] != study]
            validation = records.loc[records["study"] == study]
            if development.empty or validation.empty:
                continue
            predicted = fit_grouped_binomial(development, validation, feature, weighting)
            errors.extend(np.abs(observed.loc[validation.index].to_numpy(dtype=float) - predicted))
            held_out.append(validation)
            predictions.append(predicted)
        units = {
            "character": int(records["n"].sum()),
            "session": records.groupby(list(SESSION_KEY)).ngroups,
            "participant": records.groupby(list(PARTICIPANT_KEY)).ngroups,
        }[weighting]
        if held_out:
            evaluated = pd.concat(held_out)
            pooled = np.concatenate(predictions)
            slope = _calibration_slope(evaluated, pooled)
            matched = _calibration_slope(evaluated, pooled, weighting)
        else:
            slope = matched = float("nan")
        rows.append({
            "weighting": weighting,
            "mean_absolute_error": float(np.mean(errors)) if errors else float("nan"),
            "calibration_slope": slope,
            "calibration_slope_matched_scale": matched,
            "n_units": units,
        })
    return pd.DataFrame(rows)
