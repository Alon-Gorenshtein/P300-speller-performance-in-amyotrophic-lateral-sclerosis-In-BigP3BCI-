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

``render_recalibration_curve`` carries the cost of local recalibration, not its benefit: nowhere on
the balanced ladder does the paired improvement in mean absolute error clear zero, and the smallest
sizes are significantly worse under the slope-and-intercept refit. There is no crossing point, so the
figure plots the improvement itself, with its interval, against the null it must clear, rather than a
raw error level against a reference line that would invite a reader to look for one. The minimum
detectable effect is drawn alongside so "nothing was detected" and "this is how large an effect this
sample size could have detected" are read off the same axis.

``render_alignment_transport`` carries whether standard EEG re-alignment repairs the transport
failure. It does not: every alignment variant leaves tau close to the primary score's, and the two
that move it furthest (cohort z-score, cohort rank) do so while raising pooled error, which is the
opposite of a repair. I-squared is not drawn, because the manuscript may not lean on it, and a figure
that showed it would invite a reader to.
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

# The balanced-ladder local-participant counts. Not evenly spaced (the design coarsens once
# selections grow large enough that a fixed multiplicative step in cohorts contributing is no
# longer available), so they are declared rather than inferred from whatever a given frame contains.
LADDER_ORDER = (1, 2, 3, 4, 6, 8, 12, 14, 16)
METHOD_STYLE = {
    "intercept_only": {"color": OTHER_COLOR, "marker": OTHER_MARKER, "label": "Intercept-only refit"},
    "intercept_and_slope": {
        "color": ALS_COLOR, "marker": ALS_MARKER, "label": "Intercept-and-slope refit"
    },
}

# Left-to-right reading order the brief specifies: the primary score, then the four EEG
# re-alignment variants, then the two nonlinear re-scorings.
ROLE_ORDER = ("primary", "alignment", "nonlinear")
ROLE_STYLE = {
    "primary": {"color": ALS_COLOR, "hatch": None, "label": "Primary score"},
    "alignment": {"color": OTHER_COLOR, "hatch": "//", "label": "EEG re-alignment"},
    "nonlinear": {"color": BAND_COLOR, "hatch": "xx", "label": "Nonlinear re-scoring"},
}
# Arm names as written in alignment_transport.csv, relabelled for the axis. The mapping is display
# only; the arm column itself, not this label, is what a reader would need to trace a row back to
# the table.
ARM_LABELS = {
    "calibration_auc": "Primary (no alignment)",
    "calibration_auc_ea_session": "Euclidean alignment, within session",
    "calibration_auc_ea_cohort": "Euclidean alignment, within cohort",
    "calibration_auc_cohort_z": "Cohort z-score standardisation",
    "calibration_auc_cohort_rank": "Cohort rank standardisation",
    "calibration_auc_rbf": "RBF-kernel nonlinear score",
    "calibration_auc_gbm": "Gradient-boosted nonlinear score",
}


def _arm_label(arm: str) -> str:
    return ARM_LABELS.get(arm, arm)


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
    ax.axvline(0.0, color=LABEL_COLOR, linewidth=1.0, zorder=3)
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
            f"{label}\ntau = {block['tau']:.2f}, I² = {block['i_squared']:.0f}%"
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


