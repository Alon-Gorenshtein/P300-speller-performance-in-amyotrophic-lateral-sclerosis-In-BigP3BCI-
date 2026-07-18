"""Publication-quality rendering from frozen BigP3 ALS analysis tables."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


LANCET_BLUE = "#00468B"
LANCET_GREY = "#ADB6B6"
LANCET_SALMON = "#FDAF91"
LABEL_COLOR = "#2B2B2B"
MUTED_COLOR = "#6B7280"
STUDY_COLORS = {"StudyF": LANCET_BLUE, "StudyL": LANCET_SALMON, "StudyN": "#5B8C85"}

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Helvetica Neue", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": True,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def require_columns(table: pd.DataFrame, required: set[str]) -> None:
    """Reject rendering inputs missing fields necessary to make an auditable figure."""
    missing = sorted(required - set(table.columns))
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def _save(fig: plt.Figure, directory: Path, stem: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    fig.savefig(directory / f"{stem}.pdf", dpi=600, bbox_inches="tight", pad_inches=0.15)
    fig.savefig(directory / f"{stem}.png", dpi=600, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def render_study_flow(records: pd.DataFrame, directory: Path) -> None:
    require_columns(records, {"study", "study_participant_id", "session_id", "condition", "n"})
    study_summary = records.groupby("study").agg(
        study_records=("study_participant_id", "nunique"),
        sessions=("session_id", "nunique"),
        conditions=("condition", "size"),
        characters=("n", "sum"),
    )
    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    ax.set_axis_off()
    text = [
        "bigP3BCI v1.0.0 clinical archive",
        "760 verified EDF files from three ALS studies",
        "57 participant-session calibration records",
        f"{int(records.study_participant_id.nunique())} study-scoped ALS records; {int(records.n.sum())} eligible online character selections",
        "Leave-one-study-out external validation",
    ]
    y = np.linspace(0.86, 0.14, len(text))
    for index, (line, y_position) in enumerate(zip(text, y, strict=True)):
        fill = "#E3EDF7" if index in {0, len(text) - 1} else "#FAFBFD"
        box = plt.matplotlib.patches.FancyBboxPatch(
            (0.08, y_position - 0.085), 0.84, 0.15, boxstyle="round,pad=0.015,rounding_size=0.03",
            facecolor=fill, edgecolor=LANCET_BLUE if index in {0, len(text) - 1} else "#D1D5DB", linewidth=1.0
        )
        ax.add_patch(box)
        ax.text(0.5, y_position, line, ha="center", va="center", color=LABEL_COLOR, fontsize=10,
                fontweight="bold" if index in {0, len(text) - 1} else "normal")
        if index < len(text) - 1:
            ax.annotate("", xy=(0.5, y_position - 0.17), xytext=(0.5, y_position - 0.11),
                        arrowprops={"arrowstyle": "-|>", "color": "#9CA3AF", "lw": 0.9})
    _save(fig, directory, "figure_1_study_flow")


def render_calibration_relationship(records: pd.DataFrame, predictions: pd.DataFrame, directory: Path) -> None:
    require_columns(records, {"study", "calibration_auc", "correct", "n"})
    require_columns(predictions, {"model", "study", "calibration_auc", "correct", "n", "predicted_probability"})
    observed = records.assign(online_accuracy=records["correct"] / records["n"])
    primary = predictions.loc[predictions["model"] == "calibration_auc"].copy()
    primary["online_accuracy"] = primary["correct"] / primary["n"]
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.1), constrained_layout=True)
    for study, frame in observed.groupby("study", sort=True):
        axes[0].scatter(frame.calibration_auc, frame.online_accuracy, s=34, color=STUDY_COLORS[study],
                        edgecolors="white", linewidths=0.7, alpha=0.85, label=study)
    axes[0].set_xlabel("Calibration discriminability (cross-validated AUC)")
    axes[0].set_ylabel("Observed online character accuracy")
    axes[0].set_xlim(0.42, 1.02)
    axes[0].set_ylim(-0.04, 1.04)
    axes[0].grid(color="#F3F4F6", lw=0.6)
    axes[0].legend(loc="lower center", bbox_to_anchor=(0.5, -0.29), ncol=3, frameon=False, fontsize=9)
    axes[0].text(-0.14, 1.04, "a", transform=axes[0].transAxes, fontsize=14, fontweight="bold", color=LABEL_COLOR)
    for study, frame in primary.groupby("study", sort=True):
        axes[1].scatter(frame.predicted_probability, frame.online_accuracy, s=34, color=STUDY_COLORS[study],
                        edgecolors="white", linewidths=0.7, alpha=0.85)
    axes[1].plot([0, 1], [0, 1], ls="--", lw=0.8, color="#9CA3AF", zorder=0)
    axes[1].set_xlabel("Predicted online accuracy (held-out study)")
    axes[1].set_ylabel("Observed online character accuracy")
    axes[1].set_xlim(-0.04, 1.04)
    axes[1].set_ylim(-0.04, 1.04)
    axes[1].grid(color="#F3F4F6", lw=0.6)
    axes[1].text(-0.14, 1.04, "b", transform=axes[1].transAxes, fontsize=14, fontweight="bold", color=LABEL_COLOR)
    _save(fig, directory, "figure_2_calibration_relationship")


def render_external_auc(metrics: pd.DataFrame, directory: Path) -> None:
    required = {"model", "held_out_study", "roc_auc", "roc_auc_ci_low", "roc_auc_ci_high"}
    require_columns(metrics, required)
    primary = metrics.loc[metrics["model"] == "calibration_auc"].copy()
    order = ["StudyF", "StudyL", "StudyN", "Pooled out-of-study"]
    primary["position"] = primary.held_out_study.map({label: index for index, label in enumerate(order)})
    primary = primary.sort_values("position")
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.axvline(0.5, ls="--", lw=0.8, color="#9CA3AF", zorder=0)
    for _, row in primary.iterrows():
        color = STUDY_COLORS.get(row.held_out_study, LANCET_BLUE)
        ax.errorbar(row.roc_auc, row.position, xerr=[[row.roc_auc - row.roc_auc_ci_low], [row.roc_auc_ci_high - row.roc_auc]],
                    fmt="o", ms=7, mfc=color, mec="white", mew=0.8, ecolor=color, capsize=3, lw=1.4)
        ax.text(1.01, row.position, f"{row.roc_auc:.2f} ({row.roc_auc_ci_low:.2f}-{row.roc_auc_ci_high:.2f})",
                va="center", fontsize=9, color=LABEL_COLOR)
    ax.set_yticks(primary.position, primary.held_out_study.str.replace("Study", "Study "))
    ax.invert_yaxis()
    ax.set_xlim(0.4, 1.22)
    ax.set_xlabel("Held-out character-level ROC AUC (95% cluster-bootstrap CI)")
    ax.grid(axis="x", color="#F3F4F6", lw=0.6)
    _save(fig, directory, "figure_3_external_validation_auc")


def render_all(records: pd.DataFrame, predictions: pd.DataFrame, metrics: pd.DataFrame, directory: Path) -> None:
    """Create all main-text figures strictly from frozen analysis tables."""
    render_study_flow(records, directory)
    render_calibration_relationship(records, predictions, directory)
    render_external_auc(metrics, directory)
