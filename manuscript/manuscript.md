---
title: "Source-study-held-out estimation of online P300-speller session accuracy from calibration EEG in amyotrophic lateral sclerosis"
subtitle: "Revised manuscript draft for Journal of Neural Engineering"
---

**Authors, affiliations, corresponding author, funding, competing interests, and CRediT roles:** [to be completed by submitting authors]

## Abstract

### Objective

Calibration EEG is collected before online P300-speller use, but its ability to estimate subsequent session accuracy across source studies is uncertain. We evaluated a calibration-derived EEG score in public legacy amyotrophic lateral sclerosis (ALS) cohorts.

### Approach

This retrospective secondary analysis used BigP3BCI version 1.0.0. Four ALS source studies were screened into the primary cohort. The calibration-only predictor was grouped cross-validated multichannel P300 discriminability. The primary outcome was the proportion of correct eligible feedback selections within each participant-session-condition record. Models were trained on all but one source study and evaluated in the held-out source study. Confidence intervals used 2,000 participant-cluster bootstrap replicates that refit the development model and resampled the held-out cohort.

### Main Results

The cohort contained 47 study-scoped records, 113 participant-sessions, 194 session-condition records, and 3,318 eligible online selections. The pooled held-out model had session-condition mean absolute error 0.095 (95% CI, 0.080-0.115), root mean squared error 0.128, character-weighted Brier score 0.110, Brier skill score 0.287, calibration intercept 0.022, and slope 0.991. Character-weighted AUC was 0.828 for model probabilities. A regularized linear discriminant analysis calibration AUC yielded similar error, whereas Pz and posterior-amplitude summaries had mean absolute errors near 0.198.

### Significance

Calibration-derived EEG information was associated with average subsequent online P300-speller accuracy in held-out legacy ALS source studies. The findings support prospective evaluation of calibration quality as a session-level operational check. They do not establish individual-character prediction, clinical readiness, or criteria for restricting communication-technology access.

## Introduction

P300 spellers can provide a communication pathway for people with ALS when conventional motor access is limited.[1,2] Online performance varies between users and across sessions. EEG features have previously correlated with P300-BCI performance in ALS.[3] This evidence establishes the biological and operational premise, but does not remove the need for evaluation that keeps calibration predictors separate from later online outcomes.

BigP3BCI is a public archive of legacy online P300-BCI studies with EEG, stimulus events, and feedback streams.[4] Its ALS cohorts differ in matrix size, electrode type, and session design. Such heterogeneity makes in-sample association insufficient, but it permits a stringent source-study-held-out test of whether a simple calibration score can estimate average later accuracy.

We evaluated calibration-derived multichannel discriminability for estimating online P300-speller session-condition accuracy across held-out ALS source studies. The contribution is transparent phase separation, source-study-held-out evaluation, and reproducible processing of a public archive, rather than the first demonstration that EEG relates to P300-BCI performance.

## Methods

### Design, Data Source, and Cohort

This retrospective secondary analysis used BigP3BCI v1.0.0.[4] All 20 documented source studies were screened. Studies B, F, L, and N were included because each was documented as an ALS cohort and supplied compatible Train and Test EDF phases with the shared 16-channel montage. Numerical ALSFRS-R was not an eligibility criterion because severity was exploratory. Archive and member checksums were verified before processing (Supplementary Methods). The original-study ethics and consent statements are reported in the dataset documentation; the submitting institution must confirm its local determination for this de-identified public-data analysis.

### Predictor and Outcome

Only Train-phase EEG informed predictors. Rising phase-2 StimulusBegin events were labelled by StimulusType. The 16 shared channels were filtered from 0.5 to 30 Hz with a fourth-order, zero-phase Butterworth filter, epoched from -200 to 800 ms, baseline corrected, and excluded when absolute amplitude exceeded 150 microvolts. The primary score was grouped, EDF-file-held-out AUC of an L2-regularized logistic classifier using temporally downsampled multichannel epochs. No Test data were read during feature extraction.

The primary outcome was correct eligible feedback selections divided by eligible selections within each participant-session-condition record. The target was the final nonzero CurrentTarget during the contiguous preceding phase-2 interval; the selection was the modal nonzero SelectedTarget during phase 3. Feedback phases without displayed feedback, a recoverable target and selection, or without artificial-feedback override were excluded with an explicit reason.

### Statistical Analysis

For each held-out source study, a logistic probability model was fit in the remaining source studies after development-only standardization. Primary metrics were unweighted and selection-weighted session-condition error, Brier score and Brier skill relative to development prevalence, and calibration intercept and slope. Character-weighted AUC was secondary. The raw calibration score and fitted-probability AUCs were reported together. In each of 2,000 deterministic bootstrap replicates, development participant clusters were resampled within source study, the model was refit, and held-out participant clusters were resampled. Comparator analyses used posterior amplitude, posterior signed r-squared, calibration accuracy, regularized LDA AUC, and Pz amplitude. Analyses used Python 3.11.

