"""Robustness analyses for the ALS calibration validation study.

Listed before they were run, but no analysis plan was registered, so they are not prespecified
in the sense a registered plan would establish; see `docs/statistical_analysis_plan.md`.
"""

from __future__ import annotations

from collections.abc import Iterator

import pandas as pd

from bigp3_als.validation import ModelSpecification, _fit_probability_model, _validation_metrics


def leave_one_participant_out(records: pd.DataFrame) -> Iterator[tuple[str, pd.DataFrame, pd.DataFrame]]:
    """Yield development/validation records with one study-scoped participant held out."""
    for participant_id in sorted(records["study_participant_id"].unique()):
        development = records.loc[records["study_participant_id"] != participant_id].copy()
        validation = records.loc[records["study_participant_id"] == participant_id].copy()
        if development.empty or validation.empty:
            raise ValueError(f"invalid leave-one-participant-out split for {participant_id}")
        yield participant_id, development, validation


def run_within_study_lopo(records: pd.DataFrame, specification: ModelSpecification) -> pd.DataFrame:
    """Assess within-study participant-held-out discrimination as a secondary robustness check."""
    rows: list[dict[str, object]] = []
    for study, study_records in records.groupby("study", sort=True):
        predictions: list[pd.DataFrame] = []
        for participant_id, development, validation in leave_one_participant_out(study_records):
            held_out = validation.copy()
            held_out["predicted_probability"] = _fit_probability_model(
                development, validation, specification.features
            )
            held_out["held_out_participant"] = participant_id
            predictions.append(held_out)
        metrics = _validation_metrics(pd.concat(predictions, ignore_index=True))
        rows.append(
            {
                "analysis": "within_study_leave_one_participant_out",
                "model": specification.name,
                "study": study,
                "n_study_records": int(study_records["study_participant_id"].nunique()),
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def summarize_trial_exclusions(trials: pd.DataFrame) -> pd.DataFrame:
    """Preserve every outcome exclusion reason for the supplement and robustness matrix."""
    return (
        trials.assign(exclusion_reason=trials["exclusion_reason"].fillna("eligible"))
        .groupby(["study", "exclusion_reason"], as_index=False)
        .size()
        .rename(columns={"size": "n_trials"})
    )
