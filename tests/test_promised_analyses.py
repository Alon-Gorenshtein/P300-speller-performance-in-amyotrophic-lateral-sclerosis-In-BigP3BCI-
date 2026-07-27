"""Guards for the three analyses the Methods promise and the outputs that carry them.

The leave-two-studies-out check is the one with a correctness property worth asserting: a cohort
that is being estimated must never appear in the data the model was fitted on. The rest of the file
holds the shape of the two output tables, because the manuscript and supplement read specific rows
and columns out of them.
"""

from __future__ import annotations

import importlib.util
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bigp3_als.validation import MODEL_SPECS

REPOSITORY = Path(__file__).resolve().parents[1]
MODEL_SPECS_NAMES = [specification.name for specification in MODEL_SPECS]

# The frozen outputs are regenerable and therefore not tracked, so the tests that read them guard
# what is on disk where it exists and skip on a checkout that has not run the pipeline.
SENSITIVITY_TABLE = REPOSITORY / "output" / "expanded" / "sensitivity_analyses.csv"
COMPARATOR_TABLE = REPOSITORY / "output" / "expanded" / "comparator_metrics.csv"
needs_sensitivity_table = pytest.mark.skipif(
    not SENSITIVITY_TABLE.exists(), reason="run scripts/07_run_sensitivity.py first"
)
needs_comparator_table = pytest.mark.skipif(
    not COMPARATOR_TABLE.exists(), reason="run scripts/11_run_comparators.py first"
)


def _load_script(module_name: str, file_name: str):
    specification = importlib.util.spec_from_file_location(module_name, REPOSITORY / "scripts" / file_name)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _load_sensitivity_script():
    return _load_script("run_sensitivity", "07_run_sensitivity.py")


def _load_fold_coefficient_script():
    return _load_script("export_fold_coefficients", "12_export_fold_coefficients.py")


