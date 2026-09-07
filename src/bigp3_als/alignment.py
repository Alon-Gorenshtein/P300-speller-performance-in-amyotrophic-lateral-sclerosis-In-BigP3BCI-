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

# An eigenvalue below this fraction of the largest is treated as a numerically empty direction and
# floored rather than inverted. A 16-channel reference built from thousands of epochs is normally
# far from singular; the floor exists so that a degenerate recording returns a finite whitener and
# is caught downstream by the feature gates, instead of producing an infinite feature value that
# propagates into an AUC.
RELATIVE_EIGENVALUE_FLOOR = 1e-10


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
