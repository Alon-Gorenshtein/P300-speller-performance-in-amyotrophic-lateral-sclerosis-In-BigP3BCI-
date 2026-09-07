# JNE-111284 Major Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Answer every Referee 1, Referee 2 and Editor-in-Chief comment on JNE-111284 with real analysis where analysis was asked for, and ship the five-file revised submission packet JNE's checklist requires.

**Architecture:** Three new analyses bolt onto the existing leave-one-study-out machinery without touching the frozen primary results. A new `alignment.py` module supplies Euclidean Alignment and cohort-wise score standardisation; a new `recalibration.py` module supplies the local-recalibration learning curve; `features.py` gains a nonlinear decoder arm. Every new predictor is put through the same `run_source_study_held_out_validation` plus `cohort_calibration` plus `random_effects` path the paper's headline already uses, so the reported quantity is directly comparable to the published tau. Manuscript changes follow, then the packet build.

**Tech Stack:** Python 3.11, NumPy, SciPy, scikit-learn, statsmodels, pandas, MNE, matplotlib, pytest, pandoc + xelatex through `_pub_assets/build_pub.sh`.

**Spec:** `docs/superpowers/specs/2026-09-07-jne-111284-major-revision.md`

## Global Constraints

Every task's requirements implicitly include this section.

- **Environment is mandatory, not conventional.** Every Python command runs as
  `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run <command>`.
  A project-local `.venv` on this exFAT volume accumulates AppleDouble `._*.mplstyle` sidecars that break `import matplotlib.pyplot`. If a test fails, print `sys.prefix` before believing the failure.
- **Hold `caffeinate -ims` around any run over an hour.** Tasks 3 and 4 are ~45 min each. A sleeping Mac is indistinguishable from a hang.
- **Never overwrite the frozen primary outputs.** `output/expanded/calibration_features_all20.csv` (in `output/intermediate/`), `analysis_records.csv`, `cohort_calibration.csv`, `heterogeneity_summary.json` and `external_validation_predictions.csv` are the numbers the published manuscript is written from. New work writes new filenames.
- **Cluster-robust is primary.** `cohort_calibration.csv` stacks 54 rows in three `se_method` blocks; always filter to `se_method == "cluster"`.
- **Never write a sentence that needs I-squared above 75.** The slope's I-squared is 79.1 and clears 75 by four points; a 20% within-cohort variance understatement puts it at 74.9. The intercept (tau 0.873, I-squared 86.1) leads every transportability claim.
- **Missing is not zero.** `(s < thr).astype(float)` turns NaN into a negative. Guard every threshold with an explicit `.notna()`.
- **`pytest tests/test_regression_baseline.py` alone collects zero tests.** The slow guard needs `-m slow`.
- **Prose rules:** no em dashes, no AI tells (run the `de-ai-writing` scan), AMA-numbered references, statistics formatted exactly as the existing manuscript formats them.
- **Commit message footer,** on every commit in this plan:
  ```
  Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5
  ```
- **Work on a branch.** `git switch -c jne-r1-revision` before Task 1. Do not commit to `main` until the whole plan is done and reviewed. Two prior passes on this repo lost work to subagents committing on `main` from the wrong checkout; if a subagent's file edit lands somewhere unexpected, check `git -C . status` in both checkouts before doing anything else.
- **Baseline for every "did anything drift" check** is commit `8a56d0c`.

---

## File Structure

| Path | Status | Responsibility |
| --- | --- | --- |
| `src/bigp3_als/alignment.py` | Create | Euclidean Alignment primitives (reference covariance, inverse square root, whitening), cohort-wise score standardisation, and the `ALIGNMENT_SPECS` list of new model specifications. |
| `src/bigp3_als/recalibration.py` | Create | Local-recalibration learning curve: repeated participant draws inside each withheld cohort, intercept-only and intercept-plus-slope refits, paired comparison against the transported mapping. |
| `src/bigp3_als/features.py` | Modify | Nonlinear decoder arm inside `_grouped_cv_predictions`; new public `nonlinear_discriminability`; alignment hooks in `_session_feature_row`. |
| `src/bigp3_als/validation.py` | Modify (one line) | `build_analysis_records` feature-column list gains the new predictor columns. |
| `src/bigp3_als/render_expanded.py` | Modify | Two new figure renderers, reusing the existing colour, marker and `_save` conventions. |
| `scripts/04b_extract_alignment_features.py` | Create | The expensive EDF pass. Two invocations: session-level (writes reference covariances) then cohort-level. |
| `scripts/17_run_alignment.py` | Create | Runs every alignment arm through the held-out validation and the heterogeneity summary. |
| `scripts/18_run_recalibration.py` | Create | Runs the learning curve and writes its summary. |
| `scripts/13_render_figures.py` | Modify | Calls the two new renderers. |
| `tests/test_alignment.py` | Create | Alignment primitives and score standardisation. |
| `tests/test_recalibration.py` | Create | Learning-curve behaviour, separation guard, paired-evaluation correctness. |
| `tests/test_features.py` | Modify | Nonlinear arm. |
| `manuscript/manuscript_expanded.md` | Modify | All prose changes. |
| `manuscript/manuscript_highlighted.md` | Create | Same body with `[...]{.mark}` spans around every change. |
| `manuscript/response_to_reviewers_jne_r1.md` | Create | The Author Response document. |
| `manuscript/cover_letter_expanded.md` | Modify | Revision cover letter. |
| `supplementary/supplement_expanded.md` | Modify | New tables S13 onward, plus the estimator-agreement text moved in from the main Discussion. |
| `supplementary/tripod_checklist.md` | Modify | Updated for the new analyses. |
| `scripts/19_build_jne_revision_packet.py` | Create | Builds the numbered packet under `_submission_ready/.../REVISION_R1_JNE-111284/`. |
| `docs/pipeline_rerun_2026-09-07_alignment.md` | Create | Movement report for the new extraction pass, in the style of `docs/pipeline_rerun_2026-07-26.md`. |

---

### Task 1: Euclidean Alignment primitives

Answers the Editor-in-Chief's data re-alignment request and Referee 2 comment 3. This task is pure numerics with no I/O, so it can be fully tested before the expensive pass in Task 3 depends on it.

**Files:**
- Create: `src/bigp3_als/alignment.py`
- Test: `tests/test_alignment.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `reference_covariance(epochs: np.ndarray) -> np.ndarray` returning a `(channel, channel)` array.
  - `inverse_square_root(matrix: np.ndarray, relative_floor: float = 1e-10) -> np.ndarray`.
  - `euclidean_align(epochs: np.ndarray, reference: np.ndarray) -> np.ndarray` returning an array of the same shape as `epochs`.
  - `pooled_reference(references: Sequence[np.ndarray], weights: Sequence[float]) -> np.ndarray`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_alignment.py`:

```python
"""Tests for Euclidean Alignment of calibration epochs."""

from __future__ import annotations

import numpy as np
import pytest

from bigp3_als.alignment import (
    euclidean_align,
    inverse_square_root,
    pooled_reference,
    reference_covariance,
)


def test_reference_covariance_is_the_mean_epoch_covariance() -> None:
    rng = np.random.default_rng(11)
    epochs = rng.normal(size=(7, 3, 20))

    reference = reference_covariance(epochs)

    expected = np.mean([epoch @ epoch.T / epoch.shape[1] for epoch in epochs], axis=0)
    assert reference.shape == (3, 3)
    assert np.allclose(reference, expected)


def test_aligning_a_recording_to_its_own_reference_whitens_it() -> None:
    rng = np.random.default_rng(12)
    mixing = rng.normal(size=(4, 4))
    epochs = np.einsum("cd,tds->tcs", mixing, rng.normal(size=(200, 4, 64)))

    aligned = euclidean_align(epochs, reference_covariance(epochs))

    assert np.allclose(reference_covariance(aligned), np.eye(4), atol=1e-8)


def test_alignment_removes_a_per_channel_gain_difference() -> None:
    rng = np.random.default_rng(13)
    epochs = rng.normal(size=(120, 4, 40))
    gains = np.diag([1.0, 5.0, 0.2, 3.0])
    rescaled = np.einsum("cd,tds->tcs", gains, epochs)

    aligned = euclidean_align(epochs, reference_covariance(epochs))
    aligned_rescaled = euclidean_align(rescaled, reference_covariance(rescaled))

    # Whitening is unique only up to rotation, so compare the invariant the classifier sees:
    # the Gram matrix of the flattened trials.
    left = aligned.reshape(len(aligned), -1)
    right = aligned_rescaled.reshape(len(aligned_rescaled), -1)
    assert np.allclose(left @ left.T, right @ right.T, rtol=1e-6, atol=1e-8)


def test_inverse_square_root_floors_a_singular_direction_instead_of_exploding() -> None:
    matrix = np.diag([4.0, 1.0, 0.0])

    whitener = inverse_square_root(matrix, relative_floor=1e-6)

    assert np.isfinite(whitener).all()
    assert whitener[2, 2] == pytest.approx(1.0 / np.sqrt(4.0 * 1e-6))


def test_inverse_square_root_rejects_a_matrix_with_no_positive_eigenvalue() -> None:
    with pytest.raises(ValueError, match="positive"):
        inverse_square_root(np.zeros((3, 3)))


def test_pooled_reference_weights_recordings_by_their_epoch_count() -> None:
    first = np.eye(2)
    second = np.diag([3.0, 3.0])

    pooled = pooled_reference([first, second], [1.0, 3.0])

    assert np.allclose(pooled, np.diag([2.5, 2.5]))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest tests/test_alignment.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'bigp3_als.alignment'`.

- [ ] **Step 3: Write the implementation**

Create `src/bigp3_als/alignment.py`:

