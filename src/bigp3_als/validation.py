"""Source-study-held-out validation of calibration-derived ALS P300 scores."""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score


RANDOM_SEED = 20260718
BOOTSTRAP_REPETITIONS = 2000

# Intercept and slope. Named because the identification guard below is stated against it, the same
# way `heterogeneity.N_CALIBRATION_PARAMETERS` is.
_N_CALIBRATION_PARAMETERS = 2

# How close a fitted probability may come to 0 or 1 before a fit counts as separated. This is the
# same value and the same rationale as `heterogeneity.FITTED_BOUNDARY`: under statsmodels 0.14 a
# quasi-separated binomial fit does not raise, it converges at `maxiter` to a huge-but-finite
# coefficient with a fitted probability driven onto the boundary, which is indistinguishable from a
# real, precise estimate by finiteness alone. Restated here rather than imported from
# `heterogeneity.py` because that module already imports `RANDOM_SEED` and `BOOTSTRAP_REPETITIONS`
# from this one; importing back would be circular.
_FITTED_BOUNDARY = 1e-6


@dataclass(frozen=True)
class ModelSpecification:
    """A calibration-derived score named in the Methods, and its manuscript role.

    Every score in ``MODEL_SPECS`` was fixed before it was run, but no analysis plan was registered,
    so none is prespecified in the sense a registered plan would establish; see
    `docs/statistical_analysis_plan.md`.
    """

    name: str
    features: tuple[str, ...]
    role: str


MODEL_SPECS = (
    ModelSpecification("calibration_auc", ("calibration_auc",), "primary"),
    ModelSpecification("posterior_amplitude", ("posterior_difference_uv",), "comparator"),
    ModelSpecification("posterior_signed_r2", ("posterior_signed_r2_max",), "comparator"),
    ModelSpecification("calibration_accuracy", ("calibration_accuracy",), "comparator"),
    ModelSpecification("shrinkage_lda_auc", ("shrinkage_lda_auc",), "comparator"),
    ModelSpecification("pz_amplitude", ("pz_difference_uv",), "comparator"),
    ModelSpecification("calibration_auc_plus_alsfrs", ("calibration_auc", "alsfrs_r"), "exploratory"),
)


def leave_one_study_out(records: pd.DataFrame) -> Iterator[tuple[str, pd.DataFrame, pd.DataFrame]]:
    """Yield development and validation tables with one complete source study held out."""
    for held_out in sorted(records["study"].unique()):
        development = records.loc[records["study"] != held_out].copy()
        validation = records.loc[records["study"] == held_out].copy()
        if development.empty or validation.empty:
            raise ValueError(f"invalid held-out split for {held_out}")
        yield held_out, development, validation


def _expanded_binary(records: pd.DataFrame, probability_column: str = "predicted_probability") -> tuple[np.ndarray, np.ndarray]:
    """Expand session-condition counts only for character-weighted secondary metrics."""
    values: list[float] = []
    labels: list[int] = []
    for probability, correct, total in records[[probability_column, "correct", "n"]].itertuples(index=False):
        values.extend([float(probability)] * int(total))
        labels.extend([1] * int(correct))
        labels.extend([0] * (int(total) - int(correct)))
    return np.asarray(labels, dtype=int), np.asarray(values, dtype=float)


def _fit_probability_model(development: pd.DataFrame, validation: pd.DataFrame, features: tuple[str, ...]) -> np.ndarray:
    """Fit an L2 logistic count model and predict held-out session-condition probabilities."""
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
    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=RANDOM_SEED)
    model.fit(np.asarray(expanded_train), np.asarray(labels, dtype=int))
    return model.predict_proba(validation_standardized)[:, 1]


def _fit_calibration_model(labels: np.ndarray, probabilities: np.ndarray) -> tuple[float, float]:
    """Return logistic calibration intercept and slope on held-out observations."""
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    # A resample can leave every predicted probability identical, in which case the default
    # behaviour drops the intercept column and the slope becomes unrecoverable. Forcing the
    # constant keeps the design two-dimensional so the degenerate case returns a missing value
    # instead of raising. Non-degenerate fits are unaffected, because a constant column is added
    # in either case when the log-odds vary.
    design = sm.add_constant(np.log(clipped / (1 - clipped)), has_constant="add")
    try:
        model = sm.GLM(labels, design, family=sm.families.Binomial()).fit()
        return float(model.params[0]), float(model.params[1])
    except (
        ValueError,
        IndexError,
        np.linalg.LinAlgError,
        sm.tools.sm_exceptions.PerfectSeparationError,
    ):
        return np.nan, np.nan


