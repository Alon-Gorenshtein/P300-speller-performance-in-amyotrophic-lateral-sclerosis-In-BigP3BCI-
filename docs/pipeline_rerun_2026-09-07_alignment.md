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

## Task 4: cohort-level Euclidean Alignment, run separately from the arms above

The session-level arm above whitens each recording by its own reference covariance, removing that
recording's own scale but leaving anything a whole cohort shares (amplifier, cap, montage) intact.
The cohort-level arm this section adds, `calibration_auc_ea_cohort`, instead whitens every session
by a reference pooled across its own cohort's sessions, so it is the arm aimed directly at the
Editor-in-Chief's re-alignment question. It reuses Task 3's per-session reference covariances
(`output/intermediate/session_reference_covariances.npz`) rather than recomputing them: one
reference per study is built by grouping the 521 session references on the study component of the
key and pooling them with `alignment.pooled_reference`, weighted by each session's calibration
epoch count.

Because this pass computes only `calibration_auc_ea_cohort` and does not recompute the baseline, it
costs one grouped cross-validation per session rather than the two-to-four the arms above needed. A
5-session timing probe spanning the full epoch-count range (123 to 12,924 epochs; 4,016 epochs/s)
projected 573 s (9.5 min) for the full 521-session, 2,300,139-epoch archive; the full run itself
took under that projection and completed cleanly, writing all 521 rows.

Command:

```bash
caffeinate -ims env UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 \
  uv run python scripts/04b_extract_alignment_features.py --cache data/source_cache_full \
  --cohort-references output/intermediate/session_reference_covariances.npz \
  --merge-into output/intermediate/calibration_features_all20_alignment.csv \
  2>&1 | tee tmp/extract_alignment_pass2.log
```

`calibration_auc_ea_cohort` was merged into the existing `calibration_features_all20_alignment.csv`
on `study`, `study_participant_id`, `session_id` with `validate="one_to_one"`; the merge matched all
521 rows with no key mismatch.

### Cohort references cover 20 studies, not 18

The pooling step groups on whatever study labels are present in the per-session covariance archive,
which is the full 20-study calibration (Train-phase) archive, including StudyC and StudyP. Those two
studies are excluded from the manuscript's 18-cohort transportability design because they contribute
zero eligible Test-phase online-accuracy selections (`docs/source_study_screening.md`), not because
they lack calibration data; their Train EDF files are present and well-formed, and
`calibration_features_all20_alignment.csv` is, by its own name, the all-20-study calibration feature
file that both this pass and Task 3's arms are merged into. Restricting the pooling to 18 studies
would have left StudyC's 15 sessions and StudyP's 38 sessions with no cohort reference to align
against, for no benefit, since nothing about computing their cohort-aligned calibration AUC is
invalid. The table below therefore reports 20 condition numbers, and any consumer of this arm that
needs the 18-cohort transportability subset should filter by study after this column is in hand, the
same way the other three arms already are.

### Cohort-reference condition numbers

| Study | Condition number | Study | Condition number |
| --- | --- | --- | --- |
| StudyA | 3.906e+02 | StudyK | 2.687e+03 |
| StudyB | 5.357e+02 | StudyL | 3.974e+02 |
| StudyC | 2.002e+02 | StudyM | 1.347e+02 |
| StudyD | 6.660e+02 | StudyN | 1.215e+02 |
| StudyE | 5.002e+02 | StudyO | 9.147e+02 |
| StudyF | 5.293e+02 | StudyP | 6.822e+02 |
| StudyG | 6.958e+02 | StudyQ | 4.305e+02 |
| StudyH | 4.723e+02 | StudyR | 4.854e+02 |
| StudyI | 3.421e+02 | StudyS1 | 4.134e+02 |
| StudyJ | 2.658e+02 | StudyS2 | 4.052e+02 |

19 of the 20 cohort references sit between 1.215e+02 (StudyN) and 9.147e+02 (StudyO), a range typical
of a 16-by-16 covariance pooled over thousands of epochs. StudyK is an outlier at 2.687e+03, roughly
3 to 22 times every other cohort's value.