```python
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

from bigp3_als.validation import ModelSpecification

# Session keys: the unit a calibration score is defined on. Records are session-conditions, so a
# score repeats across the conditions of one session and standardising over records rather than
# over sessions would silently weight a cohort by how many conditions it happened to run.
SESSION_KEYS = ("study", "study_participant_id", "session_id")

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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest tests/test_alignment.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/bigp3_als/alignment.py tests/test_alignment.py
git commit -m "feat: add Euclidean Alignment primitives for the cross-cohort alignment arm

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 2: Nonlinear decoder arm

Answers Referee 2 comment 2: is the failure to transport a property of the calibration-to-accuracy mapping, or an artefact of linear decision boundaries? Both existing scores (L2 logistic, shrinkage LDA) are linear. This adds a genuinely nonlinear decision boundary computed on the same epochs by the same grouped cross-validation, so the comparison isolates the boundary.

**Files:**
- Modify: `src/bigp3_als/features.py:84-143`
- Modify: `tests/test_features.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `nonlinear_discriminability(epochs, labels, groups, classifier="rbf") -> float`, and the `"rbf"` and `"gradient_boosting"` branches of `_grouped_cv_predictions`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_features.py`:

```python
def test_nonlinear_discriminability_recovers_a_boundary_a_linear_model_cannot() -> None:
    # An exclusive-or arrangement in two channels: no linear boundary separates it, so the linear
    # score sits near chance while a kernel boundary does not. This is the property the arm exists
    # to test, so the test asserts the gap rather than only that the number is finite.
    rng = np.random.default_rng(7)
    epochs = rng.normal(scale=0.2, size=(400, 4, 12))
    corner = rng.integers(0, 2, size=(400, 2)).astype(float)
    epochs[:, 0, :] += corner[:, [0]] * 3.0
    epochs[:, 1, :] += corner[:, [1]] * 3.0
    labels = (corner[:, 0] != corner[:, 1]).astype(int)
    groups = np.arange(400) % 4

    linear = calibration_discriminability(epochs, labels, groups)
    nonlinear = nonlinear_discriminability(epochs, labels, groups)

    assert 0.4 < linear < 0.6
    assert nonlinear > 0.8


def test_nonlinear_discriminability_rejects_an_unknown_classifier() -> None:
    rng = np.random.default_rng(8)
    epochs = rng.normal(size=(40, 3, 8))
    labels = np.repeat([0, 1], 20)
    groups = np.arange(40) % 3

    with pytest.raises(ValueError, match="unknown calibration classifier"):
        nonlinear_discriminability(epochs, labels, groups, classifier="not_a_model")
```

Add `pytest` and `nonlinear_discriminability` to that file's imports.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest tests/test_features.py -v`
Expected: FAIL, `ImportError: cannot import name 'nonlinear_discriminability'`.

- [ ] **Step 3: Write the implementation**

In `src/bigp3_als/features.py`, add to the imports:

```python
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.kernel_approximation import Nystroem
```

Add two branches inside `_grouped_cv_predictions`, after the `shrinkage_lda` branch and before the `raise`:

```python
        elif classifier == "rbf":
            # A radial-basis kernel boundary, reached through a Nystroem approximation rather than
            # an exact support-vector machine. A session carries on the order of ten thousand
            # calibration epochs and an exact kernel machine is quadratic in that count, which would
            # put the extraction pass into days. The approximation is fitted inside the training
            # fold only, so the grouped split still holds.
            model = make_pipeline(
                StandardScaler(),
                Nystroem(kernel="rbf", gamma="scale", n_components=300, random_state=20260718),
                LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=20260718),
            )
        elif classifier == "gradient_boosting":
            # A tree ensemble on a principal-component reduction of the same epoch features. The
            # reduction is what makes the arm affordable: boosting bins every feature, and binning
            # a thousand of them per fold costs more than the whole rest of the pass. Both stages
            # are fitted inside the training fold.
            model = make_pipeline(
                StandardScaler(),
                PCA(n_components=40, svd_solver="randomized", random_state=20260718),
                HistGradientBoostingClassifier(
                    max_iter=100,
                    max_leaf_nodes=15,
                    learning_rate=0.1,
                    l2_regularization=1.0,
                    early_stopping=False,
                    random_state=20260718,
                ),
            )
```

Add the public function beside `shrinkage_lda_discriminability`:

```python
def nonlinear_discriminability(
    epochs: np.ndarray, labels: np.ndarray, groups: np.ndarray, classifier: str = "rbf"
) -> float:
    """Estimate grouped-CV AUC of a nonlinear decision boundary on the same calibration epochs.

    Both scores the study reports so far come from linear decoders, so a mapping that fails to
    transport could in principle be a property of linear boundaries rather than of the
    calibration-to-accuracy relationship. This arm holds the epochs, the grouped split and the
    metric fixed and varies only the boundary.
    """
    return float(roc_auc_score(labels, _grouped_cv_predictions(epochs, labels, groups, classifier)))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest tests/test_features.py -v`
Expected: all pass, including the two new tests.

- [ ] **Step 5: Time the arms on five real sessions and decide whether both survive**

The gradient-boosting arm is the expensive one and may not be affordable. Measure before committing to it. Write `tmp/probe_nonlinear_timing.py`:

```python
"""Measure the per-session cost of each new arm on five real sessions."""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

from bigp3_als.edf import parse_source_path, select_edf_paths
from bigp3_als.features import (
    _extract_file_epochs,
    calibration_discriminability,
    nonlinear_discriminability,
)

CACHE = Path("data/source_cache_full")
grouped: dict[tuple[str, str, str], list[Path]] = defaultdict(list)
for edf_path in select_edf_paths(CACHE):
    source = parse_source_path(edf_path.relative_to(CACHE).as_posix())
    if source.phase == "Train":
        grouped[(source.study, source.participant_id, source.session_id)].append(edf_path)

import numpy as np

for key, paths in sorted(grouped.items())[:5]:
    parts = [_extract_file_epochs(path) for path in paths]
    epochs = np.concatenate([part[0] for part in parts])
    labels = np.concatenate([part[1] for part in parts])
    groups = np.concatenate([np.repeat(i, len(part[1])) for i, part in enumerate(parts)])
    for name, call in (
        ("baseline_logistic", lambda: calibration_discriminability(epochs, labels, groups)),
        ("rbf", lambda: nonlinear_discriminability(epochs, labels, groups, "rbf")),
        ("gradient_boosting", lambda: nonlinear_discriminability(epochs, labels, groups, "gradient_boosting")),
    ):
        start = time.perf_counter()
        score = call()
        print(f"{key[0]}/{key[1]}/{key[2]} n={len(labels)} {name} auc={score:.4f} {time.perf_counter() - start:.1f}s")
```

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python tmp/probe_nonlinear_timing.py`

**Decision rule, applied literally.** Take the mean added seconds per session across the five probes and multiply by 521 sessions.
- Projected total added time under 2 hours: keep both arms.
- Between 2 and 4 hours: drop `gradient_boosting` to `max_iter=50` and re-probe.
- Still over 4 hours: drop the `gradient_boosting` arm entirely, keep `rbf`, and record the measured projection in `docs/pipeline_rerun_2026-09-07_alignment.md` as the stated reason. One nonlinear family answers Referee 2's question; two is a bonus, not a requirement.

Record the measured numbers in the commit message.

- [ ] **Step 6: Commit**

```bash
git add src/bigp3_als/features.py tests/test_features.py
git commit -m "feat: add a nonlinear calibration decoder arm for reviewer 2's boundary question

Probed on five sessions: <paste the measured per-session seconds and the
521-session projection, and state which arms survived the decision rule>.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 3: Extraction pass one, session-level alignment and the nonlinear arms

The expensive task. Reads every Train EDF once and produces the session-level alignment score, the nonlinear scores, and the per-session reference covariances Task 4 needs. It also **recomputes the frozen baseline `calibration_auc` and refuses to write anything if it does not reproduce**, which is what proves the new columns sit on the same footing as the published ones.

**Files:**
- Create: `scripts/04b_extract_alignment_features.py`
- Modify: `src/bigp3_als/features.py` (a new `_alignment_feature_row` and a `build_alignment_features` entry point)
- Modify: `.gitignore`
- Create: `docs/pipeline_rerun_2026-09-07_alignment.md`

