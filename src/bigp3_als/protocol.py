"""Recover the protocol descriptors the archive supports, and test them against heterogeneity.

Source studies differ in stimulus paradigm, matrix design, electrode type and stopping rule. Most
of these are not recorded as fields, but several are recoverable from the reconstructed trials and
the analysis records. If they track the cohort-specific calibration slope, then some of the apparent
transportability failure is an omitted-variable problem rather than an irreducible one.

Five of the eight descriptors are properties of the protocol proper.
`median_inter_selection_interval` is the time a cohort spent per selection, recovered from the
within-file spacing of the reconstructed selection timestamps. It is the time-domain signature of
the stopping rule: a cohort that averaged more stimulus repetitions before committing to a character
took longer over each one. `n_conditions` counts the distinct stimulus conditions a study
contributed, and is the closest the archive comes to naming paradigm variety;
`median_selections_per_record` reflects how long a copy-spelling record ran and how many of its
feedback outcomes survived reconstruction; `max_target_index` and `n_distinct_targets` are proxies
for the size of the speller matrix, bounded below by the alphabet actually spelled rather than equal
to the matrix, since a 36-cell grid in which only 24 characters were ever copied reports 24.

The other three, `mean_accuracy`, `accuracy_sd` and `fraction_at_ceiling`, are summaries of the same
outcomes the calibration slope is fitted to, and none of them is evidence about protocol. Outcome
dispersion enters the slope's own numerator, so a coefficient on `accuracy_sd` is partly arithmetic,
and `fraction_at_ceiling` governs whether a slope is identified at all, so a coefficient on it is a
statement about estimability rather than about a protocol difference. They are kept because a
reviewer will ask whether the cohorts with extreme slopes are simply the near-ceiling ones, and
because their circularity runs away from the null: it makes an association easier to find, so a null
in that group is the safe direction rather than a manufactured one. The descriptors are labelled by
kind in the output so that the two groups are never added together into one answer.

The primary test is a random-effects meta-regression. Each cohort slope is weighted by
1 / (its own variance + the residual between-cohort variance), the moderator is entered standardised
so that the coefficient reads as the change in slope per between-cohort standard deviation of the
descriptor, and inference uses the Knapp and Hartung adjustment on k - p degrees of freedom. It is
the estimator :func:`expanded.als_random_effects_meta_regression` already applies to cohort type,
with a continuous moderator in place of the ALS indicator, and it reports the share of the
between-cohort variance the moderator removes, which is the quantity the omitted-variable objection
is actually about. The rank correlation the brief specifies is retained beside it, because it
assumes no functional form and is unaffected by the weighting, but it is secondary: it ignores the
per-cohort standard errors, gives no effect size on the scale of the slope, and at 18 cohorts has
little power to separate a moderate association from none.

Both families are corrected across the eight descriptors by the Holm step-down procedure, which
controls the family-wise error rate under any dependence between the tests. That property matters
here rather than being a formality, because the descriptors are strongly rank-correlated with one
another and a correction assuming independence would not be valid. The two families are corrected
separately, because the meta-regression and the rank correlation are two analyses of the same eight
questions rather than sixteen independent ones, and pooling them would penalise the primary analysis
for the existence of its own sensitivity check. The family is a choice, and a choice that moves a p
value, so :func:`family_composition_sensitivity` reports every defensible definition of it rather
than leaving a reader to wonder which one was picked after seeing the answer.

Three further routines exist so that neither a null nor a positive result is read as more solid than
it is. :func:`joint_moderator_fit` enters several descriptors at once, which is the omitted-variable
objection in its strongest form and the only way to see which of two collinear descriptors is the
proxy for the other; :func:`leave_one_cohort_out` refits every descriptor 18 times to show how far
one cohort can move it; and :func:`stopping_rule_subgroups` splits the cohorts on whether their
selection interval was fixed or data-dependent, because under a dynamic stopping rule the interval
is partly a consequence of how quickly evidence accrued and so is not cleanly exogenous. At this
number of cohorts these tests have little power, so a descriptor that fails to reach the corrected
threshold has not been shown to be irrelevant.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

# These three are imported rather than reimplemented so that the moderator fit here is the same
# estimator the cohort-type moderator already uses. A near-copy would be free to drift from it, and
# _cohort_slopes in particular carries the guard this analysis depends on: the frozen per-cohort file
# stacks three standard-error specifications, so 18 cohorts arrive as 54 rows.
from bigp3_als.expanded import _cohort_slopes, _moment_tau_squared, _weighted_least_squares
from bigp3_als.heterogeneity import random_effects

COVARIATES = (
    "median_inter_selection_interval",
    "median_selections_per_record",
    "n_conditions",
    "max_target_index",
    "n_distinct_targets",
    "mean_accuracy",
    "accuracy_sd",
    "fraction_at_ceiling",
)

# Which descriptors describe the protocol, and which are summaries of the outcome the slope is
# fitted to. An association in the second group answers a different question from the one the
# omitted-variable objection asks.
DESCRIPTOR_KIND = {
    "median_inter_selection_interval": "protocol descriptor",
    "median_selections_per_record": "protocol descriptor",
    "n_conditions": "protocol descriptor",
    "max_target_index": "protocol descriptor",
    "n_distinct_targets": "protocol descriptor",
    "mean_accuracy": "outcome summary",
    "accuracy_sd": "outcome summary",
    "fraction_at_ceiling": "outcome summary",
}

PROTOCOL_DESCRIPTORS = tuple(
    name for name in COVARIATES if DESCRIPTOR_KIND[name] == "protocol descriptor"
)
OUTCOME_SUMMARIES = tuple(
    name for name in COVARIATES if DESCRIPTOR_KIND[name] == "outcome summary"
)

# A within-file selection interval is called fixed when its relative spread is below this. The
# archive's timestamps come from sample indices, so a fixed-repetition cohort arrives at 18.499993 s
# rather than 18.5 and an equality test would call every cohort data-dependent. The cut is not a
# tuning knob: across the 18 cohorts the relative spread is either at most 8.2e-16, which is
# floating-point dust, or at least 0.051, so any threshold between those two values gives the same
# split.
CONSTANT_INTERVAL_TOLERANCE = 1e-6


def _selection_timing(trials: pd.DataFrame) -> pd.DataFrame | None:
    """Recover per study how long a selection took, and whether that duration was fixed.

    The interval is the difference in `phase3_time_seconds` between consecutive selections **within
    one file**. Files are separate recordings whose de-identified timestamps do not share an origin,
    so a difference taken across a file boundary is not a measurement of anything and can even be
    negative. The per-file medians are then combined by a second median rather than pooled, so that
    a long file does not outvote a short one.

    This is the closest the archive comes to recording the stopping rule, which it does not document
    for any source study: a cohort that averaged more stimulus repetitions before committing to a
    character spent longer on each one. `constant_within_file_interval` separates the cohorts whose
    interval never varied inside a file, which is a fixed number of repetitions, from those whose
    interval moved from selection to selection, which is a data-dependent rule.

    Timing is taken over every reconstructed trial rather than only the eligible ones, because the
    pacing of a recording is a property of the protocol and does not depend on which of its
    selections later survived eligibility screening.
    """
    required = {"relative_path", "trial_number", "phase3_time_seconds"}
    if not required.issubset(trials.columns):
        return None
    ordered = trials.sort_values(["relative_path", "trial_number"])
    gaps = ordered.assign(
        gap=ordered.groupby("relative_path")["phase3_time_seconds"].diff()
    ).dropna(subset=["gap"])
    if gaps.empty:
        return None

    per_file = gaps.groupby(["study", "relative_path"])["gap"]
    spread = per_file.agg(
        lambda values: float(
            (values.quantile(0.75) - values.quantile(0.25)) / values.median()
        )
        if values.median()
        else float("nan")
    )
    return pd.DataFrame({
        "median_inter_selection_interval": per_file.median().groupby("study").median(),
        "constant_within_file_interval": spread.groupby("study").median()
        <= CONSTANT_INTERVAL_TOLERANCE,
    }).reset_index()


def _matrix_size_proxies(trials: pd.DataFrame) -> pd.DataFrame | None:
    """Recover per study what can be said about the size of the speller matrix.

    The archive records no matrix dimension. The index of the intended character is recorded, so its
    maximum and its number of distinct values bound the alphabet from below. Neither equals the
    matrix: a cohort that copied only 24 characters from a 36-cell grid reports 24, and one study
    indexes its targets from 10 rather than 1, which inflates the maximum without widening the
    alphabet. Both are reported so that the two failure modes do not hide in one number.
    """
    if "target" not in trials.columns:
        return None
    targets = trials.dropna(subset=["target"])
    if targets.empty:
        return None
    return (
        targets.groupby("study")["target"]
        .agg(max_target_index="max", n_distinct_targets="nunique")
        .reset_index()
    )


def protocol_covariates(trials: pd.DataFrame, records: pd.DataFrame) -> pd.DataFrame:
    """Summarise per study the protocol descriptors the archive supports.

    Conditions are counted over eligible trials only, so a study whose reconstruction yielded no
    usable outcome contributes no row and cannot appear in the association test with an accuracy
    it never supplied. The timing and matrix descriptors are attached to that row set by a left
    join, so computing them over all reconstructed trials cannot reintroduce such a study.
    """
    eligible = trials.loc[trials["eligible"]] if "eligible" in trials else trials
    conditions = (
        eligible.groupby("study")["condition"]
        .agg(n_conditions="nunique", condition_list=lambda values: ",".join(sorted(set(values))))
        .reset_index()
    )
    frame = records.copy()
    frame["accuracy"] = frame["correct"] / frame["n"]
    outcome = (
        frame.groupby("study")
        .agg(
            n_records=("accuracy", "size"),
            mean_accuracy=("accuracy", "mean"),
            accuracy_sd=("accuracy", "std"),
            fraction_at_ceiling=("accuracy", lambda s: float((s >= 1.0).mean())),
            median_selections_per_record=("n", "median"),
        )
        .reset_index()
    )
    covariates = conditions.merge(outcome, on="study", how="outer")
    for extra in (_selection_timing(trials), _matrix_size_proxies(trials)):
        if extra is not None:
            covariates = covariates.merge(extra, on="study", how="left")
    return covariates


def _holm(p_values: np.ndarray) -> np.ndarray:
    """Holm step-down family-wise adjusted p values.

    The family is the tests that were actually performed, so a descriptor whose p value is missing,
    because its fit was not identified, neither receives an adjusted value nor inflates the
    multiplier for the others.
    """
    raw = np.asarray(p_values, dtype=float)
    adjusted = np.full(raw.shape, np.nan)
    performed = np.flatnonzero(np.isfinite(raw))
    if performed.size == 0:
        return adjusted
    order = performed[np.argsort(raw[performed])]
    running = 0.0
    for rank, position in enumerate(order):
        running = max(running, (len(order) - rank) * raw[position])
        adjusted[position] = min(1.0, running)
    return adjusted


def _standardise(frame: pd.DataFrame, names: list[str]) -> tuple[np.ndarray | None, str]:
    """Centre each moderator and divide by its between-cohort standard deviation.

    The coefficients then read as the change in calibration slope per standard deviation of the
    descriptor and are comparable across descriptors on different scales. The fit itself, and every
    p value and variance share it reports, is invariant to this rescaling. A descriptor that does
    not vary across cohorts cannot be standardised, and it stops the fit with a stated reason rather
    than being dropped from it silently.
    """
    columns = []
    for name in names:
        values = frame[name].to_numpy(dtype=float)
        spread = float(np.std(values, ddof=1))
        if not np.isfinite(spread) or spread <= 0:
            return None, f"{name} does not vary across the cohorts fitted"
        columns.append((values - float(np.mean(values))) / spread)
    return np.column_stack(columns), ""


def _meta_regression(
    slope: np.ndarray, slope_se: np.ndarray, moderators: np.ndarray | None, reason: str = ""
) -> dict[str, object]:
    """Fit the random-effects meta-regression of cohort slope on one or more moderators.

    `between_cohort_variance_explained` compares the residual between-cohort variance with the
    moderators against the same estimator with them removed, on exactly the cohorts the moderated
    fit used, so the two are never computed over different sets. It is clipped below at zero: the
    moment estimator can return a larger residual variance with a moderator than without one, which
    means the moderator accounted for none of it rather than a negative share. With several
    moderators it is optimistic in the same way an unadjusted R-squared is.

    The joint p value is an F test of all moderators together, scaled by the Knapp and Hartung
    residual mean square. With a single moderator it is the square of the reported t test and gives
    the same p value.
    """
    # The count is the cohorts the fit had available, never zero merely because the fit failed:
    # zero cohorts fitted beside zero dropped would be self-contradictory, and `unidentified_reason`
    # is what distinguishes a fit that was not attempted from one that had nothing to work with.
    n_studies = len(slope)
    n_moderators = 0 if moderators is None else moderators.shape[1]
    empty: dict[str, object] = {
        "n_studies_meta": float(n_studies),
        "unidentified_reason": reason,
        "coefficients_per_sd": [float("nan")] * max(n_moderators, 1),
        "coefficient_se": [float("nan")] * max(n_moderators, 1),
        "tau_squared": float("nan"),
        "tau_squared_without_moderators": float("nan"),
        "between_cohort_variance_explained": float("nan"),
        "f_statistic": float("nan"),
        "degrees_of_freedom": float("nan"),
        "joint_p_value": float("nan"),
        "t_statistics": [float("nan")] * max(n_moderators, 1),
        "p_values": [float("nan")] * max(n_moderators, 1),
        "ci_low": [float("nan")] * max(n_moderators, 1),
        "ci_high": [float("nan")] * max(n_moderators, 1),
    }
    if moderators is None:
        return empty
    if n_studies - n_moderators - 1 < 2:
        # Fewer than two residual degrees of freedom leaves the Knapp and Hartung scale resting on
        # almost nothing, and a p value from it would be theatre.
        return {**empty, "unidentified_reason":
                f"{n_studies} cohorts leave too few residual degrees of freedom for "
                f"{n_moderators} moderators"}

    y = np.asarray(slope, dtype=float)
    variance = np.asarray(slope_se, dtype=float) ** 2
    design = np.column_stack([np.ones(n_studies), moderators])
    if np.linalg.matrix_rank(design) < design.shape[1]:
        # Two descriptors that agree exactly across cohorts, or one that repeats the intercept,
        # leave the coefficients unidentified. The normal equations would still return numbers.
        return {**empty, "unidentified_reason": "the moderators are collinear"}

    tau_squared = _moment_tau_squared(design, y, variance)
    unconditional = _moment_tau_squared(np.ones((n_studies, 1)), y, variance)
    weight = 1.0 / (variance + tau_squared)
    coefficients, covariance, residual = _weighted_least_squares(design, y, weight)

    degrees = n_studies - design.shape[1]
    scale = float((weight * residual**2).sum()) / degrees
    estimates = coefficients[1:]
    # A moderator that reproduces every cohort slope leaves no residual to judge it by. The
    # residuals do not come back as exactly zero, they come back as floating-point dust, and the
    # Knapp and Hartung scale built from them would be around 1e-30 where the model expects a
    # quantity near one. Taken at face value it would return a standard error of about 1e-15 and a
    # p value of zero, so the fit is reported without inference instead.
    if not np.isfinite(scale) or scale <= 1e-10:
        return {
            **empty,
            "unidentified_reason": "the moderators reproduce every cohort slope, leaving no residual",
            "coefficients_per_sd": [float(value) for value in estimates],
            "tau_squared": tau_squared,
            "tau_squared_without_moderators": unconditional,
            "between_cohort_variance_explained": float(max(0.0, 1.0 - tau_squared / unconditional))
            if unconditional > 0
            else float("nan"),
            "degrees_of_freedom": float(degrees),
        }

    moderator_covariance = covariance[1:, 1:] * scale
    standard_errors = np.sqrt(np.diag(moderator_covariance))
    critical = float(stats.t.ppf(0.975, df=degrees))
    with np.errstate(divide="ignore", invalid="ignore"):
        statistics = np.where(standard_errors > 0, estimates / standard_errors, np.nan)
    f_statistic = float(
        estimates @ np.linalg.inv(moderator_covariance) @ estimates / n_moderators
    )
    return {
        "n_studies_meta": float(n_studies),
        "unidentified_reason": "",
        "coefficients_per_sd": [float(value) for value in estimates],
        "coefficient_se": [float(value) for value in standard_errors],
        "tau_squared": tau_squared,
        "tau_squared_without_moderators": unconditional,
        "between_cohort_variance_explained": float(max(0.0, 1.0 - tau_squared / unconditional))
        if unconditional > 0
        else float("nan"),
        "f_statistic": f_statistic,
        "degrees_of_freedom": float(degrees),
        "joint_p_value": float(stats.f.sf(f_statistic, n_moderators, degrees)),
        "t_statistics": [float(value) for value in statistics],
        "p_values": [float(2 * stats.t.sf(abs(value), df=degrees)) for value in statistics],
        "ci_low": [float(value) for value in estimates - critical * standard_errors],
        "ci_high": [float(value) for value in estimates + critical * standard_errors],
    }


def _merge_slopes(
    covariates: pd.DataFrame, calibration: pd.DataFrame, se_method: str
) -> pd.DataFrame:
    """Attach one calibration slope per cohort to the covariate table."""
    slopes = _cohort_slopes(calibration, se_method)
    columns = ["held_out_study", "slope"] + (["slope_se"] if "slope_se" in slopes else [])
    return covariates.merge(
        slopes[columns].rename(columns={"held_out_study": "study"}), on="study"
    )


def _usable_for_meta(pair: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Split a merged frame into the cohorts a precision-weighted fit can use, and the rest."""
    if "slope_se" not in pair:
        return pair.iloc[0:0], sorted(pair["study"].astype(str))
    standard_error = pd.to_numeric(pair["slope_se"], errors="coerce")
    usable = standard_error.notna() & (standard_error > 0)
    return pair.loc[usable], sorted(pair.loc[~usable, "study"].astype(str))


