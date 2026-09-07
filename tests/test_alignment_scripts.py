"""Guards against a silently shortened or silently double-merged alignment/nonlinear arm table.

Both scripts under test have a comment (matching `11_run_comparators.py`'s) explaining why an
arm dropping out cannot be allowed to happen without a diagnostic: the supplement's transport
table claims results for every named arm, so a specification or column that silently vanished
would make that claim false while the table still looked complete.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

REPOSITORY = Path(__file__).resolve().parents[1]


def _load_script(module_name: str, file_name: str):
    specification = importlib.util.spec_from_file_location(module_name, REPOSITORY / "scripts" / file_name)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _load_run_alignment():
    return _load_script("run_alignment", "17_run_alignment.py")


def _load_extract_alignment_features():
    return _load_script("extract_alignment_features", "04b_extract_alignment_features.py")


def _records_with_arms(present_features: list[str]) -> pd.DataFrame:
    """A minimal records frame that carries only the named alignment feature columns."""
    columns = {"study": ["StudyA"], "study_participant_id": ["StudyA:P1"], "session_id": ["SE001"]}
    for feature in present_features:
        columns[feature] = [0.7]
    return pd.DataFrame(columns)


def test_resolve_specs_raises_naming_every_missing_arm() -> None:
    module = _load_run_alignment()
    all_features = [spec.features[0] for spec in module.ALIGNMENT_SPECS]
    # Drop the last two arms' feature columns; both must be named in the error, not just one.
    present = all_features[:-2]
    missing = all_features[-2:]
    records = _records_with_arms(present)

    with pytest.raises(SystemExit) as excinfo:
        module._resolve_specs(records)

    message = str(excinfo.value)
    for spec in module.ALIGNMENT_SPECS:
        if spec.features[0] in missing:
            assert spec.name in message


def test_resolve_specs_with_all_arms_present_returns_primary_plus_every_arm() -> None:
    module = _load_run_alignment()
    all_features = [spec.features[0] for spec in module.ALIGNMENT_SPECS]
    records = _records_with_arms(all_features)

    specs = module._resolve_specs(records)

    assert specs[0] is module.PRIMARY
    assert {spec.name for spec in specs[1:]} == {spec.name for spec in module.ALIGNMENT_SPECS}


def test_resolve_specs_allow_missing_arms_skips_instead_of_raising() -> None:
    module = _load_run_alignment()
    all_features = [spec.features[0] for spec in module.ALIGNMENT_SPECS]
    present = all_features[:-1]
    records = _records_with_arms(present)

    specs = module._resolve_specs(records, allow_missing_arms=True)

    # PRIMARY plus every arm except the one whose column was dropped.
    assert len(specs) == len(module.ALIGNMENT_SPECS)


def test_merge_cohort_arm_raises_when_the_column_already_exists() -> None:
    module = _load_extract_alignment_features()
    keys = module.KEYS
    existing = pd.DataFrame(
        {
            "study": ["StudyA"],
            "study_participant_id": ["StudyA:P1"],
            "session_id": ["SE001"],
            "calibration_auc_ea_cohort": [0.5],
        }
    )
    frame = pd.DataFrame(
        {
            "study": ["StudyA"],
            "study_participant_id": ["StudyA:P1"],
            "session_id": ["SE001"],
            "calibration_auc_ea_cohort": [0.9],
        }
    )
    assert list(existing.columns[:3]) == keys

    with pytest.raises(SystemExit, match="already a column"):
        module._merge_cohort_arm(existing, frame)


def test_merge_cohort_arm_succeeds_on_a_fresh_column() -> None:
    module = _load_extract_alignment_features()
    existing = pd.DataFrame(
        {
            "study": ["StudyA"],
            "study_participant_id": ["StudyA:P1"],
            "session_id": ["SE001"],
            "calibration_auc_reproduced": [0.5],
        }
    )
    frame = pd.DataFrame(
        {
            "study": ["StudyA"],
            "study_participant_id": ["StudyA:P1"],
            "session_id": ["SE001"],
            "calibration_auc_ea_cohort": [0.9],
        }
    )

    merged = module._merge_cohort_arm(existing, frame)

    assert merged["calibration_auc_ea_cohort"].iloc[0] == pytest.approx(0.9)
