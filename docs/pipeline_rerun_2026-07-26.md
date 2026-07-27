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
- All 521 sessions clear `MIN_TARGET_EPOCHS` and `MIN_NONTARGET_EPOCHS`, before and after. No session
  sits near either threshold in a way the correction could have tipped.
- Sessions carrying a usable feature value, meaning they pass every gate: 520 before, 520 after, the
  same 520. None newly surviving, none newly excluded.
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

The pre-rerun state is preserved in `docs/pipeline_rerun_2026-07-26_before_snapshot.json`, which
records the row count, full column list and SHA-256 of every file below as it stood before this
rerun. The first 16 hexadecimal digits of each hash are reproduced here so the "bytes changed" column
can be checked against the current files without opening that snapshot.

| File | Rows before | Rows after | SHA-256 before | SHA-256 after | Bytes changed |
| --- | --- | --- | --- | --- | --- |
| `output/intermediate/calibration_features_all20.csv` | 521 | 521 | `e68c144230d3343d` | `e11b9593add73aad` | yes |
| `output/expanded/study_inventory.csv` | 20 | 20 | `b2915ba309c386b5` | `b2915ba309c386b5` | no |
| `output/expanded/analysis_records.csv` | 739 | 739 | `d46006a62753c614` | `a298da2b7dab54a2` | yes |
| `output/expanded/external_validation_metrics.csv` | 19 | 19 | `e5a34fbb89ce0b62` | `d99f3034e256f581` | yes |
| `output/expanded/external_validation_predictions.csv` | 739 | 739 | `5dda7cc8eaa026e3` | `eb10b993bbbb335e` | yes |
| `output/expanded/random_effects_pooling.csv` | 5 | 5 | `2d61b70ab7f8fc78` | `cc8a6faf4ec0cb79` | yes |
| `output/expanded/als_subgroup_metrics.csv` | 5 | 5 | `89d6c87207eee639` | `0b0f3b9f0f7c4ca5` | yes |
| `output/expanded/transfer_to_als.csv` | 4 | 4 | `01c102c27771084a` | `805c10dda9986670` | yes |
| `output/expanded/als_moderation.csv` | 3 | 3 | `7a5e508744538f7c` | `e5413a1cbaca2e11` | yes |
| `output/expanded/null_benchmark.csv` | 19 | 19 | `fd87df7b8c95f762` | `fd87df7b8c95f762` | no |
| `output/expanded/within_study_association.csv` | 20 | 20 | `c9bf934dd99d2a98` | `802440c9e79a6798` | yes |
| `output/expanded/participant_level_association.csv` | 1 | 1 | `c550f9dd339b9277` | `c2301db146ea4341` | yes |
| `output/expanded/across_session_pairs.csv` | 139 | 139 | `eba41dfa6ff47153` | `db9c91063a58aa8b` | yes |
| `output/expanded/across_session_association.csv` | 9 | 9 | `6773dff108bb1fe5` | `4118d4be4211ccd2` | yes |
| `output/expanded/sensitivity_analyses.csv` | 6 | 6 | `e5475eb3de5477fe` | `f61880ce54851c91` | yes |
| `output/expanded/session_clustering.json` | n/a | n/a | `de9a4b03a78ee1e4` | `de9a4b03a78ee1e4` | no |

`study_inventory.csv` and `null_benchmark.csv` are byte-identical because neither reads the
predictor: the inventory is derived from the trial table, and the null benchmark is the
no-predictor reference built from observed accuracy alone. `session_clustering.json` is unchanged for
the same reason, since the intraclass correlation is computed on session accuracy.

## Where the regenerated numbers landed

Reported here so that Tasks 4 to 15 can see at a glance which manuscript numbers need updating. The
"before" column is the value printed in the current `build_expanded/manuscript.md`, which was written
from the aliased pipeline. It is quoted at the manuscript's own rounding, because `output/` is not
version-controlled and the pre-correction analysis CSVs were overwritten by this rerun.

