"""Figures for the widened design.

Four displays carry the argument the four-cohort version could not make.

``render_calibration_forest`` puts the quantity the paper's headline rests on, the cohort-specific
calibration slope and intercept, on one axis with the interval each was estimated with, the pooled
value, and the interval a cohort outside the archive would be expected to fall in. It is the direct
picture of a mapping that does not transport: the reader sees the spread, the reference value the
mapping would have to hold near, and how little of that spread is sampling error.

``render_calibration_curves`` shows the same failure one cohort at a time, plotting observed against
estimated accuracy in equal-count bins of the estimate. The forest gives the spread of the mapping; these
panels give its direction, so a cohort in which accuracy is overstated is distinguishable from one
in which it is understated rather than both being absorbed into a single spread.

``render_transportability`` places every withheld cohort's estimation error on one axis together
with the mean across cohorts, its confidence interval, and the interval a cohort outside the archive
would be expected to fall in. Drawing the confidence interval and the prediction interval on the
same axis is the point: they answer different questions and only the second is relevant to a reader
deciding what to expect in their own setting.

``render_skill_by_cohort`` reports each cohort's error against the development-mean benchmark, so
that cohorts where the score adds nothing, or costs something, are visible rather than absorbed into
a pooled average. That benchmark, not the cohort's own mean, is the one the plotted skill is computed
against.

``render_cohort_type_relationship`` is descriptive only and draws no fitted line. An earlier version
fitted a straight line separately to the ALS cohorts and to the rest, which is the visual form of a
record-level interaction; that test was demoted to the study level because treating 739 records as
independent overstates its precision by roughly an order of magnitude. The cohort-type contrast is
carried by the colouring of the forest instead, which asserts no fitted interaction.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from bigp3_als.render import LABEL_COLOR, _save, require_columns

ALS_COLOR = "#B24745"
OTHER_COLOR = "#374E55"
# Marker shape is a second, color-independent channel encoding ALS-vs-other cohort type, so the
# distinction survives grayscale reproduction and is legible to readers with color-vision deficiency.
ALS_MARKER = "D"
OTHER_MARKER = "o"
BAND_COLOR = "#79AF97"

# The same critical value the analysis used to write the interval columns of cohort_calibration.csv.
CRITICAL_VALUE = float(stats.norm.ppf(0.975))
# The interval is derived here from the standard error rather than read from the file, so that a
# frame carrying only standard errors renders. Where the file also carries its own interval the two
# are required to agree, which catches a figure drifting from the table it is supposed to depict.
INTERVAL_TOLERANCE = 1e-9


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
    is_als = per_study["held_out_study"].isin(als_studies).to_numpy()
    values = per_study[metric].to_numpy()

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
               label="geometric mean across withheld cohorts")
    # A single scatter() call cannot vary marker shape by point, so the ALS and other-cohort
    # subsets are drawn as two calls sharing the same size and z-order.
    ax.scatter(values[is_als], positions[is_als], color=ALS_COLOR, marker=ALS_MARKER, s=44, zorder=3)
    ax.scatter(values[~is_als], positions[~is_als], color=OTHER_COLOR, marker=OTHER_MARKER, s=44,
               zorder=3)

    ax.set_yticks(positions)
    ax.set_yticklabels([_cohort_label(s) for s in per_study["held_out_study"]])
    ax.set_xlabel("Mean absolute error of estimated session accuracy")
    ax.set_ylim(-0.8, len(per_study) - 0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color="white", linewidth=0)

    handles, labels = ax.get_legend_handles_labels()
    marker_handles = [
        plt.Line2D([], [], marker=ALS_MARKER, linestyle="none", color=ALS_COLOR, label="ALS cohort"),
        plt.Line2D([], [], marker=OTHER_MARKER, linestyle="none", color=OTHER_COLOR, label="Other cohort"),
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
    is_als = merged["held_out_study"].isin(als_studies).to_numpy()
    colours = [ALS_COLOR if s in als_studies else OTHER_COLOR for s in merged["held_out_study"]]
    # Hatching is a second, color-independent channel encoding ALS-vs-other cohort type, the same
    # precedent as the ALS_MARKER/OTHER_MARKER shape distinction used in the other figures, so the
    # distinction survives grayscale reproduction.
    hatches = ["//" if value else None for value in is_als]

    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    ax.axvline(0.0, color=LABEL_COLOR, linewidth=1.0, zorder=1)
    bars = ax.barh(positions, merged["skill"], color=colours, height=0.62, zorder=2,
                    edgecolor="white", linewidth=0.6)
    for bar, hatch in zip(bars, hatches, strict=True):
        if hatch:
            bar.set_hatch(hatch)
    ax.set_yticks(positions)
    ax.set_yticklabels([_cohort_label(s) for s in merged["held_out_study"]])
    ax.set_xlabel("Error reduction against the development-mean benchmark")
    ax.set_ylim(-0.6, len(merged) - 0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(
        handles=[
            plt.Rectangle((0, 0), 1, 1, facecolor=ALS_COLOR, edgecolor="white", hatch="//",
                          label="ALS cohort"),
            plt.Rectangle((0, 0), 1, 1, facecolor=OTHER_COLOR, edgecolor="white", label="Other cohort"),
        ],
        loc="lower right", frameon=False, fontsize=8.5,
    )
    _save(fig, directory, "figure_skill_by_cohort")


def _cohort_intervals(calibration: pd.DataFrame, quantity: str) -> pd.DataFrame:
    """Return the cohort estimates for one quantity with the 95% interval of each."""
    require_columns(calibration, {"held_out_study", quantity, f"{quantity}_se"})
    ordered = calibration.sort_values(quantity).reset_index(drop=True)
    lower = ordered[quantity] - CRITICAL_VALUE * ordered[f"{quantity}_se"]
    upper = ordered[quantity] + CRITICAL_VALUE * ordered[f"{quantity}_se"]
    for bound, written in ((lower, f"{quantity}_ci_low"), (upper, f"{quantity}_ci_high")):
        if written in ordered.columns:
            departure = float(np.max(np.abs(bound - ordered[written])))
            if departure > INTERVAL_TOLERANCE:
                raise ValueError(
                    f"{quantity}: the interval derived from the standard error departs from the "
                    f"one in the table by {departure:.3e}"
                )
    return ordered.assign(lower=lower, upper=upper)


def _forest_panel(
    ax: plt.Axes,
    calibration: pd.DataFrame,
    quantity: str,
    block: dict[str, float] | None,
    als_studies: tuple[str, ...],
    reference: float,
    label: str,
) -> None:
    """Draw one forest of cohort estimates against the value a transportable mapping would hold."""
    frame = _cohort_intervals(calibration, quantity)
    positions = np.arange(len(frame))

    anchors = [frame[quantity].to_numpy(dtype=float), np.array([reference], dtype=float)]
    if block is not None:
        anchors.append(
            np.array([block["prediction_interval_low"], block["prediction_interval_high"]])
        )
    # An interval far wider than the rest, which happens where a near-ceiling cohort barely
    # identifies its own mapping, would otherwise compress every other cohort into a few pixels.
    # The axis is set from the estimates themselves and one typical interval width of margin, and
    # anything running past it is drawn with an arrow rather than silently truncated.
    margin = 0.5 * float(np.median(frame["upper"] - frame["lower"]))
    low = float(np.concatenate(anchors).min()) - margin
    high = float(np.concatenate(anchors).max()) + margin

    if block is not None:
        ax.axvspan(
            block["prediction_interval_low"], block["prediction_interval_high"],
            color=BAND_COLOR, alpha=0.22, zorder=0,
            label="95% interval for a cohort not in the archive",
        )
        ax.axvline(block["pooled"], color=BAND_COLOR, linewidth=1.6, zorder=1, label="pooled estimate")
    # One legend serves both panels, so the reference is named for what it means rather than by the
    # value it takes, which differs between them.
    ax.axvline(reference, color=LABEL_COLOR, linewidth=1.0, linestyle="--", zorder=2,
               label="no miscalibration (slope 1, intercept 0)")

    arrow_length = 0.05 * (high - low)
    for position, row in zip(positions, frame.itertuples(), strict=True):
        row_is_als = row.held_out_study in als_studies
        colour = ALS_COLOR if row_is_als else OTHER_COLOR
        marker = ALS_MARKER if row_is_als else OTHER_MARKER
        ax.plot([max(row.lower, low), min(row.upper, high)], [position, position],
                color=colour, linewidth=1.5, solid_capstyle="butt", zorder=3)
        ax.plot([getattr(row, quantity)], [position], marker=marker, markersize=5.0,
                color=colour, zorder=4)
        if row.lower < low:
            ax.annotate("", xy=(low, position), xytext=(low + arrow_length, position),
                        arrowprops={"arrowstyle": "-|>", "color": colour, "lw": 1.1}, zorder=3)
        if row.upper > high:
            ax.annotate("", xy=(high, position), xytext=(high - arrow_length, position),
                        arrowprops={"arrowstyle": "-|>", "color": colour, "lw": 1.1}, zorder=3)

    if block is not None:
        label = (
            f"{label}\ntau = {block['tau']:.2f}, I-squared = {block['i_squared']:.0f}%"
        )
    ax.set_yticks(positions)
    ax.set_yticklabels([_cohort_label(study) for study in frame["held_out_study"]], fontsize=12)
    ax.set_xlabel(label, fontsize=12)
    ax.tick_params(axis="x", labelsize=12)
    ax.set_xlim(low, high)
    ax.set_ylim(-0.8, len(frame) - 0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def render_calibration_forest(
    calibration: pd.DataFrame,
    summary: dict[str, dict[str, float]],
    als_studies: tuple[str, ...],
    directory: Path,
) -> None:
    """Plot every cohort's calibration slope and intercept against a transportable mapping.

    ``calibration`` must already be filtered to one standard-error specification; the table on disk
    stacks three of them. ``summary`` is the matching block of the heterogeneity summary, keyed by
    quantity, and a quantity absent from it is drawn without the pooled value or the band.
    """
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 7.4), constrained_layout=True)
    _forest_panel(axes[0], calibration, "slope", summary.get("slope"), als_studies, 1.0,
                  "Calibration slope (95% CI)")
    _forest_panel(axes[1], calibration, "intercept", summary.get("intercept"), als_studies, 0.0,
                  "Calibration intercept, log odds (95% CI)")
    for axis, letter in zip(axes, "ab", strict=True):
        axis.text(-0.30, 1.02, letter, transform=axis.transAxes, fontsize=14, fontweight="bold",
                  color=LABEL_COLOR)

    handles, _ = axes[0].get_legend_handles_labels()
    handles += [
        plt.Line2D([], [], marker=ALS_MARKER, linestyle="none", color=ALS_COLOR, label="ALS cohort"),
        plt.Line2D([], [], marker=OTHER_MARKER, linestyle="none", color=OTHER_COLOR, label="Other cohort"),
    ]
    fig.legend(handles=handles, loc="outside lower center", ncol=3, frameon=False, fontsize=12)
    _save(fig, directory, "figure_calibration_forest")


def _calibration_bins(frame: pd.DataFrame, bins: int) -> pd.DataFrame:
    """Group one cohort's records into equal-count bins of the estimate, weighting by selections.

    A cohort supports at most as many bins as it has distinct estimates, and the predictor is
    constant within a session, so the small cohorts draw fewer than the requested ten.
    """
    working = frame.copy()
    distinct = int(working["predicted_probability"].nunique())
    if distinct < 2:
        working["bin"] = 0
    else:
        working["bin"] = pd.qcut(
            working["predicted_probability"], q=min(bins, distinct), duplicates="drop", labels=False
        )
    rows = []
    for _, group in working.groupby("bin", sort=True):
        selections = group["n"].to_numpy(dtype=float)
        rows.append(
            {
                "predicted": float(np.average(group["predicted_probability"], weights=selections)),
                "observed": float(group["correct"].sum() / group["n"].sum()),
                "selections": float(selections.sum()),
            }
        )
    return pd.DataFrame(rows)


def render_calibration_curves(
    predictions: pd.DataFrame,
    als_studies: tuple[str, ...],
    directory: Path,
    bins: int = 10,
    cohorts: tuple[str, ...] | None = None,
    filename: str = "figure_calibration_curves",
    *,
    max_columns: int | None = None,
    panel_width: float = 1.62,
    panel_height: float = 1.78,
) -> None:
    """Plot observed against estimated accuracy, one panel per withheld cohort.

    Each point is one of up to ``bins`` equal-count groups of the estimate within that cohort,
    positioned at the selection-weighted mean estimate and the observed accuracy of the records in
    it. Points above the identity line are bins whose accuracy the mapping understated and points
    below are bins whose accuracy it overstated, which is the direction the forest does not show.

    ``cohorts``, when given, restricts the panel grid to that subset (used for a readable
    main-text figure); the default ``None`` draws every cohort (used for the full supplementary
    figure). ``filename`` lets the two versions be written without one overwriting the other.

    ``max_columns``, ``panel_width``, and ``panel_height`` control the grid shape and the size of
    each panel. The defaults reproduce the original single-row-of-up-to-six layout; the main-text
    call passes a narrower ``max_columns`` and larger panel dimensions so the six-cohort figure
    fills a portrait page instead of rendering as a wide, short strip.
    """
    require_columns(predictions, {"held_out_study", "predicted_probability", "correct", "n"})
    frame = predictions
    if "model_role" in frame.columns:
        frame = frame.loc[frame["model_role"] == "primary"]
    if frame.empty:
        raise ValueError("no primary predictions available to draw calibration curves")

    available = sorted(frame["held_out_study"].unique())
    if cohorts is not None:
        missing = sorted(set(cohorts) - set(available))
        if missing:
            raise ValueError(f"cohorts not present in predictions: {missing}")
        cohort_list = list(cohorts)
    else:
        cohort_list = available
    columns = min(max_columns or 6, len(cohort_list))
    rows = math.ceil(len(cohort_list) / columns)
    fig, axes = plt.subplots(
        rows, columns, figsize=(panel_width * columns, panel_height * rows + 0.5),
        sharex=True, sharey=True, constrained_layout=True,
    )
    flat = np.atleast_1d(np.asarray(axes)).ravel()

    for axis, cohort in zip(flat, cohort_list, strict=False):
        cohort_frame = frame.loc[frame["held_out_study"] == cohort]
        binned = _calibration_bins(cohort_frame, bins)
        colour = ALS_COLOR if cohort in als_studies else OTHER_COLOR
        marker = ALS_MARKER if cohort in als_studies else OTHER_MARKER
        axis.plot([0, 1], [0, 1], linestyle="--", linewidth=0.8, color="#9CA3AF", zorder=0)
        axis.plot(binned["predicted"], binned["observed"], color=colour, linewidth=1.0,
                  alpha=0.55, zorder=1)
        axis.scatter(binned["predicted"], binned["observed"],
                     s=6.0 + 0.9 * np.sqrt(binned["selections"]), color=colour, marker=marker,
                     edgecolors="white", linewidths=0.5, zorder=2)
        weights = cohort_frame["n"].to_numpy(dtype=float)
        departure = float(
            cohort_frame["correct"].sum() / weights.sum()
            - np.average(cohort_frame["predicted_probability"], weights=weights)
        )
        axis.set_title(_cohort_label(cohort), fontsize=9, color=LABEL_COLOR, pad=3)
        axis.text(0.04, 0.93, f"{departure:+.2f}", transform=axis.transAxes, fontsize=7.5,
                  color=LABEL_COLOR, va="top")
        axis.set_xlim(-0.04, 1.04)
        axis.set_ylim(-0.04, 1.04)
        axis.set_xticks([0, 0.5, 1.0])
        axis.set_yticks([0, 0.5, 1.0])
        axis.tick_params(labelsize=8)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    for axis in flat[len(cohort_list):]:
        axis.set_axis_off()

    fig.supxlabel("Estimated session accuracy (equal-count bin of the estimate)", fontsize=10)
    fig.supylabel("Observed session accuracy", fontsize=10)
    _save(fig, directory, filename)


def _build_cohort_type_relationship(
    records: pd.DataFrame, als_studies: tuple[str, ...], feature: str
) -> plt.Figure:
    """Return the descriptive cohort-type scatter, with no fitted line of any kind."""
    frame = records.dropna(subset=[feature]).copy()
    frame["accuracy"] = frame["correct"] / frame["n"]
    frame["is_als"] = frame["study"].isin(als_studies)

    fig, ax = plt.subplots(figsize=(6.0, 4.6))
    for is_als, colour, marker, name in (
        (False, OTHER_COLOR, OTHER_MARKER, "Other cohorts"),
        (True, ALS_COLOR, ALS_MARKER, "ALS cohorts"),
    ):
        subset = frame.loc[frame["is_als"] == is_als]
        if subset.empty:
            continue
        ax.scatter(subset[feature], subset["accuracy"], s=np.sqrt(subset["n"]) * 3.0,
                   color=colour, marker=marker, alpha=0.45, edgecolors="none",
                   label=f"{name} (n = {len(subset)})")

    ax.set_xlabel("Calibration discriminability (grouped cross-validated AUC)")
    ax.set_ylabel("Observed online session accuracy")
    ax.set_ylim(-0.03, 1.03)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    return fig


def render_cohort_type_relationship(
    records: pd.DataFrame, als_studies: tuple[str, ...], directory: Path,
    feature: str = "calibration_auc",
) -> None:
    """Plot calibration score against observed accuracy, marked by cohort type and unfitted."""
    _save(_build_cohort_type_relationship(records, als_studies, feature), directory,
          "figure_cohort_type_relationship")
