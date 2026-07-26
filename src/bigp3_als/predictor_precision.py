"""Measure how precisely the calibration score itself was estimated in each cohort.

The score is a cross-validated area under the curve computed from that session's calibration files.
Sessions differ several-fold in files, folds and surviving epochs, so the score is not measured
equally well everywhere. Measurement error in a predictor attenuates a fitted slope, which is an
alternative explanation for between-cohort differences in calibration.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

MAX_FOLDS = 5


def _auc_standard_error(auc: float, n_target: float, n_nontarget: float) -> float:
    """Hanley and McNeil approximate standard error of an area under the curve."""
    if n_target < 1 or n_nontarget < 1:
        return float("nan")
    q1 = auc / (2 - auc)
    q2 = 2 * auc**2 / (1 + auc)
    variance = (
        auc * (1 - auc) + (n_target - 1) * (q1 - auc**2) + (n_nontarget - 1) * (q2 - auc**2)
    ) / (n_target * n_nontarget)
    return float(np.sqrt(max(variance, 0.0)))


def precision_table(features: pd.DataFrame) -> pd.DataFrame:
    """Summarise, per study, how much data supported each session's calibration score.

    `n_nontarget_epochs` is read directly from the features file rather than derived as
    `n_calibration_epochs - n_target_epochs`: on the real data the two agree exactly, but the
    stored column is what the pipeline actually counted, and reading it directly does not depend
    on that agreement continuing to hold.
    """
    frame = features.dropna(subset=["calibration_auc"]).copy()
    frame["folds"] = frame["train_file_count"].clip(upper=MAX_FOLDS)
    if "n_nontarget_epochs" not in frame.columns:
        frame["n_nontarget_epochs"] = frame["n_calibration_epochs"] - frame["n_target_epochs"]
    frame["auc_se"] = [
        _auc_standard_error(a, t, nt)
        for a, t, nt in zip(frame["calibration_auc"], frame["n_target_epochs"], frame["n_nontarget_epochs"])
    ]
    return (
        frame.groupby("study", sort=True)
        .agg(
            median_train_files=("train_file_count", "median"),
            median_folds=("folds", "median"),
            median_calibration_epochs=("n_calibration_epochs", "median"),
            median_target_epochs=("n_target_epochs", "median"),
            auc_standard_error=("auc_se", "median"),
        )
        .reset_index()
    )


def precision_versus_slope(precision: pd.DataFrame, calibration: pd.DataFrame) -> dict[str, float]:
    """Test whether cohorts with a noisier predictor show flatter calibration slopes."""
    merged = precision.merge(
        calibration.rename(columns={"held_out_study": "study"})[["study", "slope"]], on="study"
    ).dropna(subset=["auc_standard_error", "slope"])
    if len(merged) < 3:
        return {"n_studies": float(len(merged)), "spearman_rho": float("nan"), "p_value": float("nan")}
    rho, p_value = stats.spearmanr(merged["auc_standard_error"], merged["slope"])
    return {"n_studies": float(len(merged)), "spearman_rho": float(rho), "p_value": float(p_value)}
