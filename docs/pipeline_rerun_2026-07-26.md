# Pipeline rerun after the decimation fix, 2026-07-26

Task 2 replaced the aliasing decimator in `src/bigp3_als/features.py`. The feature pipeline used to
keep every twelfth sample of a 256 Hz signal band-limited to 30 Hz, which leaves a Nyquist frequency
of 10.7 Hz and folds everything from 10.7 to 30 Hz onto lower frequencies. `DECIMATION_FACTOR` is now
4, leaving Nyquist at 32 Hz, above the 30 Hz passband edge.

This document records the rerun that propagates that correction, so that no number in the study still
comes from the aliased pipeline.

All commands ran with `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv` and `COPYFILE_DISABLE=1` through
`uv run`, on Python 3.11.14 with pandas 3.0.3, numpy 2.4.6, scikit-learn 1.9.0 and MNE 1.12.1.

## What was regenerated

| Stage | Command | Wall clock | Exit |
| --- | --- | --- | --- |
| Calibration features | `scripts/04_extract_features.py --cache data/source_cache_full` | 38 min 28 s | 0 |
| Four-cohort regression guard | `pytest tests/test_regression_baseline.py -v -m slow` | 3 min 48 s | 0, PASSED |
| Expanded analysis | `scripts/06_run_expanded.py --bootstrap-repetitions 2000` | 68 min 40 s | 0 |
| Sensitivity analyses | `scripts/07_run_sensitivity.py` | 6 min 38 s | 0 |

The brief estimated several minutes for `06_run_expanded.py`. The real cost is a little over an hour,
because the pooled bootstrap refits the model on all 18 held-out splits for each of 2,000
repetitions, on top of the per-cohort intervals. Anyone rerunning this should budget for that.

## Effect of the decimation correction on the predictor

Output of the movement check, comparing the pre-correction features saved to
`/tmp/features_aliased_backup.csv` against the regenerated
`output/intermediate/calibration_features_all20.csv`:

```
sessions 521 | mean change +0.0089 | sd 0.0196 | max |change| 0.0934
rank correlation old vs new: 0.9820
```

The brief set the interpretation bands in advance: above 0.98 the corrected pipeline tells a similar
story and the revision is mostly about inference, below 0.9 the primary results may change materially
and every number has to be re-read rather than merely re-run. The observed rank correlation of 0.9820
falls in the first band, exceeding the 0.98 threshold by 0.0020.

The correction raised discriminability slightly and almost uniformly, which is what recovering
unfolded 10.7 to 30 Hz content would be expected to do. Of 520 evaluable sessions, 359 improved and
161 worsened.

| Feature | Mean before | Mean after | Mean change | SD of change | Max absolute change | Spearman |
| --- | --- | --- | --- | --- | --- | --- |
| `calibration_auc` | 0.7957 | 0.8046 | +0.0089 | 0.0196 | 0.0934 | 0.9820 |
| `calibration_accuracy` | 0.8118 | 0.8555 | +0.0437 | 0.0191 | 0.1229 | 0.9766 |
| `shrinkage_lda_auc` | 0.8118 | 0.8289 | +0.0170 | 0.0196 | 0.1156 | 0.9808 |
| `pz_difference_uv` | 0.0211 | 0.0211 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| `posterior_difference_uv` | 0.1889 | 0.1889 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| `posterior_signed_r2_max` | 0.1590 | 0.1590 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

The three amplitude features are bit-identical before and after. That is the expected result and a
useful check on the change: `_downsampled_epoch_features` feeds only the classifier features, while
the Pz and posterior contrasts are computed on the full-rate epochs and never passed through the
decimator. Only the three classifier-derived columns could move, and only those three did.

Distribution of the per-session change in `calibration_auc`, from minimum to maximum:
-0.0449, -0.0202 (5th), -0.0032 (25th), +0.0080 (median), +0.0194 (75th), +0.0431 (95th), +0.0934.

## The set of sessions surviving the epoch minimums did not change

This matters more than the shift in values, because a change in which sessions survive would alter
the cohort itself rather than the numbers computed on it.

- Row count: 521 before, 521 after. No session key added, none dropped.
- Sessions passing `MIN_TARGET_EPOCHS` and `MIN_NONTARGET_EPOCHS`: 520 before, 520 after, the same
  520. None newly surviving, none newly excluded.
- The single excluded session is excluded for the same reason as before, "at least two calibration
  files are required for grouped validation", which is a grouping constraint and not an epoch count.
- `train_file_count`, `n_target_epochs`, `n_nontarget_epochs`, `n_calibration_epochs`,
  `n_calibration_epochs_pre_artifact` and `artifact_rejection_fraction` are all identical row for row.

That is structurally guaranteed rather than lucky: decimation happens after epoching, artifact
rejection and the epoch-count gates, so it cannot move any of those quantities. The cohort is
unchanged and only the predictor values moved.