Study-level summary, the quantity the manuscript uses for transportability. This is supplement
Table S2 in full, together with the mean absolute error figures quoted at `manuscript.md:20` and
`:116`:

| Quantity | Before | After |
| --- | --- | --- |
| Mean absolute error, mean across 18 held-out cohorts | 0.104 | 0.1006 |
| Between-cohort SD of that error | 0.048 | 0.0472 |
| 95% CI for the mean | 0.080 to 0.128 | 0.0771 to 0.1240 |
| 95% prediction interval for a new cohort | 0.001 to 0.208 | -0.0017 to 0.2029 |
| Brier skill, mean across cohorts | 0.167 | 0.1742 |
| Brier skill, between-cohort SD | 0.210 | 0.2168 |
| Brier skill, 95% CI for the mean | 0.063 to 0.271 | 0.0664 to 0.2821 |
| Brier skill, interval for a new cohort | -0.287 to 0.621 | -0.2958 to 0.6443 |
| Character-weighted AUC, mean across cohorts | 0.710 | 0.7132 |
| AUC, between-cohort SD | 0.105 | 0.1025 |
| AUC, 95% CI for the mean | 0.658 to 0.762 | 0.6623 to 0.7642 |
| AUC, interval for a new cohort | 0.482 to 0.937 | 0.4912 to 0.9353 |
| Calibration intercept, mean across cohorts | -0.078 | -0.0082 |
| Calibration intercept, between-cohort SD | 1.073 | 1.1749 |
| Calibration intercept, 95% CI for the mean | -0.612 to 0.456 | -0.5925 to 0.5761 |
| Calibration intercept, interval for a new cohort | -2.405 to 2.249 | -2.5550 to 2.5386 |
| Calibration slope, mean across cohorts | 1.167 | 1.1004 |
| Calibration slope, between-cohort SD | 0.586 | 0.5596 |
| Calibration slope, 95% CI for the mean | 0.875 to 1.458 | 0.8221 to 1.3787 |
| Calibration slope, interval for a new cohort | -0.104 to 2.437 | -0.1126 to 2.3134 |

**One quantity changed character and must not be carried across unexamined.** The 95% prediction
interval for a new cohort's mean absolute error ran from 0.001 to 0.208 and now runs from -0.0017 to
0.2029. The lower bound crossed zero. This is not a substantive reversal: a mean absolute error
cannot be negative, and the bound is the t-based expression mean plus or minus t times the
between-cohort SD times the square root of one plus one over k, which is not constrained to the
support of the quantity it describes. It was already close to zero before the correction and the
interval barely moved. It matters because the positive lower bound appears in the abstract at
`manuscript.md:20`, in the Results at `:116`, and in supplement Tables S2 and S4, so a later task
could carry "0.001" forward as though the interval still excluded zero. Whichever task rewrites those
sentences should either report the bound as negative or say plainly that it is truncated at zero, and
should not describe the interval as showing that error stays above zero in a new cohort.

Pooled bootstrap summary, conditional on the observed cohorts:

| Quantity | Before | After |
| --- | --- | --- |
| Mean absolute error | 0.103 (0.094 to 0.112) | 0.0984 (0.0906 to 0.1073) |
| Character Brier score | 0.124 (0.115 to 0.134) | 0.1226 (0.1134 to 0.1323) |
| Character Brier skill | 0.098 (0.049 to 0.138) | 0.1095 (0.0626 to 0.1494) |
| Character-weighted AUC | 0.743 (0.714 to 0.766) | 0.7476 (0.7191 to 0.7705) |
| Calibration intercept | 0.080 (-0.290 to 0.464) | 0.0540 (-0.2642 to 0.3946) |
| Calibration slope | 0.950 (0.754 to 1.146) | 0.9667 (0.7911 to 1.1268) |

