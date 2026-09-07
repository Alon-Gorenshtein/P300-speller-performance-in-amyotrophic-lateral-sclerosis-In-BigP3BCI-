"""Measure the PCA explained-variance the GBM arm's downsampled epoch features carry.

This is the measurement `docs/pipeline_rerun_2026-09-07_alignment.md` cites to justify the
150-component PCA budget used by the `gradient_boosting` nonlinear arm (`calibration_auc_gbm`).
An earlier draft justified that budget by matching the RBF arm's component count, which the same
document retracted as a coincidence rather than a reason; this script replaces that retracted
argument with a direct measurement, so the budget rests on how much of the feature space's own
variance a given number of components retains, not on matching an unrelated arm.

It answers that question on five real sessions spanning the archive's size range: the smallest
evaluable session, the 25th/50th/75th percentile sessions by epoch count, and the largest session.
For each, PCA is fit twice: once on the full session (every epoch) and once on the smallest actual
training fold `StratifiedGroupKFold` produces for that session, since that fold, not the full
session, is what the classifier trains on inside `_grouped_cv_predictions`. Cumulative explained
variance is reported at 20, 40, 60, 80, 100 and 150 components.

Not part of the pipeline: it reads directly from the EDF cache rather than from an extracted
feature file, and its output (`tmp/pca_variance_probe.csv`) is a diagnostic table for the doc above,
not a manuscript or supplement deliverable. Kept in `scripts/` and committed, rather than left as a
gitignored throwaway, because it is the sole source of the variance table that replaced a retracted
justification for the PCA budget: a referee asking how the 150-component budget was chosen has to be
able to run this and reproduce the numbers.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.model_selection import StratifiedGroupKFold

from bigp3_als.edf import parse_source_path, select_edf_paths
from bigp3_als.features import _downsampled_epoch_features, _extract_file_epochs

CACHE = Path("data/source_cache_full")
OUTPUT = Path("tmp/pca_variance_probe.csv")

PROBE_KEYS = [
    ("StudyJ", "J_07", "SE001"),   # min, 123 epochs
    ("StudyB", "B_17", "SE003"),   # p25, 3778 epochs
    ("StudyO", "O_17", "SE002"),   # p50, 4312 epochs
    ("StudyP", "P_18", "SE002"),   # p75, 4320 epochs
    ("StudyA", "A_02", "SE001"),   # max, 12924 epochs
]
COMPONENT_GRID = [20, 40, 60, 80, 100, 150]


def main() -> None:
    grouped_paths: dict[tuple[str, str, str], list[Path]] = defaultdict(list)
    for edf_path in select_edf_paths(CACHE):
        source = parse_source_path(edf_path.relative_to(CACHE).as_posix())
        if source.phase == "Train":
            grouped_paths[(source.study, source.participant_id, source.session_id)].append(edf_path)

    rows = []
    for key in PROBE_KEYS:
        paths = sorted(grouped_paths[key])
        epochs_list, labels_list, groups_list = [], [], []
        for group_index, path in enumerate(paths):
            epochs, labels, _, _ = _extract_file_epochs(path)
            epochs_list.append(epochs)
            labels_list.append(labels)
            groups_list.append(np.repeat(group_index, len(labels)))
        epochs = np.concatenate(epochs_list)
        labels = np.concatenate(labels_list)
        groups = np.concatenate(groups_list)
        features = _downsampled_epoch_features(epochs)
        n_samples, n_features = features.shape

        unique_groups = np.unique(groups)
        n_splits = min(5, len(unique_groups))
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=20260718)
        splits = list(splitter.split(features, labels, groups))
        fold_sizes = [len(train_idx) for train_idx, _ in splits]
        smallest_fold = min(fold_sizes)
        smallest_fold_train_idx = min(splits, key=lambda s: len(s[0]))[0]

        for scope, X in [
            ("full_session", features),
            ("smallest_training_fold", features[smallest_fold_train_idx]),
        ]:
            cap = min(X.shape[0], X.shape[1])
            pca = PCA(n_components=cap, svd_solver="randomized", random_state=20260718)
            pca.fit(X)
            cumulative = np.cumsum(pca.explained_variance_ratio_)
            row = {
                "session": "|".join(key), "n_samples_in_scope": X.shape[0], "n_features": n_features,
                "scope": scope, "session_n_epochs": n_samples, "smallest_fold_size": smallest_fold,
            }
            for component_count in COMPONENT_GRID:
                if component_count <= len(cumulative):
                    row[f"cum_var_at_{component_count}"] = float(cumulative[component_count - 1])
                else:
                    # Capped at the achievable maximum, e.g. the smallest session's smallest fold.
                    row[f"cum_var_at_{component_count}"] = float(cumulative[-1])
            rows.append(row)
            print(f"{key} [{scope}] n={X.shape[0]} smallest_fold={smallest_fold} -> "
                  + ", ".join(f"{c}:{row[f'cum_var_at_{c}']:.4f}" for c in COMPONENT_GRID))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUTPUT, index=False)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
