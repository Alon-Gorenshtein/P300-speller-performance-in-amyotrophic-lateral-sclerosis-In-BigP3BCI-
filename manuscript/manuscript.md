---
title: "Can calibration EEG predict online P300-speller performance in amyotrophic lateral sclerosis? A leave-one-study-out validation study"
subtitle: "Manuscript draft for Journal of Neural Engineering or Clinical Neurophysiology"
---

**Authors:** [to be completed by submitting authors]

**Affiliations:** [to be completed by submitting authors]

**Corresponding author:** [to be completed by submitting authors]

## Abstract

### Objective

Calibration recordings are routinely collected before P300-speller use, but whether a calibration-derived EEG score identifies people likely to achieve accurate online selection has not been tested across independent amyotrophic lateral sclerosis (ALS) source studies. We evaluated this question using public legacy data.

### Approach

We performed a secondary analysis of BigP3BCI version 1.0.0, selecting 29 ALS study-scoped records from 3 source studies (57 sessions). The primary predictor was a calibration-only, grouped cross-validated P300 discriminability score derived from 16-channel EEG. The outcome was correct feedback-phase character selection. Models were trained on 2 source studies and tested in the third; each source study was held out once. The primary metrics were character-level area under the receiver-operating-characteristic curve (AUC) and Brier score. Confidence intervals used 1,000 deterministic resamples of held-out study-scoped participant clusters.

### Main results

Of 2,549 reconstructed feedback phases, 2,537 were eligible and 1,995 were correct. The calibration score achieved AUCs of 0.860 (95% CI, 0.694-0.915), 0.803 (95% CI, 0.657-0.884), and 0.799 (95% CI, 0.635-0.886) in the 3 held-out studies. The pooled out-of-study AUC was 0.829 (95% CI, 0.757-0.872), with a Brier score of 0.120 and session-condition mean absolute error of 0.091. A prespecified Pz amplitude feature had a pooled AUC of 0.480. Adding ALS Functional Rating Scale-Revised values where available did not improve the pooled AUC (0.826).

### Significance

Within these historical ALS P300-speller cohorts, a calibration-derived multichannel EEG score was associated with online selection accuracy in held-out studies. The finding supports prospective evaluation of calibration-based operational checks before communication sessions; it does not establish prediction of current clinical deployment performance or causal effects on communication ability.

## Key points

**Question:** Can calibration-phase EEG identify online P300-speller character-selection performance when tested in a different ALS source study?

**Findings:** In a public-data validation study of 29 ALS study-scoped records and 2,537 eligible feedback selections, calibration-only P300 discriminability achieved a pooled held-out-study AUC of 0.829 (95% CI, 0.757-0.872). A single-electrode Pz amplitude measure did not provide comparable discrimination.

**Meaning:** Calibration EEG may support an operational pre-session performance check, but prospective validation in contemporary assistive-communication practice is required.

## Introduction

P300 spellers can provide an access pathway for people with ALS whose motor disability limits conventional communication. [5,6] Their clinical utility depends on reliable online selection, yet online performance can vary across users and sessions. Calibration data are routinely collected to configure a system, but a calibration-derived measure that generalizes to an independent source study would be more useful than an in-sample association.

The BigP3BCI resource preserves synchronized EEG, stimulus events, and online feedback from legacy P300-based BCI studies. [1] It includes ALS cohorts collected with related but nonidentical matrices, protocols, and user populations. Several source studies evaluated P300 BCI use in ALS and related implementation choices, including dynamic stopping, interface design, and dry electrodes. [2-4] These features make the resource suitable for a deliberately stringent historical validation test, while also preventing claims about contemporary clinical performance.

We assessed whether a calibration-only multichannel P300 discriminability score predicted feedback-phase character correctness in held-out ALS source studies. We prespecified leave-one-source-study-out validation, a single-electrode Pz comparator, and an exploratory model incorporating ALS Functional Rating Scale-Revised (ALSFRS-R) values where recorded.

## Methods

