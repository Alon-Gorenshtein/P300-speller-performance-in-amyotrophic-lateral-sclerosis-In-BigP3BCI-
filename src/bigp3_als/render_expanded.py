"""Figures for the widened design.

Two displays carry the argument the four-cohort version could not make.

``render_transportability`` places every withheld cohort's estimation error on one axis together
with the mean across cohorts, its confidence interval, and the interval a cohort outside the archive
would be expected to fall in. Drawing the confidence interval and the prediction interval on the
same axis is the point: they answer different questions and only the second is relevant to a reader
deciding what to expect in their own setting.

``render_skill_by_cohort`` reports each cohort's error against the development-mean benchmark, so
that cohorts where the score adds nothing, or costs something, are visible rather than absorbed into
a pooled average. That benchmark, not the cohort's own mean, is the one the plotted skill is computed
against.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bigp3_als.render import LABEL_COLOR, _save

ALS_COLOR = "#B24745"
OTHER_COLOR = "#374E55"
BAND_COLOR = "#79AF97"


def _cohort_label(study: str) -> str:
    return study.replace("Study", "Study ")


def render_transportability(
    metrics: pd.DataFrame,
    pooling: pd.DataFrame,
    als_studies: tuple[str, ...],
    directory: Path,
    metric: str = "session_mean_absolute_error",
) -> None:
    """Plot withheld-cohort estimation error with the mean and new-cohort prediction interval."""
    per_study = metrics.loc[~metrics["held_out_study"].astype(str).str.startswith("Pooled")].copy()
    per_study = per_study.dropna(subset=[metric]).sort_values(metric)
    summary = pooling.loc[pooling["quantity"] == metric]
    if per_study.empty or summary.empty:
        raise ValueError(f"no per-study values available for {metric}")
    summary = summary.iloc[0]

    positions = np.arange(len(per_study))
    colours = [
        ALS_COLOR if study in als_studies else OTHER_COLOR for study in per_study["held_out_study"]
    ]

    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    ax.axvspan(
        summary["prediction_interval_low"],
        summary["prediction_interval_high"],
        color=BAND_COLOR,
        alpha=0.20,
        zorder=0,
        label="95% interval for a cohort not in the archive",
    )
    ax.axvspan(
        summary["confidence_interval_low"],
        summary["confidence_interval_high"],
        color=BAND_COLOR,
        alpha=0.55,
        zorder=1,
        label="95% interval for the mean across cohorts",
    )
    ax.axvline(summary["mean"], color=LABEL_COLOR, linewidth=1.2, zorder=2,
               label="mean across withheld cohorts")
    ax.scatter(per_study[metric], positions, c=colours, s=44, zorder=3)

    ax.set_yticks(positions)
    ax.set_yticklabels([_cohort_label(s) for s in per_study["held_out_study"]])
    ax.set_xlabel("Mean absolute error of estimated session accuracy")
    ax.set_ylim(-0.8, len(per_study) - 0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color="white", linewidth=0)

    handles, labels = ax.get_legend_handles_labels()
    marker_handles = [
        plt.Line2D([], [], marker="o", linestyle="none", color=ALS_COLOR, label="ALS cohort"),
        plt.Line2D([], [], marker="o", linestyle="none", color=OTHER_COLOR, label="Other cohort"),
    ]
    ax.legend(
        handles=handles + marker_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.30),
        ncol=2,
        frameon=False,
        fontsize=8.5,
    )
    _save(fig, directory, "figure_transportability")


def render_skill_by_cohort(
    metrics: pd.DataFrame,
    benchmark: pd.DataFrame,
    als_studies: tuple[str, ...],
    directory: Path,
    metric: str = "session_mean_absolute_error",
) -> None:
    """Plot each cohort's error reduction against the development-mean benchmark."""
    per_study = metrics.loc[~metrics["held_out_study"].astype(str).str.startswith("Pooled")]
    null = benchmark.loc[benchmark["held_out_study"] != "Pooled held-out records"]
    merged = per_study.merge(
        null[["held_out_study", "development_mean_benchmark_mae"]], on="held_out_study", how="inner"
    ).dropna(subset=[metric, "development_mean_benchmark_mae"])
    merged["skill"] = 1.0 - merged[metric] / merged["development_mean_benchmark_mae"]
    merged = merged.sort_values("skill")

    positions = np.arange(len(merged))
    colours = [ALS_COLOR if s in als_studies else OTHER_COLOR for s in merged["held_out_study"]]

    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    ax.axvline(0.0, color=LABEL_COLOR, linewidth=1.0, zorder=1)
    ax.barh(positions, merged["skill"], color=colours, height=0.62, zorder=2)
    ax.set_yticks(positions)
    ax.set_yticklabels([_cohort_label(s) for s in merged["held_out_study"]])
    ax.set_xlabel("Error reduction against the development-mean benchmark")
    ax.set_ylim(-0.6, len(merged) - 0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(
        handles=[
            plt.Line2D([], [], marker="s", linestyle="none", color=ALS_COLOR, label="ALS cohort"),
            plt.Line2D([], [], marker="s", linestyle="none", color=OTHER_COLOR, label="Other cohort"),
        ],
        loc="lower right", frameon=False, fontsize=8.5,
    )
    _save(fig, directory, "figure_skill_by_cohort")


def render_cohort_type_relationship(
    records: pd.DataFrame, als_studies: tuple[str, ...], directory: Path,
    feature: str = "calibration_auc",
) -> None:
    """Plot calibration score against observed accuracy separately for each cohort type."""
    frame = records.dropna(subset=[feature]).copy()
    frame["accuracy"] = frame["correct"] / frame["n"]
    frame["is_als"] = frame["study"].isin(als_studies)

    fig, ax = plt.subplots(figsize=(6.0, 4.6))
    for is_als, colour, name in ((False, OTHER_COLOR, "Other cohorts"), (True, ALS_COLOR, "ALS cohorts")):
        subset = frame.loc[frame["is_als"] == is_als]
        if subset.empty:
            continue
        ax.scatter(subset[feature], subset["accuracy"], s=np.sqrt(subset["n"]) * 3.0,
                   color=colour, alpha=0.45, edgecolors="none", label=f"{name} (n = {len(subset)})")
        x = subset[feature].to_numpy(dtype=float)
        y = subset["accuracy"].to_numpy(dtype=float)
        centred = x - x.mean()
        denominator = float(centred @ centred)
        if denominator > 0:
            slope = float(centred @ (y - y.mean()) / denominator)
            grid = np.linspace(x.min(), x.max(), 50)
            fitted = y.mean() + slope * (grid - x.mean())
            # The outcome is a proportion, so the drawn line is bounded even though the
            # straight-line fit used for the slope contrast is not.
            inside = fitted <= 1.0
            ax.plot(grid[inside], fitted[inside], color=colour, linewidth=1.8)

    ax.set_xlabel("Calibration discriminability (grouped cross-validated AUC)")
    ax.set_ylabel("Observed online session accuracy")
    ax.set_ylim(-0.03, 1.03)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    _save(fig, directory, "figure_cohort_type_relationship")