def _fit_moderators(fit: pd.DataFrame, names: list[str]) -> dict[str, object]:
    """Standardise the named moderators on the cohorts that can be fitted, and run the regression."""
    if not len(fit):
        return _meta_regression(np.empty(0), np.empty(0), None, "no cohort carries a usable slope")
    moderators, reason = _standardise(fit, names)
    return _meta_regression(
        fit["slope"].to_numpy(dtype=float),
        fit["slope_se"].to_numpy(dtype=float) if "slope_se" in fit else np.full(len(fit), np.nan),
        moderators,
        reason,
    )


def explains_heterogeneity(
    covariates: pd.DataFrame, calibration: pd.DataFrame, se_method: str = "cluster"
) -> pd.DataFrame:
    """Test each protocol descriptor against the cohort-specific calibration slope.

    The primary column is `meta_p_value_holm`, from the precision-weighted meta-regression;
    `spearman_rho` and `p_value_holm` report the rank correlation the same descriptor gives without
    the weights. Cohorts that carry no usable standard error are named in `dropped_labels` rather
    than silently excluded, because a descriptor tested on 16 cohorts and one tested on 18 are not
    the same test.
    """
    merged = _merge_slopes(covariates, calibration, se_method)

    rows: list[dict[str, object]] = []
    for name in COVARIATES:
        if name not in merged:
            continue
        wanted = ["study", name, "slope"] + (["slope_se"] if "slope_se" in merged else [])
        pair = merged[wanted].dropna(subset=[name, "slope"])
        row: dict[str, object] = {
            "covariate": name,
            "kind": DESCRIPTOR_KIND.get(name, "unclassified"),
            "n_studies": len(pair),
            "spearman_rho": float("nan"),
            "p_value": float("nan"),
        }
        # A descriptor that takes one value across cohorts has no rank correlation either, and
        # scipy answers that question with a warning and a NaN rather than an error.
        if len(pair) >= 3 and pair[name].nunique() > 1:
            rho, p_value = stats.spearmanr(pair[name], pair["slope"])
            row["spearman_rho"] = float(rho)
            row["p_value"] = float(p_value)

        fit, dropped = _usable_for_meta(pair)
        row["dropped_labels"] = ",".join(dropped)
        row["n_dropped"] = len(dropped)
        result = _fit_moderators(fit, [name])
        row["n_studies_meta"] = result["n_studies_meta"]
        row["unidentified_reason"] = result["unidentified_reason"]
        row["coefficient_per_sd"] = result["coefficients_per_sd"][0]
        row["coefficient_se"] = result["coefficient_se"][0]
        row["ci_low"] = result["ci_low"][0]
        row["ci_high"] = result["ci_high"][0]
        row["t_statistic"] = result["t_statistics"][0]
        row["degrees_of_freedom"] = result["degrees_of_freedom"]
        row["meta_p_value"] = result["p_values"][0]
        row["tau_squared"] = result["tau_squared"]
        row["tau_squared_without_moderator"] = result["tau_squared_without_moderators"]
        row["between_cohort_variance_explained"] = result["between_cohort_variance_explained"]
        row["se_method"] = se_method
        rows.append(row)

    table = pd.DataFrame(rows)
    if len(table):
        table["p_value_holm"] = _holm(table["p_value"].to_numpy(dtype=float))
        table["meta_p_value_holm"] = _holm(table["meta_p_value"].to_numpy(dtype=float))
    return table