**Interfaces:**
- Consumes: `alignment.reference_covariance`, `alignment.euclidean_align` (Task 1); `features.nonlinear_discriminability` (Task 2).
- Produces:
  - `output/intermediate/calibration_features_all20_alignment.csv` with columns `study, participant_id, study_participant_id, session_id, calibration_auc_reproduced, calibration_auc_ea_session, calibration_auc_rbf, calibration_auc_gbm` (the last only if Task 2's decision rule kept it).
  - `output/intermediate/session_reference_covariances.npz`, one 16-by-16 array per session keyed `study|participant|session`, plus an `n_epochs` array in the same key order.

- [ ] **Step 1: Add the builder to `features.py`**

Add near `build_calibration_features`:

```python
def _alignment_feature_row(session_paths: list[Path], cache_path: Path, arms: tuple[str, ...]) -> dict[str, object]:
    """Return one session's alignment and nonlinear scores, plus its reference covariance.

    The baseline `calibration_auc` is recomputed here and returned as
    `calibration_auc_reproduced`. It is not used by the manuscript; it exists so the caller can
    prove this pass reproduces the frozen feature file before any new column derived in the same
    pass is trusted.
    """
    source = parse_source_path(session_paths[0].relative_to(cache_path).as_posix())
    epochs_list, labels_list, groups_list = [], [], []
    for group_index, path in enumerate(session_paths):
        epochs, labels, _, _ = _extract_file_epochs(path)
        epochs_list.append(epochs)
        labels_list.append(labels)
        groups_list.append(np.repeat(group_index, len(labels)))
    epochs = np.concatenate(epochs_list)
    labels = np.concatenate(labels_list)
    groups = np.concatenate(groups_list)
    row: dict[str, object] = {
        "study": source.study,
        "participant_id": source.participant_id,
        "study_participant_id": source.study_participant_id,
        "session_id": source.session_id,
        "n_calibration_epochs": int(len(labels)),
    }
    reference = reference_covariance(epochs) if len(labels) else None
    if (
        int((labels == 1).sum()) < MIN_TARGET_EPOCHS
        or int((labels == 0).sum()) < MIN_NONTARGET_EPOCHS
        or len(np.unique(groups)) < 2
    ):
        for column in ("calibration_auc_reproduced", *arms):
            row[column] = np.nan
        return {**row, "reference_covariance": reference}
    try:
        row["calibration_auc_reproduced"] = calibration_discriminability(epochs, labels, groups)
        if "calibration_auc_ea_session" in arms:
            aligned = euclidean_align(epochs, reference)
            row["calibration_auc_ea_session"] = calibration_discriminability(aligned, labels, groups)
        if "calibration_auc_rbf" in arms:
            row["calibration_auc_rbf"] = nonlinear_discriminability(epochs, labels, groups, "rbf")
        if "calibration_auc_gbm" in arms:
            row["calibration_auc_gbm"] = nonlinear_discriminability(
                epochs, labels, groups, "gradient_boosting"
            )
    except ValueError:
        for column in ("calibration_auc_reproduced", *arms):
            row.setdefault(column, np.nan)
    return {**row, "reference_covariance": reference}


def build_alignment_features(
    cache_path: Path, arms: tuple[str, ...]
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """Return the alignment feature table and the per-session reference covariances."""
    grouped_paths: dict[tuple[str, str, str], list[Path]] = defaultdict(list)
    for edf_path in select_edf_paths(cache_path):
        source = parse_source_path(edf_path.relative_to(cache_path).as_posix())
        if source.phase == "Train":
            grouped_paths[(source.study, source.participant_id, source.session_id)].append(edf_path)
    if not grouped_paths:
        raise ValueError("no Train EDF files found in source cache")
    rows, references = [], {}
    for key, paths in sorted(grouped_paths.items()):
        row = _alignment_feature_row(paths, cache_path, arms)
        reference = row.pop("reference_covariance")
        if reference is not None:
            references["|".join(key)] = reference
        rows.append(row)
    frame = pd.DataFrame(rows).sort_values(["study", "participant_id", "session_id"], ignore_index=True)
    return frame, references
```

Add `from bigp3_als.alignment import euclidean_align, reference_covariance` to the imports.

- [ ] **Step 2: Write the script**

Create `scripts/04b_extract_alignment_features.py`:

```python
"""Derive the alignment and nonlinear calibration scores the JNE revision requires.

Kept separate from `04_extract_features.py` because that script writes the frozen feature file the
published results are computed from, and nothing in this revision may overwrite it. The baseline
score is nonetheless recomputed here and checked against the frozen file: a new column is only
worth reading if the pass that produced it reproduces the column the paper already reports.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from bigp3_als.features import build_alignment_features

KEYS = ["study", "study_participant_id", "session_id"]
REPRODUCTION_TOLERANCE = 1e-9


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path("data/source_cache_full"))
    parser.add_argument("--frozen", type=Path,
                        default=Path("output/intermediate/calibration_features_all20.csv"))
    parser.add_argument("--output", type=Path,
                        default=Path("output/intermediate/calibration_features_all20_alignment.csv"))
    parser.add_argument("--covariances", type=Path,
                        default=Path("output/intermediate/session_reference_covariances.npz"))
    parser.add_argument("--arms", nargs="+",
                        default=["calibration_auc_ea_session", "calibration_auc_rbf", "calibration_auc_gbm"])
    arguments = parser.parse_args()

    frame, references = build_alignment_features(arguments.cache, tuple(arguments.arms))

    frozen = pd.read_csv(arguments.frozen)
    merged = frame.merge(frozen[[*KEYS, "calibration_auc"]], on=KEYS, how="inner", validate="one_to_one")
    if len(merged) != len(frozen):
        raise SystemExit(f"session key mismatch: {len(merged)} matched against {len(frozen)} frozen rows")
    both = merged["calibration_auc"].notna() & merged["calibration_auc_reproduced"].notna()
    if bool((merged["calibration_auc"].isna() != merged["calibration_auc_reproduced"].isna()).any()):
        raise SystemExit("a session is usable in one pass and not the other")
    difference = float(np.abs(merged.loc[both, "calibration_auc"]
                              - merged.loc[both, "calibration_auc_reproduced"]).max())
    print(f"baseline reproduction: max |difference| = {difference:.3e} over {int(both.sum())} sessions")
    if difference > REPRODUCTION_TOLERANCE:
        raise SystemExit(f"baseline did not reproduce within {REPRODUCTION_TOLERANCE:g}; refusing to write")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(arguments.output, index=False)
    keys = sorted(references)
    np.savez_compressed(
        arguments.covariances,
        keys=np.array(keys),
        references=np.stack([references[key] for key in keys]),
        n_epochs=frame.set_index([*KEYS])["n_calibration_epochs"].reindex(
            [tuple(key.split("|", 2)) for key in keys]
        ).to_numpy(dtype=float),
    )
    print(f"wrote {len(frame)} alignment feature rows and {len(keys)} reference covariances")


if __name__ == "__main__":
    main()
```

Note: the covariance key is `study|participant_id|session_id` while the frame is indexed on `study|study_participant_id|session_id`. Build the `n_epochs` array by joining on the same three columns you used to construct the key; if the reindex above returns any NaN, the key construction and the frame index disagree and the script must fail rather than write a NaN. Add before `np.savez_compressed`:

```python
    epoch_counts = frame.set_index(["study", "participant_id", "session_id"])["n_calibration_epochs"]
    ordered = epoch_counts.reindex([tuple(key.split("|", 2)) for key in keys])
    if ordered.isna().any():
        raise SystemExit("covariance keys do not match the feature frame index")
```

and pass `n_epochs=ordered.to_numpy(dtype=float)`.

- [ ] **Step 3: Smoke-test on the small cache**

Run:
```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/04b_extract_alignment_features.py \
  --cache data/source_cache \
  --frozen output/intermediate/calibration_features.csv \
  --output tmp/smoke_alignment.csv \
  --covariances tmp/smoke_covariances.npz
```
Expected: reproduction difference printed as `0.000e+00` (the baseline path is byte-identical code), and the row count matching `calibration_features.csv`.

If it does not reproduce exactly, stop and diagnose before spending 45 minutes on the full cache. The likely cause is a difference in how epochs are concatenated across files.

- [ ] **Step 4: Run the full pass**

```bash
caffeinate -ims env UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 \
  uv run python scripts/04b_extract_alignment_features.py --cache data/source_cache_full \
  2>&1 | tee tmp/extract_alignment_pass1.log
```
Expected: 45 minutes to a few hours depending on Task 2's decision rule; 521 rows; reproduction difference at or below 1e-9.

- [ ] **Step 5: Write the movement report**

Create `docs/pipeline_rerun_2026-09-07_alignment.md` in the style of `docs/pipeline_rerun_2026-07-26.md`. It must state, with numbers computed from the two files, not from memory:

- the command, wall clock and exit status;
- the baseline reproduction difference;
- for each new arm: mean, SD, and the Spearman correlation against `calibration_auc`, plus how many of the 520 evaluable sessions moved up and down;
- **the interpretation set in advance:** a Spearman correlation against the baseline above 0.98 means the arm reorders sessions barely at all, so any change in tau it produces comes from the scale of the score rather than from which sessions score highly; below 0.90 means the arm is measuring something materially different and its transportability result stands on its own footing. State which band each arm landed in before looking at Task 5's tau values.

- [ ] **Step 6: Gitignore the new intermediates and commit**

Add to `.gitignore` under the existing generated-artifact block:
```
output/intermediate/calibration_features_all20_alignment.csv
output/intermediate/session_reference_covariances.npz
```
(These sit under the already-excluded `output/*`, so this is documentation rather than a new exclusion; add the lines as comments in that block instead if the existing pattern already covers them.)

```bash
git add src/bigp3_als/features.py scripts/04b_extract_alignment_features.py docs/pipeline_rerun_2026-09-07_alignment.md
git commit -m "feat: extract session-level Euclidean-Alignment and nonlinear calibration scores

Baseline reproduced to <difference> over <n> sessions before any new column was written.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 4: Extraction pass two, cohort-level alignment

Session-level Euclidean Alignment removes each recording's own scale. The paper's claim is about *cohorts*, so the arm aimed straight at it uses one reference per cohort, which removes what a cohort's amplifiers, caps and montage share while leaving the between-session variation inside a cohort intact. This is the arm the Editor-in-Chief's comment most directly asks for.

**Files:**
- Modify: `src/bigp3_als/features.py` (a `cohort_reference` argument through `_alignment_feature_row` and `build_alignment_features`)
- Modify: `scripts/04b_extract_alignment_features.py`

**Interfaces:**
- Consumes: `output/intermediate/session_reference_covariances.npz` (Task 3); `alignment.pooled_reference` (Task 1).
- Produces: `calibration_auc_ea_cohort` merged into `output/intermediate/calibration_features_all20_alignment.csv`.

- [ ] **Step 1: Add the cohort-reference path**

Give `_alignment_feature_row` and `build_alignment_features` an extra parameter `cohort_references: dict[str, np.ndarray] | None = None`. When it is present, the row computes only:

```python
        if "calibration_auc_ea_cohort" in arms:
            aligned = euclidean_align(epochs, cohort_references[source.study])
            row["calibration_auc_ea_cohort"] = calibration_discriminability(aligned, labels, groups)
```

and skips the session-level and nonlinear arms, so the pass costs one grouped cross-validation per session.

- [ ] **Step 2: Add the script flag**

Add `--cohort-references PATH` and `--merge-into PATH` to `scripts/04b_extract_alignment_features.py`. When `--cohort-references` is given the script:

1. loads the npz, groups the per-session references by the `study` component of each key, and builds one cohort reference per study with `pooled_reference(references, n_epochs)`;
2. runs `build_alignment_features` with `arms=("calibration_auc_ea_cohort",)` and those references;
3. merges the single new column into the file named by `--merge-into` on the three session keys with `validate="one_to_one"`, failing if any key fails to match;
4. skips the baseline reproduction check, because this invocation does not compute the baseline. Print the number of cohorts and the condition number of each cohort reference, so a badly conditioned cohort is visible rather than silent.

- [ ] **Step 3: Smoke-test on the small cache, then run the full pass**

```bash
caffeinate -ims env UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 \
  uv run python scripts/04b_extract_alignment_features.py --cache data/source_cache_full \
  --cohort-references output/intermediate/session_reference_covariances.npz \
  --merge-into output/intermediate/calibration_features_all20_alignment.csv \
  2>&1 | tee tmp/extract_alignment_pass2.log
```
Expected: ~45 minutes, 521 merged rows, no key mismatch.

- [ ] **Step 4: Extend the movement report**

Add the cohort-level arm's row to the table in `docs/pipeline_rerun_2026-09-07_alignment.md`, with the same statistics and interpretation band, plus the 18 cohort-reference condition numbers.

- [ ] **Step 5: Commit**

```bash
git add src/bigp3_als/features.py scripts/04b_extract_alignment_features.py docs/pipeline_rerun_2026-09-07_alignment.md
git commit -m "feat: add cohort-level Euclidean Alignment as the second alignment arm

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 5: Alignment transportability sweep

Puts every alignment arm and the nonlinear arms through the identical leave-one-study-out validation and random-effects summary the paper's headline uses, so the numbers land on the same axis as tau 0.43 and tau 0.87. Also adds the two score-space arms, which need no EDF pass at all.

**Files:**
- Modify: `src/bigp3_als/alignment.py`
- Create: `scripts/17_run_alignment.py`
- Modify: `tests/test_alignment.py`

**Interfaces:**
- Consumes: `output/intermediate/calibration_features_all20_alignment.csv` (Tasks 3 and 4); `validation.ModelSpecification`, `validation.run_source_study_held_out_validation`, `heterogeneity.cohort_calibration`, `heterogeneity.random_effects`, `expanded.random_effects_pooling`.
- Produces:
  - `cohort_standardised(records, feature, method) -> pd.Series`
  - `ALIGNMENT_SPECS: tuple[ModelSpecification, ...]`
  - `output/expanded/alignment_transport.csv`, one row per arm.
  - `output/expanded/alignment_cohort_calibration.csv`, per-arm per-cohort slope and intercept.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_alignment.py`:

```python
import pandas as pd

from bigp3_als.alignment import ALIGNMENT_SPECS, cohort_standardised


def test_cohort_standardisation_uses_session_values_not_repeated_records() -> None:
    # Two sessions per cohort, one of which was run under three conditions and the other under one.
    # Standardising over records would centre on the repeated session; standardising over sessions
    # centres on the midpoint of the two.
    records = pd.DataFrame(
        {
            "study": ["A"] * 4,
            "study_participant_id": ["A:1", "A:1", "A:1", "A:2"],
            "session_id": ["S1", "S1", "S1", "S2"],
            "condition": ["CB", "RC", "CBcol", "CB"],
            "calibration_auc": [0.9, 0.9, 0.9, 0.7],
        }
    )

    standardised = cohort_standardised(records, "calibration_auc", method="z")

    assert standardised.iloc[0] == pytest.approx(1.0)
    assert standardised.iloc[3] == pytest.approx(-1.0)


def test_cohort_standardisation_is_computed_within_each_cohort_separately() -> None:
    records = pd.DataFrame(
        {
            "study": ["A", "A", "B", "B"],
            "study_participant_id": ["A:1", "A:2", "B:1", "B:2"],
            "session_id": ["S1", "S2", "S1", "S2"],
            "condition": ["CB"] * 4,
            "calibration_auc": [0.60, 0.70, 0.85, 0.95],
        }
    )

    standardised = cohort_standardised(records, "calibration_auc", method="z")

    assert standardised.tolist() == pytest.approx([-1.0, 1.0, -1.0, 1.0])


def test_cohort_standardisation_rank_method_is_monotone_and_finite() -> None:
    records = pd.DataFrame(
        {
            "study": ["A"] * 5,
            "study_participant_id": [f"A:{i}" for i in range(5)],
            "session_id": [f"S{i}" for i in range(5)],
            "condition": ["CB"] * 5,
            "calibration_auc": [0.5, 0.6, 0.7, 0.8, 0.9],
        }
    )

    standardised = cohort_standardised(records, "calibration_auc", method="rank")

    assert np.isfinite(standardised).all()
    assert standardised.is_monotonic_increasing


def test_cohort_standardisation_returns_missing_for_a_single_session_cohort() -> None:
    records = pd.DataFrame(
        {
            "study": ["A"],
            "study_participant_id": ["A:1"],
            "session_id": ["S1"],
            "condition": ["CB"],
            "calibration_auc": [0.8],
        }
    )

    assert cohort_standardised(records, "calibration_auc", method="z").isna().all()


def test_every_alignment_specification_names_one_feature_and_a_role() -> None:
    names = [spec.name for spec in ALIGNMENT_SPECS]

    assert len(names) == len(set(names))
    assert all(len(spec.features) == 1 for spec in ALIGNMENT_SPECS)
    assert all(spec.role in {"alignment", "nonlinear"} for spec in ALIGNMENT_SPECS)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest tests/test_alignment.py -v`
Expected: FAIL, `ImportError: cannot import name 'ALIGNMENT_SPECS'`.

- [ ] **Step 3: Write the implementation**

Append to `src/bigp3_als/alignment.py`:

```python
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
                scale = float(values[observed].std(ddof=1))
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
```

Add `from scipy import stats` to the imports. If Task 2's decision rule dropped the gradient-boosting arm, delete its `ModelSpecification` line and say so in the commit message.

- [ ] **Step 4: Write the sweep script**

Create `scripts/17_run_alignment.py`:

```python
"""Put every alignment and nonlinear arm through the primary transportability procedure.

The question these arms answer is not whether they discriminate better. It is whether a mapping
fitted on 17 cohorts holds in the eighteenth, which is the quantity the paper's conclusion rests on,
so each arm is summarised by the same random-effects tau, the same prediction interval and the same
pooled estimation error as the primary score, computed by the same functions.

No participant bootstrap is run, for the reason `11_run_comparators.py` gives: the primary
predictor's intervals are already reported from 2,000 replicates in the main text, and a second,
slightly different interval for the same quantity does not belong in the same paper.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from bigp3_als.alignment import ALIGNMENT_SPECS, cohort_standardised
from bigp3_als.expanded import random_effects_pooling
from bigp3_als.heterogeneity import cohort_calibration, random_effects
from bigp3_als.validation import MODEL_SPECS, ModelSpecification, run_source_study_held_out_validation

KEYS = ["study", "study_participant_id", "session_id"]
POOLED_PREFIX = "Pooled"
METRIC = "session_mean_absolute_error"
PRIMARY = next(spec for spec in MODEL_SPECS if spec.name == "calibration_auc")


def _summarise(records: pd.DataFrame, specification: ModelSpecification) -> tuple[dict, pd.DataFrame]:
    modeled = records.dropna(subset=list(specification.features)).copy()
    predictions, metrics = run_source_study_held_out_validation(
        modeled, specification, bootstrap_repetitions=0
    )
    per_cohort = metrics.loc[~metrics["held_out_study"].astype(str).str.startswith(POOLED_PREFIX)]
    pooled = metrics.loc[metrics["held_out_study"].astype(str).str.startswith(POOLED_PREFIX)].iloc[0]
    calibration = cohort_calibration(predictions, se_method="cluster")
    calibration.insert(0, "arm", specification.name)
    indexed = calibration.set_index("study")
    slope = random_effects(indexed["slope"], indexed["slope_standard_error"])
    intercept = random_effects(indexed["intercept"], indexed["intercept_standard_error"])
    error = random_effects_pooling(per_cohort[METRIC], label=METRIC, transform="log")
    row = {
        "arm": specification.name,
        "role": specification.role,
        "n_cohorts": int(len(per_cohort)),
        "n_records": int(len(modeled)),
        "n_selections": int(modeled["n"].sum()),
        "mae": float(pooled[METRIC]),
        "brier_skill": float(pooled["character_brier_skill_score"]),
        "character_auc": float(pooled["predicted_probability_character_auc"]),
        "mae_prediction_low": float(error["prediction_interval_low"]),
        "mae_prediction_high": float(error["prediction_interval_high"]),
        "slope_pooled": slope["pooled"],
        "slope_tau": slope["tau"],
        "slope_i_squared": slope["i_squared"],
        "slope_prediction_low": slope["prediction_interval_low"],
        "slope_prediction_high": slope["prediction_interval_high"],
        "intercept_pooled": intercept["pooled"],
        "intercept_tau": intercept["tau"],
        "intercept_i_squared": intercept["i_squared"],
        "intercept_prediction_low": intercept["prediction_interval_low"],
        "intercept_prediction_high": intercept["prediction_interval_high"],
        "n_cohorts_dropped_slope": slope["n_dropped"],
        "n_cohorts_dropped_intercept": intercept["n_dropped"],
    }
    return row, calibration


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, default=Path("output/expanded/analysis_records.csv"))
    parser.add_argument("--alignment-features", type=Path,
                        default=Path("output/intermediate/calibration_features_all20_alignment.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    arguments = parser.parse_args()

    records = pd.read_csv(arguments.records)
    extra = pd.read_csv(arguments.alignment_features)
    columns = [column for column in extra.columns
               if column.startswith("calibration_auc_") and column != "calibration_auc_reproduced"]
    records = records.merge(extra[[*KEYS, *columns]], on=KEYS, how="left", validate="many_to_one")
    records["calibration_auc_cohort_z"] = cohort_standardised(records, "calibration_auc", "z")
    records["calibration_auc_cohort_rank"] = cohort_standardised(records, "calibration_auc", "rank")

    specs = [PRIMARY, *[spec for spec in ALIGNMENT_SPECS if spec.features[0] in records.columns]]
    rows, calibrations = [], []
    for specification in specs:
        available = int(records[specification.features[0]].notna().sum())
        print(f"{specification.name}: {available} of {len(records)} records carry the score")
        if available < len(records):
            print(f"  warning: {len(records) - available} records dropped for this arm")
        row, calibration = _summarise(records, specification)
        rows.append(row)
        calibrations.append(calibration)
        print(f"  tau slope {row['slope_tau']:.3f}  tau intercept {row['intercept_tau']:.3f}  "
              f"MAE {row['mae']:.4f}")

    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(arguments.output_directory / "alignment_transport.csv", index=False)
    pd.concat(calibrations, ignore_index=True).to_csv(
        arguments.output_directory / "alignment_cohort_calibration.csv", index=False
    )
    print(f"wrote {len(rows)} arms")


if __name__ == "__main__":
    main()
```

Before writing this file, open `src/bigp3_als/heterogeneity.py:104` and confirm the exact column names `cohort_calibration` returns for the per-cohort slope, intercept and their standard errors. Use the real names; the ones above are the expected ones and must be checked, not assumed.

- [ ] **Step 5: Run the tests, then the sweep**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest tests/test_alignment.py -v
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/17_run_alignment.py
```
Expected: tests pass; the sweep prints one line per arm and writes both CSVs.

**Verification that matters more than the run succeeding:** the `calibration_auc` row of `alignment_transport.csv` must reproduce the published headline. Slope tau 0.432 and intercept tau 0.873, to three decimals. If it does not, the merge or the specification is wrong and no other row in the file can be trusted. Check it explicitly:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -c "
import pandas as pd
row = pd.read_csv('output/expanded/alignment_transport.csv').set_index('arm').loc['calibration_auc']
print(row[['slope_tau','intercept_tau','mae']])
assert abs(row['slope_tau'] - 0.432) < 5e-4, row['slope_tau']
assert abs(row['intercept_tau'] - 0.873) < 5e-4, row['intercept_tau']
print('primary arm reproduces the published headline')"
```

- [ ] **Step 6: Commit**

```bash
git add src/bigp3_als/alignment.py scripts/17_run_alignment.py tests/test_alignment.py output/expanded/alignment_transport.csv output/expanded/alignment_cohort_calibration.csv
git commit -m "feat: run every alignment and nonlinear arm through the transportability procedure

Primary arm reproduces the published slope tau 0.432 and intercept tau 0.873.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 6: Local recalibration learning curve

Answers Referee 1 comment 3, Referee 2 comment 4, and the Conclusion's own unquantified recommendation. The paper tells a reader to recalibrate locally and does not say what that costs. This measures it: how many local participants, and how many character selections, before a locally recalibrated mapping beats the transported one in the same cohort.

Runs entirely off `output/expanded/external_validation_predictions.csv`, which is already on disk and tracked in git. Minutes, not hours.

**Files:**
- Create: `src/bigp3_als/recalibration.py`
- Create: `scripts/18_run_recalibration.py`
- Test: `tests/test_recalibration.py`

**Interfaces:**
- Consumes: `validation._expanded_binary`, `validation.RANDOM_SEED`, `validation._FITTED_BOUNDARY`.
- Produces:
  - `recalibration_draws(predictions, sizes, draws, seed) -> pd.DataFrame` with one row per (cohort, local size, draw, method) and columns `held_out_study, n_local_participants, n_local_selections, draw, method, mean_absolute_error, transported_mean_absolute_error, identified`.
  - `recalibration_summary(draws) -> pd.DataFrame` with one row per (local size, method).
  - `output/expanded/recalibration_draws.csv`, `output/expanded/recalibration_summary.csv`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_recalibration.py`:

```python
"""Tests for the local-recalibration learning curve."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bigp3_als.recalibration import (
    LOCAL_SIZES,
    MINIMUM_EVALUATION_PARTICIPANTS,
    recalibration_draws,
    recalibration_summary,
)


