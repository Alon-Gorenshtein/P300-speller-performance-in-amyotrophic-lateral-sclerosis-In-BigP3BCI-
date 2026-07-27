# Analysis design note for the original four-cohort study, 2026-07-18

**This is not a registered analysis plan, and it was never registered anywhere.** It is the project's
own working design note for the original study, written and committed on 2026-07-18 (commits
`6971f4d` and `c426986`), before the design was widened from the four documented ALS cohorts to every
source study that yields an eligible online outcome. It is kept, unedited below this heading, because
the Methods say the ALS subgroup was fixed in the project documentation before that widening and that
the commit history records the dates. This file is that documentation, and its history is that
record. It is retained as evidence of ordering, not offered as a protocol.

Two things follow, and the manuscript states both. Nothing in this study is prespecified in the sense
a registered plan would establish. And the design this note describes is the four-cohort one: it
holds out only Studies B, F, L and N, so it does not describe the widened analysis the manuscript
reports, and the sensitivity, comparator and protocol-moderator analyses reported there were fixed
later. The protocol-descriptor moderator analysis was added later still and is exploratory.

---

The primary model uses only calibration-phase grouped cross-validated P300 AUC. The primary outcome is the proportion of correct eligible online selections among all eligible selections in each study-scoped participant-session-condition. The model is trained on all but one source study and evaluated in the complete held-out source study, repeated until Studies B, F, L, and N have each been held out once. No observation from a held-out source study contributes to feature standardization or model fitting.

The primary cross-study results are session-condition probability-estimation measures: unweighted and selection-weighted mean absolute error, root mean squared error, Brier score, Brier skill score versus the training-source prevalence, and logistic calibration intercept and slope. Character-weighted ROC AUC is secondary and is labelled as a ranking metric for session-condition scores rather than as individual-character prediction. Raw-score and logistic-prediction AUCs are reported together because the primary model has one monotonic predictor.

Confidence intervals use 2,000 deterministic bootstrap replicates. In each replicate, participant clusters are resampled within every development source study, the probability model is refit, and participant clusters are resampled in the held-out source study before metrics are recalculated. This preserves each participant's nested sessions and conditions and incorporates training-model uncertainty.

Comparator analyses replace the primary score with posterior target-minus-nontarget amplitude, posterior signed r-squared, calibration classification accuracy, regularized linear discriminant analysis AUC, or Pz amplitude. The ALSFRS-R-enhanced model is exploratory and is restricted to records with an observed numerical ALSFRS-R value. None of these analyses supports causal, prognostic, or access-restriction language.
