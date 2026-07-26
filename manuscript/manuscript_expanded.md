---
title: "Transportability of a calibration-derived estimate of online P300-speller accuracy across eighteen source studies, with amyotrophic lateral sclerosis as the primary subgroup"
subtitle: "Draft for Journal of Neural Engineering, Original Research"
---

**Authors, affiliations, corresponding author, funding, competing interests, and CRediT roles:** [to be completed by submitting authors]

<!-- STATUS: draft in progress. Numbers marked [PENDING] await the 2,000-replicate bootstrap. -->

## Introduction

The P300 speller lets a person select characters from a visual matrix using event-related potentials rather than movement, and it remains one of the few communication routes available when motor control is lost.[1,2] It has been evaluated repeatedly in amyotrophic lateral sclerosis (ALS),[3,4] including long-term independent use at home,[5,6] and it sits alongside implanted systems as part of the communication options for people with severe paralysis.[7,8]

Performance is not uniform. Online spelling accuracy varies widely between users and between sessions in the same user, and a proportion of users do not reach usable accuracy at all.[9] This variability motivated a line of work asking whether performance can be anticipated from data recorded before a session begins. Neurophysiological features measured at rest or during a short calibration block relate to later brain-computer interface performance,[10] and in ALS specifically, event-related potential and spectral measures recorded during calibration relate to P300-speller accuracy.[11,12] Attentional and motivational state have also been linked to performance in this population.[13,14] Mainsah and colleagues went furthest, deriving P300-speller accuracy analytically as a function of a calibration-derived detectability index, with the explicit purpose of estimating performance without extensive online testing.[15]

Two features of that literature limit what it can support. First, the relationships were established within the cohort in which they were measured. A relationship that holds inside one study does not establish that a mapping fitted in one set of cohorts will estimate accuracy in a cohort it has never seen, which is the question that matters if a calibration score is to be used anywhere other than where it was developed. Second, these studies report discrimination, usually as a correlation or an area under the receiver operating characteristic curve. Discrimination describes whether users can be ranked. It does not describe whether the estimated accuracy is numerically close to the accuracy that follows, which is what a session-level check would require.

Evaluating transportability also imposes a requirement that has not previously been met in this setting. When a model is evaluated by withholding an entire cohort, the cohort is the unit of replication, and the spread of performance across withheld cohorts is what determines the interval a reader should expect in their own setting.[16,17] Estimating that spread from a small number of cohorts yields an interval too imprecise to be informative. Public archives that aggregate many independent P300-speller studies under a shared recording montage now make a larger number of withheld cohorts available.[18]

We evaluated whether a calibration-derived score estimates subsequent online session accuracy in cohorts withheld from model development, across every source study in a public archive that yields eligible online outcomes. The documented ALS cohorts were the prespecified primary subgroup. Because the archive also contains cohorts without a documented ALS population, we further asked whether a mapping developed without any ALS data transports to the ALS cohorts, and whether the calibration-to-accuracy relationship itself differs between cohort types.

## Methods

### Study Design and Reporting

This was a retrospective secondary analysis of a public archive of legacy online P300-speller recordings. The design was an external validation in which an entire source study was withheld from model development and the fitted mapping was evaluated in that withheld cohort. Reporting follows the TRIPOD statement for prediction-model studies.[19] The analysis was not registered.

Calibration and online blocks come from the same recording session throughout. Every timestamp in the archive is de-identified, so recording order cannot be established from file headers, and the separation enforced here is between protocol phases and between the data used to fit the predictor and the data used to measure the outcome, not a demonstrated temporal precedence. An analysis in which the predictor comes from a session preceding the outcome session is reported separately as a secondary result.

### Data Source and Cohort

The source was BigP3BCI version 1.0.0.[18] The downloaded archive was fixed by SHA256 digest (`eea294aa34e9ed11e5a25d07e30aeefdf8b2d467a8309e2c38405a289afcd72f`) before ingestion, and every selected European Data Format file was checked against the distributor checksum manifest.

All 20 documented source studies were screened. Every study supplied the shared 16-channel montage sampled at 256 Hz together with the stimulus and phase event channels, so montage compatibility excluded none. Two studies contributed no eligible online outcome and could not enter the analysis: in one, every feedback phase was overridden by artificial feedback, and in the other the intended character could not be recovered in any feedback phase. Both are retained in the study inventory with their reason, because their exclusion follows from the archive rather than from any analysis choice.

The archive documentation identifies an ALS study population for four source studies. These were the prespecified primary subgroup. The remaining cohorts carry no documented ALS population and are described here as other cohorts rather than as healthy or control cohorts, because the documentation does not support a positive characterisation.

### Calibration Predictor

Only Train-phase files informed the predictor. A calibration event was a rising `StimulusBegin` transition during phase 2, labelled target or non-target by `StimulusType`. The 16 shared channels were filtered from 0.5 to 30 Hz with a fourth-order zero-phase Butterworth filter, epoched from 200 ms before to 800 ms after each event, baseline corrected to the prestimulus interval, and rejected when absolute amplitude exceeded 150 microvolts. A session entered the analysis only if at least 10 target and 40 non-target epochs survived rejection.

Each epoch was decimated by taking every twelfth sample, giving 22 samples per channel and 352 features. At 256 Hz this corresponds to an effective sampling rate of about 21.3 Hz, which is below twice the 30 Hz filter edge; a sensitivity analysis at the documented decimation is reported in the supplement.