def _cohort(n_participants: int, offset: float, seed: int) -> pd.DataFrame:
    """One cohort whose transported probabilities are shifted by a constant on the log-odds scale."""
    rng = np.random.default_rng(seed)
    truth = rng.uniform(0.35, 0.9, size=n_participants)
    transported = 1.0 / (1.0 + np.exp(-(np.log(truth / (1 - truth)) - offset)))
    return pd.DataFrame(
        {
            "held_out_study": "StudyX",
            "study_participant_id": [f"StudyX:{i:02d}" for i in range(n_participants)],
            "session_id": "S1",
            "condition": "CB",
            "n": 40,
            "correct": rng.binomial(40, truth),
            "predicted_probability": transported,
        }
    )


def test_intercept_only_recalibration_removes_a_pure_offset() -> None:
    predictions = _cohort(16, offset=1.2, seed=3)

    draws = recalibration_draws(predictions, sizes=(6,), draws=40, seed=11)
    summary = recalibration_summary(draws)
    row = summary.set_index(["method", "n_local_participants"]).loc[("intercept_only", 6)]

    assert row["mean_improvement"] > 0.05
    assert row["win_fraction"] > 0.9


def test_recalibration_is_evaluated_only_on_participants_outside_the_local_draw() -> None:
    predictions = _cohort(12, offset=0.8, seed=4)

    draws = recalibration_draws(predictions, sizes=(4,), draws=5, seed=12)

    # 12 participants, 4 drawn locally, so every row must have been scored on the other 8.
    assert (draws["n_evaluation_participants"] == 8).all()