def joint_moderator_fit(
    covariates: pd.DataFrame,
    calibration: pd.DataFrame,
    moderators: tuple[str, ...] = PROTOCOL_DESCRIPTORS,
    se_method: str = "cluster",
) -> dict[str, object]:
    """Enter several descriptors at once, which is the omitted-variable objection at full strength.

    Testing descriptors one at a time answers whether any single one accounts for the spread. It
    does not answer whether they account for it together, which is what a reviewer proposing
    omitted-variable bias is claiming. The descriptors are collinear, so a joint fit can leave less
    of the variance accounted for than the better single moderator did, and with five moderators on
    18 cohorts the fit is close to the limit of what the data identify. The joint F test is reported
    in preference to the individual coefficients for that reason.
    """
    merged = _merge_slopes(covariates, calibration, se_method)
    # A caller's covariate table need not carry every descriptor this module knows about, and a
    # missing column is not the same as a moderator worth nothing, so the fit reports which
    # moderators it actually entered rather than failing or quietly counting an absent one.
    present = [name for name in moderators if name in merged]
    if not present:
        return {
            "moderators": [],
            "n_studies": 0,
            "n_dropped": 0,
            "dropped_labels": [],
            "se_method": se_method,
            **_meta_regression(np.empty(0), np.empty(0), None,
                               "the covariate table carries none of these moderators"),
        }
    wanted = ["study", "slope", *present] + (["slope_se"] if "slope_se" in merged else [])
    pair = merged[wanted].dropna(subset=["slope", *present])
    fit, dropped = _usable_for_meta(pair)
    result = _fit_moderators(fit, present)
    return {
        "moderators": present,
        "n_studies": len(pair),
        "n_dropped": len(dropped),
        "dropped_labels": dropped,
        "se_method": se_method,
        **result,
    }


