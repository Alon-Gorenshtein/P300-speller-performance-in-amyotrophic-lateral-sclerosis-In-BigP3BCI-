"""Tests for clinical metadata and EDF schema parsing."""

from __future__ import annotations

from datetime import date

from pathlib import Path

from bigp3_als.edf import parse_patient_identification, parse_source_path, select_edf_paths


def test_patient_identification_extracts_numeric_alsfrs_and_uses_shifted_age() -> None:
    identity = parse_patient_identification(
        "F_08 F 01-JAN-1958 White_NotHispanicLatino ALS_42", recording_year=2020
    )

    assert identity.participant_id == "F_08"
    assert identity.sex == "F"
    assert identity.date_of_birth == date(1958, 1, 1)
    assert identity.age_years == 62
    assert identity.als_status == "ALS"
    assert identity.alsfrs_r == 42


def test_patient_identification_treats_2020_birth_year_as_missing_age_and_score() -> None:
    identity = parse_patient_identification("B_01 X 01-JAN-2020 X_X ALS", recording_year=2020)

    assert identity.sex is None
    assert identity.age_years is None
    assert identity.als_status == "ALS"
    assert identity.alsfrs_r is None


def test_source_path_preserves_study_scoped_identity_and_condition() -> None:
    metadata = parse_source_path(
        "bigP3BCI-data/StudyL/L_01/SE001/Test/CB/L_01_SE001_CB_Test06.edf"
    )

    assert metadata.study == "StudyL"
    assert metadata.participant_id == "L_01"
    assert metadata.session_id == "SE001"
    assert metadata.phase == "Test"
    assert metadata.condition == "CB"
    assert metadata.study_participant_id == "StudyL:L_01"


def test_edf_selection_ignores_macos_appledouble_sidecars(tmp_path: Path) -> None:
    valid = tmp_path / "bigP3BCI-data" / "StudyF" / "F_01.edf"
    sidecar = valid.with_name("._F_01.edf")
    valid.parent.mkdir(parents=True)
    valid.write_bytes(b"edf")
    sidecar.write_bytes(b"not an EDF")

    assert select_edf_paths(tmp_path) == [valid]
