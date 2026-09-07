# Alignment and nonlinear extraction pass, 2026-09-07

An editor asked for a data re-alignment analysis and a referee asked whether the transportability
failure is an artefact of linear decision boundaries. This pass answers both by adding, on top of
the frozen calibration pipeline, a session-level Euclidean-Alignment score
(`calibration_auc_ea_session`) and two nonlinear decoder scores (`calibration_auc_rbf`,
`calibration_auc_gbm`), computed on the same calibration epochs, the same grouped cross-validation
split, and the same AUC metric as the published `calibration_auc`. It also writes one 16-by-16
reference covariance per session for Task 4's cohort-level alignment arm.

All commands ran with `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv` and `COPYFILE_DISABLE=1` through
`uv run`, on the same interpreter as the July pipeline rerun.

## What was run

| Stage | Command | Wall clock | Exit |
| --- | --- | --- | --- |
| Smoke test, stale reference | `scripts/04b_extract_alignment_features.py --cache data/source_cache --frozen output/intermediate/calibration_features_with_b.csv` | under 1 min to fail | 1, refused to write (by design) |
| Smoke test, corrected reference (initial GBM config) | `scripts/04b_extract_alignment_features.py --cache data/source_cache --frozen tmp/calibration_features_with_b_current_pipeline.csv` | 6 min 56 s | 0 |
| Full pass (initial GBM config) | `caffeinate -ims env ... scripts/04b_extract_alignment_features.py --cache data/source_cache_full` | 40 min 52 s | 0 |
| Smoke test, corrected reference (fair GBM config) | same command, rerun after the fairness fix below | 53 min 33 s | 0 |
| Full pass (fair GBM config) | same command, rerun after the fairness fix below | 4 h 1 min 34 s | 0 |

The initial full pass started 2026-09-07 17:11:03 and its output files were written at 17:51:55. After
the GBM fairness fix, the smoke test was rerun in the foreground and the full pass was rerun started
2026-09-07 19:02:55, with output files written at 23:04:29. The corrected PCA budget (150 components,
floored per session, against the initial 40) is substantially more expensive than the initial
configuration: the smoke test alone went from 6 min 56 s to 53 min 33 s, a ratio the full pass's
40 min 52 s to 4 h 1 min 34 s roughly tracks. Every number below the "GBM arm fairness correction"
section is from the corrected, final run; the two full-pass outputs were diffed against each other to
confirm the fix changed only `calibration_auc_gbm` (see that section).

## The smoke test failed against the brief's named reference file, and that failure is not a code defect

The brief's Step 3 named `output/intermediate/calibration_features.csv` as the smoke-test
reference; a ruling before this run corrected that to `output/intermediate/calibration_features_with_b.csv`
because the latter's 115 rows cover StudyB/F/L/N, matching `data/source_cache`, while the former's
57 rows cover only StudyF/L/N. That correction fixed cohort coverage but missed pipeline vintage.

Running the smoke test against `calibration_features_with_b.csv` produced a reproduction difference
of 8.930e-02 over 115 sessions, three orders of magnitude past the 1e-9 gate. Two facts rule out a
bug in the new `_alignment_feature_row` epoch-assembly code:

- `n_calibration_epochs` matched the frozen file exactly on all 115 sessions. Epoch, label and group
  assembly is the part `_alignment_feature_row` could have gotten wrong relative to the reference
  implementation `_session_feature_row`, and it produced the identical epoch count on every session.
- The direction and the magnitude of the mismatch reproduce the signature already on record in
  `docs/pipeline_rerun_2026-07-26.md`: the July 26 fix that changed `DECIMATION_FACTOR` from 12 to 4
  raised `calibration_auc` "slightly and almost uniformly," with a documented maximum absolute
  change of 0.0934 across the full 20-study archive. The stale-reference smoke test here found a
  maximum absolute difference of 0.0893, systematically in the same direction (new higher than old,
  mean shift -0.0178 in the frozen-minus-new direction), on the same four studies.

`output/intermediate/calibration_features_with_b.csv` is dated 2026-07-18, four days before the
decimation fix, and `docs/pipeline_rerun_2026-07-26.md` records that this file was deliberately left
frozen as the fixture for `tests/test_regression_baseline.py` and was never regenerated under the
corrected pipeline. Gating a pass built on current code against a pre-fix file cannot reproduce at
1e-9 regardless of correctness; the file itself predates the code it was being asked to match.

