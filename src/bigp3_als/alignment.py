"""Euclidean Alignment of calibration epochs, and cohort-wise alignment of the score itself.

Two questions sit behind this module, and they are not the same question.

Euclidean Alignment whitens each recording by the inverse square root of its own mean epoch
covariance, so that recordings made through different amplifiers, caps and impedances arrive at the
classifier on a common scale.[He and Wu 2020] It is the standard unsupervised answer in the
brain-computer interface transfer literature to inter-subject and inter-cohort variation, and it
needs no labels from the target recording, so a site could apply it on day one. Whether it makes a
calibration-derived score comparable enough across cohorts for a single fitted mapping to hold is
the question this study can answer and had not asked.

The second family aligns the score rather than the signal. Standardising a cohort's calibration
scores within that cohort, or replacing them by within-cohort normal quantiles, needs only the
target cohort's own unlabeled calibration recordings, never its online accuracy. That is a real
deployment requirement, not a free lunch: it assumes a new site can collect calibration blocks from
enough users to characterise its own score distribution before it estimates anyone's accuracy.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy import stats

from bigp3_als.validation import ModelSpecification

# An eigenvalue below this fraction of the largest is treated as a numerically empty direction and
# floored rather than inverted. A 16-channel reference built from thousands of epochs is normally
# far from singular; the floor exists so that a degenerate recording returns a finite whitener and
# is caught downstream by the feature gates, instead of producing an infinite feature value that
# propagates into an AUC.
RELATIVE_EIGENVALUE_FLOOR = 1e-10

# Standardisation happens over a cohort's distinct sessions, not its records: a session run under
# several conditions would otherwise pull a cohort's mean and scale toward however many conditions
# it happened to run, which is a protocol fact and not a property of the score.
SESSION_KEYS = ("study", "study_participant_id", "session_id")


def reference_covariance(epochs: np.ndarray) -> np.ndarray:
    """Return the Euclidean Alignment reference: the mean epoch covariance of one recording."""
    if epochs.ndim != 3 or len(epochs) == 0:
        raise ValueError("epochs must be a non-empty (trial, channel, sample) array")
    n_samples = epochs.shape[2]
    if n_samples == 0:
        raise ValueError("epochs must have at least one sample")
    return np.einsum("tcs,tds->cd", epochs, epochs) / (n_samples * len(epochs))


def inverse_square_root(matrix: np.ndarray, relative_floor: float = RELATIVE_EIGENVALUE_FLOOR) -> np.ndarray:
    """Return the symmetric inverse square root, flooring numerically empty directions."""
    eigenvalues, eigenvectors = np.linalg.eigh(np.asarray(matrix, dtype=float))
    largest = float(eigenvalues.max())
    if not np.isfinite(largest) or largest <= 0.0:
        raise ValueError("reference matrix has no positive eigenvalue")
    clipped = np.clip(eigenvalues, largest * relative_floor, None)
    return (eigenvectors * clipped**-0.5) @ eigenvectors.T


def euclidean_align(epochs: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Whiten every epoch of a recording by the inverse square root of a reference covariance."""
    if epochs.ndim != 3:
        raise ValueError("epochs must be a (trial, channel, sample) array")
    if reference.shape != (epochs.shape[1], epochs.shape[1]):
        raise ValueError("reference must be square in the channel dimension")
    return np.einsum("cd,tds->tcs", inverse_square_root(reference), epochs)


def pooled_reference(references: Sequence[np.ndarray], weights: Sequence[float]) -> np.ndarray:
    """Return the epoch-count-weighted mean of several recordings' reference covariances."""
    stacked = np.stack([np.asarray(reference, dtype=float) for reference in references])
    weight_array = np.asarray(weights, dtype=float)
    if len(weight_array) != len(stacked):
        raise ValueError("references and weights must align")
    if not np.all(weight_array > 0):
        raise ValueError("weights must be positive")
    return np.tensordot(weight_array, stacked, axes=(0, 0)) / weight_array.sum()


def cohort_standardised(records: pd.DataFrame, feature: str, method: str = "z") -> pd.Series:
    """Align a predictor within each cohort using only that cohort's unlabeled calibration scores.

    The score is defined per session, so the location and scale are taken over a cohort's distinct
    sessions and then mapped back onto its records. Taking them over records would weight a cohort
    by how many conditions it happened to run, which is a protocol fact and not a property of the
    score.

    A cohort with one distinct session has no scale to estimate, so its rows come back missing
    rather than zero. Zero would be a valid-looking standardised score for a cohort where the
    quantity is undefined, and the held-out validation would then fit against a fabricated value.
    """
    if method not in {"z", "rank"}:
        raise ValueError(f"unknown cohort alignment method: {method}")
    keys = list(SESSION_KEYS)
    sessions = records[[*keys, feature]].drop_duplicates(subset=keys)
    transformed: list[pd.DataFrame] = []
    for study, block in sessions.groupby("study", sort=False):
        values = pd.to_numeric(block[feature], errors="coerce")
        observed = values.notna()
        aligned = pd.Series(np.nan, index=block.index, dtype=float)
        if int(observed.sum()) >= 2:
            if method == "z":
                # Population standard deviation, not sample: a cohort's distinct sessions are the
                # entire population this transform standardises over, not a sample estimating some
                # larger one, and ddof=1 gives a two-session cohort a z of 1/sqrt(2) instead of 1.
                # Matches the ddof=0 convention `validation._fit_probability_model` already uses.
                scale = float(values[observed].std(ddof=0))
                if scale > 0:
                    aligned.loc[observed] = (values[observed] - float(values[observed].mean())) / scale
            else:
                ranks = values[observed].rank(method="average")
                aligned.loc[observed] = stats.norm.ppf(ranks / (int(observed.sum()) + 1))
        block = block.assign(**{"_aligned": aligned})
        transformed.append(block[[*keys, "_aligned"]])
    lookup = pd.concat(transformed, ignore_index=True)
    merged = records[keys].merge(lookup, on=keys, how="left", validate="many_to_one")
    return pd.Series(merged["_aligned"].to_numpy(dtype=float), index=records.index, name=f"{feature}_{method}")


ALIGNMENT_SPECS = (
    ModelSpecification("calibration_auc_ea_session", ("calibration_auc_ea_session",), "alignment"),
    ModelSpecification("calibration_auc_ea_cohort", ("calibration_auc_ea_cohort",), "alignment"),
    ModelSpecification("calibration_auc_cohort_z", ("calibration_auc_cohort_z",), "alignment"),
    ModelSpecification("calibration_auc_cohort_rank", ("calibration_auc_cohort_rank",), "alignment"),
    ModelSpecification("calibration_auc_rbf", ("calibration_auc_rbf",), "nonlinear"),
    ModelSpecification("calibration_auc_gbm", ("calibration_auc_gbm",), "nonlinear"),
)