def _fit_calibration_model_guarded(labels: np.ndarray, probabilities: np.ndarray) -> tuple[float, float, bool]:
    """Return logistic calibration intercept and slope, with an explicit identification flag.

    ``_fit_calibration_model`` only catches the exceptions statsmodels still raises on a
    non-identified fit. Under statsmodels 0.14 a quasi-separated binomial fit does not raise: it
    warns and converges, at ``maxiter``, to a huge-but-finite coefficient with a fitted probability
    driven onto the 0/1 boundary. That looks like an ordinary, precise estimate by finiteness alone,
    which is exactly the failure mode `heterogeneity.py`'s bootstrap guards against explicitly with
    a design-rank check before the fit and a fitted-value boundary check after it (see
    `heterogeneity._bootstrap_standard_errors`, `heterogeneity._fit_cohort`, and
    `heterogeneity.FITTED_BOUNDARY`). This function ports both guards for the joint bootstrap's
    per-replicate, per-fold fits, which have the same exposure: a resample can draw an
    unrepresentative, near-constant mix of a held-out cohort's outcomes. A caller that used
    `_fit_calibration_model` here instead would let those replicates through, and their
    huge-but-finite parameter values would then dominate any spread computed across replicates.
    """
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    design = sm.add_constant(np.log(clipped / (1 - clipped)), has_constant="add")
    if np.linalg.matrix_rank(design) < _N_CALIBRATION_PARAMETERS:
        return np.nan, np.nan, False
    try:
        with warnings.catch_warnings():
            # Neutralised rather than escalated, for the same reason `heterogeneity._fit_cohort`
            # neutralises it: identification is judged from the fitted values below, not from
            # whether statsmodels happened to warn, so an ambient -W error should not abort a whole
            # bootstrap run over a warning this function does not otherwise act on.
            warnings.simplefilter("ignore", sm.tools.sm_exceptions.PerfectSeparationWarning)
            model = sm.GLM(labels, design, family=sm.families.Binomial()).fit()
        parameters = np.asarray(model.params, dtype=float)
        fitted = np.asarray(model.fittedvalues, dtype=float)
    except (
        ValueError,
        IndexError,
        np.linalg.LinAlgError,
        sm.tools.sm_exceptions.PerfectSeparationError,
    ):
        return np.nan, np.nan, False
    if fitted.min() <= _FITTED_BOUNDARY or fitted.max() >= 1.0 - _FITTED_BOUNDARY:
        return np.nan, np.nan, False
    if not np.all(np.isfinite(parameters)):
        return np.nan, np.nan, False
    return float(parameters[0]), float(parameters[1]), True


def _validation_metrics(records: pd.DataFrame) -> dict[str, float]:
    """Calculate primary session-condition and secondary character-weighted metrics."""
    observed = records["correct"].to_numpy(dtype=float) / records["n"].to_numpy(dtype=float)
    probabilities = records["predicted_probability"].to_numpy(dtype=float)
    raw_scores = records.get("raw_score", records["predicted_probability"]).to_numpy(dtype=float)
    null_probabilities = records.get(
        "null_probability", pd.Series(np.repeat(observed.mean(), len(records)), index=records.index)
    ).to_numpy(dtype=float)
    weights = records["n"].to_numpy(dtype=float)
    labels, expanded_probabilities = _expanded_binary(records)
    expanded_labels, expanded_raw_scores = _expanded_binary(records, "raw_score") if "raw_score" in records else (labels, expanded_probabilities)
    expanded_null_labels, expanded_null = _expanded_binary(records, "null_probability") if "null_probability" in records else (labels, np.repeat(observed.mean(), len(labels)))
    if not np.array_equal(labels, expanded_labels) or not np.array_equal(labels, expanded_null_labels):
        raise ValueError("character expansions are inconsistent")
    residual = observed - probabilities
    character_brier = float(brier_score_loss(labels, expanded_probabilities))
    null_brier = float(brier_score_loss(labels, expanded_null))
    intercept, slope = _fit_calibration_model(labels, expanded_probabilities)
    rho, rho_p = spearmanr(raw_scores, observed)
    return {
        "n_session_condition_records": float(len(records)),
        "n_sessions": float(records[["study", "study_participant_id", "session_id"]].drop_duplicates().shape[0]),
        "n_study_records": float(records["study_participant_id"].nunique()),
        "n_character_trials": float(len(labels)),
        "raw_score_character_auc": float(roc_auc_score(labels, expanded_raw_scores)),
        "predicted_probability_character_auc": float(roc_auc_score(labels, expanded_probabilities)),
        "raw_vs_probability_auc_difference": float(
            roc_auc_score(labels, expanded_raw_scores) - roc_auc_score(labels, expanded_probabilities)
        ),
        "character_brier_score": character_brier,
        "null_character_brier_score": null_brier,
        "character_brier_skill_score": float(1.0 - character_brier / null_brier) if null_brier else np.nan,
        "session_brier_score": float(np.mean(residual**2)),
        "weighted_session_brier_score": float(np.average(residual**2, weights=weights)),
        "session_mean_absolute_error": float(np.mean(np.abs(residual))),
        "weighted_session_mean_absolute_error": float(np.average(np.abs(residual), weights=weights)),
        "session_root_mean_squared_error": float(np.sqrt(np.mean(residual**2))),
        "weighted_session_root_mean_squared_error": float(np.sqrt(np.average(residual**2, weights=weights))),
        "calibration_intercept": intercept,
        "calibration_slope": slope,
        "session_spearman_rho": float(rho),
        "session_spearman_p_value": float(rho_p),
    }