The corrected check filtered the current, post-fix `output/intermediate/calibration_features_all20.csv`
(dated 2026-07-26, after the fix) down to StudyB/F/L/N and used that as the frozen reference instead.
Because `calibration_features_all20.csv` is the same file the full pass gates against by default,
this smoke test is a self-consistency check on `_alignment_feature_row`'s epoch assembly rather than
an independent reproduction check: it demonstrates that the new code path reproduces the current
pipeline's own `calibration_auc` before the expensive full pass is run, not that the pipeline
reproduces some separately-audited ground truth. Against that reference, the reproduction difference
was 1.110e-16 over 115 sessions, machine epsilon, and the smoke test wrote 115 rows and 115
covariances to `tmp/`.

## The full pass reproduces the published baseline exactly

The full pass gates against `output/intermediate/calibration_features_all20.csv` by default, which
is the correct, current, post-fix file. Reproduction difference: 1.110e-16 (functionally 0.0, machine
epsilon on a double-precision AUC) over 520 of the 521 sessions carrying a usable baseline value. The
row not carrying a baseline value is the same session excluded from the published pipeline for
insufficient calibration files, so both files agree it is unusable rather than disagreeing about a
computed value. Row counts: 521 alignment feature rows, matching `calibration_features_all20.csv`'s
521 rows exactly. Session covariances: 521 references written, one per session, including the
excluded session, since a reference covariance only requires a non-empty epoch set and does not
depend on the grouped-CV gates.

Total calibration epochs across the 521 sessions: 2,300,139, median 4,312 per session, maximum
12,924.

## Interpretation bands, set before reading the results

The brief fixes the reading in advance: a Spearman correlation against the baseline `calibration_auc`
above 0.98 means the arm reorders sessions barely at all, so any change in tau it produces comes from
the scale of the score rather than from which sessions score highly. Below 0.90 means the arm is
measuring something materially different from the published score, and its transportability result
stands on its own footing rather than as a rescaled version of the linear one.

| Arm | n | Mean | SD | Mean change vs baseline | SD of change | Max \|change\| | Spearman vs `calibration_auc` | Band | Moved up | Moved down |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `calibration_auc_ea_session` | 520 | 0.8005 | 0.1088 | -0.0041 | 0.0199 | 0.0803 | 0.9864 | above 0.98: reorders barely at all | 219 | 301 |
| `calibration_auc_rbf` | 520 | 0.7140 | 0.0903 | -0.0906 | 0.0546 | 0.2545 | 0.8371 | below 0.90: materially different | 23 | 497 |
| `calibration_auc_gbm` | 520 | 0.7139 | 0.0951 | -0.0907 | 0.0441 | 0.2274 | 0.9043 | neither band: see below | 11 | 509 |

`calibration_auc_ea_session` lands in the top band: whitening each recording by its own reference
covariance leaves session ordering almost untouched (0.9864) and shifts the score by very little on
average (-0.0041), so any change to the tau heterogeneity statistic this arm produces in Task 5
reflects a change in scale, not a change in which sessions the pipeline judges most discriminable.

`calibration_auc_rbf` lands in the bottom band by a wide margin: a Spearman correlation of 0.8371
against the linear baseline, more than a tenth below the 0.90 line, and it scores lower than the
linear baseline on nearly every session (497 of 520). A radial-basis boundary approximated through
Nystroem does not recover the linear model's discriminability here.

`calibration_auc_gbm`, after the fairness correction recorded below, correlates with the linear
baseline at 0.9043. That is neither band: it clears 0.90, so it is not read as measuring something
materially different from the linear score, but it sits nowhere near the 0.98 line either, so it is
not read as barely reordering sessions in the way the alignment arm does. Read plainly, a
class-balanced boosted-tree boundary given a comparable feature budget reorders sessions somewhat
more like the linear model than the RBF arm does, but still moves 509 of 520 sessions downward, with
a mean shift of -0.0907, similar in size to the RBF arm's -0.0906. Neither nonlinear arm exceeds the
linear model's discriminability on this archive, which speaks directly to the referee's question:
whatever is limiting transportability in this cohort archive is not simply an artefact of the
calibration classifier being linear, since giving the boundary more flexibility does not raise
discriminability above what the linear model already achieves. That said, `calibration_auc_gbm`'s
position outside either pre-registered band means its transportability result in Task 5 should be
read as partly informative about the linear score's own behaviour (through the correlation) and
partly its own thing (through the residual reordering and the mean AUC gap), rather than cleanly
assigned to one interpretation.