Downstream, `analysis_records.csv` again holds 739 records, 271 participants, 18 of 20 contributing
studies and 19,611 selections, and `session_clustering.json` is unchanged at 410 sessions with an
intraclass correlation of 0.4125.

## Row counts before and after

Every regenerated file kept its row count and its columns. Three files came out byte-identical.

| File | Rows before | Rows after | Bytes changed |
| --- | --- | --- | --- |
| `output/intermediate/calibration_features_all20.csv` | 521 | 521 | yes |
| `output/expanded/study_inventory.csv` | 20 | 20 | no |
| `output/expanded/analysis_records.csv` | 739 | 739 | yes |
| `output/expanded/external_validation_metrics.csv` | 19 | 19 | yes |
| `output/expanded/external_validation_predictions.csv` | 739 | 739 | yes |
| `output/expanded/random_effects_pooling.csv` | 5 | 5 | yes |
| `output/expanded/als_subgroup_metrics.csv` | 5 | 5 | yes |
| `output/expanded/transfer_to_als.csv` | 4 | 4 | yes |
| `output/expanded/als_moderation.csv` | 3 | 3 | yes |
| `output/expanded/null_benchmark.csv` | 19 | 19 | no |
| `output/expanded/within_study_association.csv` | 20 | 20 | yes |
| `output/expanded/participant_level_association.csv` | 1 | 1 | yes |
| `output/expanded/across_session_pairs.csv` | 139 | 139 | yes |
| `output/expanded/across_session_association.csv` | 9 | 9 | yes |
| `output/expanded/sensitivity_analyses.csv` | 6 | 6 | yes |
| `output/expanded/session_clustering.json` | n/a | n/a | no |

`study_inventory.csv` and `null_benchmark.csv` are byte-identical because neither reads the
predictor: the inventory is derived from the trial table, and the null benchmark is the
no-predictor reference built from observed accuracy alone. `session_clustering.json` is unchanged for
the same reason, since the intraclass correlation is computed on session accuracy.

## Where the regenerated numbers landed

Reported here so that Tasks 4 to 15 can see at a glance which manuscript numbers need updating. The
"before" column is the value printed in the current `build_expanded/manuscript.md`, which was written
from the aliased pipeline. It is quoted at the manuscript's own rounding, because `output/` is not
version-controlled and the pre-correction analysis CSVs were overwritten by this rerun.

Study-level summary, the quantity the manuscript uses for transportability:

| Quantity | Before | After |
| --- | --- | --- |
| Mean absolute error, mean across 18 held-out cohorts | 0.104 | 0.1006 |
| Between-cohort SD of that error | 0.048 | 0.0472 |
| 95% CI for the mean | 0.080 to 0.128 | 0.0771 to 0.1240 |
| 95% prediction interval for a new cohort | 0.001 to 0.208 | -0.0017 to 0.2029 |
| Between-cohort SD of the calibration slope | 0.586 | 0.5596 |
| Between-cohort SD of the calibration intercept | 1.073 | 1.1749 |

Pooled bootstrap summary, conditional on the observed cohorts:

| Quantity | Before | After |
| --- | --- | --- |
| Mean absolute error | 0.103 (0.094 to 0.112) | 0.0984 (0.0906 to 0.1073) |
| Character Brier score | 0.124 (0.115 to 0.134) | 0.1226 (0.1134 to 0.1323) |
| Character Brier skill | 0.098 (0.049 to 0.138) | 0.1095 (0.0626 to 0.1494) |
| Character-weighted AUC | 0.743 (0.714 to 0.766) | 0.7476 (0.7191 to 0.7705) |
| Calibration intercept | 0.080 (-0.290 to 0.464) | 0.0540 (-0.2642 to 0.3946) |
| Calibration slope | 0.950 (0.754 to 1.146) | 0.9667 (0.7911 to 1.1268) |

Other quantities that moved enough to need editing in the text:

- Within-cohort correlation range: 0.083 to 0.920 before, 0.1898 to 0.9278 after, with the median
  moving from 0.630 to 0.635. The weakest cohort after the correction is StudyH at 0.1898, which is
  not significant (p = 0.48). The manuscript does not name the cohort that held the old floor of
  0.083, and the pre-correction per-cohort table was overwritten by this rerun, so whether it was the
  same cohort cannot be checked from what survives.
- Pooled correlation across the 410 sessions: 0.699 before, 0.7162 after. Participant-level: 0.701
  before, 0.7137 after. Study-centred: 0.652 before, 0.6771 after.
- Calibration slope across cohorts: 0.075 to 2.233 before, 0.1852 to 2.1847 after. Intercept: -2.445
  to 1.870 before, -2.1694 to 1.9947 after.
- Cohorts with negative skill against the no-predictor reference: still 2 of 18, still StudyH and
  StudyK, but the values are now -0.110 and -0.044 rather than -0.281 and -0.093.