def leave_one_cohort_out(
    covariates: pd.DataFrame, calibration: pd.DataFrame, se_method: str = "cluster"
) -> pd.DataFrame:
    """Refit every descriptor with each cohort in turn withheld, and report how far it moves.

    A descriptor that clears no threshold at 18 cohorts has not been shown to be irrelevant, and one
    that clears a threshold may owe it to a single cohort. Both directions are recorded here: the
    range of the uncorrected p value and of the variance share across the refits, and the cohort
    whose removal produces each extreme. The p values are uncorrected because this is a stability
    check on the primary test rather than a second family of hypotheses.
    """
    rows: list[dict[str, object]] = []
    for withheld in sorted(covariates["study"].astype(str)):
        refit = explains_heterogeneity(
            covariates.loc[covariates["study"].astype(str) != withheld], calibration, se_method
        )
        for _, row in refit.iterrows():
            rows.append(
                {
                    "covariate": row["covariate"],
                    "withheld": withheld,
                    "n_studies_meta": row["n_studies_meta"],
                    "meta_p_value": row["meta_p_value"],
                    "between_cohort_variance_explained": row["between_cohort_variance_explained"],
                    "p_value": row["p_value"],
                }
            )
    refits = pd.DataFrame(rows)
    if refits.empty:
        return refits

    def _withheld_at(group: pd.DataFrame, column: str, extreme: str) -> str:
        """Name the cohort at an extreme, or nothing when no refit produced a value at all."""
        values = group[column]
        if not values.notna().any():
            return ""
        position = values.idxmin() if extreme == "min" else values.idxmax()
        return str(group.loc[position, "withheld"])

    summaries: list[dict[str, object]] = []
    for name, group in refits.groupby("covariate", sort=False):
        summaries.append(
            {
                "covariate": name,
                "n_refits": len(group),
                "meta_p_value_min": float(group["meta_p_value"].min()),
                "meta_p_value_max": float(group["meta_p_value"].max()),
                "withheld_at_min_meta_p": _withheld_at(group, "meta_p_value", "min"),
                "variance_explained_min": float(group["between_cohort_variance_explained"].min()),
                "variance_explained_max": float(group["between_cohort_variance_explained"].max()),
                "withheld_at_max_variance_explained": _withheld_at(
                    group, "between_cohort_variance_explained", "max"
                ),
                "spearman_p_value_min": float(group["p_value"].min()),
                "spearman_p_value_max": float(group["p_value"].max()),
            }
        )
    return pd.DataFrame(summaries)