## GBM arm fairness correction, made before any transportability analysis used the column

The first version of the `gradient_boosting` branch in `_grouped_cv_predictions` used
`PCA(n_components=40)` and left `HistGradientBoostingClassifier`'s `class_weight` at its scikit-learn
default of `None`, while the linear arms it was meant to compare against, the baseline and the RBF
arm, both fit `LogisticRegression(class_weight="balanced")`. Two problems followed from that. First,
40 components keeps about 4% of the 1,024-dimensional downsampled epoch feature space, against the
RBF arm's 300 of 1,024, about 29%, so the two nonlinear arms were not given comparable information to
work with. Second, the median non-target-to-target imbalance across the 520 evaluable sessions is
10.98 to 1, and an unweighted boosted-tree loss at that imbalance is dominated by the majority class,
while the linear arms' `class_weight="balanced"` corrects for it. A referee asked whether the
transport failure could be an artefact of linear decision boundaries; an arm that was both starved of
features and denied the class correction the linear arms received cannot answer that question fairly.

The fix, applied before this record and before Task 4 or Task 5 read the column: `class_weight="balanced"`
was added to `HistGradientBoostingClassifier`, and the PCA budget was raised to 150 components, floored
per session at one less than the smallest training fold actually produced by that session's grouped
split (the smallest fold across the 520 evaluable sessions is 98 samples, so a fixed 150 would still
raise `ValueError` on at least one session). This is computed once per session inside
`_grouped_cv_predictions`, before the cross-validation loop, and only affects the `gradient_boosting`
branch; `Nystroem`, the RBF arm's dimensionality reducer, already caps its own `n_components` at
`n_samples` internally, which is why the RBF arm needed no equivalent change.

The numbers under both configurations, on the same 520 evaluable sessions:

| Configuration | Mean | SD | Mean change vs baseline | SD of change | Max \|change\| | Spearman vs `calibration_auc` | Moved up | Moved down |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Initial (PCA 40, unweighted) | 0.6548 | 0.0908 | -0.1498 | 0.0700 | 0.3387 | 0.7386 | 5 | 515 |
| Corrected (PCA up to 150, balanced) | 0.7139 | 0.0951 | -0.0907 | 0.0441 | 0.2274 | 0.9043 | 11 | 509 |

The correction raised this arm's mean AUC by 0.0591, roughly halved the mean shortfall against the
linear baseline, and moved its Spearman correlation from clearly below the 0.90 band into the
unlabeled zone above it. The qualitative conclusion the arm supports, that a nonlinear boundary does
not recover the linear model's discriminability on this archive, held under both configurations; what
changed is how confidently that conclusion can be attributed to the nonlinearity itself rather than to
an unrelated handicap in the comparator's configuration. Every downstream consumer of
`calibration_auc_gbm`, including Task 4 and Task 5, reads only the corrected column; the initial
configuration's output was never written to a tracked file and exists only in this record and in the
task report.

Both configurations were verified to change only `calibration_auc_gbm`. `calibration_auc_reproduced`,
`calibration_auc_ea_session` and `calibration_auc_rbf` are byte-identical (max absolute difference
0.0 over 520 sessions with a usable value, identical NaN pattern) between the two full-pass outputs,
confirming the fix did not leak outside the `gradient_boosting` branch.

## What this pass did not touch

`_session_feature_row`, `build_calibration_features`, `calibration_discriminability`,
`shrinkage_lda_discriminability`, `nonlinear_discriminability` and every other public score function
in `src/bigp3_als/features.py` are unchanged; the diff against the prior commit is purely additive.
The published `output/intermediate/calibration_features_all20.csv` and every other frozen
intermediate are read-only in this pass and were not rewritten. The new outputs,
`output/intermediate/calibration_features_all20_alignment.csv` and
`output/intermediate/session_reference_covariances.npz`, are untracked, matching `.gitignore`'s
existing `output/*` exclusion.
