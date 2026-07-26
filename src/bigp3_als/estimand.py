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

One caveat belongs on the `session` row rather than in a reviewer's letter. A session appears once
per spelling condition, so `session` weighting gives one unit to each session-condition record, and
a session evaluated under four conditions therefore carries four units while `n_units` counts it as
one session. On these data that is 410 sessions behind 739 records, sessions carrying between one
and four. Weighting strictly per session instead, at one over the records in that session, moves
the pooled mean absolute error from 0.0968 to 0.0963 and the calibration slope from 0.872 to 0.878,
against a character-to-session gap in that slope of 0.094. So the row answers a question about a
randomly chosen session-condition record rather than a randomly chosen session, and the difference
between those two questions is far smaller than the difference this table exists to show.

The two reported quantities are held fixed across the three weightings on purpose. `weighting`
names what the *fit* treats as one unit of evidence; the evaluation is deliberately not re-weighted
alongside it, because a column that moved for both reasons could not say which one moved it. The
two evaluation metrics are the two the manuscript already reports for the same held-out
predictions: an unweighted mean absolute error over session-condition records
(`session_mean_absolute_error`) and a character-weighted calibration slope (`calibration_slope`).
So the character row is directly comparable to the existing pipeline, and the other two rows say
what happens to those same numbers when the fit stops being character-weighted.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

WEIGHTINGS = ("character", "session", "participant")
PROBABILITY_CLIP = 1e-6


def _unit_weights(records: pd.DataFrame, weighting: str) -> np.ndarray:
    """How much evidence one session-condition record carries under each estimand."""
    if weighting == "character":
        return records["n"].to_numpy(dtype=float)
    if weighting == "session":
        return np.ones(len(records), dtype=float)
    if weighting == "participant":
        counts = records.groupby("study_participant_id")["n"].transform("size")
        return (1.0 / counts).to_numpy(dtype=float)
    raise ValueError(f"unknown weighting: {weighting}; expected one of {WEIGHTINGS}")


def fit_grouped_binomial(
    development: pd.DataFrame, validation: pd.DataFrame, feature: str, weighting: str
) -> np.ndarray:
    """Fit on grouped successes and trials, then estimate accuracy for the validation records."""
    if weighting not in WEIGHTINGS:
        raise ValueError(f"unknown weighting: {weighting}; expected one of {WEIGHTINGS}")

    development = development.dropna(subset=[feature])
    mean = float(development[feature].mean())
    deviation = float(development[feature].std(ddof=0)) or 1.0

    x_dev = sm.add_constant(
        ((development[feature].to_numpy(dtype=float) - mean) / deviation), has_constant="add"
    )
    successes = development["correct"].to_numpy(dtype=float)
    trials = development["n"].to_numpy(dtype=float)
    if (trials <= 0).any():
        raise ValueError("every development record needs at least one character trial")
    weights = _unit_weights(development, weighting)
    # statsmodels multiplies a frequency weight back through the grouped denominator, so dividing
    # by the denominator first leaves each record contributing its unit weight and nothing else.
    # Rescaling to mean one changes no coefficient and keeps the residual degrees of freedom of the
    # fitted object from going negative; see the module docstring.
    scale = weights / trials
    scale = scale * (len(scale) / scale.sum())

    model = sm.GLM(
        np.column_stack([successes, trials - successes]),
        x_dev,
        family=sm.families.Binomial(),
        freq_weights=scale,
    ).fit()

    x_val = sm.add_constant(
        ((validation[feature].to_numpy(dtype=float) - mean) / deviation), has_constant="add"
    )
    return np.asarray(model.predict(x_val), dtype=float)


def _calibration_slope(records: pd.DataFrame, predicted: np.ndarray) -> float:
    """Character-weighted slope of observed accuracy on the predicted log odds.

    Grouped successes and failures against an unweighted binomial GLM is exactly the fit
    `bigp3_als.validation` performs on character-expanded Bernoulli rows, so this reproduces the
    manuscript's `calibration_slope` rather than defining a second, subtly different one. A
    degenerate design, where every held-out prediction is identical and the slope is therefore not
    recoverable, returns a missing value instead of raising, matching the same convention there.
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
            "session": records.groupby(["study", "study_participant_id", "session_id"]).ngroups,
            "participant": records["study_participant_id"].nunique(),
        }[weighting]
        slope = (
            _calibration_slope(pd.concat(held_out), np.concatenate(predictions))
            if held_out
            else float("nan")
        )
        rows.append({
            "weighting": weighting,
            "mean_absolute_error": float(np.mean(errors)) if errors else float("nan"),
            "calibration_slope": slope,
            "n_units": units,
        })
    return pd.DataFrame(rows)
