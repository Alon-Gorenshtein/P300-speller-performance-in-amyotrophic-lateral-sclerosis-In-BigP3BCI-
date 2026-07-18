# Statistical analysis plan

The primary model uses only calibration-phase cross-validated P300 AUC. The outcome is the number of correct eligible online selections of the total eligible selections within each study-scoped participant-session-condition. The model is fit on two source studies and evaluated in the entire third source study; each study is held out once. No observation from a held-out study contributes to feature standardization or model fitting.

Each held-out study is reported before the pooled out-of-study summary. Reported performance is character-level ROC AUC and Brier score, session-condition mean absolute error, and logistic calibration intercept and slope. Confidence intervals use 1,000 deterministic bootstrap resamples of study-scoped participant clusters, preserving each selected participant's sessions and conditions.

Secondary analysis substitutes Pz target-minus-nontarget amplitude. The ALSFRS-R-enhanced model is exploratory; it does not support causal or prognostic language.