### Design, data source, and ethics

This retrospective secondary analysis used BigP3BCI version 1.0.0, a public dataset containing data from 20 legacy online P300 BCI studies. [1] We restricted the primary analysis to source Studies F, L, and N because their study-scoped ALS records included numerical ALSFRS-R values and their EEG acquisitions shared 16 channels. The downloaded archive was fixed by SHA256 digest before ingestion; every selected EDF file was checked against the distributor-provided checksum manifest (Supplementary Methods S1).

The original studies reported institutional review board approval and participant or legally authorized representative consent in the source dataset documentation. This analysis used de-identified public data and involved no new participant contact or intervention. The submitting institution must confirm its local determination before submission.

### Participants and unit of analysis

The analytic cohort comprised 29 study-scoped ALS records from 3 source studies, representing 57 recorded sessions. Study-scoped identifiers were retained as provided and were not interpreted as unique persons across studies because cross-study linkage is unavailable. The model-fitting unit was a participant-session-condition record; character selections were retained as the outcome level for discrimination and probability metrics.

### Calibration EEG predictor

Only Train-phase EDF files contributed to predictors. Calibration events were rising StimulusBegin transitions in phase 2, labelled target or non-target from StimulusType. EEG was filtered from 0.5 to 30 Hz with zero-phase filtering, epoched from 200 ms before to 800 ms after each event, baseline corrected using the 200-ms prestimulus interval, and excluded when any epoch exceeded 150 microvolts in absolute amplitude. A regularized logistic classifier received temporally downsampled epochs from the 16 shared channels. Its grouped cross-validated AUC, with folds grouped by EDF file, was the primary calibration score. No Test-phase recording, character selection, or outcome was read when deriving this feature.

The prespecified secondary predictor was the target-minus-nontarget Pz amplitude from 250 to 500 ms. Both predictors were calculated once per participant-session from all eligible calibration files in that session.

### Online selection outcome

The outcome was feedback-phase character correctness. For each transition to phase 3, the target was the final nonzero CurrentTarget value in the immediately preceding contiguous phase-2 interval. The selected character was the modal nonzero SelectedTarget value during the phase-3 interval. A feedback phase was eligible when feedback was displayed, both characters could be recovered, and FakeFeedback did not override the selection. It was correct when the selected and target characters matched. Each ineligible phase was retained with a single exclusion reason (Supplementary Methods S2).

### Statistical analysis

For the primary analysis, a regularized logistic model was trained using the calibration score in 2 source studies, with feature standardization learned only from those studies. It was then evaluated in the third source study, repeated until every study had been held out once. The pooled out-of-study summary combined predictions that were generated only in their held-out source study. We report character-level AUC and Brier score, session-condition mean absolute error, and logistic calibration intercept and slope. The primary AUC confidence intervals used 1,000 deterministic bootstrap resamples of held-out study-scoped participant clusters; the resampling quantifies uncertainty in the validation metrics conditional on the frozen held-out predictions.

The Pz predictor was substituted for the primary score in the prespecified secondary analysis. An exploratory analysis added recorded ALSFRS-R values. A within-study leave-one-participant-out analysis was conducted as a sensitivity analysis. Analyses were performed with Python 3.11; the full provenance, feature specification, analysis plan, and frozen outputs are included in the submission package.

## Results

### Cohort and outcome reconstruction

The analysis included 10, 11, and 8 study-scoped ALS records from Studies F, L, and N, respectively, across 57 sessions (Table 1). ALSFRS-R values ranged from 1 to 42 in Study F, 0 to 36 in Study L, and 4 to 46 in Study N. Of 2,549 reconstructed feedback phases, 2,537 were eligible. Twelve feedback phases from Study F were excluded because feedback was not displayed; no feedback phase in Studies L or N met an exclusion criterion. There were 1,995 correct eligible selections (Figure 1).

### External-study validation