def family_composition_sensitivity(descriptors: pd.DataFrame) -> list[dict[str, object]]:
    """Recompute the Holm correction under every defensible definition of the family.

    The correction divides by the number of tests, so the family is a choice that moves a p value,
    and here it moves it in the direction the paper would prefer: only some of these descriptors
    bear on the omitted-variable objection, and correcting those few by the count of all of them
    makes a null easier to reach. Reporting each definition is cheaper than defending one.

    The pooled row is the least favourable definition, treating the meta-regression and the rank
    correlation as one family of twice the size, and is included so that the separation of the two
    families cannot be mistaken for the thing carrying a result.
    """
    families: list[dict[str, object]] = []
    subsets = [
        ("all descriptors", descriptors),
        ("protocol descriptors", descriptors.loc[descriptors["kind"] == "protocol descriptor"]),
        ("outcome summaries", descriptors.loc[descriptors["kind"] == "outcome summary"]),
    ]
    for label, subset in subsets:
        if subset.empty:
            continue
        names = list(subset["covariate"])
        families.append({
            "family": label,
            "n_tests": len(subset),
            "meta_p_holm": dict(
                zip(names, _holm(subset["meta_p_value"].to_numpy(dtype=float)))
            ),
            "spearman_p_holm": dict(zip(names, _holm(subset["p_value"].to_numpy(dtype=float)))),
        })
    pooled = np.concatenate([
        descriptors["meta_p_value"].to_numpy(dtype=float),
        descriptors["p_value"].to_numpy(dtype=float),
    ])
    adjusted = _holm(pooled)
    names = list(descriptors["covariate"])
    families.append({
        "family": "both analyses pooled",
        "n_tests": 2 * len(descriptors),
        "meta_p_holm": dict(zip(names, adjusted[: len(names)])),
        "spearman_p_holm": dict(zip(names, adjusted[len(names) :])),
    })
    return families