def test_a_cohort_too_small_for_a_size_contributes_no_rows_at_that_size() -> None:
    predictions = _cohort(5, offset=0.5, seed=5)

    draws = recalibration_draws(predictions, sizes=(1, 3, 4), draws=5, seed=13)

    # 5 participants and a floor of 3 evaluation participants leaves sizes 1 and 2 only.
    assert sorted(draws["n_local_participants"].unique()) == [1]


def test_slope_recalibration_is_not_attempted_on_a_single_local_participant() -> None:
    predictions = _cohort(10, offset=0.6, seed=6)

    draws = recalibration_draws(predictions, sizes=(1,), draws=5, seed=14)

    assert set(draws["method"]) == {"intercept_only"}


def test_a_non_identified_draw_is_flagged_rather_than_scored() -> None:
    # Every local participant at 100% accuracy separates the fit perfectly.
    predictions = _cohort(12, offset=0.0, seed=7)
    predictions.loc[predictions.index[:4], "correct"] = predictions.loc[predictions.index[:4], "n"]

    draws = recalibration_draws(predictions, sizes=(4,), draws=30, seed=15)

    assert draws["identified"].dtype == bool
    assert draws.loc[~draws["identified"], "mean_absolute_error"].isna().all()


def test_summary_reports_the_paired_difference_not_two_independent_means() -> None:
    predictions = _cohort(14, offset=1.0, seed=8)

    draws = recalibration_draws(predictions, sizes=(5,), draws=30, seed=16)
    summary = recalibration_summary(draws)
    row = summary.set_index(["method", "n_local_participants"]).loc[("intercept_only", 5)]

    identified = draws.loc[draws["identified"] & (draws["method"] == "intercept_only")]
    paired = identified["transported_mean_absolute_error"] - identified["mean_absolute_error"]
    assert row["mean_improvement"] == pytest.approx(float(paired.mean()))


def test_local_sizes_are_ascending_and_start_at_one() -> None:
    assert LOCAL_SIZES[0] == 1
    assert list(LOCAL_SIZES) == sorted(LOCAL_SIZES)
    assert MINIMUM_EVALUATION_PARTICIPANTS >= 3
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest tests/test_recalibration.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'bigp3_als.recalibration'`.

- [ ] **Step 3: Write the implementation**

Create `src/bigp3_als/recalibration.py`:

```python
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
```

Note on the percentile interval: it describes the spread of the paired improvement across draws and cohorts, which is a description of variability, not a confidence interval for a mean. Label it that way everywhere it appears, including the manuscript.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest tests/test_recalibration.py -v`
Expected: 7 passed.

- [ ] **Step 5: Write and run the script**

Create `scripts/18_run_recalibration.py`:

```python
"""Quantify what local recalibration costs, in participants and in character selections."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from bigp3_als.recalibration import recalibration_draws, recalibration_summary

PRIMARY_MODEL = "calibration_auc"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path,
                        default=Path("output/expanded/external_validation_predictions.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    parser.add_argument("--draws", type=int, default=200)
    arguments = parser.parse_args()

    predictions = pd.read_csv(arguments.predictions)
    predictions = predictions.loc[predictions["model"] == PRIMARY_MODEL].copy()
    if predictions.empty:
        raise SystemExit(f"no rows for model {PRIMARY_MODEL}")

    draws = recalibration_draws(predictions, draws=arguments.draws)
    summary = recalibration_summary(draws)

    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    draws.to_csv(arguments.output_directory / "recalibration_draws.csv", index=False)
    summary.to_csv(arguments.output_directory / "recalibration_summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
```

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/18_run_recalibration.py`

**Read the output before moving on and write down the answer the manuscript will report:** the smallest `n_local_participants` at which `mean_improvement` is positive with `improvement_low` above zero, separately for `intercept_only` and `intercept_and_slope`, together with `median_local_selections` at that size. That pair of numbers is what Referee 1 comment 3 and Referee 2 comment 4 asked for.

- [ ] **Step 6: Commit**

```bash
git add src/bigp3_als/recalibration.py scripts/18_run_recalibration.py tests/test_recalibration.py output/expanded/recalibration_draws.csv output/expanded/recalibration_summary.csv
git commit -m "feat: quantify the local-recalibration learning curve in participants and selections

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 7: Two new figures

**Files:**
- Modify: `src/bigp3_als/render_expanded.py`
- Modify: `scripts/13_render_figures.py`
- Modify: `tests/test_render_expanded.py`

**Interfaces:**
- Consumes: `output/expanded/recalibration_summary.csv` (Task 6); `output/expanded/alignment_transport.csv` (Task 5).
- Produces: `render_recalibration_curve(summary, directory)` writing `figure_recalibration_curve.{png,pdf}`; `render_alignment_transport(transport, directory)` writing `figure_alignment_transport.{png,pdf}`.

- [ ] **Step 1: Read the existing conventions before writing anything**

Open `src/bigp3_als/render_expanded.py:36-60` and reuse, exactly: `LABEL_COLOR`, `_save`, `require_columns` from `bigp3_als.render`, and `ALS_COLOR = "#B24745"`, `OTHER_COLOR = "#374E55"`, `BAND_COLOR = "#79AF97"`, `ALS_MARKER = "D"`, `OTHER_MARKER = "o"`. Match the module docstring style: each renderer gets a paragraph in the module docstring saying what argument the display carries, not what it plots.

Also reuse the marker-shape rule: every colour distinction must be carried by a second, colour-independent channel, so the figures survive grayscale reproduction.

- [ ] **Step 2: Write `render_recalibration_curve`**

One panel. X axis: local participants (the `LOCAL_SIZES` ladder, log-spaced or categorical). Y axis: mean absolute error. Draw:
- a horizontal reference line at the transported mapping's mean absolute error, labelled with its value;
- one line with markers per refit method (`intercept_only`, `intercept_and_slope`), each with a shaded band from `improvement_low` to `improvement_high` translated back onto the error scale;
- a second X axis on top, or an annotation at each tick, giving `median_local_selections`, because the operational question is asked in both units;
- a vertical annotation at the crossing point, the smallest size where the band clears the reference line.

Caption content, to be written in the manuscript, not the figure: the band is the 2.5th to 97.5th percentile of the paired improvement across draws and cohorts, a description of variability rather than a confidence interval.

- [ ] **Step 3: Write `render_alignment_transport`**

Two panels sharing a Y axis of arm names, ordered primary first then alignment then nonlinear. Left panel: intercept tau per arm with the primary arm's value drawn as a dashed vertical reference. Right panel: slope tau, same treatment. Annotate each row with the arm's pooled mean absolute error, so a reader sees at once that an arm which lowers tau while raising error has not helped.

Do not plot I-squared anywhere. The manuscript may not lean on it and a figure that shows it invites a reader to.

- [ ] **Step 4: Add regression tests**

Append to `tests/test_render_expanded.py`, following the existing pattern in that file: build a small frame, call each renderer into `tmp_path`, and assert both the `.png` and `.pdf` exist and are non-empty. Add one test per renderer asserting that a frame missing a required column raises through `require_columns` rather than producing a broken figure.

- [ ] **Step 5: Wire into the figure script and run**

Add both renderers to `scripts/13_render_figures.py`'s imports and `main()`, reading the two new CSVs beside the existing inputs.

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest tests/test_render_expanded.py -v
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/13_render_figures.py
```
Expected: tests pass; eight figure stems now exist under `output/expanded/figures/`.

- [ ] **Step 6: Look at the rendered PNGs**

Open both new PNGs. Check the axis labels are not clipped, the legend does not cover data, and the annotated numbers agree with the CSVs they came from. A figure that disagrees with its table is the specific failure this repo's figure script was written to prevent.

- [ ] **Step 7: Commit**

```bash
git add src/bigp3_als/render_expanded.py scripts/13_render_figures.py tests/test_render_expanded.py output/expanded/figures/
git commit -m "feat: add the recalibration-curve and alignment-transport figures

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 8: Methods and Results text for the three new analyses

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (Methods after `### Validation Design`; Results after `### Transportability`)