The primary calibration score achieved AUCs of 0.860 (95% CI, 0.694-0.915) for Study F, 0.803 (95% CI, 0.657-0.884) for Study L, and 0.799 (95% CI, 0.635-0.886) for Study N when each was held out from model fitting (Table 2; Figure 3). Across all 2,537 out-of-study selections, the pooled AUC was 0.829 (95% CI, 0.757-0.872), Brier score was 0.120, and session-condition mean absolute error was 0.091. The pooled calibration slope was 1.000.

### Secondary and sensitivity analyses

The Pz amplitude comparator had a pooled held-out-study AUC of 0.480 (95% CI, 0.370-0.592), with Brier score 0.172 and mean absolute error 0.208. The exploratory model that added ALSFRS-R values had a pooled AUC of 0.826 (95% CI, 0.753-0.870), Brier score 0.121, and mean absolute error 0.094. In within-study leave-one-participant-out analyses, calibration-score AUCs were 0.858 in Study F, 0.801 in Study L, and 0.756 in Study N (Supplementary Table S3).

## Discussion

In this validation analysis of historical ALS P300-speller studies, a calibration-only multichannel EEG score discriminated correct from incorrect online character selections in each source study held out from model fitting. The pooled out-of-study AUC was 0.829, while a Pz-only amplitude measure had near-chance pooled discrimination. The result was retained when the testing procedure was changed to within-study leave-one-participant-out validation.

The comparison with Pz amplitude matters operationally. A standard P300 component summary may miss information distributed across channels and time that is retained in the multichannel calibration score. The present study does not show that a calibration score should determine whether an individual may use a BCI. It instead provides a testable basis for a prospective workflow in which calibration quality is reviewed before a communication session and paired with user-centered performance assessment.

The study was designed to test transport across legacy source studies rather than repeat an in-sample association. This is a stronger test than fitting and evaluating within the same study, but it remains bounded by the dataset. The source cohorts used related P300-speller paradigms, and prior work in these cohorts evaluated implementation variants such as dynamic stopping and interface design. [2-4] Heterogeneity in matrices, instructions, hardware, session timing, and user support may account for part of the between-study variation. A future prospective study should use a prespecified calibration score, record conventional access and communication outcomes, and evaluate calibration-guided review against standard session preparation.

### Study limitations

First, this was a secondary analysis of historical data rather than a prospective clinical study. The results therefore do not establish current performance with contemporary hardware, software, or assistive-communication workflows. Second, the 29 records are study-scoped, and the dataset cannot exclude an individual appearing in more than one source study; we did not treat them as 29 unique persons. Third, source-study protocols differed, including grid configuration and session structure, which limits attribution of between-study differences to EEG features alone. Fourth, repeated selections within a session are correlated. The reported bootstrap intervals resampled held-out participant clusters but were conditional on frozen model predictions; they do not represent fully nested model-fitting uncertainty. Fifth, online character correctness is an operational BCI endpoint, not a measure of successful real-world communication, quality of life, or clinical outcome. Finally, ALSFRS-R was unavailable for some dataset studies and was evaluated only as an exploratory covariate in the selected cohorts.

Calibration-phase P300 discriminability was associated with held-out-study online selection accuracy in public legacy ALS cohorts. Prospective replication should test whether the score can support a clinician and user review process before a communication session without restricting access on the basis of an automated prediction.

## Tables

**Table 1. Analytic cohort and feedback-phase eligibility.**

| Source study | ALS study-scoped records | Sessions | ALSFRS-R range | Eligible feedback selections | Correct selections |
|---|---:|---:|---:|---:|---:|
| Study F | 10 | 30 | 1-42 | 1,067 | 831 |
| Study L | 11 | 11 | 0-36 | 990 | 831 |
| Study N | 8 | 16 | 4-46 | 480 | 333 |
| Total | 29 | 57 | 0-46 | 2,537 | 1,995 |

ALSFRS-R indicates ALS Functional Rating Scale-Revised. Study-scoped records must not be interpreted as unique people across source studies.

**Table 2. Validation metrics for the primary calibration score.**