def stopping_rule_subgroups(
    covariates: pd.DataFrame,
    calibration: pd.DataFrame,
    se_method: str = "cluster",
    moderator: str = "median_inter_selection_interval",
) -> list[dict[str, object]]:
    """Refit the selection interval separately in fixed-interval and data-dependent cohorts.

    The interval is built from timestamps and never touches whether a selection was correct, so it
    is less circular than the outcome summaries. It is not fully exogenous either: where the stopping
    rule was data-dependent, a session in which evidence accrued quickly ends sooner, so part of the
    interval is a consequence of the recording rather than a setting chosen before it. Splitting on
    `constant_within_file_interval` puts the cohorts whose interval was fixed by design on one side
    of that objection, where the descriptor is a pure protocol setting.

    Each subgroup is roughly half the cohorts, so neither has the power of the pooled fit, and the
    agreement of the two in sign is what the split can support rather than either p value.
    """
    split = "constant_within_file_interval"
    if split not in covariates or moderator not in covariates:
        return []
    merged = _merge_slopes(covariates, calibration, se_method)
    rows: list[dict[str, object]] = []
    for label, selected in (
        ("constant interval", merged[split].astype(bool)),
        ("variable interval", ~merged[split].astype(bool)),
    ):
        subset = merged.loc[selected, ["study", moderator, "slope"]
                            + (["slope_se"] if "slope_se" in merged else [])]
        subset = subset.dropna(subset=[moderator, "slope"])
        fit, dropped = _usable_for_meta(subset)
        rows.append({
            "subgroup": label,
            "moderator": moderator,
            "cohorts": sorted(subset["study"].astype(str)),
            "n_dropped": len(dropped),
            "dropped_labels": dropped,
            "se_method": se_method,
            **_fit_moderators(fit, [moderator]),
        })
    return rows