**Interfaces:**
- Consumes: every number in `alignment_transport.csv`, `recalibration_summary.csv`, and `docs/pipeline_rerun_2026-09-07_alignment.md`.
- Produces: three new Methods paragraphs and three new Results subsections that Tasks 9 through 13 cross-reference by name.

- [ ] **Step 1: Build the number inventory first**

Before writing a word, extract every number the new text will cite into `tmp/new_numbers.md`, straight from the CSVs. For each: the value, the file it came from, and the column. Every statistic in the new prose must appear in that inventory, and Task 16 checks the prose against it. This is the discipline that caught two dropped citations in the July length-trim pass.

- [ ] **Step 2: Write the Methods additions**

Three paragraphs, placed after `### Validation Design` and before `### Statistical Analysis`, under a new heading `### Alignment, Nonlinear Boundaries, and Local Recalibration`:

1. **Alignment.** Define Euclidean Alignment in one sentence with its reference [He and Wu 2020], state the two reference choices (session and cohort) and what each removes, then state the two score-space variants and, explicitly, that they require the target cohort's unlabeled calibration recordings but never its online accuracy. Say that every arm goes through the identical held-out procedure and the identical random-effects summary, so the reported tau is comparable to the primary one.
2. **Nonlinear boundary.** State the arm, the kernel approximation and why an exact kernel machine was not affordable at this epoch count, and that the training-fold-only fitting keeps the grouped split intact. If Task 2's decision rule dropped the gradient-boosting arm, say so here in one clause with the measured reason, rather than leaving it unmentioned.
3. **Local recalibration.** State the resampling design in full: participants drawn without replacement inside each withheld cohort, at least three participants retained for evaluation, both refits, the separation guard, the paired comparison on identical evaluation participants, 200 draws, and that the reported interval is a percentile range across draws and cohorts and not a confidence interval.

- [ ] **Step 3: Write the Results additions**

Three subsections after `### Transportability`:

- `#### Alignment Did Not Restore Transportability` (retitle if the result is otherwise; the heading must state what happened, and the plan does not know the answer in advance). Report, for each arm: pooled mean absolute error, slope tau, intercept tau, and the prediction interval for the intercept. Lead with the intercept, per the standing constraint. Reference Figure `alignment_transport` and the new supplement table.
- `#### A Nonlinear Decision Boundary` with the same quantities, plus one sentence on how the nonlinear score's discriminability compared to the linear one, from the movement report, so a reader can see whether the arm changed the score at all before asking whether it changed the mapping.
- `#### What Local Recalibration Costs` with the headline pair: the smallest number of local participants, and the corresponding median number of character selections, at which each refit's improvement over the transported mapping is positive with its percentile range clear of zero. Report the identified fraction at each size, because a guard that discarded draws is part of the answer.

Write the alignment result honestly whichever way it falls. If an arm does reduce tau materially, that is a finding and the paper's framing in Tasks 9 and 12 changes with it. If none does, say that the mapping's cohort-specificity survives the standard alignment remedy, which is a stronger version of the paper's existing claim and is exactly what the Editor-in-Chief asked to be tested.

- [ ] **Step 4: Verify every cited number against the inventory**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python - <<'PY'
import re, pathlib
text = pathlib.Path("manuscript/manuscript_expanded.md").read_text()
inventory = pathlib.Path("tmp/new_numbers.md").read_text()
start = text.index("### Alignment, Nonlinear Boundaries, and Local Recalibration")
new = text[start:]
missing = [n for n in set(re.findall(r"\d+\.\d+", new)) if n not in inventory]
print("numbers in the new prose absent from the inventory:", sorted(missing))
PY
```
Every value printed must be either a number defined in the prose itself (a threshold, a count of draws) or a genuine transcription error. Fix the errors.

- [ ] **Step 5: Rebuild and check length**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python "/Volumes/Extreme SSD/Mimic-IV/_pub_assets/wordcount.py" manuscript/manuscript_expanded.md
```
Record the new body word count. It will exceed 6,601; Task 11 brings it back.

- [ ] **Step 6: Commit**

```bash
git add manuscript/manuscript_expanded.md
git commit -m "docs: add Methods and Results for the alignment, nonlinear and recalibration analyses

Addresses R1.3, R2.2, R2.3, R2.4 and the Editor's re-alignment request.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 9: Framing and limitations fixes

Four text-only referee comments that do not depend on the new analyses. Grouped because they touch the same three sections and a reviewer would judge them as one editorial pass.

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (Abstract Significance, Discussion opening, `### Study Limitations`)

- [ ] **Step 1: Referee 1 comment 2, the reconstructed decoder, surfaced to the framing**

The caveat currently lives in Methods `### What the Calibration Score Is, and What It Is Not` and as the two-word second limitation. Add one clause to the Abstract's **Significance** paragraph naming it, and one sentence to the **first paragraph of the Discussion**, so a reader meets it before the implications.

Suggested Abstract clause, to be fitted to the existing sentence rhythm: the score is the cross-validated discriminability of a classifier fitted here on each session's calibration data, not the decoder the source studies used online, which the archive does not document.

Keep the Abstract at or under **300 words** (it is currently 283). Verify with `wc -w` on the extracted prose, not a regex: a naive recount in a previous pass reported 306 instead of 289 because of a decimal-point tokenization bug.

- [ ] **Step 2: Referee 1 comment 1, the direction of the archive-homogenization bias**

The manuscript says "not external validation in the strict sense" and stops. Add a paragraph to the **Discussion**, not only Methods, that reasons about the direction:

BigP3BCI imposes a shared 16-channel montage, a common sampling rate and a single amplifier model across every source study. Every one of those is a source of between-cohort variation that a reader's own deployment would have and this archive does not. The heterogeneity reported here is therefore a **lower bound** on what a site meeting a genuinely independent cohort should expect, and the transportability failure is if anything understated. State that this reasoning cuts one way only and is not symmetric: no plausible mechanism by which curation would inflate the observed tau was identified.

Then note the one qualification honestly: cohort-level Euclidean Alignment (Task 4) is the arm that removes what a cohort's recording chain shares, and its result bears on how much of the residual spread a montage difference could plausibly add. Cross-reference the new Results subsection.

- [ ] **Step 3: Referee 1 comment 5, ALS clinical characterization**

The seventh limitation currently says the archive identifies an ALS population for four cohorts only, with no participant-level clinical characteristics. Extend it explicitly: ALSFRS-R is recorded for three of the eighteen cohorts, and **no cohort carries disease duration, time since diagnosis, bulbar versus limb onset, or respiratory status**. The ALS framing in the title and the subgroup analysis therefore identify a population, not a disease stage, and no claim here is conditional on severity. Say plainly that a mapping could be stage-dependent in a way this archive cannot show.

- [ ] **Step 4: Referee 1 minor comment, researcher degrees of freedom**

Add a short paragraph to the **Discussion**, near the existing non-registration disclosure, not to the Limitations list (the reviewer asked for an acknowledgment of cumulative risk, which is a framing point, not a study defect). It must say:

- no analysis plan was registered, which is already stated in Methods;
- the configurations reported here (two stimulus paradigms, seven comparator predictors, an ALSFRS-R add-on, and now the alignment and nonlinear arms) were each fixed before being run, and the moderator tests are Holm-corrected across the ten descriptors;
- **formal correction bounds the family it is applied to and nothing else.** The number of specifications a study could have run, and the order in which analyses followed one another across revision rounds, are not captured by any correction, and the exploratory results here should be read as hypothesis-generating for that reason;
- the primary result does not rest on a selected configuration: it is one prespecified comparison reported in every sensitivity specification.

- [ ] **Step 5: Rebuild, de-AI scan, word count**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py
grep -n "—" manuscript/manuscript_expanded.md   # must return nothing
```
Then run the `de-ai-writing` skill's scan over the new paragraphs only.

- [ ] **Step 6: Commit**

```bash
git add manuscript/manuscript_expanded.md
git commit -m "docs: surface the reconstructed-decoder caveat and reason about the homogenization bias

Addresses R1.1, R1.2, R1.5 and R1's minor researcher-degrees-of-freedom point.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 10: Introduction, recent literature and the historical question

Referee 2 comment 1 has two halves and the second is the interesting one: did earlier researchers explicitly flag why they did not cross cohorts?

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (`## Introduction`, `## References`)
- Modify: `refs_AMA.txt`, `refs_for_zotero.bib`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: new reference numbers appended after the current 39, and the renumbering, if any, that follows.

- [ ] **Step 1: Search for the recent literature**

Search for work published 2021 or later on: calibration-based or pre-session prediction of P300-speller or ERP-BCI performance; cross-dataset and cross-subject transfer in P300 spellers; transfer learning and alignment for ERP BCIs. Aim for four to six genuinely recent citations that bear on prediction of performance, not on classification accuracy alone.

Then, separately, read the discussion and limitations sections of references [15], [37] and [38] and of any recent transfer-learning paper found, looking for an explicit statement about why the evaluation stayed within one dataset. Report what is actually there. Three outcomes are all publishable and only one of them is a guess:
- an author states the mapping was not expected to generalise: quote and cite it, this is the strongest version of the paper's motivation;
- an author states only that no other dataset was available: cite it as the convenience explanation, which is also informative;
- nothing is stated either way: say so plainly in one sentence, that the literature does not record a reason, rather than inventing one.

**Do not write a motivation the sources do not support.** Referee 2 asked a factual question and a fabricated answer is the worst possible response to it.

- [ ] **Step 2: Verify every new reference**

REQUIRED SUB-SKILL: use the `ama-citation-zotero` skill. Verify each new DOI against Crossref (or DataCite for dataset DOIs), format in AMA, append to `refs_AMA.txt` and `refs_for_zotero.bib`, and push to Zotero. Zero fabricated DOIs. If `zotero-mcp` exposes only read tools this session, use the documented fallback `open -a Zotero references.bib`.

- [ ] **Step 3: Write the Introduction changes**

Two edits to the existing Introduction, both small:

- In the second paragraph, after the sentence citing [15], [37] and [38], add one sentence citing the recent work, so the reader sees the question is live rather than historical.
- In the third paragraph, which currently opens "Two features of that literature limit what it can support," add the historical finding from Step 1 as one sentence at the end of the first numbered limitation. This is the sentence Referee 2 asked for and it belongs exactly where the limitation is stated.

Do not lengthen the Introduction by more than about 60 words; Task 11 has to absorb it.

- [ ] **Step 4: Check the citation numbering did not break**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python - <<'PY'
import re, pathlib, subprocess
def brackets(text):
    out = set()
    for group in re.findall(r"\[([\d,\-\s]+)\]", text):
        for part in group.split(","):
            part = part.strip()
            if "-" in part:
                low, high = part.split("-")
                out.update(range(int(low), int(high) + 1))
            elif part:
                out.add(int(part))
    return out