The primary score was the out-of-fold area under the receiver operating characteristic curve of an L2-regularised logistic classifier (C = 1.0, lbfgs solver) trained on standardised features, with stratified grouped cross-validation grouping by European Data Format file so that no epoch was scored by a model fitted on the same recording file. The number of folds was the smaller of five and the number of files in the session, so fold count varies between sessions and studies. The score is a property of a session and is constant across the conditions recorded within it.

Comparator scores computed from the same calibration epochs were a regularised linear discriminant analysis area under the curve, grouped cross-validated classification accuracy, mean target-minus-non-target amplitude at Pz between 250 and 500 ms, the same contrast averaged over six posterior channels, and the maximum posterior signed r-squared.

### Outcome

At each Test-phase transition to phase 3, the intended character was the final nonzero `CurrentTarget` in the directly preceding phase-2 interval and the selected character was the modal nonzero `SelectedTarget` during phase 3. A feedback phase was eligible when feedback was displayed, both values could be recovered, and artificial feedback did not override the selection. Correctness required an exact character match. The outcome was the proportion of correct eligible selections within a participant-session-condition record.

### Model Specification

The development model was a logistic regression of character-level correctness on the standardised calibration score, fitted on character-expanded records from the development studies. Standardisation used development-study means and standard deviations only. For a session with calibration score s, the estimated accuracy is the inverse logit of a + b (s - m) / d, where m and d are the development mean and standard deviation of the score and a and b are the fitted coefficients; fitted values for every fold are reported in the supplement so that any estimate can be recomputed.

### Validation Design

The primary evaluation withheld one source study at a time. Three further analyses used the wider cohort set. The ALS subgroup analysis repeated the same procedure within the four ALS cohorts alone. The transfer analysis developed the mapping on the other cohorts only, with every ALS cohort withheld simultaneously, and evaluated it in each ALS cohort. The moderation analysis tested whether the slope relating calibration score to accuracy differed between ALS and other cohorts, through the interaction between score and cohort type.

### Statistical Analysis

The primary metric was the mean absolute difference between estimated and observed session-condition accuracy in the withheld cohort. Because an absolute error is not interpretable without a reference, three references are reported: a model with no predictor that estimates every withheld record at the development-set mean accuracy, an oracle told the withheld cohort's own mean accuracy, and the skill of the model against the no-predictor model, defined as one minus the ratio of their errors. Secondary metrics were root mean squared error, character-weighted Brier score, Brier skill score against development prevalence, calibration intercept and slope, and character-weighted area under the curve.

Two uncertainty statements are reported and are not interchangeable. Confidence intervals from 2,000 deterministic bootstrap replicates, in which development participant clusters were resampled within source study, the model was refitted, and withheld participant clusters were resampled, describe uncertainty conditional on the observed set of source studies. Separately, the source study was treated as the unit of replication: the withheld-cohort estimates were summarised by their mean and between-study standard deviation, with a t-distributed confidence interval for the mean and a prediction interval for a cohort not represented in the archive.[16,17] The prediction interval is the quantity a reader should use when asking what to expect in their own cohort.

Because records are session-conditions nested within sessions within participants, and because the predictor is constant within a session, the intraclass correlation of session accuracy within participant is reported alongside an effective number of independent sessions. Associations are reported as Pearson and Spearman coefficients at the session, study-centred and participant levels. Calibration slope power is reported as the departure from unity the design could have detected. Prespecified sensitivity analyses covered restriction to cohorts with meaningful outcome variance, exclusion of records with high artifact rejection, exclusion of small-denominator records, and leave-two-studies-out development.

The significance threshold was P < .05, two-sided. Analyses used Python 3.11 with NumPy 2.3, SciPy 1.16, scikit-learn 1.7, statsmodels 0.14, and pandas 2.3.

### Ethics

The study involved no new data collection, participant contact, or intervention. The original source studies' ethics and consent statements are reported in the archive documentation. The submitting institution must confirm its own determination for this secondary analysis of a de-identified public archive.

### Relationship Between the Predictor and the Deployed Decoder

In these copy-spelling protocols the classifier used online during the Test phase was itself fitted on the Train-phase files from which the calibration score is computed. The quantity evaluated here is therefore the cross-validated fit quality of the decoder that was actually deployed, measured against that decoder's subsequent online accuracy, rather than an independent physiological marker of user aptitude. This is stated because it explains the strength of the within-session relationship and because it is the property a session-level operational check would exploit.

## Results

<!-- awaiting the completed bootstrap -->

## Discussion

<!-- drafting -->

## References

<!-- Final numbering assigned once all sections are drafted. Working assignment:
1  Farwell 1988      10.1016/0013-4694(88)90149-6
2  Wolpaw 2002       10.1016/S1388-2457(02)00057-3
3  Sellers 2006      10.1016/j.clinph.2005.06.027
4  Nijboer 2008      10.1016/j.clinph.2008.03.034
5  Sellers 2010      10.3109/17482961003777470
6  Wolpaw 2018       10.1212/wnl.0000000000005812
7  Vansteensel 2016  10.1056/nejmoa1608085
8  Chaudhary 2016    10.1038/nrneurol.2016.113
9  Guger 2009        10.1016/j.neulet.2009.06.045
10 Blankertz 2010    10.1016/j.neuroimage.2010.03.022
11 Mak 2012          10.1088/1741-2560/9/2/026014
12 Halder 2013       10.1371/journal.pone.0076148
13 Riccio 2013       10.3389/fnhum.2013.00732
14 Kleih 2010        10.1016/j.clinph.2010.01.034
15 Mainsah 2016      10.1088/1741-2560/13/6/066007
16 Debray 2015       10.1016/j.jclinepi.2014.06.018
17 Riley 2016        10.1136/bmj.i3140
18 bigP3BCI          10.13026/0byy-ry86
-->