- ALS subgroup: mean absolute error 0.095 to 0.0909, Brier skill 0.287 to 0.3032, AUC 0.828 to
  0.8306, calibration slope 0.991 to 0.9855, and the between-cohort SD of the ALS slope 0.204 to
  0.223, against 0.5596 across all contributing cohorts.
- Transfer with all ALS cohorts withheld: per-cohort error was 0.089, 0.112, 0.124, 0.142 (mean
  0.117) before and is 0.1093, 0.1064, 0.0867, 0.1312 (mean 0.1084) after.
- ALS moderation: slope 1.0019 in other cohorts against 1.6993 in ALS cohorts, interaction 0.6974.

Sensitivity analyses, mean absolute error and calibration-slope SD:

| Analysis | Before | After |
| --- | --- | --- |
| Primary, all contributing cohorts | 0.104, SD 0.586 | 0.1006, SD 0.560 |
| Cohorts with outcome SD at least 0.10 (12 cohorts) | 0.129, SD 0.674 | 0.1242, SD 0.601 |
| Artifact rejection at most 20 percent | 0.084, SD 0.438 | 0.0873, SD 0.465 |
| At least 10 eligible selections | 0.104 | 0.1004, SD 0.560 |
| Other cohorts only (14 cohorts) | 0.104, SD 0.716 | 0.1007, SD 0.663 |
| ALS cohorts only (4 cohorts) | SD 0.204 | 0.0932, SD 0.223 |

No conclusion in the manuscript reverses. The direction and the ordering of every sensitivity are
preserved, including the one analysis in which transportability improves, artifact screening. Every
individual figure in the text nonetheless has to be updated to the regenerated value.

## The 256 Hz montage claim, checked against the data

Task 2 added a guard in `_extract_file_epochs` that refuses to decimate a file whose sampling
frequency is below `2 * 30 Hz * 4 = 240 Hz`. The manuscript and supplement both assert that all 20
source studies share a 256 Hz montage, and that assertion had not previously been checked against the
archive. Feature extraction completed without raising the guard, which establishes that every Train
file clears 240 Hz.

A direct header-only audit of all 6,980 EDF files in `data/source_cache_full` confirms the stronger
claim. Every EEG signal in every file in all 20 studies is sampled at 256 Hz. The observed range is
256.000000 to 256.000128 Hz, a spread of 1.3e-4 Hz that comes from EDF storing the data-record
duration as a rounded ASCII field rather than from any real difference in rate. No file mixes
sampling rates across its EEG channels.

One caveat for anyone repeating the audit. Reading the per-signal sample counts straight out of the
EDF header also picks up the EDF+ Annotations channel, which carries a handful of samples per record
and therefore reports an apparent rate below 1 Hz. It is not a low-rate EEG channel, MNE does not
expose it as data, and the pipeline never reads it. It must be excluded by label before summarising
rates, or the audit appears to find sub-Hertz channels everywhere.

The 240 Hz guard therefore has a margin of 16 Hz against the real archive, and the assertion in the
manuscript is supported.

## Why the four-cohort intermediates were not regenerated

`output/intermediate/*_with_b.csv` were deliberately left frozen and were not rebuilt from the
corrected feature pipeline.

The four-cohort regression guard in `tests/test_regression_baseline.py` reads those stored files. That
is what makes it a clean detector. It isolates the statistical code in `validation.py` and
`strengthening.py`, which Tasks 4 through 15 refactor, from the feature pipeline that this task
changed. If the guard were re-pointed at regenerated features, a change in either layer would trip it
and the signal would be useless for the rest of the revision.

The guard was re-run after the feature regeneration and passed, as expected, since its inputs were
untouched:

```
tests/test_regression_baseline.py::test_four_cohort_primary_is_unchanged PASSED [100%]
======================== 1 passed in 227.97s (0:03:47) =========================
```

The cost is that the repository keeps one set of pre-correction feature artifacts.
`output/intermediate/calibration_features_with_b.csv`, `output/intermediate/online_trials_with_b.csv`
and `output/intermediate/file_metadata_with_b.csv` still come from the aliased pipeline, and
`output/final/` holds the superseded four-cohort analysis built on them.

Neither is an input to any manuscript number. The manuscript reports the expanded 18-cohort analysis
under `output/expanded/`, which this task regenerated in full. The four-cohort artifacts survive only
as the guard's fixture. They should be regenerated, or deleted along with the guard, once Tasks 4
through 15 are finished and the guard has served its purpose.

## Still stale after this rerun

- `output/expanded/figures/` was not re-rendered. The three PDF and PNG figures still plot the
  pre-correction analysis. Task 14 rebuilds them.
- `build_expanded/manuscript.md`, `build_expanded/supplement.md` and the rendered docx and pdf still
  quote the pre-correction numbers listed above. Tasks 4 through 16 rewrite them.