def _resample_clusters(records: pd.DataFrame, rng: np.random.Generator, stratify_study: bool) -> pd.DataFrame:
    """Resample participant clusters while preserving all nested sessions and conditions."""
    groups = records.groupby("study", sort=True) if stratify_study else [("pooled", records)]
    sampled: list[pd.DataFrame] = []
    for _, group in groups:
        identifiers = group["study_participant_id"].drop_duplicates().to_numpy()
        chosen = rng.choice(identifiers, size=len(identifiers), replace=True)
        for draw, participant_id in enumerate(chosen):
            member = group.loc[group["study_participant_id"] == participant_id].copy()
            member["bootstrap_cluster_id"] = f"{participant_id}__draw{draw}"
            sampled.append(member)
    return pd.concat(sampled, ignore_index=True)


def _bootstrap_intervals(
    development: pd.DataFrame,
    validation: pd.DataFrame,
    specification: ModelSpecification,
    repetitions: int,
) -> dict[str, tuple[float, float]]:
    """Refit development models and resample held-out participant clusters for every replicate."""
    rng = np.random.default_rng(RANDOM_SEED)
    rows: list[dict[str, float]] = []
    for _ in range(repetitions):
        boot_development = _resample_clusters(development, rng, stratify_study=True)
        boot_validation = _resample_clusters(validation, rng, stratify_study=False)
        boot_validation["predicted_probability"] = _fit_probability_model(
            boot_development, boot_validation, specification.features
        )
        boot_validation["raw_score"] = boot_validation[specification.features[0]]
        boot_validation["null_probability"] = boot_development["correct"].sum() / boot_development["n"].sum()
        rows.append(_validation_metrics(boot_validation))
    metrics = pd.DataFrame(rows)
    return {
        metric: (float(metrics[metric].quantile(0.025)), float(metrics[metric].quantile(0.975)))
        for metric in metrics.columns
        if metric not in {"n_session_condition_records", "n_sessions", "n_study_records", "n_character_trials"}
    }


def build_analysis_records(
    trial_table: pd.DataFrame, feature_table: pd.DataFrame, metadata_table: pd.DataFrame
) -> pd.DataFrame:
    """Link calibration-only features to session-condition online spelling outcomes."""
    eligible = trial_table.loc[trial_table["eligible"]].copy()
    outcome = (
        eligible.groupby(["study", "study_participant_id", "session_id", "condition"], as_index=False)
        .agg(correct=("correct", "sum"), n=("correct", "size"))
    )
    feature_columns = [
        "study",
        "study_participant_id",
        "session_id",
        "calibration_auc",
        "calibration_accuracy",
        "shrinkage_lda_auc",
        "pz_difference_uv",
        "posterior_difference_uv",
        "posterior_signed_r2_max",
        "train_file_count",
        "n_target_epochs",
        "n_nontarget_epochs",
        "n_calibration_epochs",
        "n_calibration_epochs_pre_artifact",
        "artifact_rejection_fraction",
    ]
    missing_features = sorted(set(feature_columns) - set(feature_table.columns))
    if missing_features:
        raise ValueError(f"feature table missing columns: {', '.join(missing_features)}")
    clinical = metadata_table[["study", "study_participant_id", "alsfrs_r"]].drop_duplicates()
    records = (
        outcome.merge(
            feature_table[feature_columns],
            on=["study", "study_participant_id", "session_id"],
            how="inner",
            validate="many_to_one",
        )
        .merge(clinical, on=["study", "study_participant_id"], how="left", validate="many_to_one")
        .sort_values(["study", "study_participant_id", "session_id", "condition"], ignore_index=True)
    )
    if records.empty or records["calibration_auc"].isna().any():
        raise ValueError("analysis records contain missing primary calibration scores")
    return records


