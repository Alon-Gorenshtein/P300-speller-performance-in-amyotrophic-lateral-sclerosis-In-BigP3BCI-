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