current = pathlib.Path("manuscript/manuscript_expanded.md").read_text()
before = subprocess.run(["git", "show", "8a56d0c:manuscript/manuscript_expanded.md"],
                        capture_output=True, text=True, check=True).stdout
body, _, refs = current.partition("\n## References\n")
cited = brackets(body)
listed = {int(m.group(1)) for m in re.finditer(r"^(\d+)\.\s", refs, re.M)}
print("cited but not listed:", sorted(cited - listed))
print("listed but not cited:", sorted(listed - cited))
print("dropped since 8a56d0c:", sorted(brackets(before.partition("\n## References\n")[0]) - cited))
PY
```
All three lists must be empty. The third check is the one that caught references [34] and [35] silently vanishing during the July trim.

- [ ] **Step 5: Commit**

```bash
git add manuscript/manuscript_expanded.md refs_AMA.txt refs_for_zotero.bib
git commit -m "docs: add recent calibration-prediction literature and the cross-cohort historical context

Addresses R2.1. Every new DOI verified against Crossref.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 11: Length trim to offset the new content

Referee 1 comment 4, and the author's decision D3: net body words must end at or below **6,601** despite everything Tasks 8 through 10 added.

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (`## Discussion`)
- Modify: `supplementary/supplement_expanded.md`

- [ ] **Step 1: Move the estimator-agreement comparison to the supplement**

This is the move Referee 1 named specifically, and its tables are already in the supplement (S4). Two passages go:

- the Discussion paragraph beginning "The 18 folds are also not independent, since any two share up to 16 of 17 development cohorts", which runs through the joint bootstrap's within-replicate spread and the explanation that it estimates something structurally larger than tau. Move the whole passage into supplement section S4 and leave in the Discussion one sentence: that the folds are not independent, that a joint bootstrap measures the resulting correlation directly, and that it estimates a quantity structurally larger than tau, with a cross-reference to S4;
- the Methods `### Statistical Analysis` sentences comparing cluster-robust pooling on the bootstrap's 17 identified cohorts against the all-18 values. Move to S4; leave a cross-reference.

Do not delete a single number. Every value in the moved text must appear in S4 afterwards. Verify by grepping each one.

- [ ] **Step 2: Cut Discussion passages that restate Results**

Referee 1's exact complaint is that the Discussion "recapitulates the Results using similar statistical framing." Work through the Discussion paragraph by paragraph and, for each statistic it repeats, check whether the Results already state it. Where they do, cut the restatement and keep the interpretation. The technique that worked in the July pass: consolidate a fact to one canonical location and leave brief cross-references, rather than deleting content.

Candidates, all of which repeat Results verbatim or nearly:
- the first paragraph's re-listing of tau 0.87, its confidence interval, tau 0.43 and the slope range;
- the fold-stability paragraph's coefficients of variation, which Table S12 already carries;
- the predictor-precision paragraph's reliability range, which the Results already give.

- [ ] **Step 3: Verify the trim did not drop anything**

Run the citation-bracket diff from Task 10 Step 4 again, and the same diff for table and figure references:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python - <<'PY'
import re, pathlib, subprocess
pattern = re.compile(r"\b(?:Table|Figure)\s+S?\d+\b")
current = set(pattern.findall(pathlib.Path("manuscript/manuscript_expanded.md").read_text()))
before = set(pattern.findall(subprocess.run(
    ["git", "show", "8a56d0c:manuscript/manuscript_expanded.md"],
    capture_output=True, text=True, check=True).stdout))
print("cross-references dropped since 8a56d0c:", sorted(before - current))
PY
```
Anything printed must be a deliberate move to the supplement, and you must be able to name which S-section now carries it.

- [ ] **Step 4: Check the word count target is met**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python "/Volumes/Extreme SSD/Mimic-IV/_pub_assets/wordcount.py" manuscript/manuscript_expanded.md
```
Expected: at or below 6,601 body words. If it is above, keep cutting Discussion restatement; do not cut Methods or Results, which the reviewers asked to be expanded.

- [ ] **Step 5: Rebuild and spot-check the rendered pages**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py
```
Open the rendered PDF at the title page, one Methods page, one Results page including a table, and one Discussion page. Look for broken cross-references, a caption separated from its figure by a page break, and garbled text.

- [ ] **Step 6: Commit**

```bash
git add manuscript/manuscript_expanded.md supplementary/supplement_expanded.md
git commit -m "edit: move estimator-agreement to the supplement and cut Discussion restatement

Addresses R1.4. Body words <before> to <after>, at or below the pre-revision 6,601.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 12: Title

Referee 2 comment 5, and author decision D2: three candidates, drafted now that the results are known, for the author to pick from.

**Files:**
- Create: `tmp/title_candidates.md`
- Modify: `manuscript/manuscript_expanded.md:1` (after the author picks)

- [ ] **Step 1: Draft three candidates**

Each must be defensible against the actual results, including whatever the alignment arms returned. Give, for each: the title, its word count, and one line on what it claims and what it gives up. Cover a range:

- one that leads with the failure and keeps the association as a subordinate clause;
- one that leads with the operational consequence, the recalibration cost measured in Task 6;
- one that keeps the current two-clause structure but shortens it.

If any alignment arm materially reduced tau, at least one candidate must reflect that, and the current title becomes indefensible rather than merely long.

- [ ] **Step 2: Present them to the author and wait**

Use `AskUserQuestion` with the three candidates as options, each with the count and trade-off line as its description. Do not pick one unilaterally.

- [ ] **Step 3: Apply the chosen title everywhere it appears**

```bash
grep -rn "Calibration-derived decoder discriminability is associated" \
  manuscript/ supplementary/ submission/ docs/ 2>/dev/null
```
Update the manuscript heading, the cover letter, the response document, the supplement header and the packet README. Missing one leaves the submission internally inconsistent.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs: adopt the revised title

Addresses R2.5.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 13: Supplement and reporting checklist

**Files:**
- Modify: `supplementary/supplement_expanded.md`
- Modify: `supplementary/tripod_checklist.md`

- [ ] **Step 1: Add the new supplementary tables**

Continue the existing ascending numbering; the supplement currently ends at Table S12, so the new ones are S13 onward. Assign numbers by physical position in the document, as the third pre-submission review established, and place each table where a reader following the argument would want it, not at the end.

- **Table S13, alignment and nonlinear arms.** One row per arm: pooled mean absolute error with its prediction interval, Brier skill, character AUC, slope tau, intercept tau, both prediction intervals, and the number of records the arm could be computed on. Straight from `alignment_transport.csv`.
- **Table S14, per-cohort calibration under each alignment arm.** From `alignment_cohort_calibration.csv`. Landscape block if it needs one; reuse the scoped `\footnotesize` plus `\setlength{\tabcolsep}{3pt}` inside `\begin{landscape}` that fixed the Table S9 spillover, and check the rendered PDF for a near-empty continuation page.
- **Table S15, the recalibration learning curve.** From `recalibration_summary.csv`: method, local participants, median local selections, identified fraction, transported error, recalibrated error, mean improvement, percentile range, win fraction.
- **Section S4 additions:** the estimator-agreement text moved in from Task 11.

Every table needs a title and a description; the JNE checklist requires it of the supplementary file.

- [ ] **Step 2: Update the TRIPOD checklist**

The new analyses touch several items. Re-read the actual published instrument rather than the current file's wording, as the first pre-submission pass had to: items 5 (sources of data), 10 (statistical analysis methods, which now includes the alignment arms, the nonlinear arm and the recalibration resampling), 13 (participants), and 17 (limitations, which now carries the ALS characterization and researcher-degrees-of-freedom additions).

- [ ] **Step 3: Update the test-count and analysis-inventory statements**