def run_source_study_held_out_validation(
    records: pd.DataFrame,
    specification: ModelSpecification,
    bootstrap_repetitions: int = BOOTSTRAP_REPETITIONS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit on source studies and evaluate session-condition probabilities in each held-out source."""
    required = {"study", "study_participant_id", "session_id", "correct", "n", *specification.features}
    missing = sorted(required - set(records.columns))
    if missing:
        raise ValueError(f"records missing model columns: {', '.join(missing)}")
    modeled = records.dropna(subset=list(specification.features)).copy()
    predictions: list[pd.DataFrame] = []
    metric_rows: list[dict[str, object]] = []
    split_definitions: list[tuple[str, pd.DataFrame, pd.DataFrame]] = []
    for held_out, development, validation in leave_one_study_out(modeled):
        held_out_predictions = validation.copy()
        held_out_predictions["predicted_probability"] = _fit_probability_model(
            development, held_out_predictions, specification.features
        )
        held_out_predictions["raw_score"] = held_out_predictions[specification.features[0]]
        held_out_predictions["null_probability"] = development["correct"].sum() / development["n"].sum()
        held_out_predictions["held_out_study"] = held_out
        held_out_predictions["model"] = specification.name
        held_out_predictions["model_role"] = specification.role
        metrics = _validation_metrics(held_out_predictions)
        intervals = _bootstrap_intervals(development, validation, specification, bootstrap_repetitions)
        row: dict[str, object] = {
            "model": specification.name,
            "model_role": specification.role,
            "held_out_study": held_out,
            **metrics,
        }
        for metric, interval in intervals.items():
            row[f"{metric}_ci_low"], row[f"{metric}_ci_high"] = interval
        metric_rows.append(row)
        predictions.append(held_out_predictions)
        split_definitions.append((held_out, development, validation))
    all_predictions = pd.concat(predictions, ignore_index=True)
    pooled_metrics = _validation_metrics(all_predictions)
    pooled_bootstrap_rows: list[dict[str, float]] = []
    rng = np.random.default_rng(RANDOM_SEED)
    for _ in range(bootstrap_repetitions):
        boot_predictions: list[pd.DataFrame] = []
        for _, development, validation in split_definitions:
            boot_development = _resample_clusters(development, rng, stratify_study=True)
            boot_validation = _resample_clusters(validation, rng, stratify_study=False)
            boot_validation["predicted_probability"] = _fit_probability_model(
                boot_development, boot_validation, specification.features
            )
            boot_validation["raw_score"] = boot_validation[specification.features[0]]
            boot_validation["null_probability"] = boot_development["correct"].sum() / boot_development["n"].sum()
            boot_predictions.append(boot_validation)
        pooled_bootstrap_rows.append(_validation_metrics(pd.concat(boot_predictions, ignore_index=True)))
    pooled_bootstrap = pd.DataFrame(pooled_bootstrap_rows)
    pooled_row: dict[str, object] = {
        "model": specification.name,
        "model_role": specification.role,
        "held_out_study": "Pooled held-out predictions",
        **pooled_metrics,
    }
    for metric in pooled_bootstrap.columns:
        if metric not in {"n_session_condition_records", "n_sessions", "n_study_records", "n_character_trials"}:
            pooled_row[f"{metric}_ci_low"] = float(pooled_bootstrap[metric].quantile(0.025))
            pooled_row[f"{metric}_ci_high"] = float(pooled_bootstrap[metric].quantile(0.975))
    metric_rows.append(pooled_row)
    return all_predictions, pd.DataFrame(metric_rows)


def joint_bootstrap_fold_covariance(
    records: pd.DataFrame,
    specification: ModelSpecification,
    repetitions: int = BOOTSTRAP_REPETITIONS,
) -> dict[str, object]:
    """Jointly bootstrap every leave-one-study-out fold to capture their shared-development covariance.

    A bootstrap run independently per held-out cohort (as ``_bootstrap_intervals`` and
    ``heterogeneity._bootstrap_standard_errors`` both do) cannot see that up to 16 of 17 development
    cohorts are shared between any two folds: each fold resamples its own development set separately,
    so a cohort appearing in two different folds' development sets gets two independent draws instead
    of the same one. This function resamples every cohort's participants once per replicate, then
    refits all 18 folds from that single resampled dataset, so the correlation the shared development
    data induces between folds is captured directly in the resulting empirical covariance rather than
    assumed away by treating the 18 held-out estimates as independent, which the primary random-effects
    pooling does.

    Each fold's fit uses ``_fit_calibration_model_guarded`` rather than ``_fit_calibration_model``,
    because a resampled fold can draw an unrepresentative, near-constant mix of a held-out cohort's
    outcomes: under statsmodels 0.14 that quasi-separated fit does not raise, it converges to a
    huge-but-finite coefficient, which is indistinguishable from a real, precise estimate by
    finiteness alone. Left unguarded, those replicates dominate the resulting covariance and the
    per-replicate spread below. A cohort whose surviving-replicate count falls below
    ``repetitions // 2`` is reported as not identified under this method, the same threshold and the
    same reporting convention ``heterogeneity._bootstrap_standard_errors`` and
    ``scripts/08_run_heterogeneity.py``'s ``bootstrap_replicate_diagnostics.csv`` already use.

    ``replicate_between_cohort_sd_intercept``/``_slope`` is not a dependence-aware substitute for the
    meta-analytic tau. Studies themselves are never resampled here, only the participants within each
    fixed cohort, so the spread of the 18 held-out estimates within one replicate mixes genuine
    between-cohort heterogeneity together with each fold's own within-cohort sampling noise: it
    estimates something closer to ``sqrt(tau^2 + mean within-cohort sampling variance)``, which is
    structurally at least as large as tau and does not converge to it as the within-cohort sample
    grows. Report it as an empirical, assumption-light quantity that combines both sources of spread,
    not as a corrected or dependence-aware tau.
    """
    modeled = records.dropna(subset=list(specification.features)).copy()
    studies = sorted(modeled["study"].unique())
    rng = np.random.default_rng(RANDOM_SEED)

    intercepts: dict[str, list[float]] = {study: [] for study in studies}
    slopes: dict[str, list[float]] = {study: [] for study in studies}
    replicate_spread_intercept: list[float] = []
    replicate_spread_slope: list[float] = []

    for _ in range(repetitions):
        resampled = _resample_clusters(modeled, rng, stratify_study=True)
        this_replicate_intercepts: list[float] = []
        this_replicate_slopes: list[float] = []
        for held_out, development, validation in leave_one_study_out(resampled):
            validation = validation.copy()
            validation["predicted_probability"] = _fit_probability_model(
                development, validation, specification.features
            )
            labels, expanded_probabilities = _expanded_binary(validation)
            intercept, slope, identified = _fit_calibration_model_guarded(labels, expanded_probabilities)
            intercepts[held_out].append(intercept)
            slopes[held_out].append(slope)
            if identified:
                this_replicate_intercepts.append(intercept)
                this_replicate_slopes.append(slope)
        if len(this_replicate_intercepts) >= 2:
            replicate_spread_intercept.append(float(np.std(this_replicate_intercepts, ddof=1)))
        if len(this_replicate_slopes) >= 2:
            replicate_spread_slope.append(float(np.std(this_replicate_slopes, ddof=1)))

    frame = pd.DataFrame(
        {f"{study}_intercept": intercepts[study] for study in studies}
        | {f"{study}_slope": slopes[study] for study in studies}
    )
    covariance = frame.cov()
    correlation = frame.corr()
    n_finite_per_study = {
        study: int(np.sum(np.isfinite(intercepts[study]) & np.isfinite(slopes[study])))
        for study in studies
    }
    discard_threshold = repetitions // 2
    identified_per_study = {
        study: bool(n_finite_per_study[study] >= discard_threshold) for study in studies
    }

    def _spread_summary(values: list[float]) -> dict[str, float]:
        if not values:
            return {"mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
        return {
            "mean": float(np.mean(values)),
            "ci_low": float(np.quantile(values, 0.025)),
            "ci_high": float(np.quantile(values, 0.975)),
        }

    return {
        "n_replicates": repetitions,
        "studies": studies,
        "covariance_matrix": covariance,
        "correlation_matrix": correlation,
        "n_finite_per_study": n_finite_per_study,
        "discard_threshold": discard_threshold,
        "identified_per_study": identified_per_study,
        "replicate_between_cohort_sd_intercept": _spread_summary(replicate_spread_intercept),
        "replicate_between_cohort_sd_slope": _spread_summary(replicate_spread_slope),
    }


# Backward-compatible public name retained for scripts and reproducible reruns.
run_external_validation = run_source_study_held_out_validation