## Results

### Cohort

The included sources contributed 18, 10, 11, and 8 study-scoped records in Studies B, F, L, and N, respectively. The 194 participant-session-condition records represented 3,318 eligible selections, of which 2,699 were correct. Study B contributed 56 records, Study F 89, Study L 33, and Study N 16 (Table 1).

### Source-Study-Held-Out Estimation

The pooled held-out probability model had session-condition mean absolute error 0.095 (95% CI, 0.080-0.115), root mean squared error 0.128, character-weighted Brier score 0.110, and Brier skill score 0.287. Calibration intercept was 0.022 (95% CI, -0.301 to 0.378) and slope was 0.991 (95% CI, 0.783-1.201). Held-out-study MAE ranged from 0.076 to 0.129 (Figure 3). Character-weighted AUC was 0.828 for model probabilities; raw-score and probability AUCs were identical within each held-out study and differed by 0.006 in the pooled summary because source-specific probability transformations changed pooled ranking.

### Comparator Analyses

Regularized LDA calibration AUC had similar pooled MAE (0.095) and Brier skill (0.283). Calibration classification accuracy, posterior signed r-squared, Pz amplitude, and posterior amplitude had pooled MAEs of 0.154, 0.184, 0.197, and 0.198, respectively. No comparator supports access-restriction or clinical-deployment claims.

## Discussion

In four historical ALS P300-speller source studies, calibration-derived discriminability estimated average later online session-condition accuracy when each source study was held out from model fitting. The probability metrics, rather than the secondary character-weighted AUC, are the central result. The calibration slope was close to 1, but the intervals and the small number of source studies require cautious interpretation.

Prior ALS work found that ERP amplitude and spectral features relate to P300-BCI performance.[3] The present analysis extends that premise by enforcing separation between calibration and later feedback phases and by evaluating across source studies. Its result is not evidence that an EEG score should select candidates for BCI access. A prospective study should predefine a calibration-quality review procedure, measure user-centered communication outcomes, and test whether review improves preparation without withholding a communication option.

### Study Limitations

First, this was a retrospective analysis of legacy protocols and does not establish performance with contemporary assistive-communication workflows. Second, only four source studies were available, limiting transportability assessment. Third, identifiers are study-scoped and cannot establish cross-study person uniqueness. Fourth, session-condition accuracy is an operational endpoint, not communication effectiveness, quality of life, or clinical outcome. Fifth, numerical ALSFRS-R was unavailable in Study B and was not used in the primary model.

## Tables and Figure Legends

**Table 1. Included ALS source studies and analytic records.** Study B: 18 records, 56 session-condition records, 781 eligible selections; Study F: 10, 89, 1,067; Study L: 11, 33, 990; Study N: 8, 16, 480. Totals: 47 records, 194 session-condition records, and 3,318 eligible selections.

**Figure 1. Source-study screening and analytic flow.** All 20 BigP3BCI source studies were screened; four documented ALS cohorts with compatible Train and Test phases entered the analysis.

**Figure 2. Calibration discriminability and observed session-condition accuracy.** Point size represents eligible selections. Calibration features used Train EEG only; observed accuracy was reconstructed from later feedback phases.

**Figure 3. Source-study-held-out session-condition mean absolute error.** Each row reports a source study excluded from development-model fitting; the pooled row combines only held-out predictions.

![](../output/final/figures_revised/figure_1_study_flow.png){width=92%}

![](../output/final/figures_revised/figure_2_calibration_relationship.png){width=92%}

![](../output/final/figures_revised/figure_3_session_accuracy_validation.png){width=92%}

## References

1. Sellers EW, Donchin E. A P300-based brain-computer interface: initial tests by ALS patients. *Clin Neurophysiol*. 2006;117(3):538-548. doi:10.1016/j.clinph.2005.06.027
2. Wolpaw JR, Birbaumer N, McFarland DJ, Pfurtscheller G, Vaughan TM. Brain-computer interfaces for communication and control. *Clin Neurophysiol*. 2002;113(6):767-791. doi:10.1016/S1388-2457(02)00057-3
3. Mak JN, McFarland DJ, Vaughan TM, et al. EEG correlates of P300-based brain-computer interface performance in people with amyotrophic lateral sclerosis. *J Neural Eng*. 2012;9(2):026014. doi:10.1088/1741-2560/9/2/026014
4. Mainsah B, Fleeting C, Balmat T, Sellers E, Collins L. bigP3BCI: An Open, Diverse and Machine Learning Ready P300-based Brain-Computer Interface Dataset. Version 1.0.0. PhysioNet. Published 2025. doi:10.13026/0byy-ry86
