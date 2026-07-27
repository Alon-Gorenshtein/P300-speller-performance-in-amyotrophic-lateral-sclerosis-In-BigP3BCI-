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


def _load_sensitivity_script():
    specification = importlib.util.spec_from_file_location(
        "run_sensitivity", REPOSITORY / "scripts" / "07_run_sensitivity.py"
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


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
def test_comparator_table_reports_every_prespecified_predictor() -> None:
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