def render_recalibration_curve(summary: pd.DataFrame, directory: Path) -> None:
    """Plot the paired improvement in mean absolute error from local recalibration, against zero.

    ``summary`` is the balanced-ladder recalibration table (``recalibration_summary_balanced.csv``):
    the cohort set contributing to each rung is held fixed at 6, so the curve is not confounded by a
    changing, progressively easier cohort mix as the ladder thins. Because that set is fixed by
    construction, the contributing-cohort annotation on this figure reads 6 at every size; that
    constancy is itself what the annotation is there to show, not evidence the analysis failed to
    thin anything.
    """
    required = {
        "method", "n_local_participants", "cohort_mean_improvement", "cohort_improvement_ci_low",
        "cohort_improvement_ci_high", "mae_minimum_detectable_effect", "n_cohorts_contributing",
        "median_local_selections",
    }
    require_columns(summary, required)

    # The ladder is not evenly spaced in participants (1, 2, 3, 4, 6, 8, 12, 14, 16), so plotting it
    # on its own numeric scale, log or linear, crowds the three largest rungs into a few pixels and
    # collides their tick annotations. Categorical positions, one slot per rung actually present in
    # the data, give every rung equal room regardless of its value.
    present = sorted(set(summary["n_local_participants"]))
    # A size outside the declared ladder has no slot and .map(slot) below would turn it into NaN,
    # which matplotlib simply omits rather than plots or errors on. A row silently missing from a
    # figure is the exact failure this repository's figure script exists to prevent, so this must
    # raise rather than render an incomplete plot that looks complete.
    unlisted = sorted(set(present) - set(LADDER_ORDER))
    if unlisted:
        raise ValueError(
            f"n_local_participants value(s) not in LADDER_ORDER, would be dropped silently: {unlisted}"
        )
    ticks = [n for n in LADDER_ORDER if n in present]
    slot = {n: index for index, n in enumerate(ticks)}

    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    ax.axhline(0.0, color=LABEL_COLOR, linewidth=1.0, zorder=1, label="No improvement")

    # A small additive offset in slot units so the two methods' error bars at a shared rung do not
    # sit exactly on top of one another.
    dodge = {"intercept_only": -0.09, "intercept_and_slope": 0.09}
    selections_by_n: dict[float, float] = {}
    contributing_by_n: dict[float, set[int]] = {}

    for method in sorted(summary["method"].unique()):
        style = METHOD_STYLE[method]
        frame = summary.loc[summary["method"] == method].sort_values("n_local_participants")
        x = frame["n_local_participants"].map(slot).to_numpy(dtype=float) + dodge.get(method, 0.0)
        y = frame["cohort_mean_improvement"].to_numpy(dtype=float)
        low = frame["cohort_improvement_ci_low"].to_numpy(dtype=float)
        high = frame["cohort_improvement_ci_high"].to_numpy(dtype=float)
        mde = frame["mae_minimum_detectable_effect"].to_numpy(dtype=float)

        ax.plot(x, y, color=style["color"], linewidth=1.2, alpha=0.9, zorder=2)
        ax.errorbar(
            x, y, yerr=[y - low, high - y], fmt=style["marker"], ms=6.5, mfc=style["color"],
            mec="white", mew=0.7, color=style["color"], ecolor=style["color"], elinewidth=1.3,
            capsize=3, linestyle="none", zorder=3, label=style["label"],
        )
        # The envelope is drawn dashed, not filled, so it reads as a detection threshold rather than
        # competing visually with the 95% interval already drawn on the observed points.
        ax.plot(x, mde, color=style["color"], linestyle="--", linewidth=1.0, alpha=0.55, zorder=1)
        ax.plot(x, -mde, color=style["color"], linestyle="--", linewidth=1.0, alpha=0.55, zorder=1)

        for n, count, sel in zip(
            frame["n_local_participants"], frame["n_cohorts_contributing"],
            frame["median_local_selections"], strict=True,
        ):
            contributing_by_n.setdefault(n, set()).add(int(count))
            selections_by_n[n] = sel

    ax.set_xticks(range(len(ticks)))
    tick_labels = [
        f"{n}\n{int(selections_by_n[n])} sel\n"
        f"{'/'.join(str(c) for c in sorted(contributing_by_n[n]))} cohorts"
        for n in ticks
    ]
    ax.set_xticklabels(tick_labels, fontsize=8)
    ax.set_xlim(-0.5, len(ticks) - 0.5)

    ax.set_xlabel("Local participants used for recalibration")
    ax.set_ylabel("MAE improvement over the transported mapping\n(cohort mean, 95% CI)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    _save(fig, directory, "figure_recalibration_curve")


def render_alignment_transport(transport: pd.DataFrame, directory: Path) -> None:
    """Plot each re-alignment arm's calibration tau against the primary arm's own value.

    ``transport`` is the per-arm alignment-transport table (``alignment_transport.csv``): the primary
    calibration score, four standard EEG re-alignment variants of it, and two nonlinear
    re-scorings, each pooled the same way. Tau carries the comparison; I-squared is never drawn
    here, matching the standing constraint not to lean on it anywhere in the manuscript. The pooled
    mean absolute error is annotated on every row because an arm that moves tau without lowering
    error, or raises error while moving tau, has not repaired anything.
    """
    require_columns(transport, {"arm", "role", "mae", "slope_tau", "intercept_tau"})
    frame = transport.copy()
    unexpected = sorted(set(frame["role"]) - set(ROLE_ORDER))
    if unexpected:
        raise ValueError(f"unexpected arm role(s): {unexpected}")
    frame["role"] = pd.Categorical(frame["role"], categories=ROLE_ORDER, ordered=True)
    frame = frame.sort_values("role", kind="mergesort").reset_index(drop=True)

    primary_rows = frame.loc[frame["role"] == "primary"]
    if len(primary_rows) != 1:
        raise ValueError(f"expected exactly one primary arm, found {len(primary_rows)}")
    primary = primary_rows.iloc[0]

    positions = np.arange(len(frame))
    colors = [ROLE_STYLE[str(role)]["color"] for role in frame["role"]]
    hatches = [ROLE_STYLE[str(role)]["hatch"] for role in frame["role"]]

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6), sharey=True, constrained_layout=True)
    panels = (
        (axes[0], "intercept_tau", float(primary["intercept_tau"]), "Calibration intercept tau (between-cohort)"),
        (axes[1], "slope_tau", float(primary["slope_tau"]), "Calibration slope tau (between-cohort)"),
    )
    for axis, quantity, reference, title in panels:
        values = frame[quantity].to_numpy(dtype=float)
        bars = axis.barh(positions, values, color=colors, height=0.6, edgecolor="white",
                          linewidth=0.6, zorder=2)
        for bar, hatch in zip(bars, hatches, strict=True):
            if hatch:
                bar.set_hatch(hatch)
        axis.axvline(reference, color=LABEL_COLOR, linestyle="--", linewidth=1.1, zorder=3)
        span = float(values.max())
        for position, value, mae in zip(positions, values, frame["mae"], strict=True):
            axis.text(value + 0.03 * span, position, f"MAE {mae:.3f}", va="center", fontsize=8,
                      color=LABEL_COLOR)
        axis.set_xlabel(title)
        axis.set_xlim(0, span * 1.34)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    axes[0].set_yticks(positions)
    axes[0].set_yticklabels([_arm_label(arm) for arm in frame["arm"]], fontsize=9)
    axes[0].invert_yaxis()
    for axis, letter in zip(axes, "ab", strict=True):
        axis.text(-0.34, 1.04, letter, transform=axis.transAxes, fontsize=14, fontweight="bold",
                  color=LABEL_COLOR)

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=ROLE_STYLE[role]["color"], edgecolor="white",
                      hatch=ROLE_STYLE[role]["hatch"], label=ROLE_STYLE[role]["label"])
        for role in ROLE_ORDER
    ]
    handles.append(plt.Line2D([], [], color=LABEL_COLOR, linestyle="--", label="Primary arm's own value"))
    fig.legend(handles=handles, loc="outside lower center", ncol=4, frameon=False, fontsize=9)
    _save(fig, directory, "figure_alignment_transport")
