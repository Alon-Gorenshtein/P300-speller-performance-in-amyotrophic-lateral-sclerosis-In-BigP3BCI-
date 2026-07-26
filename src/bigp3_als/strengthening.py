"""Analyses that establish what the calibration score adds beyond trivial alternatives.

The primary validation reports how closely a held-out study's session-condition accuracy can be
estimated. On its own that number cannot be judged, because no reference point is given. Four
analyses here supply the reference points a reader needs.

``null_benchmark`` asks what the same held-out design achieves with no predictor at all, by
estimating every held-out record at the development-set mean accuracy. It also reports an oracle that
is told each held-out study's own mean, which isolates how much of the model's advantage comes from
ranking participants within a study rather than from tracking differences between studies.

``within_study_association`` removes each study's mean from both the predictor and the outcome. If
the association survives that, it is not an artefact of studies differing in both difficulty and
signal quality.

``participant_level_association`` collapses each participant to one observation, so the association
cannot be produced by repeated sessions from the same person.

``across_session_association`` is the clinically meaningful ordering: a calibration recording from one
session is used to anticipate the accuracy of a later session, rather than of the session it came
from.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

SESSION_KEYS = ["study", "study_participant_id", "session_id"]


def collapse_to_sessions(records: pd.DataFrame, feature: str = "calibration_auc") -> pd.DataFrame:
    """Reduce session-condition records to one row per participant-session.

    The calibration score is a property of a session, not of a condition within it, so the
    session-condition records repeat the predictor. Collapsing prevents that repetition from being
    read as independent information.
    """
    missing = [key for key in [*SESSION_KEYS, feature, "n", "correct"] if key not in records.columns]
    if missing:
        raise ValueError(f"records missing required columns: {missing}")

    grouped = records.groupby(SESSION_KEYS, sort=True)
    distinct_features = grouped[feature].nunique()
    if (distinct_features > 1).any():
        offending = distinct_features[distinct_features > 1].index.tolist()
        raise ValueError(f"{feature} varies within participant-session: {offending[:3]}")

    sessions = grouped.agg(
        selections=("n", "sum"),
        correct=("correct", "sum"),
        **{feature: (feature, "first")},
    ).reset_index()
    sessions["accuracy"] = sessions["correct"] / sessions["selections"]
    return sessions


def null_benchmark(records: pd.DataFrame) -> pd.DataFrame:
    """Report source-study-held-out error for a no-predictor model and for a same-study oracle.

    The null estimates every held-out record at the development-set mean accuracy. The oracle is
    given the held-out study's own mean, which no real deployment would know. A model that beats the
    oracle is ranking participants inside the study, which is the property that would make a
    session-level check useful.
    """
    required = ["study", "n", "correct"]
    missing = [key for key in required if key not in records.columns]
    if missing:
        raise ValueError(f"records missing required columns: {missing}")

    frame = records.copy()
    frame["accuracy"] = frame["correct"] / frame["n"]

    rows: list[dict[str, object]] = []
    null_errors: list[float] = []
    oracle_errors: list[float] = []
    for study in sorted(frame["study"].unique()):
        development = frame.loc[frame["study"] != study]
        held_out = frame.loc[frame["study"] == study]
        if development.empty or held_out.empty:
            raise ValueError(f"invalid source-study split for {study}")

        development_mean = float(development["accuracy"].mean())
        own_mean = float(held_out["accuracy"].mean())
        null_error = (held_out["accuracy"] - development_mean).abs()
        oracle_error = (held_out["accuracy"] - own_mean).abs()
        null_errors.extend(null_error.tolist())
        oracle_errors.extend(oracle_error.tolist())

        rows.append(
            {
                "held_out_study": study,
                "n_records": int(len(held_out)),
                "development_mean_accuracy": development_mean,
                "held_out_mean_accuracy": own_mean,
                "null_mean_absolute_error": float(null_error.mean()),
                "same_study_oracle_mean_absolute_error": float(oracle_error.mean()),
            }
        )

    rows.append(
        {
            "held_out_study": "Pooled held-out records",
            "n_records": int(len(frame)),
            "development_mean_accuracy": np.nan,
            "held_out_mean_accuracy": float(frame["accuracy"].mean()),
            "null_mean_absolute_error": float(np.mean(null_errors)),
            "same_study_oracle_mean_absolute_error": float(np.mean(oracle_errors)),
        }
    )
    return pd.DataFrame(rows)


def _correlations(x: pd.Series, y: pd.Series, label: str, n_label: str) -> dict[str, object]:
    pearson, pearson_p = stats.pearsonr(x, y)
    spearman, spearman_p = stats.spearmanr(x, y)
    return {
        "analysis": label,
        n_label: int(len(x)),
        "pearson_r": float(pearson),
        "pearson_p_value": float(pearson_p),
        "spearman_rho": float(spearman),
        "spearman_p_value": float(spearman_p),
    }


def within_study_association(records: pd.DataFrame, feature: str = "calibration_auc") -> pd.DataFrame:
    """Test the predictor-outcome association inside each study and after removing study means."""
    sessions = collapse_to_sessions(records, feature=feature)

    rows: list[dict[str, object]] = []
    centred_feature: list[float] = []
    centred_accuracy: list[float] = []
    for study in sorted(sessions["study"].unique()):
        subset = sessions.loc[sessions["study"] == study]
        if len(subset) < 3:
            rows.append({"analysis": f"within_study:{study}", "n_sessions": int(len(subset))})
            continue
        rows.append(_correlations(subset[feature], subset["accuracy"], f"within_study:{study}", "n_sessions"))
        centred_feature.extend((subset[feature] - subset[feature].mean()).tolist())
        centred_accuracy.extend((subset["accuracy"] - subset["accuracy"].mean()).tolist())

    rows.append(_correlations(sessions[feature], sessions["accuracy"], "pooled_raw", "n_sessions"))
    rows.append(
        _correlations(
            pd.Series(centred_feature), pd.Series(centred_accuracy), "pooled_study_centred", "n_sessions"
        )
    )
    return pd.DataFrame(rows)


def participant_level_association(records: pd.DataFrame, feature: str = "calibration_auc") -> pd.DataFrame:
    """Collapse each participant to one observation and retest the association."""
    sessions = collapse_to_sessions(records, feature=feature)
    grouped = sessions.groupby(["study", "study_participant_id"], sort=True)
    participants = grouped.agg(
        feature_mean=(feature, "mean"),
        selections=("selections", "sum"),
        correct=("correct", "sum"),
        n_sessions=("accuracy", "size"),
    ).reset_index()
    participants["accuracy"] = participants["correct"] / participants["selections"]
    return pd.DataFrame(
        [_correlations(participants["feature_mean"], participants["accuracy"], "participant_level", "n_participants")]
    )


def session_accuracy_icc(records: pd.DataFrame, feature: str = "calibration_auc") -> dict[str, float]:
    """Estimate how much session accuracy clusters within participant.

    Reported so that the number of session-condition records is not mistaken for the number of
    independent observations.
    """
    sessions = collapse_to_sessions(records, feature=feature)
    groups = [group["accuracy"].to_numpy() for _, group in sessions.groupby(["study", "study_participant_id"])]
    values = np.concatenate(groups)
    grand_mean = values.mean()
    n_groups = len(groups)
    if n_groups < 2:
        raise ValueError("intraclass correlation needs at least two participants")

    mean_group_size = float(np.mean([len(group) for group in groups]))
    between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups) / (n_groups - 1)
    within_denominator = len(values) - n_groups
    within = (
        sum(((g - g.mean()) ** 2).sum() for g in groups) / within_denominator if within_denominator > 0 else 0.0
    )
    denominator = between + (mean_group_size - 1) * within
    icc = float((between - within) / denominator) if denominator > 0 else float("nan")
    effective = float(len(values) / (1 + (mean_group_size - 1) * max(icc, 0.0)))
    return {
        "n_sessions": float(len(values)),
        "n_participants": float(n_groups),
        "mean_sessions_per_participant": mean_group_size,
        "intraclass_correlation": icc,
        "effective_independent_sessions": effective,
    }


def across_session_association(records: pd.DataFrame, feature: str = "calibration_auc") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Use one session's calibration recording to anticipate a later session's accuracy.

    Sessions are ordered by their identifier, which is assigned in recording order in this archive.
    Consecutive pairs are formed within participant, so the predictor always precedes the outcome and
    never comes from the session being estimated.
    """
    sessions = collapse_to_sessions(records, feature=feature)

    pairs: list[dict[str, object]] = []
    for (study, participant), group in sessions.groupby(["study", "study_participant_id"], sort=True):
        ordered = group.sort_values("session_id").reset_index(drop=True)
        for index in range(len(ordered) - 1):
            earlier = ordered.loc[index]
            later = ordered.loc[index + 1]
            pairs.append(
                {
                    "study": study,
                    "study_participant_id": participant,
                    "predictor_session": earlier["session_id"],
                    "outcome_session": later["session_id"],
                    "prior_session_feature": float(earlier[feature]),
                    "later_session_accuracy": float(later["accuracy"]),
                    "later_session_selections": int(later["selections"]),
                    "same_session_feature": float(later[feature]),
                }
            )

    pair_frame = pd.DataFrame(pairs)
    if len(pair_frame) < 3:
        return pair_frame, pd.DataFrame([{"analysis": "across_session", "n_pairs": int(len(pair_frame))}])

    summary = [
        _correlations(
            pair_frame["prior_session_feature"],
            pair_frame["later_session_accuracy"],
            "across_session_prior_to_later",
            "n_pairs",
        ),
        _correlations(
            pair_frame["same_session_feature"],
            pair_frame["later_session_accuracy"],
            "same_session_reference",
            "n_pairs",
        ),
    ]
    counts = pair_frame.groupby("study", sort=True).size()
    for study, count in counts.items():
        summary.append({"analysis": f"across_session_pairs:{study}", "n_pairs": int(count)})
    return pair_frame, pd.DataFrame(summary)
