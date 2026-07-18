# Data dictionary

`file_metadata.csv` has one row per verified EDF file. `study_participant_id` is intentionally scoped as `StudyX:subject`; it must not be treated as a cross-study person identifier.

- `study`, `participant_id`, `session_id`, `phase`, `condition`, `filename`: source hierarchy fields.
- `sex`, `date_of_birth`, `age_years`, `race_ethnicity`: standardized EDF header fields. A 2020 birth year denotes missing age, not age zero.
- `als_status`, `alsfrs_r`: standardized EDF header clinical fields. `ALS` without a suffix is a known ALS status with unavailable ALSFRS-R.
- `relative_path`: source-cache path traceable to the archive checksum manifest.
