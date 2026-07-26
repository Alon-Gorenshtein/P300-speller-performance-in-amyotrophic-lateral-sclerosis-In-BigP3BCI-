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

## Canonical sources

- `manuscript/manuscript.md`
- `supplementary/supplement.md`
- `output/final/` (frozen analysis records, validation metrics, exclusions, sensitivity, figures)

## To produce a submittable package

1. Rebuild the `.docx` and `.pdf` renderings from the two canonical markdown sources. The renderings
   currently sitting in `manuscript/` were built before the supplement corrections of 2026-07-26 and
   should be regenerated.
2. Regenerate the package from the current `output/final/`, not from this folder.
3. Delete or archive the three `.zip` files so they cannot be uploaded by mistake.

## Note on the frozen outputs

`output/final/trial_exclusion_summary.csv` and `output/final/within_study_lopo_sensitivity.csv` were
regenerated on 2026-07-26 from `output/intermediate/*_with_b.csv`, which the original run had never
been re-executed against. Studies F, L and N reproduced bit-identically; Study B was added (858
trial-eligible selections, 781 entering the analysis records, leave-one-participant-out AUC 0.806).