The supplement states the test count and lists the frozen outputs by filename. Both changed. Get the real numbers:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest -q 2>&1 | tail -3
ls output/expanded/*.csv output/expanded/*.json | wc -l
```
Update the supplement to match. A stale count here was an Important finding in the second pre-submission review.

- [ ] **Step 4: Rebuild and check the page count**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py
```
Open the supplement PDF. Check no table spills a single row onto an otherwise-blank continuation page.

- [ ] **Step 5: Commit**

```bash
git add supplementary/
git commit -m "docs: add supplementary tables S13 to S15 and update the TRIPOD checklist

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 14: Response to Reviewers

The required Author Response file. JNE's checklist requires a point-by-point response to **every** reviewer comment **and the Editor report**.

**Files:**
- Create: `manuscript/response_to_reviewers_jne_r1.md`
- Modify: `manuscript/cover_letter_expanded.md`

- [ ] **Step 1: Invoke the skill**

REQUIRED SUB-SKILL: `response-to-reviewers`. Follow it rather than this plan's formatting instincts.

- [ ] **Step 2: Cover all thirteen items**

Referee 1: A1 through A5 plus minor B1. Referee 2: C1 through C5. Editor in Chief: the re-alignment request and the detailed-response request. Thirteen numbered responses, each quoting the comment verbatim, then what changed, then where in the revised manuscript it changed, by section name and, where useful, the new sentence quoted.

- [ ] **Step 3: Embed the two new result tables in the response**

Reviewers should not have to open the supplement to see whether the analyses they asked for were done. Embed, inline in the response: the alignment-arm summary (Table S13's key columns) under the response to C3 and the Editor, and the recalibration curve (Table S15) under the response to A3 and C4.

- [ ] **Step 4: Handle the one place a reviewer may be pushed back on**

If Task 12's chosen title keeps the current structure, the response to C5 must say so and give the reason, courteously and in two sentences. Do not silently ignore a comment; an unaddressed comment is what triggers a second major revision.

- [ ] **Step 5: Rewrite the cover letter for the revision**

Short, single-spaced, one page. It is correspondence, not manuscript body: build at `linestretch=1`. This was the actual root cause of the previous cover letter running to three pages, and word cuts alone did not fix it. State the manuscript ID, that this is a revision, and in three or four sentences what substantively changed: the alignment analyses the Editor asked for, the nonlinear arm, the recalibration quantification, and the length reduction.

Per the standing instruction on this study, the cover letter carries **no companion-manuscript disclosure**. That instruction governs this study's own letter and has been reconfirmed twice.

- [ ] **Step 6: De-AI scan and verify every claim**

Run the `de-ai-writing` skill over both documents. Then verify every claim the response makes about the manuscript against the manuscript itself, by grepping for the exact numbers and phrases. Two of five wording complaints in an earlier review round traced to real, checkable manuscript facts; a response document that misdescribes its own manuscript is worse than one that says less.

- [ ] **Step 7: Commit**

```bash
git add manuscript/response_to_reviewers_jne_r1.md manuscript/cover_letter_expanded.md
git commit -m "docs: write the point-by-point response and the revision cover letter

Thirteen numbered responses covering both referees and the Editor report.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 15: Highlighted manuscript and the packet build

**Files:**
- Create: `manuscript/manuscript_highlighted.md`
- Create: `scripts/19_build_jne_revision_packet.py`
- Create: `_submission_ready/study_bigp3_als_calibration/REVISION_R1_JNE-111284/` and its contents

- [ ] **Step 1: Create the highlighted source**

Copy `manuscript_expanded.md` to `manuscript_highlighted.md` and wrap every passage changed since `8a56d0c` in a pandoc bracketed span, `[changed text]{.mark}`, which the house pipeline renders as yellow highlight. Find the changes with:

```bash
git diff 8a56d0c -- manuscript/manuscript_expanded.md > tmp/manuscript_changes.diff
```

Highlight at the sentence or paragraph level, not the word level; a reviewer wants to see what changed, not a mosaic.

- [ ] **Step 2: Write the packet build script**

Create `scripts/19_build_jne_revision_packet.py`, modelled on `study_delirium_unscreenable/code/build_ccm_packet.py`. Jobs:

| Markdown stem | Highlighted | Packet filename |
| --- | --- | --- |
| `manuscript_expanded` | no | `3_Manuscript_CLEAN.docx` |
| `manuscript_highlighted` | yes | `4_Manuscript_HIGHLIGHTED.docx` |
| `supplement_expanded` | no | `5_Supplement.docx` |
| `tripod_checklist` | no | `6_TRIPOD_Checklist.docx` |
| `cover_letter_expanded` | no | `1_Cover_Letter.docx` |
| `response_to_reviewers_jne_r1` | no | `2_Response_to_Reviewers.docx` |

Single-space the cover letter and the response; they are correspondence. Build through the house CMU-Serif pipeline, and carry forward the two study-specific workarounds this repo needs and the shared `_pub_assets/build_pub.sh` does not provide: the pandoc format string extended to `gfm+superscript+raw_attribute+attributes`, and the scoped `\usepackage{setspace}` plus `\AtBeginEnvironment{longtable}{\singlespacing}` plus `\usepackage{pdflscape}` layered on `_pub_assets/header.tex`. Do not commit either workaround into the shared pipeline.

End the script with the same assertion the delirium build ends with, because it is the check that catches a broken highlight pass:

```python
    clean_words = body_words(f"{PKT}/3_Manuscript_CLEAN.docx")
    highlighted_words = body_words(f"{PKT}/4_Manuscript_HIGHLIGHTED.docx")
    highlighted_runs = sum(
        1
        for paragraph in docx.Document(f"{PKT}/4_Manuscript_HIGHLIGHTED.docx").paragraphs
        for run in paragraph.runs
        if run.font.highlight_color is not None and run.text.strip()
    )
    assert clean_words == highlighted_words, (clean_words, highlighted_words)
    assert highlighted_runs > 0
    print(f"CLEAN words={clean_words}  HIGHLIGHTED words={highlighted_words}  runs={highlighted_runs}")
```

- [ ] **Step 3: Build the packet and the PDFs**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/19_build_jne_revision_packet.py
```

The JNE checklist requires the **Highlighted PDF** and the **Clean PDF** as PDFs, not docx. Produce both, then run every PDF and every figure through the portal font fix, without which IOP's portal rejects the upload:

```bash
"/Volumes/Extreme SSD/Mimic-IV/_pub_assets/make_portal_pdf.sh" \
  _submission_ready/study_bigp3_als_calibration/REVISION_R1_JNE-111284/*.pdf \
  _submission_ready/study_bigp3_als_calibration/REVISION_R1_JNE-111284/Figures/*
```

- [ ] **Step 4: Walk the JNE checklist item by item**

Open `/Volumes/Extreme SSD/Mimic-IV/reproting checklist.pdf` and check every box against the built files. In particular:

- `3_Manuscript_CLEAN.docx` must contain the full author list with affiliations, the corresponding author clearly marked **with their email address**, funding and acknowledgements, and the ethical statement. Confirm the corresponding author matches the submission form.
- No colour or grey-scale shading and no coloured text anywhere in the tables of the clean file. Check the built docx, not the markdown.
- Tables, figure captions and equations editable, not images.
- `4_Manuscript_HIGHLIGHTED` is a PDF, includes figures and tables, and its file designation on upload is "Complete Document for Review (PDF Only)".
- The supplementary file has a title and description.
- Anonymisation does not apply: this manuscript was not submitted for double-anonymous review. **Confirm this in the Author Centre before uploading** rather than trusting the plan.

- [ ] **Step 5: Write the packet README**

`README.md` in the packet directory, following the convention of the existing `_submission_ready/study_command_following/REVISION_R1_NECA-D-26-00849/README.md`: what each file is, which JNE upload step and file designation it goes to, the word counts, the commit it was built from, and a **Human-only items** list. That list must carry, at minimum: the Zenodo or OSF DOI still to be minted and substituted for the repository citation, the GitHub push, confirmation of the anonymisation question, and confirmation of current JNE author instructions.

- [ ] **Step 6: Commit**

```bash
git add manuscript/manuscript_highlighted.md scripts/19_build_jne_revision_packet.py
git commit -m "build: assemble the JNE-111284 revised-submission packet

Six numbered files plus figures, built to the JNE revised submission checklist.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 16: Final verification

Nothing here is optional. Two of this repository's previous revision rounds shipped a defect that one of these checks would have caught.

**Files:** none modified unless a check fails.

- [ ] **Step 1: Full test suite, including the slow guard**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -c "import sys; print(sys.prefix)"
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest -q
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest tests/test_regression_baseline.py -v -m slow
```
Expected: the previous 182 tests plus the new ones, all passing, and the slow regression guard passing. `pytest tests/test_regression_baseline.py` without `-m slow` collects zero tests and looks green; that is not a pass.

- [ ] **Step 2: The primary results did not move**

The whole revision is additive. Prove it:

```bash
git diff --stat 8a56d0c -- output/expanded/
```
`cohort_calibration.csv`, `heterogeneity_summary.json`, `analysis_records.csv`, `external_validation_predictions.csv` and `random_effects_pooling.csv` must be unchanged. Only new files should appear. If any of them changed, find out why before anything else.

- [ ] **Step 3: Citation and cross-reference completeness**

Re-run both diff scripts from Task 10 Step 4 and Task 11 Step 3. Empty lists, or a named supplement destination for every moved reference.

- [ ] **Step 4: Numeric consistency across documents**

Every statistic that appears in more than one of the manuscript, the supplement, the response document, the figure captions and the packet README must agree. Extract each number with its source file and compare. The values most likely to drift, because they are cited in four places each: the two tau values, the pooled mean absolute error, the recalibration crossing point, and the body word count.

- [ ] **Step 5: Word and abstract counts**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python "/Volumes/Extreme SSD/Mimic-IV/_pub_assets/wordcount.py" manuscript/manuscript_expanded.md
```
Body at or below 6,601. Abstract at or below 300, counted with `wc -w` on the extracted prose.

- [ ] **Step 6: De-AI scan over the whole revision diff**

```bash
grep -n "—" manuscript/*.md supplementary/*.md   # must return nothing
```
Then run the `de-ai-writing` skill over the full diff against `8a56d0c`, not only over individual paragraphs.

- [ ] **Step 7: Visual spot-check of every rendered PDF**

Open and look at: the clean manuscript's title page, one Methods page, one Results page carrying a table, the two new figures in place, the supplement's new landscape table, the highlighted manuscript's first highlighted passage, and the one-page cover letter. Confirm the cover letter is one page.

- [ ] **Step 8: Confirm the packet is complete against the checklist one more time**

Every required file present, correctly named, and in the right format. Required means Author Response, Highlighted PDF, Source File and Clean PDF.

- [ ] **Step 9: Merge to main**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest -q
git switch main
git merge --no-ff jne-r1-revision -m "merge: JNE-111284 major revision

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

Do not push. This repository has never been pushed from a session and the GitHub remote is a human-gated action.

- [ ] **Step 10: Update the memory topic file**

Update `/Users/alongorenshtein/.claude/projects/-Volumes-Extreme-SSD-Mimic-IV/memory/study-bigp3-als-calibration.md` and the `MEMORY.md` index line: the decision, what the alignment arms returned, the recalibration crossing point, the merge commit, and the fact that the packet is built but not submitted. Keep the index line to one line; the detail goes in the topic file.

---

## Self-Review

**Spec coverage.** Every item in the spec's two referee tables and the Editor report maps to a task: A1 to Task 9 Step 2; A2 to Task 9 Step 1; A3 to Tasks 6, 7 and 8; A4 to Task 11; A5 to Task 9 Step 3; B1 to Task 9 Step 4; C1 to Task 10; C2 to Tasks 2, 3 and 5; C3 to Tasks 1, 3, 4 and 5; C4 to Tasks 6 and 8; C5 to Task 12; the Editor's re-alignment request to Tasks 1 and 3 through 5; the Editor's detailed-response request to Task 14. Every checklist deliverable in spec section 3 maps to Task 15.

**Placeholders.** Three places deliberately do not carry final text, and each says why rather than deferring silently: the alignment Results heading in Task 8 Step 3, which cannot be written before the analysis runs; the title candidates in Task 12, which are the author's decision by D2; and the reference numbers in Task 10, which depend on what the literature search finds. Every code step carries the code.

**Type consistency.** `ModelSpecification(name, features, role)` is used identically in `alignment.ALIGNMENT_SPECS` and `validation.MODEL_SPECS`. `SESSION_KEYS` in `alignment.py` is the three-element `study, study_participant_id, session_id` tuple used as `KEYS` in both new scripts. `recalibration_draws` produces exactly the columns `recalibration_summary` groups and differences, and `n_evaluation_participants` is produced in Task 6 Step 3 and asserted in Task 6 Step 1. Task 5 Step 4 explicitly instructs verifying `cohort_calibration`'s real column names against the source before relying on them, because those are the one set of names this plan asserts without having read them.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-07-jne-111284-major-revision.md`. Two execution options:

**1. Subagent-Driven (recommended for Tasks 1 through 7)** - a fresh subagent per task, with review between tasks. Suits the analysis tasks, which have clean test boundaries. **Never point two parallel subagents at `/tmp/calib_venv`**: two agents repairing one virtualenv at once has previously landed on a lockfile pin that does not load. Run them sequentially, or give each its own environment.

**2. Inline Execution (recommended for Tasks 8 through 16)** - the manuscript tasks are precision edits on a document that has survived eight revision rounds, and the July length-trim pass chose inline execution for exactly this reason.