def _synthetic_records(n_studies: int = 6, n_participants: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows = []
    for study_index in range(n_studies):
        study = f"Study{study_index}"
        for participant_index in range(n_participants):
            score = float(rng.uniform(0.6, 0.95))
            rows.append(
                {
                    "study": study,
                    "study_participant_id": f"{study}:P{participant_index}",
                    "session_id": "SE001",
                    "condition": "RC",
                    "calibration_auc": score,
                    "n": 30,
                    "correct": int(round(30 * min(0.98, max(0.3, score + rng.normal(0, 0.05))))),
                }
            )
    return pd.DataFrame(rows)


def test_leave_two_studies_out_never_fits_on_a_withheld_cohort(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_sensitivity_script()
    records = _synthetic_records()
    seen: list[tuple[frozenset[str], frozenset[str]]] = []

    def spy(development: pd.DataFrame, validation: pd.DataFrame, features) -> np.ndarray:
        seen.append((frozenset(development["study"].unique()), frozenset(validation["study"].unique())))
        return np.full(len(validation), 0.8)

    monkeypatch.setattr(module, "_fit_probability_model", spy)
    row = module._leave_two_studies_out(records, "leave-two-studies-out development")

    studies = set(records["study"].unique())
    assert len(seen) == len(list(itertools.combinations(sorted(studies), 2)))
    for development_studies, validation_studies in seen:
        assert len(validation_studies) == 2
        assert not development_studies & validation_studies
        assert development_studies | validation_studies == studies
    assert f"{len(seen)} splits" in str(row["analysis"])


def test_leave_two_studies_out_row_has_the_same_columns_as_the_other_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_sensitivity_script()
    records = _synthetic_records()
    monkeypatch.setattr(
        module, "_fit_probability_model", lambda development, validation, features: np.full(len(validation), 0.8)
    )
    row = module._leave_two_studies_out(records, "leave-two-studies-out development")

    expected = {
        "analysis",
        "n_studies",
        "n_records",
        "n_selections",
        "mae_mean",
        "mae_between_study_sd",
        "mae_prediction_low",
        "mae_prediction_high",
        "slope_mean",
        "slope_between_study_sd",
        "slope_prediction_low",
        "slope_prediction_high",
    }
    assert set(row) == expected
    assert row["n_studies"] == records["study"].nunique()
    assert row["n_records"] == len(records)


def test_every_cohort_contributes_the_same_number_of_leave_two_out_estimates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_sensitivity_script()
    records = _synthetic_records()
    withheld: list[str] = []

    def spy(development: pd.DataFrame, validation: pd.DataFrame, features) -> np.ndarray:
        withheld.extend(sorted(validation["study"].unique()))
        return np.full(len(validation), 0.8)

    monkeypatch.setattr(module, "_fit_probability_model", spy)
    module._leave_two_studies_out(records, "leave-two-studies-out development")

    counts = pd.Series(withheld).value_counts()
    assert set(counts.index) == set(records["study"].unique())
    assert counts.nunique() == 1
    assert counts.iloc[0] == records["study"].nunique() - 1


@needs_sensitivity_table
def test_sensitivity_table_carries_the_leave_two_studies_out_row() -> None:
    table = pd.read_csv(SENSITIVITY_TABLE)
    matched = table.loc[table["analysis"].str.startswith("leave-two-studies-out development")]
    assert len(matched) == 1
    row = matched.iloc[0]
    assert row["analysis"].endswith("(153 splits)")
    assert row["n_studies"] == 18
    assert row[["mae_mean", "mae_between_study_sd", "slope_mean", "slope_between_study_sd"]].notna().all()


@needs_comparator_table
def test_comparator_table_reports_every_named_predictor() -> None:
    table = pd.read_csv(COMPARATOR_TABLE)
    assert set(MODEL_SPECS_NAMES) <= set(table["predictor"])
    assert (table["role"] == "exploratory reference").sum() == 1
    primary = table.loc[table["role"] == "primary"].iloc[0]
    assert primary["n_cohorts"] == 18
    assert primary["n_records"] == 739


@needs_comparator_table
def test_comparator_table_restricts_the_exploratory_specification_to_its_own_records() -> None:
    table = pd.read_csv(COMPARATOR_TABLE)
    exploratory = table.loc[table["role"].str.startswith("exploratory")]
    assert len(exploratory) == 2
    assert exploratory["n_cohorts"].nunique() == 1
    assert exploratory["n_records"].nunique() == 1
    assert int(exploratory["n_cohorts"].iloc[0]) < 18


def test_leave_two_studies_out_reports_rather_than_fails_below_five_cohorts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_sensitivity_script()
    records = _synthetic_records(n_studies=4)
    monkeypatch.setattr(
        module, "_fit_probability_model", lambda development, validation, features: np.full(len(validation), 0.8)
    )
    row = module._leave_two_studies_out(records, "leave-two-studies-out development")

    assert row["note"] == "too few cohorts"
    assert row["n_studies"] == 4


def test_leave_two_studies_out_drops_records_missing_the_primary_feature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_sensitivity_script()
    records = _synthetic_records()
    records.loc[records.index[:2], "calibration_auc"] = np.nan
    seen: list[int] = []

    def spy(development: pd.DataFrame, validation: pd.DataFrame, features) -> np.ndarray:
        assert not development[list(features)].isna().any().any()
        assert not validation[list(features)].isna().any().any()
        seen.append(len(development))
        return np.full(len(validation), 0.8)

    monkeypatch.setattr(module, "_fit_probability_model", spy)
    row = module._leave_two_studies_out(records, "leave-two-studies-out development")

    assert seen
    assert row["n_records"] == len(records) - 2


def test_supplement_table_s6_has_a_row_for_every_specification() -> None:
    """Guard the supplement's claim, on tracked files, so it holds on a fresh checkout.

    ``11_run_comparators.py`` no longer swallows a failing specification, so a missing predictor
    stops the run rather than shipping a short table. This catches the other direction: a
    specification added to ``MODEL_SPECS`` without a corresponding row in the supplement.
    """
    supplement = (REPOSITORY / "supplementary" / "supplement_expanded.md").read_text()
    body = supplement.split("**Table S6.")[1].split("\n\n")[1]
    rows = [line for line in body.splitlines() if line.startswith("|")]
    header, separator, *data = rows
    assert separator.startswith("|---")
    # one row per named predictor plus the matched reference for the exploratory one
    assert len(data) == len(MODEL_SPECS) + 1
    assert sum(1 for line in data if "Exploratory reference" in line) == 1


def test_fold_coefficients_reconstruct_every_held_out_estimate() -> None:
    """The reproducibility promise, checked end to end on synthetic cohorts.

    A reader is promised they can recompute any estimate from four numbers per fold. This asserts
    the exported numbers do that, without depending on the frozen outputs.
    """
    module = _load_fold_coefficient_script()
    records = _synthetic_records(n_studies=5, n_participants=6)
    table = module.build_fold_coefficients(records)

    assert len(table) == records["study"].nunique()
    assert set(table.columns) >= {"held_out_study", "intercept_a", "slope_b", "development_mean_m", "development_sd_d"}
    assert (table["max_reconstruction_error"] <= module.RECONSTRUCTION_TOLERANCE).all()

    from bigp3_als.validation import _fit_probability_model, leave_one_study_out

    coefficients = table.set_index("held_out_study")
    for held_out, development, validation in leave_one_study_out(records):
        row = coefficients.loc[held_out]
        scores = validation["calibration_auc"].to_numpy(dtype=float)
        standardised = (scores - row["development_mean_m"]) / row["development_sd_d"]
        recomputed = 1.0 / (1.0 + np.exp(-(row["intercept_a"] + row["slope_b"] * standardised)))
        fitted = _fit_probability_model(development, validation, ("calibration_auc",))
        assert np.allclose(recomputed, fitted, atol=1e-10)


def test_fold_coefficient_export_refuses_to_write_an_unusable_table(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_fold_coefficient_script()
    records = _synthetic_records(n_studies=5, n_participants=6)
    monkeypatch.setattr(module, "RECONSTRUCTION_TOLERANCE", -1.0)
    with pytest.raises(ValueError, match="reproduce the fold"):
        module.build_fold_coefficients(records)