def functional_form_sensitivity(
    covariates: pd.DataFrame,
    calibration: pd.DataFrame,
    moderator: str = "median_inter_selection_interval",
    se_method: str = "cluster",
) -> dict[str, object]:
    """Refit one descriptor on the log scale, since a duration has no reason to act linearly.

    A selection interval runs from about 7 to 50 seconds across these cohorts, and the difference
    between 7 and 14 seconds is a doubling of the stimulus repetitions while the difference between
    43 and 50 is not. This is a sensitivity on the functional form of one descriptor, not a further
    hypothesis, so it is not entered into the multiplicity correction; the rank correlation is
    unchanged by it, being invariant to any monotone transformation.
    """
    if moderator not in covariates:
        return {}
    merged = _merge_slopes(covariates, calibration, se_method)
    columns = ["study", moderator, "slope"] + (["slope_se"] if "slope_se" in merged else [])
    pair = merged[columns].dropna(subset=[moderator, "slope"])
    pair = pair.loc[pair[moderator] > 0]
    fit, dropped = _usable_for_meta(pair)
    transformed = fit.assign(**{moderator: np.log(fit[moderator].to_numpy(dtype=float))})
    return {
        "moderator": f"log({moderator})",
        "n_dropped": len(dropped),
        "dropped_labels": dropped,
        "se_method": se_method,
        **_fit_moderators(transformed, [moderator]),
    }


