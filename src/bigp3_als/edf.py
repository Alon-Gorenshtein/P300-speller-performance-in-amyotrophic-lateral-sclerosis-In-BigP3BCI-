"""Clinical metadata and EDF schema utilities for the BigP3 ALS cohorts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

import mne
import pandas as pd


SHARED_EEG_CHANNELS = (
    "EEG_F3",
    "EEG_Fz",
    "EEG_F4",
    "EEG_T7",
    "EEG_C3",
    "EEG_Cz",
    "EEG_C4",
    "EEG_T8",
    "EEG_CP3",
    "EEG_CP4",
    "EEG_P3",
    "EEG_Pz",
    "EEG_P4",
    "EEG_PO7",
    "EEG_PO8",
    "EEG_Oz",
)
REQUIRED_EVENT_CHANNELS = (
    "StimulusType",
    "SelectedTarget",
    "PhaseInSequence",
    "StimulusBegin",
    "CurrentTarget",
    "FakeFeedback",
    "DisplayResults",
)


@dataclass(frozen=True)
class PatientIdentity:
    participant_id: str
    sex: str | None
    date_of_birth: date | None
    age_years: int | None
    race_ethnicity: str | None
    als_status: str | None
    alsfrs_r: int | None


@dataclass(frozen=True)
class SourcePath:
    study: str
    participant_id: str
    session_id: str
    phase: str
    condition: str
    filename: str

    @property
    def study_participant_id(self) -> str:
        return f"{self.study}:{self.participant_id}"


def parse_patient_identification(value: str, *, recording_year: int) -> PatientIdentity:
    """Parse the standardized EDF patient field without inventing missing values."""
    fields = value.strip().split()
    if len(fields) < 4:
        raise ValueError(f"malformed EDF patient identification: {value!r}")
    participant_id, sex_code, date_of_birth_text = fields[:3]
    try:
        date_of_birth = datetime.strptime(date_of_birth_text, "%d-%b-%Y").date()
    except ValueError as error:
        raise ValueError(f"invalid EDF birth date: {date_of_birth_text!r}") from error
    age_years = None if date_of_birth.year == recording_year else recording_year - date_of_birth.year
    profile = fields[3:]
    als_text = profile[-1]
    if als_text == "NonALS":
        als_status, alsfrs_r = "NonALS", None
    elif als_text == "ALS":
        als_status, alsfrs_r = "ALS", None
    elif als_text.startswith("ALS_"):
        als_status = "ALS"
        score_text = als_text.removeprefix("ALS_")
        alsfrs_r = None if score_text == "X" else int(score_text)
    else:
        raise ValueError(f"unrecognized ALS status: {als_text!r}")
    race_ethnicity = " ".join(profile[:-1]) or None
    return PatientIdentity(
        participant_id=participant_id,
        sex=sex_code if sex_code in {"M", "F"} else None,
        date_of_birth=date_of_birth,
        age_years=age_years,
        race_ethnicity=race_ethnicity,
        als_status=als_status,
        alsfrs_r=alsfrs_r,
    )


def parse_source_path(relative_path: str) -> SourcePath:
    """Parse a cache-relative BigP3 EDF path into reproducible study identifiers."""
    parts = Path(relative_path).parts
    if len(parts) != 7 or parts[0] != "bigP3BCI-data":
        raise ValueError(f"unexpected BigP3 source path: {relative_path!r}")
    _, study, participant_id, session_id, phase, condition, filename = parts[-7:]
    if phase not in {"Train", "Test"}:
        raise ValueError(f"unexpected phase {phase!r} in {relative_path!r}")
    return SourcePath(
        study=study,
        participant_id=participant_id,
        session_id=session_id,
        phase=phase,
        condition=condition,
        filename=filename,
    )


def read_patient_identification(edf_path: Path, *, recording_year: int = 2020) -> PatientIdentity:
    """Read the fixed-width patient field without loading EDF signal data."""
    with edf_path.open("rb") as handle:
        header = handle.read(88)
    if len(header) != 88:
        raise ValueError(f"truncated EDF header: {edf_path}")
    patient_identification = header[8:88].decode("ascii", errors="strict")
    return parse_patient_identification(patient_identification, recording_year=recording_year)


def validate_clinical_schema(edf_path: Path) -> None:
    """Require the shared EEG montage and event streams used by the study protocol."""
    raw = mne.io.read_raw_edf(edf_path, preload=False, verbose="ERROR")
    available = set(raw.ch_names)
    required = set(SHARED_EEG_CHANNELS) | set(REQUIRED_EVENT_CHANNELS)
    missing = sorted(required - available)
    if missing:
        raise ValueError(f"missing required channels in {edf_path}: {', '.join(missing)}")


def select_edf_paths(cache_path: Path) -> list[Path]:
    """Return source EDF paths while excluding macOS AppleDouble sidecars."""
    return sorted(
        path
        for path in cache_path.rglob("*.edf")
        if not any(component.startswith("._") for component in path.relative_to(cache_path).parts)
    )


def build_file_metadata(cache_path: Path) -> pd.DataFrame:
    """Build file-level clinical metadata from the already verified selective cache."""
    rows: list[dict[str, object]] = []
    for edf_path in select_edf_paths(cache_path):
        relative_path = edf_path.relative_to(cache_path).as_posix()
        source = parse_source_path(relative_path)
        patient = read_patient_identification(edf_path)
        row = {
            **asdict(source),
            "study_participant_id": source.study_participant_id,
            "relative_path": relative_path,
            "sex": patient.sex,
            "date_of_birth": patient.date_of_birth.isoformat(),
            "age_years": patient.age_years,
            "race_ethnicity": patient.race_ethnicity,
            "als_status": patient.als_status,
            "alsfrs_r": patient.alsfrs_r,
        }
        if source.participant_id != patient.participant_id:
            raise ValueError(f"path/header participant mismatch: {relative_path}")
        rows.append(row)
    return pd.DataFrame(rows).sort_values("relative_path", ignore_index=True)
