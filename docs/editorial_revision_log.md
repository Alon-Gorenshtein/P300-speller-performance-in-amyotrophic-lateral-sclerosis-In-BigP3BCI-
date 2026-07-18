# Editorial Revision Log

The attached editorial assessment was treated as a major revision before any revised submission package is built.

## Changes implemented

1. The primary outcome is the participant-session-condition proportion of correct eligible online selections, modeled as a binomial count. Character-expanded AUC is retained only as a secondary, character-weighted ranking measure.
2. The cohort now includes every ALS-labelled BigP3BCI source study with the shared 16-channel montage and recoverable Train and Test phases: B, F, L, and N. Numerical ALSFRS-R was removed as an eligibility criterion because it is exploratory only.
3. The validation terminology is source-study-held-out or cross-study. The manuscript will not describe the legacy source studies as independent external clinical cohorts.
4. Primary model evaluation now reports session-level MAE, RMSE, Brier score, Brier skill score, calibration intercept, and calibration slope. Every confidence interval uses 2,000 participant-cluster bootstrap replicates that refit the development model and resample the held-out source study.
5. The analysis records raw-score and logistic-probability character AUCs side by side. With a single monotonic predictor they are equal within each held-out source study; the pooled difference reflects source-specific probability transformations.
6. Comparator features now include posterior target-minus-nontarget amplitude, posterior signed r-squared, grouped calibration accuracy, regularized LDA AUC, Pz amplitude, usable calibration epoch count, and artifact-rejection fraction.
7. The revised manuscript will cite direct ALS P300 performance-prediction literature and frame the contribution as transparent cross-study evaluation with strict Train/Test phase separation, not as the first evidence that EEG and P300-BCI performance are related.

## Remaining production work

The manuscript, supplement, figures, AMA bibliography, cover letter, and rendered submission folder must be regenerated from the revised outputs. The prior submission package is superseded and must not be submitted.