**The two reference points did not move at all.** The no-predictor benchmark is 0.146246 and the
same-cohort oracle is 0.123370, exactly as before, because `null_benchmark.csv` is byte-identical.
[Correction, 2026-07-27: "same-cohort oracle" is the term this record was written with; it was
retired from the manuscript and supplement during the revision, because the quantity is a benchmark
that estimates every withheld record at that cohort's own mean rather than an oracle. It is called
the held-out-cohort-mean benchmark in the live files. The number is unchanged; only the name is.
This record is left as written otherwise, because it is a dated log of what was run.]
Both are quoted at `manuscript.md:112` as 0.146 and 0.123 and both stand as written. What does move
is the skill computed against the first of them: one minus the ratio of the pooled error to the
no-predictor error was 0.298 and is now 0.3274. Any task touching that sentence should change the
skill and leave the two benchmarks alone.

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
- ALS subgroup: mean absolute error 0.095 to 0.0909, Brier skill 0.287 to 0.3032, AUC 0.828 to
  0.8306, calibration slope 0.991 to 0.9855, and the between-cohort SD of the ALS slope 0.204 to
  0.223, against 0.5596 across all contributing cohorts.
- Transfer with all ALS cohorts withheld: per-cohort error was 0.089, 0.112, 0.124, 0.142 (mean
  0.117) before and is 0.1093, 0.1064, 0.0867, 0.1312 (mean 0.1084) after. Signed bias ranged from
  -0.085 to 0.063 before and from -0.0860 to 0.0488 after. The comparator that sentence is measured
  against, the error in the same four cohorts when other ALS cohorts were available for development,
  was 0.101 and is now 0.1044, so the gap the sentence describes narrows from 0.016 to 0.004.
- ALS moderation: slope 1.018 in other cohorts before and 1.0019 after, 1.672 in ALS cohorts before
  and 1.6993 after, interaction 0.655 before and 0.6974 after. Direction and significance are
  preserved: the ALS slope is still the steeper one and the interaction is still p < 0.001.

### The negative-skill claim changed, and the metric behind it was misidentified

This bullet replaces an earlier version of this document that reported "still 2 of 18, still StudyH
and StudyK, values now -0.110 and -0.044 rather than -0.281 and -0.093". That was wrong twice over,
and the correction matters because the claim appears in the Results at `manuscript.md:120` and in the
Figure 2 caption at `:225`.

The first error was a metric confusion. The manuscript's -0.281 and -0.093 are the error-reduction
skill, one minus the ratio of a cohort's mean absolute error to its own no-predictor error, which is
what Figure 2 plots. The -0.110 and -0.044 previously reported here are `character_brier_skill_score`,
a different column measuring a different thing. The two were compared as though they were the same
quantity.

The second error was to call the cohort identities uncheckable. They are recoverable, because
`null_benchmark.csv` is byte-identical across the rerun and manuscript Table 2 carries the
pre-correction per-cohort mean absolute error. Dividing the second by the first reconstructs the
pre-correction skill for every cohort, and reproduces the manuscript's two negative values as -0.277
and -0.0915 against the published -0.281 and -0.093, the small gap being Table 2's rounding to three
decimals. No other cohort is anywhere near zero, the next-lowest being 0.089, so the identification is
unambiguous.

On the manuscript's own metric:

| | Before | After |
| --- | --- | --- |
| Cohorts with negative error-reduction skill | 2 of 18: StudyH -0.277, StudyJ -0.093 | 1 of 18: StudyH -0.2683 |
| StudyJ | -0.093 | +0.0033 |
| Highest skill in the remainder | 0.668 (StudyS1) | 0.7165 (StudyS1) |
| The four ALS cohorts | 0.226, 0.370, 0.397, 0.474 | 0.3174, 0.3828, 0.4482, 0.5022 |

**The count changed from two cohorts to one.** StudyJ crossed from -0.093 to +0.0033, which is
essentially zero but no longer negative. The pre-correction pair was StudyH and StudyJ, not StudyH
and StudyK.

