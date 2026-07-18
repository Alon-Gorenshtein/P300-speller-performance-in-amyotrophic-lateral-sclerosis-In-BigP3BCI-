"""External-study validation for calibration-only ALS P300 models."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score


RANDOM_SEED = 20260718


@dataclass(frozen=True)
class ModelSpecification:
    name: str
    features: tuple[str, ...]
    role: str


MODEL_SPECS = (
    ModelSpecification("calibration_auc", ("calibration_auc",), "primary"),
    ModelSpecification("pz_amplitude", ("pz_difference_uv",), "secondary"),
    ModelSpecification("calibration_auc_plus_alsfrs", ("calibration_auc", "alsfrs_r"), "exploratory"),
)


def leave_one_study_out(records: pd.DataFrame) -> Iterator[tuple[str, pd.DataFrame, pd.DataFrame]]:
    """Yield development and validation tables with a complete source study held out."""
    for held_out in sorted(records["study"].unique()):
        development = records.loc[records["study"] != held_out].copy()
        validation = records.loc[records["study"] == held_out].copy()
        if development.empty or validation.empty:
            raise ValueError(f"invalid held-out split for {held_out}")
        yield held_out, development, validation


def _expanded_binary(records: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    values: list[float] = []
    labels: list[int] = []
    for probability, correct, total in records[["predicted_probability", "correct", "n"]].itertuples(index=False):
        values.extend([float(probability)] * int(total))
        labels.extend([1] * int(correct))
        labels.extend([0] * (int(total) - int(correct)))
    return np.asarray(labels, dtype=int), np.asarray(values, dtype=float)


def _fit_probability_model(development: pd.DataFrame, validation: pd.DataFrame, features: tuple[str, ...]) -> np.ndarray:
    train_values = development.loc[:, features].to_numpy(dtype=float)
    validation_values = validation.loc[:, features].to_numpy(dtype=float)
    location = train_values.mean(axis=0)
    scale = train_values.std(axis=0, ddof=0)
    scale[scale == 0] = 1.0
    train_standardized = (train_values - location) / scale
    validation_standardized = (validation_values - location) / scale
    expanded_train: list[np.ndarray] = []
    labels: list[int] = []
    for values, correct, total in zip(
        train_standardized,
        development["correct"].astype(int),
        development["n"].astype(int),
        strict=True,
    ):
        expanded_train.extend([values] * int(total))
        labels.extend([1] * int(correct))
        labels.extend([0] * (int(total) - int(correct)))
    model = LogisticRegression(C=1.0, max_iter=1000, random_state=RANDOM_SEED)
    model.fit(np.asarray(expanded_train), np.asarray(labels, dtype=int))
    return model.predict_proba(validation_standardized)[:, 1]


def _validation_metrics(records: pd.DataFrame) -> dict[str, float]:
    labels, probabilities = _expanded_binary(records)
    observed_accuracy = records["correct"].to_numpy(dtype=float) / records["n"].to_numpy(dtype=float)
    metrics = {
        "n_character_trials": float(len(labels)),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "brier_score": float(brier_score_loss(labels, probabilities)),
        "mean_absolute_error": float(np.mean(np.abs(observed_accuracy - records["predicted_probability"]))),
    }
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    design = sm.add_constant(np.log(clipped / (1 - clipped)))
    try:
        calibration_model = sm.GLM(labels, design, family=sm.families.Binomial()).fit()
        metrics["calibration_intercept"] = float(calibration_model.params[0])
        metrics["calibration_slope"] = float(calibration_model.params[1])
    except (ValueError, np.linalg.LinAlgError):
        metrics["calibration_intercept"] = np.nan
        metrics["calibration_slope"] = np.nan
    return metrics


def _bootstrap_intervals(records: pd.DataFrame, *, repetitions: int = 1000) -> dict[str, tuple[float, float]]:
    patient_ids = records["study_participant_id"].drop_duplicates().to_numpy()
    rng = np.random.default_rng(RANDOM_SEED)
    metric_rows: list[dict[str, float]] = []
    for _ in range(repetitions):
        sampled_ids = rng.choice(patient_ids, size=len(patient_ids), replace=True)
        sampled = pd.concat(
            [records.loc[records["study_participant_id"] == patient_id] for patient_id in sampled_ids],
            ignore_index=True,
        )
        metric_rows.append(_validation_metrics(sampled))
    metrics = pd.DataFrame(metric_rows)
    return {
        metric: (float(metrics[metric].quantile(0.025)), float(metrics[metric].quantile(0.975)))
        for metric in ("roc_auc", "brier_score", "mean_absolute_error", "calibration_intercept", "calibration_slope")
    }


def build_analysis_records(
    trial_table: pd.DataFrame, feature_table: pd.DataFrame, metadata_table: pd.DataFrame
) -> pd.DataFrame:
    """Link calibration-only features to valid feedback outcomes at session-condition level."""
    eligible = trial_table.loc[trial_table["eligible"]].copy()
    outcome = (
        eligible.groupby(["study", "study_participant_id", "session_id", "condition"], as_index=False)
        .agg(correct=("correct", "sum"), n=("correct", "size"))
    )
    clinical = metadata_table[["study", "study_participant_id", "alsfrs_r"]].drop_duplicates()
    records = (
        outcome.merge(
            feature_table[
                ["study", "study_participant_id", "session_id", "calibration_auc", "pz_difference_uv"]
            ],
            on=["study", "study_participant_id", "session_id"],
            how="inner",
            validate="many_to_one",
        )
        .merge(clinical, on=["study", "study_participant_id"], how="left", validate="many_to_one")
        .sort_values(["study", "study_participant_id", "session_id", "condition"], ignore_index=True)
    )
    if records.empty or records[["calibration_auc", "pz_difference_uv"]].isna().any().any():
        raise ValueError("analysis records contain missing calibration features")
    return records


def run_external_validation(records: pd.DataFrame, specification: ModelSpecification) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit calibration-only models in two studies and evaluate the held-out third study."""
    required = {"study", "study_participant_id", "correct", "n", *specification.features}
    missing = sorted(required - set(records.columns))
    if missing:
        raise ValueError(f"records missing model columns: {', '.join(missing)}")
    predictions: list[pd.DataFrame] = []
    metric_rows: list[dict[str, object]] = []
    for held_out, development, validation in leave_one_study_out(records):
        predicted_probability = _fit_probability_model(development, validation, specification.features)
        held_out_predictions = validation.copy()
        held_out_predictions["held_out_study"] = held_out
        held_out_predictions["model"] = specification.name
        held_out_predictions["model_role"] = specification.role
        held_out_predictions["predicted_probability"] = predicted_probability
        metrics = _validation_metrics(held_out_predictions)
        intervals = _bootstrap_intervals(held_out_predictions)
        metric_row: dict[str, object] = {
            "model": specification.name,
            "model_role": specification.role,
            "held_out_study": held_out,
            "n_study_records": int(held_out_predictions["study_participant_id"].nunique()),
            **metrics,
        }
        for metric, interval in intervals.items():
            metric_row[f"{metric}_ci_low"] = interval[0]
            metric_row[f"{metric}_ci_high"] = interval[1]
        predictions.append(held_out_predictions)
        metric_rows.append(metric_row)
    all_predictions = pd.concat(predictions, ignore_index=True)
    pooled_metrics = _validation_metrics(all_predictions)
    pooled_row: dict[str, object] = {
        "model": specification.name,
        "model_role": specification.role,
        "held_out_study": "Pooled out-of-study",
        "n_study_records": int(all_predictions["study_participant_id"].nunique()),
        **pooled_metrics,
    }
    for metric, interval in _bootstrap_intervals(all_predictions).items():
        pooled_row[f"{metric}_ci_low"] = interval[0]
        pooled_row[f"{metric}_ci_high"] = interval[1]
    metric_rows.append(pooled_row)
    return all_predictions, pd.DataFrame(metric_rows)
