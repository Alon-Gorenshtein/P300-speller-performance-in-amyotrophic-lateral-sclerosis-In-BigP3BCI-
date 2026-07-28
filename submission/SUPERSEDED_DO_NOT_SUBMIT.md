# SUPERSEDED - do not submit anything in this folder

Everything in `submission/` (the three `.zip` files, `final_submission/`, `clean_bundle/`,
`Submission_Ready_ALS_P300_Calibration/`) was built before the Study B reframe and describes a
**different version of this study**. Submitting from these artefacts would submit the wrong paper.

The zips were built 2026-07-18 15:29-15:31. The reframe that added Study B landed 15:48-16:12 and was
committed as `9dcbb13 docs: reframe ALS P300 manuscript around session accuracy`.

## What differs

| | Packaged here (superseded) | Current sources |
|---|---|---|
| Source studies | F, L, N, selected because they carried numerical ALSFRS-R | B, F, L, N; ALSFRS-R explicitly not an eligibility criterion |
| Study-scoped records | 29 | 47 |
| Sessions | 57 | 113 |
| Session-condition records | not reported | 194 |
| Eligible selections | 2,537 (1,995 correct) | 3,318 (2,699 correct) |
| Headline result | pooled AUC 0.829 (0.757-0.872) | session-condition MAE 0.095 (0.080-0.115); AUC 0.828 |
| Bootstrap | 1,000 replicates, held-out resampling only | 2,000 replicates, development refit each replicate |
| ALSFRS-R exploratory analysis | present | removed |

The packaged `reproducibility/analysis_records.csv` has 138 rows covering Studies F, L and N. The
current frozen `output/final/analysis_records.csv` has 194 rows covering Studies B, F, L and N.

## Second, more recent supersession (2026-07-28)

The comparison above (Study B reframe, 4 cohorts) is itself now historical. A second, larger
supersession has since happened: a 16-task revision pass widened the design from 4 cohorts to all
18 cohorts in the BigP3BCI archive. That widened design lives in `manuscript/manuscript_expanded.md`,
`supplementary/supplement_expanded.md`, and `output/expanded/`. As a result, `manuscript/manuscript.md`
and `supplementary/supplement.md` (the bare, non-`_expanded` files) are now also superseded, not only
the packaged zips this file originally warned about. Do not submit from the bare files either; treat
everything without the `_expanded` suffix, and everything under `output/final/`, as historical.

## Canonical sources

- `manuscript/manuscript_expanded.md`
- `supplementary/supplement_expanded.md`
- `output/expanded/` (frozen analysis records, validation metrics, heterogeneity, sensitivity,
  comparators, figures)

These are now built via `scripts/15_build_manuscript.py` (which also renders
`manuscript/cover_letter_expanded.md`) rather than by a manual pandoc/Word process.

## To produce a submittable package

1. Rebuild the `.docx` and `.pdf` renderings by running
   `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py`,
   which renders all three current markdown sources (`manuscript/manuscript_expanded.md`,
   `manuscript/cover_letter_expanded.md`, `supplementary/supplement_expanded.md`) into
   `build_expanded/`. The `.docx`/`.pdf` files previously sitting in `manuscript/` predate both the
   2026-07-26 supplement corrections and the 2026-07-27/28 18-cohort widening pass, and should not be
   used; the current renderings live in `build_expanded/`, not `manuscript/`.
2. Regenerate the package from the current `output/expanded/`, not from this folder and not from
   `output/final/`.
3. Delete or archive the three `.zip` files so they cannot be uploaded by mistake.

## Note on the frozen outputs

`output/final/trial_exclusion_summary.csv` and `output/final/within_study_lopo_sensitivity.csv` were
regenerated on 2026-07-26 from `output/intermediate/*_with_b.csv`, which the original run had never
been re-executed against. Studies F, L and N reproduced bit-identically; Study B was added (858
trial-eligible selections, 781 entering the analysis records, leave-one-participant-out AUC 0.806).