Session count does not explain it: StudyK and StudyE both pool exactly 8 sessions, yet StudyE's
condition number (5.002e+02) sits squarely inside the unremarkable range. What actually singles
StudyK out is total pooled calibration epochs, the quantity `pooled_reference` weights by, not the
number of sessions contributing to the average: StudyK pools 16,071 epochs, the fewest of any of the
20 studies, against StudyE's 34,272, roughly double, and against the archive-wide range that runs up
to StudyQ's 460,644. StudyK's pooled covariance is simply built from the least data of any cohort
reference, so it is the least well estimated, and less averaging leaves more of any one session's
particular epoch sample in the pooled matrix. StudyK is worth flagging in the supplement as both the
smallest-data and the most extreme-conditioned cohort reference in the archive.

That said, StudyK still sits four orders of magnitude below any numerically concerning range for a
double-precision inverse-square-root whitener (the eigenvalue floor in `alignment.inverse_square_root`
only engages once a matrix's own condition number approaches 1e10). No cohort crossed the pass's own
`> 1e4` flag threshold, so nothing here indicates the whitener is amplifying noise; StudyK's elevated
but still well-conditioned reference is noted because it is the one cohort furthest from the pack and
built from the least data, not because it is unsafe.

### Score-level movement

Same interpretation bands as the session-level arm: a Spearman correlation above 0.98 against the
baseline `calibration_auc` means the arm reorders sessions barely at all; below 0.90 means the arm
measures something materially different.

| Arm | n | Mean | SD | Mean change vs baseline | SD of change | Max \|change\| | Spearman vs `calibration_auc` | Band | Moved up | Moved down |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `calibration_auc_ea_session` | 520 | 0.8005 | 0.1088 | -0.0041 | 0.0199 | 0.0803 | 0.9864 | above 0.98: reorders barely at all | 219 | 301 |
| `calibration_auc_ea_cohort` | 520 | 0.8021 | 0.1073 | -0.0025 | 0.0170 | 0.1197 | 0.9902 | above 0.98: reorders barely at all | 214 | 306 |
| `calibration_auc_rbf` | 520 | 0.7140 | 0.0903 | -0.0906 | 0.0546 | 0.2545 | 0.8371 | below 0.90: materially different | 23 | 497 |
| `calibration_auc_gbm` | 520 | 0.7139 | 0.0951 | -0.0907 | 0.0441 | 0.2274 | 0.9043 | neither band: see below | 11 | 509 |

(Baseline `calibration_auc_reproduced` over the same 520 sessions: mean 0.8046, SD 0.1013.)

`calibration_auc_ea_cohort` lands in the same top band as the session-level arm, and slightly further
into it: Spearman 0.9902 against 0.9864, meaning whitening by a pooled cohort reference reorders
sessions even less than whitening each session by its own reference does, and its mean shift
(-0.0025) is smaller than the session-level arm's (-0.0041). Both alignment arms leave session
ordering almost untouched; whichever change either arm produces to the tau heterogeneity statistic
elsewhere in this revision reflects a change in scale, not in which sessions the pipeline judges most
discriminable. This section is a record of that score-level movement only; it says nothing about
transportability, which is reported wherever the transportability sweep consumes this column.

### The two alignment arms are not interchangeable: a cheap-and-immediate arm versus a stronger-but-more-demanding one

Session-level and cohort-level alignment answer the Editor's re-alignment question with two
different deployment stories, and the difference is a real constraint on what either arm can claim,
not an implementation detail. Session-level Euclidean Alignment whitens a recording by its own
reference covariance, computed from that recording's own calibration epochs; a new site can apply it
to its very first user's very first session; nothing outside that one recording is needed. Cohort-
level alignment whitens a session by a reference pooled across its cohort's other sessions, computed
here from that cohort's own held-out calibration recordings. That is legitimate transductive,
label-free, unsupervised adaptation, since it needs no online-accuracy outcome, but it is not free in
the way the session-level arm is: a new site cannot use it on its first user, because there is no
cohort yet to pool. It must first collect calibration recordings from several users to estimate its
own cohort reference before the whitener it fits can be applied to anyone. Read together, these are a
cheap-and-immediate arm and a stronger-but-more-demanding arm, not two variants of the same
intervention, and if their transportability behaviour differs, that difference is itself a result
about what re-alignment can and cannot buy a site depending on how much data it can collect before it
starts.

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

**For whoever reruns this script next:** the plan budgeted about 50 minutes for the full pass and
under 10 minutes for the smoke test. Under the `PCA(150)`, class-balanced GBM configuration this file
leaves in place, the real figures are roughly 4 hours for the full pass and 50 to 60 minutes for the
smoke test, both far past the plan's estimate. The plan's numbers held only for the initial, unfair
GBM configuration (6 min 56 s smoke, 40 min 52 s full, both consistent with "about 50 minutes" and
"under 10 minutes") and do not hold once the fairness fix is applied.

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
class-balanced boosted-tree boundary given a generously-sized feature budget reorders sessions
somewhat more like the linear model than the RBF arm does, but still moves 509 of 520 sessions
downward, with
a mean shift of -0.0907, similar in size to the RBF arm's -0.0906. Neither nonlinear arm exceeds the
linear model's discriminability on this archive, which speaks directly to the referee's question:
whatever is limiting transportability in this cohort archive is not simply an artefact of the
calibration classifier being linear, since giving the boundary more flexibility does not raise
discriminability above what the linear model already achieves. That said, `calibration_auc_gbm`'s
position outside either pre-registered band means its transportability result in Task 5 should be
read as partly informative about the linear score's own behaviour (through the correlation) and
partly its own thing (through the residual reordering and the mean AUC gap), rather than cleanly
assigned to one interpretation.

**The most useful single number this pass produces for the referee's question is that the two
nonlinear arms agree with each other almost exactly, not with the linear baseline.** RBF's mean AUC
is 0.71401 and the fair GBM arm's is 0.71394, a difference of 0.00006, against a linear baseline mean
of 0.80463: both nonlinear arms fall short of the linear model by essentially the same amount (0.0906
and 0.0907). A kernel approximation with a logistic head and a boosted-tree ensemble on a
principal-component reduction are structurally unrelated ways of fitting a nonlinear boundary, built
from different libraries, different hyperparameters and, for GBM, a different dimensionality
reduction entirely. Two unrelated model families landing within six hundred-thousandths of an AUC
point of each other is much stronger evidence than either arm alone that roughly 0.714 is a genuine
ceiling this data imposes on nonlinear calibration discriminability, rather than an artefact of one
modelling choice. Had the original, unfair GBM configuration's mean of 0.6548 been reported instead,
it would have implied a materially larger linear advantage over nonlinear boundaries (a gap of 0.150
rather than 0.091) and would have obscured this convergence entirely, since 0.6548 sits nowhere near
either the linear baseline or the RBF arm.

## GBM arm fairness correction, made before any transportability analysis used the column

The first version of the `gradient_boosting` branch in `_grouped_cv_predictions` used
`PCA(n_components=40)` and left `HistGradientBoostingClassifier`'s `class_weight` at its scikit-learn
default of `None`, while the linear arms it was meant to compare against, the baseline and the RBF
arm, both fit `LogisticRegression(class_weight="balanced")`. The class-weight omission is
unambiguous: the median non-target-to-target imbalance across the 520 evaluable sessions is 10.98 to
1, and an unweighted boosted-tree loss at that imbalance is dominated by the majority class, while the
linear arms' `class_weight="balanced"` corrects for it.

Whether 40 components was also a real handicap is a question about how much variance that budget
throws away, and an early draft of this fix answered it by picking a number that matched the RBF
arm's 300 Nystroem components. That comparison does not hold: Nystroem components approximate a
kernel, PCA components retain variance, and the two counts are not the same currency. The right way
to answer the question is to measure the variance a candidate budget retains on real sessions,
not to match a count from an unrelated reduction.

**Measurement.** Five real sessions from `data/source_cache_full` were probed, spanning the size
range: the smallest evaluable session (`StudyJ:J_07|SE001`, 123 calibration epochs total), sessions
near the 25th, 50th and 75th percentiles of `n_calibration_epochs` (`StudyB:B_17|SE003`, 3,778;
`StudyO:O_17|SE002`, 4,312; `StudyP:P_18|SE002`, 4,320), and the largest session in the archive
(`StudyA:A_02|SE001`, 12,924). For each, `_downsampled_epoch_features` was built exactly as the
classifier sees it, `StratifiedGroupKFold` was run with the same `random_state`, and PCA was fit on
the smallest training fold that split actually produces for that session, the worst case the
classifier itself trains on. Cumulative explained-variance ratio at 20, 40, 60, 80, 100 and 150
components:

| Session | Smallest training fold (samples) | 20 | 40 | 60 | 80 | 100 | 150 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `StudyJ:J_07\|SE001` (smallest, 123 epochs) | 65 | 0.8792 | 0.9662 | 0.9974 | 1.0000 | 1.0000 | 1.0000 |
| `StudyB:B_17\|SE003` (p25, 3,778 epochs) | 2,878 | 0.5578 | 0.6855 | 0.7759 | 0.8211 | 0.8507 | 0.9024 |
| `StudyO:O_17\|SE002` (p50, 4,312 epochs) | 3,360 | 0.6795 | 0.8089 | 0.8719 | 0.9129 | 0.9377 | 0.9662 |
| `StudyP:P_18\|SE002` (p75, 4,320 epochs) | 3,360 | 0.6411 | 0.7659 | 0.8356 | 0.8738 | 0.9012 | 0.9405 |
| `StudyA:A_02\|SE001` (largest, 12,924 epochs) | 10,291 | 0.5796 | 0.7657 | 0.8325 | 0.8693 | 0.8955 | 0.9331 |

The smallest session is a degenerate case: with only 65 samples in its worst training fold, 40
components already retain 96.6% of the variance, and the budget is capped at the fold size anyway.
On the four substantive sessions, the ones with enough data for a 1,024-dimensional feature space to
carry real structure, the picture is different. **The original 40-component budget retained only 56
to 81 percent of variance. 150 components retains 90 to 97 percent, closing most but not all of the
gap; no probed session reaches 95% at 150 components except the p50 session at 96.6%.** So both
suspected defects were real: the missing class weighting was the unambiguous part, and the 40-component
PCA budget was, independently, throwing away roughly half the variance the classifier's own feature
representation carries on a typical session.

**The budget used is 150, chosen as generous rather than tuned.** It was not selected to hit a
variance target exactly, and it does not: three of the four substantive probe sessions fall short of
95% even at 150 components. It was selected because it recovers most of the variance the 40-component
budget discarded, at a computational cost the archive could still absorb (see the runtime discussion
below), and because a generous rather than a precisely-tuned budget means a null result for this arm
cannot later be attributed to under-resourcing it. A reader checking whether 150 was picked to match
the RBF arm's component count should read this section as the record that it was not; an earlier
draft of this fix and its code comments said exactly that, and both have been corrected.

The fix, applied before this record and before Task 4 or Task 5 read the column: `class_weight="balanced"`
was added to `HistGradientBoostingClassifier`, and the PCA budget was raised to 150 components, floored
per session at one less than the smallest training fold actually produced by that session's grouped
split. This is computed once per session inside `_grouped_cv_predictions`, before the cross-validation
loop, and only affects the `gradient_boosting` branch; `Nystroem`, the RBF arm's dimensionality
reducer, already caps its own `n_components` at `n_samples` internally, which is why the RBF arm
needed no equivalent change.

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