| Held-out study | Study-scoped records | Character selections | AUC (95% CI) | Brier score | Mean absolute error | Calibration slope |
|---|---:|---:|---:|---:|---:|---:|
| Study F | 10 | 1,067 | 0.860 (0.694-0.915) | 0.107 | 0.086 | 0.971 |
| Study L | 11 | 990 | 0.803 (0.657-0.884) | 0.112 | 0.092 | 1.289 |
| Study N | 8 | 480 | 0.799 (0.635-0.886) | 0.164 | 0.121 | 0.756 |
| Pooled out-of-study | 29 | 2,537 | 0.829 (0.757-0.872) | 0.120 | 0.091 | 1.000 |

AUC indicates area under the receiver-operating-characteristic curve. Confidence intervals were calculated with 1,000 held-out participant-cluster bootstrap resamples.

## Figure legends

**Figure 1. Study flow and feedback-phase eligibility.** The analytic cohort included 29 study-scoped ALS records from three BigP3BCI source studies. The outcome reconstruction retained 2,537 of 2,549 feedback phases; 12 Study F phases were excluded because feedback was not displayed.

**Figure 2. Relation between calibration score and online character correctness.** Each point represents a participant-session-condition record. The calibration score was created using Train-phase EEG only; online character correctness was derived from Test-phase feedback events.

**Figure 3. External-study validation of calibration EEG.** Each point is the AUC for a model trained on two source studies and evaluated in the third. The pooled result combines only held-out-study predictions.

![](../output/final/figures/figure_1_study_flow.png){width=92%}

![](../output/final/figures/figure_2_calibration_relationship.png){width=92%}

![](../output/final/figures/figure_3_external_validation_auc.png){width=92%}

## Declarations

### Data availability

BigP3BCI version 1.0.0 is publicly available through PhysioNet. [1] The analysis code, archive checksum, derived outputs, and manuscript-generation materials are included in the accompanying reproducibility package. Redistribution of source EDF files is not included.

### Code availability

All analysis and rendering code used for this manuscript is contained in the repository accompanying this submission.

### Funding

[to be completed by submitting authors]

### Competing interests

[to be completed by submitting authors]

### Author contributions

[to be completed by submitting authors using CRediT roles]

### Acknowledgments

We thank the BigP3BCI dataset contributors and the participants in the original studies.

## References

1. Mainsah B, Fleeting C, Balmat T, Sellers E, Collins L. bigP3BCI: An Open, Diverse and Machine Learning Ready P300-based Brain-Computer Interface Dataset. Version 1.0.0. PhysioNet. Published May 19, 2025. doi:10.13026/0byy-ry86

2. Mainsah BO, Collins LM, Colwell KA, Sellers EW, Ryan DB, Caves K, et al. Increasing BCI communication rates with dynamic stopping towards more practical use: an ALS study. *J Neural Eng*. 2015;12(1):016013. doi:10.1088/1741-2560/12/1/016013

3. Ryan DB, Colwell KA, Throckmorton CS, Collins LM, Caves K, Sellers EW. Evaluating brain-computer interface performance in an ALS population: checkerboard and color paradigms. *Clin EEG Neurosci*. 2018;49(2):114-121. doi:10.1177/1550059417737443

4. Clements JM, Sellers EW, Ryan DB, Caves K, Collins LM, Throckmorton CS. Applying dynamic data collection to improve dry electrode system performance for a P300-based brain-computer interface. *J Neural Eng*. 2016;13(6):066018. doi:10.1088/1741-2560/13/6/066018

5. Sellers EW, Donchin E. A P300-based brain-computer interface: initial tests by ALS patients. *Clin Neurophysiol*. 2006;117(3):538-548. doi:10.1016/j.clinph.2005.06.027

6. Wolpaw JR, Birbaumer N, McFarland DJ, Pfurtscheller G, Vaughan TM. Brain-computer interfaces for communication and control. *Clin Neurophysiol*. 2002;113(6):767-791. doi:10.1016/s1388-2457(02)00057-3