Three sentences in the current text are therefore false as written and cannot simply be renumbered.
`manuscript.md:120` says skill "was negative in two of 18 cohorts (-0.281 and -0.093) and ranged up to
0.667 in the remainder". The Figure 2 caption at `:225` says "two cohorts without a documented ALS
population were negative". The abstract at `:20` says "skill was negative in two of 18". All four ALS
cohorts do remain positive, and the one remaining negative cohort is still a cohort without a
documented ALS population, so the shape of the claim survives; the count does not. Tasks 8, 11 and 14
own these sentences.

For completeness, since the earlier version of this document quoted them: on
`character_brier_skill_score` the negative cohorts after the correction are StudyH at -0.1105 and
StudyK at -0.0436. That is a real property of the regenerated outputs, but it is not the quantity the
manuscript reports, and the pre-correction values of that column were overwritten by this rerun.

### Two of the four per-cohort extremes changed hands

Unlike the negative-skill identities and the within-cohort correlation floor, these endpoints are
directly checkable, because manuscript Table 2 lists the calibration intercept and slope for every
cohort. Task 4 rewrites that table, so the reordering is worth recording rather than rediscovering.

| Endpoint | Before | After |
| --- | --- | --- |
| Highest calibration slope | StudyA, 2.233 | **StudyS2, 2.1847** (StudyA now 1.9986) |
| Lowest calibration slope | StudyH, 0.075 | StudyH, 0.1852 |
| Highest calibration intercept | StudyH, 1.870 | **StudyS1, 1.9947** (StudyH now 1.7053) |
| Lowest calibration intercept | StudyA, -2.445 | StudyA, -2.1694 |

The two floors keep their cohorts and the two ceilings do not. The range sentence at
`manuscript.md:118` and the Table 2 caption at `:200` quote the endpoint values without naming the
cohorts, so both remain correct once the numbers are replaced, but any text that names the extreme
cohort would now be wrong.

### Sensitivity analyses

Mean absolute error and calibration-slope SD. Before-values are supplement Table S4:

| Analysis | Before | After |
| --- | --- | --- |
| Primary, all contributing cohorts | 0.104, SD 0.586 | 0.1006, SD 0.560 |
| Cohorts with outcome SD at least 0.10 (12 cohorts) | 0.129, SD 0.674 | 0.1242, SD 0.601 |
| Artifact rejection at most 20 percent | 0.084, SD 0.438 | 0.0873, SD 0.465 |
| At least 10 eligible selections | 0.104, SD 0.586 | 0.1004, SD 0.560 |
| Other cohorts only (14 cohorts) | 0.104, SD 0.716 | 0.1007, SD 0.663 |
| ALS cohorts only (4 cohorts) | 0.101, SD 0.204 | 0.0932, SD 0.223 |

The direction and the ordering of every sensitivity are preserved, including the one analysis in
which transportability improves, artifact screening. Every individual figure in the text has to be
updated to the regenerated value.

### What holds and what does not

**One conclusion does change**, and it is the only one: the count of cohorts in which the score does
worse than that cohort's own mean falls from two to one, as set out above. An earlier version of this
document said flatly that no conclusion reverses. That was based on the wrong metric and is
withdrawn. Everything else holds in direction and in ordering: the mapping still fails to transport,
the between-cohort spread in calibration slope is still large, the ALS subgroup is still more
favourable and more precise than the full archive, and artifact screening is still the only
sensitivity that improves transportability.

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

- `output/expanded/figures/` was not re-rendered here, and the three PDF and PNG figures still
  plotted the pre-correction analysis. Task 14 rebuilt every figure from the corrected outputs and
  added `scripts/13_render_figures.py`, which writes all five from one command, so the same drift
  cannot recur unnoticed. Resolved.
- `build_expanded/manuscript.md`, `build_expanded/supplement.md` and the rendered docx and pdf still
  quote the pre-correction numbers listed above. Tasks 4 through 16 rewrite them.