def protocol_report(
    covariates: pd.DataFrame, calibration: pd.DataFrame, se_method: str = "cluster"
) -> dict[str, object]:
    """Bundle the descriptor tests with the unmoderated heterogeneity they are meant to explain.

    The baseline block is the same random-effects summary the heterogeneity analysis reports, and it
    carries `n_dropped` and `dropped_labels`, so a reader can see how many cohorts the pooling
    actually used rather than assuming every cohort in the archive was fitted.
    """
    slopes = _cohort_slopes(calibration, se_method)
    baseline = random_effects(
        slopes.set_index("held_out_study")["slope"], slopes.set_index("held_out_study")["slope_se"]
    )
    descriptors = explains_heterogeneity(covariates, calibration, se_method)
    return {
        "quantity": f"cohort calibration slope, {se_method}",
        "se_method": se_method,
        "n_cohorts_in_calibration": int(len(slopes)),
        "n_cohorts_with_covariates": int(descriptors["n_studies"].max()) if len(descriptors) else 0,
        "primary_analysis": "random-effects meta-regression, moderator standardised, "
        "Knapp and Hartung adjusted",
        "secondary_analysis": "Spearman rank correlation",
        "multiple_testing": f"Holm step-down across {len(descriptors)} descriptors, "
        "applied separately within each analysis; see family_composition for every other "
        "definition of the family",
        "baseline_heterogeneity": {
            key: (list(value) if isinstance(value, tuple) else value)
            for key, value in baseline.items()
        },
        "descriptors": descriptors.to_dict(orient="records"),
        "joint_fits": [
            joint_moderator_fit(covariates, calibration, moderators, se_method)
            for moderators in (
                PROTOCOL_DESCRIPTORS,
                COVARIATES,
                # The two pairs that decide which of a collinear pair is the proxy for the other.
                ("median_inter_selection_interval", "fraction_at_ceiling"),
                ("median_inter_selection_interval", "median_selections_per_record"),
            )
        ],
        "family_composition": family_composition_sensitivity(descriptors),
        "stopping_rule_subgroups": stopping_rule_subgroups(covariates, calibration, se_method),
        "functional_form_sensitivity": functional_form_sensitivity(
            covariates, calibration, se_method=se_method
        ),
        "leave_one_cohort_out": leave_one_cohort_out(covariates, calibration, se_method).to_dict(
            orient="records"
        ),
    }
