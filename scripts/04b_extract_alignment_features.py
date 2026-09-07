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

from bigp3_als.alignment import pooled_reference
from bigp3_als.features import build_alignment_features

KEYS = ["study", "study_participant_id", "session_id"]
REPRODUCTION_TOLERANCE = 1e-9


def _build_cohort_references(covariances_path: Path) -> dict[str, np.ndarray]:
    """Pool each cohort's session reference covariances, weighted by each session's epoch count.

    The key format is study|participant_id|session_id (Task 3's convention), so the study is the
    text before the first separator.
    """
    archive = np.load(covariances_path)
    keys = archive["keys"]
    per_session_references = archive["references"]
    n_epochs = archive["n_epochs"]
    studies = np.array([str(key).split("|", 1)[0] for key in keys])
    cohort_references: dict[str, np.ndarray] = {}
    for study in sorted(set(studies)):
        mask = studies == study
        cohort_references[study] = pooled_reference(per_session_references[mask], n_epochs[mask])
    return cohort_references


def _run_cohort_pass(arguments: argparse.Namespace) -> None:
    """Compute calibration_auc_ea_cohort only, and merge it into an existing feature file.

    This invocation does not recompute calibration_auc_reproduced, so it costs one grouped
    cross-validation per session rather than two, and it does not check baseline reproduction:
    there is no baseline column in this pass's own output to check it against.
    """
    cohort_references = _build_cohort_references(arguments.cohort_references)
    print(f"pooled {len(cohort_references)} cohort references from {arguments.cohort_references}")
    for study in sorted(cohort_references):
        condition_number = float(np.linalg.cond(cohort_references[study]))
        flag = "  <-- poorly conditioned" if condition_number > 1e4 else ""
        print(f"  {study}: condition number = {condition_number:.3e}{flag}")

    frame, _ = build_alignment_features(
        arguments.cache, ("calibration_auc_ea_cohort",), cohort_references
    )

    existing = pd.read_csv(arguments.merge_into)
    merged = existing.merge(
        frame[[*KEYS, "calibration_auc_ea_cohort"]], on=KEYS, how="inner", validate="one_to_one"
    )
    if not (len(existing) == len(frame) == len(merged)):
        raise SystemExit(
            f"session key mismatch: existing file has {len(existing)} rows, new pass has "
            f"{len(frame)} rows, merged has {len(merged)} rows"
        )
    merged.to_csv(arguments.merge_into, index=False)
    print(f"merged calibration_auc_ea_cohort into {arguments.merge_into} ({len(merged)} rows)")


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
    parser.add_argument("--cohort-references", type=Path, default=None,
                        help="npz of per-session reference covariances (Task 3's output) to pool "
                             "into one reference per cohort; when given, runs the cohort-level "
                             "Euclidean Alignment arm only and merges it into --merge-into")
    parser.add_argument("--merge-into", type=Path, default=None,
                        help="existing alignment feature file to merge calibration_auc_ea_cohort "
                             "into; required when --cohort-references is given")
    arguments = parser.parse_args()

    if arguments.cohort_references is not None:
        if arguments.merge_into is None:
            raise SystemExit("--merge-into is required when --cohort-references is given")
        _run_cohort_pass(arguments)
        return

    frame, references = build_alignment_features(arguments.cache, tuple(arguments.arms))

    frozen = pd.read_csv(arguments.frozen)
    merged = frame.merge(frozen[[*KEYS, "calibration_auc"]], on=KEYS, how="inner", validate="one_to_one")
    # An inner join drops any row on either side with no match on the other, silently, so checking
    # the merged count against only one side would pass even if `frame` carried extra unmatched rows
    # that never got compared. All three counts have to agree for the join to be a true bijection.
    if not (len(frame) == len(frozen) == len(merged)):
        raise SystemExit(
            f"session key mismatch: frame has {len(frame)} rows, frozen has {len(frozen)} rows, "
            f"merged has {len(merged)} rows"
        )
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
    # The covariance key is study|participant_id|session_id, while the frame is indexed on
    # study|study_participant_id|session_id, so the epoch counts have to be pulled through the
    # same three raw columns the key was built from rather than through study_participant_id.
    # Indexing on the wrong column would silently emit NaN counts here instead of failing, and
    # Task 4 would then consume those NaNs without any signal that something upstream disagreed.
    epoch_counts = frame.set_index(["study", "participant_id", "session_id"])["n_calibration_epochs"]
    ordered = epoch_counts.reindex([tuple(key.split("|", 2)) for key in keys])
    if ordered.isna().any():
        raise SystemExit("covariance keys do not match the feature frame index")
    np.savez_compressed(
        arguments.covariances,
        keys=np.array(keys),
        references=np.stack([references[key] for key in keys]),
        n_epochs=ordered.to_numpy(dtype=float),
    )
    print(f"wrote {len(frame)} alignment feature rows and {len(keys)} reference covariances")


if __name__ == "__main__":
    main()
