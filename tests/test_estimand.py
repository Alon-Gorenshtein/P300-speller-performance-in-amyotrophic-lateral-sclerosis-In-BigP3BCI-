"""The fitted mapping depends on what is being weighted. Make that explicit.

The four tests from the task brief come first. The rest pin the statsmodels behaviour the module
is built on, against constructions that do not use it: that a grouped binomial already weights by
its own denominators, that dividing the frequency weight by those denominators therefore buys back
an unweighted unit, and that rescaling the weight vector moves no prediction. Every number this
module reports is wrong in a silent way if any of those is not what statsmodels does.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from bigp3_als.estimand import _unit_weights, compare_estimands, fit_grouped_binomial


def _records() -> pd.DataFrame:
    rows = []
    for study in ("StudyA", "StudyB", "StudyC"):
        for participant in range(6):
            score = 0.55 + 0.06 * participant
            n = 4 if participant < 3 else 30
            rows.append({
                "study": study,
                "study_participant_id": f"{study}:P{participant}",
                "session_id": "SE001",
                "condition": "CB",
                "n": n,
                "correct": int(round(n * min(0.99, 0.4 + 0.09 * participant))),
                "calibration_auc": score,
            })
    return pd.DataFrame(rows)


def test_grouped_binomial_returns_one_probability_per_validation_record() -> None:
    records = _records()
    development = records.loc[records["study"] != "StudyC"]
    validation = records.loc[records["study"] == "StudyC"]

    predictions = fit_grouped_binomial(development, validation, "calibration_auc", "character")

    assert predictions.shape == (len(validation),)
    assert ((predictions > 0) & (predictions < 1)).all()


def test_session_weighting_differs_from_character_weighting_when_denominators_differ() -> None:
    records = _records()
    development = records.loc[records["study"] != "StudyC"]
    validation = records.loc[records["study"] == "StudyC"]

    by_character = fit_grouped_binomial(development, validation, "calibration_auc", "character")
    by_session = fit_grouped_binomial(development, validation, "calibration_auc", "session")

    assert not np.allclose(by_character, by_session)


def test_unknown_weighting_is_rejected() -> None:
    records = _records()
    with pytest.raises(ValueError, match="weighting"):
        fit_grouped_binomial(records, records, "calibration_auc", "per-hour")


def test_compare_estimands_reports_every_weighting() -> None:
    result = compare_estimands(_records(), "calibration_auc")

    assert set(result["weighting"]) == {"character", "session", "participant"}
    assert (result["mean_absolute_error"] > 0).all()


def _unequal_records() -> pd.DataFrame:
    """Two studies where participants differ in how many records they contribute.

    `_records` gives every participant exactly one record, which makes participant weighting and
    session weighting the same question. Telling those two apart needs a frame where they are not.
    """
    rows = []
    for study in ("StudyA", "StudyB"):
        for participant in range(5):
            for session in range(1 + 2 * (participant % 3)):
                n = 4 if participant < 2 else 30
                rows.append({
                    "study": study,
                    "study_participant_id": f"{study}:P{participant}",
                    "session_id": f"SE{session:03d}",
                    "condition": "CB",
                    "n": n,
                    "correct": int(round(n * min(0.95, 0.35 + 0.11 * participant))),
                    "calibration_auc": 0.52 + 0.07 * participant,
                })
    return pd.DataFrame(rows)


def _standardized(development: pd.DataFrame, feature: str) -> tuple[float, float]:
    mean = float(development[feature].mean())
    return mean, float(development[feature].std(ddof=0)) or 1.0


def _expanded_bernoulli_predictions(
    development: pd.DataFrame, validation: pd.DataFrame, feature: str
) -> np.ndarray:
    """The character-expanded fit, built without any weighting argument at all."""
    mean, deviation = _standardized(development, feature)
    values: list[float] = []
    labels: list[int] = []
    for score, correct, total in development[[feature, "correct", "n"]].itertuples(index=False):
        values.extend([(float(score) - mean) / deviation] * int(total))
        labels.extend([1] * int(correct) + [0] * (int(total) - int(correct)))
    design = sm.add_constant(np.asarray(values, dtype=float), has_constant="add")
    model = sm.GLM(np.asarray(labels, dtype=float), design, family=sm.families.Binomial()).fit()
    x_validation = sm.add_constant(
        (validation[feature].to_numpy(dtype=float) - mean) / deviation, has_constant="add"
    )
    return np.asarray(model.predict(x_validation), dtype=float)


def test_character_weighting_reproduces_the_character_expanded_fit() -> None:
    """The estimand the pipeline chose silently is the one `"character"` names."""
    records = _records()
    development = records.loc[records["study"] != "StudyC"]
    validation = records.loc[records["study"] == "StudyC"]

    by_character = fit_grouped_binomial(development, validation, "calibration_auc", "character")
    expanded = _expanded_bernoulli_predictions(development, validation, "calibration_auc")

    assert np.allclose(by_character, expanded)


def test_session_weighting_matches_a_one_trial_per_record_fit() -> None:
    """Dividing the frequency weight by the denominator buys back one unit per record.

    `_unequal_records` gives every session exactly one condition record, so one unit per session and
    one unit per record are the same thing there and the mechanism can be checked in isolation.
    `test_weights_sum_to_one_within_each_session` is what pins the two apart.
    """
    records = _unequal_records()
    development = records.loc[records["study"] != "StudyB"]
    validation = records.loc[records["study"] == "StudyB"]

    by_session = fit_grouped_binomial(development, validation, "calibration_auc", "session")

    mean, deviation = _standardized(development, "calibration_auc")
    proportion = (development["correct"] / development["n"]).to_numpy(dtype=float)
    design = sm.add_constant(
        (development["calibration_auc"].to_numpy(dtype=float) - mean) / deviation,
        has_constant="add",
    )
    reference = sm.GLM(
        np.column_stack([proportion, 1.0 - proportion]), design, family=sm.families.Binomial()
    ).fit()
    x_validation = sm.add_constant(
        (validation["calibration_auc"].to_numpy(dtype=float) - mean) / deviation, has_constant="add"
    )

    assert np.allclose(by_session, np.asarray(reference.predict(x_validation), dtype=float))


def test_rescaling_the_weight_vector_moves_no_prediction() -> None:
    """The mean-one rescaling exists to keep the residual degrees of freedom sane, nothing more."""
    records = _unequal_records()
    development = records.loc[records["study"] != "StudyB"]
    validation = records.loc[records["study"] == "StudyB"]

    by_session = fit_grouped_binomial(development, validation, "calibration_auc", "session")

    mean, deviation = _standardized(development, "calibration_auc")
    design = sm.add_constant(
        (development["calibration_auc"].to_numpy(dtype=float) - mean) / deviation,
        has_constant="add",
    )
    successes = development["correct"].to_numpy(dtype=float)
    trials = development["n"].to_numpy(dtype=float)
    unscaled = sm.GLM(
        np.column_stack([successes, trials - successes]),
        design,
        family=sm.families.Binomial(),
        freq_weights=1.0 / trials,
    ).fit()
    x_validation = sm.add_constant(
        (validation["calibration_auc"].to_numpy(dtype=float) - mean) / deviation, has_constant="add"
    )

    assert np.allclose(by_session, np.asarray(unscaled.predict(x_validation), dtype=float))


def test_participant_weighting_differs_from_session_weighting_when_records_are_unbalanced() -> None:
    records = _unequal_records()
    development = records.loc[records["study"] != "StudyB"]
    validation = records.loc[records["study"] == "StudyB"]

    by_session = fit_grouped_binomial(development, validation, "calibration_auc", "session")
    by_participant = fit_grouped_binomial(development, validation, "calibration_auc", "participant")

    assert not np.allclose(by_session, by_participant)


def _multi_condition_records() -> pd.DataFrame:
    """Sessions carrying one to three conditions, with a participant identifier reused across studies.

    Two properties need this shape. Sessions with unequal numbers of conditions are what tell one
    unit per session apart from one unit per session-condition record. And `P0` appearing in both
    studies is what tells grouping on the full participant key apart from grouping on the bare
    identifier, which would merge two people into one.
    """
    rows = []
    for study in ("StudyA", "StudyB"):
        for participant in range(4):
            for session in range(2):
                for condition in ("CB", "RC", "DC")[: 1 + (participant + session) % 3]:
                    n = 4 if participant < 2 else 30
                    rows.append({
                        "study": study,
                        "study_participant_id": f"P{participant}",
                        "session_id": f"SE{session:03d}",
                        "condition": condition,
                        "n": n,
                        "correct": int(round(n * min(0.95, 0.4 + 0.1 * participant))),
                        "calibration_auc": 0.55 + 0.06 * participant + 0.01 * session,
                    })
    return pd.DataFrame(rows)


def test_weights_sum_to_one_within_each_session() -> None:
    """One unit per session, not one per session-condition record."""
    records = _multi_condition_records()
    weights = pd.Series(_unit_weights(records, "session"), index=records.index)

    totals = weights.groupby([records["study"], records["study_participant_id"],
                              records["session_id"]]).sum()
    assert len(totals) == 16
    assert np.allclose(totals.to_numpy(dtype=float), 1.0)


def test_weights_sum_to_one_within_each_participant() -> None:
    """One unit per participant, and a participant is a study and an identifier, not an identifier."""
    records = _multi_condition_records()
    weights = pd.Series(_unit_weights(records, "participant"), index=records.index)

    totals = weights.groupby([records["study"], records["study_participant_id"]]).sum()
    assert len(totals) == 8
    assert np.allclose(totals.to_numpy(dtype=float), 1.0)
    # Grouping on the bare identifier would merge `P0` across the two studies and halve these.
    assert not np.allclose(weights.groupby(records["study_participant_id"]).sum().to_numpy(), 1.0)


def test_compare_estimands_counts_the_units_it_says_it_weights() -> None:
    records = _multi_condition_records()
    result = compare_estimands(records, "calibration_auc").set_index("weighting")

    assert result.loc["character", "n_units"] == records["n"].sum()
    assert result.loc["session", "n_units"] == 16
    assert result.loc["participant", "n_units"] == 8
    assert result.loc["character", "n_units"] > len(records) > result.loc["session", "n_units"]
    assert result.loc["session", "n_units"] > result.loc["participant", "n_units"]


def test_matched_scale_slope_equals_the_fixed_slope_only_for_character_weighting() -> None:
    """The shipped slope scores every fit on the character scale; the matched one does not."""
    result = compare_estimands(_multi_condition_records(), "calibration_auc").set_index("weighting")

    assert result.loc["character", "calibration_slope_matched_scale"] == pytest.approx(
        result.loc["character", "calibration_slope"]
    )
    for weighting in ("session", "participant"):
        assert result.loc[weighting, "calibration_slope_matched_scale"] != pytest.approx(
            result.loc[weighting, "calibration_slope"]
        )


def test_a_missing_predictor_in_a_held_out_record_is_refused_not_predicted() -> None:
    records = _records()
    development = records.loc[records["study"] != "StudyC"]
    validation = records.loc[records["study"] == "StudyC"].copy()
    validation.loc[validation.index[0], "calibration_auc"] = np.nan

    with pytest.raises(ValueError, match="missing calibration_auc"):
        fit_grouped_binomial(development, validation, "calibration_auc", "character")


def test_compare_estimands_reports_a_character_weighted_calibration_slope() -> None:
    """The slope column is the manuscript's slope, computed on the same held-out predictions."""
    records = _unequal_records()
    result = compare_estimands(records, "calibration_auc").set_index("weighting")
    assert result["calibration_slope"].notna().all()

    labels: list[int] = []
    log_odds: list[float] = []
    for study in sorted(records["study"].unique()):
        development = records.loc[records["study"] != study]
        validation = records.loc[records["study"] == study]
        predicted = fit_grouped_binomial(development, validation, "calibration_auc", "session")
        for probability, correct, total in zip(
            predicted, validation["correct"], validation["n"], strict=True
        ):
            odds = float(np.log(probability / (1 - probability)))
            log_odds.extend([odds] * int(total))
            labels.extend([1] * int(correct) + [0] * (int(total) - int(correct)))
    design = sm.add_constant(np.asarray(log_odds, dtype=float), has_constant="add")
    expanded = sm.GLM(np.asarray(labels, dtype=float), design, family=sm.families.Binomial()).fit()

    assert result.loc["session", "calibration_slope"] == pytest.approx(float(expanded.params[1]))
