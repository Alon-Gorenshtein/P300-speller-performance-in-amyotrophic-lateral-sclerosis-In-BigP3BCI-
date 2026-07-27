---
title: "Calibration discriminability tracks online P300-speller accuracy in eighteen cohorts, but the fitted mapping does not transport"
subtitle: "Journal of Neural Engineering, Paper"
---

**Authors, affiliations, corresponding author, funding, competing interests, and CRediT roles:** [to be completed by submitting authors]

## Abstract

### Objective

Calibration recordings precede P300-speller sessions, and a score derived from them has been related to online spelling accuracy, but always within the cohort measured. We evaluated whether a fitted mapping from that score to expected accuracy transports to withheld cohorts.

### Approach

Retrospective secondary analysis of BigP3BCI version 1.0.0. Of 20 source studies, 18 yielded eligible online outcomes: 271 participants, 410 sessions, 739 session-condition records, 19,611 character selections. The four documented amyotrophic lateral sclerosis (ALS) cohorts were the prespecified primary subgroup. The predictor was grouped cross-validated discriminability of a classifier fitted to calibration epochs only. One source study at a time was withheld from development. Uncertainty is reported conditional on the observed cohorts and, treating the study as the unit of replication, for an unrepresented cohort.

### Main Results

The score was associated with online accuracy in all 18 cohorts (within-cohort r 0.083 to 0.920; participant level r = 0.701, n = 271, p < 0.001), and after removing between-cohort differences (r = 0.652, p < 0.001). Estimation error was 0.103 (95% CI 0.094 to 0.112) against the development-mean benchmark, 0.146. The fitted mapping did not transport: calibration slope ranged from 0.075 to 2.233 and intercept from -2.445 to 1.870 across cohorts, and skill was negative in one of 18. For an unrepresented cohort, intervals spanned 0.001 to 0.208 for estimation error and 0.482 to 0.937 for discrimination. The ALS cohorts alone gave a slope of 0.991 with a between-cohort standard deviation of 0.204, against 0.586 overall.

### Significance

The score carries a reproducible signal about subsequent accuracy, but the mapping between them is cohort-specific. It may support ranking sessions within a setting, but should not be used to report an expected accuracy where the mapping was not developed without local recalibration. Evaluating on few cohorts, as the ALS cohorts illustrate, understates how much performance varies elsewhere.

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

The regularised logistic classifier and the linear discriminant comparator were chosen because they are the families evaluated for this paradigm in the P300-speller literature.[20,21] Spatially filtered and Riemannian pipelines,[22,23,24] and the wider set of classifiers reviewed for event-related potential decoding,[25] were not used, because the study evaluates a mapping from a calibration summary to online accuracy rather than proposing a decoder.

Comparator scores computed from the same calibration epochs were a regularised linear discriminant analysis area under the curve, grouped cross-validated classification accuracy, mean target-minus-non-target amplitude at Pz between 250 and 500 ms, the same contrast averaged over six posterior channels, and the maximum posterior signed r-squared.

### Outcome

At each Test-phase transition to phase 3, the intended character was the final nonzero `CurrentTarget` in the directly preceding phase-2 interval and the selected character was the modal nonzero `SelectedTarget` during phase 3. A feedback phase was eligible when feedback was displayed, both values could be recovered, and artificial feedback did not override the selection. Correctness required an exact character match. The outcome was the proportion of correct eligible selections within a participant-session-condition record.

### Model Specification

The development model was a logistic regression of character-level correctness on the standardised calibration score, fitted on character-expanded records from the development studies. Standardisation used development-study means and standard deviations only. For a session with calibration score s, the estimated accuracy is the inverse logit of a + b (s - m) / d, where m and d are the development mean and standard deviation of the score and a and b are the fitted coefficients; fitted values for every fold are reported in the supplement so that any estimate can be recomputed.

### Validation Design

The primary evaluation withheld one source study at a time. Three further analyses used the wider cohort set. The ALS subgroup analysis repeated the same procedure within the four ALS cohorts alone. The transfer analysis developed the mapping on the other cohorts only, with every ALS cohort withheld simultaneously, and evaluated it in each ALS cohort. The moderation analysis tested whether the slope relating calibration score to accuracy differed between ALS and other cohorts, through the interaction between score and cohort type.

### Statistical Analysis

The primary metric was the mean absolute difference between estimated and observed session-condition accuracy in the withheld cohort. Because an absolute error is not interpretable without a reference, three references are reported: a development-mean benchmark that estimates every withheld record at the development-set mean accuracy, a held-out-cohort-mean benchmark that estimates every withheld record at that cohort's own mean accuracy, and the skill of the model against the development-mean benchmark, defined as one minus the ratio of their errors. Skill is reported against the development-mean benchmark throughout unless the cohort's own mean is named. The second benchmark is the harder of the two pooled, but not in every cohort: mean absolute error is minimised by the median rather than the mean, so a cohort's own mean is not guaranteed to beat any other constant, and it is the easier target in 7 of the 18 cohorts. Secondary metrics were root mean squared error, character-weighted Brier score, Brier skill score against development prevalence, calibration intercept and slope, and character-weighted area under the curve. Calibration intercept and slope are reported per withheld cohort as well as pooled, because a pooled value can conceal opposing departures in individual cohorts.[26,27]

Two uncertainty statements are reported and are not interchangeable. Confidence intervals from 2,000 deterministic bootstrap replicates, in which development participant clusters were resampled within source study, the model was refitted, and withheld participant clusters were resampled, describe uncertainty conditional on the observed set of source studies. Separately, the source study was treated as the unit of replication: the withheld-cohort estimates were summarised by their mean and between-study standard deviation, with a t-distributed confidence interval for the mean and a prediction interval for a cohort not represented in the archive.[16,17] The prediction interval is the quantity a reader should use when asking what to expect in their own cohort.

Because records are session-conditions nested within sessions within participants, and because the predictor is constant within a session, the intraclass correlation of session accuracy within participant is reported alongside an effective number of independent sessions. Associations are reported as Pearson and Spearman coefficients at the session, study-centred and participant levels. Calibration slope power is reported as the departure from unity the design could have detected. Prespecified sensitivity analyses covered restriction to cohorts with meaningful outcome variance, exclusion of records with high artifact rejection, exclusion of small-denominator records, and leave-two-studies-out development.

The significance threshold was P < .05, two-sided. Analyses used Python 3.11 with NumPy 2.3, SciPy 1.16, scikit-learn 1.7, statsmodels 0.14, and pandas 2.3.

### Ethics

The study involved no new data collection, participant contact, or intervention. The original source studies' ethics and consent statements are reported in the archive documentation. The submitting institution must confirm its own determination for this secondary analysis of a de-identified public archive.

### Relationship Between the Predictor and the Deployed Decoder

In these copy-spelling protocols the Train phase supplies the data from which an online classifier is derived before the Test phase begins. The archive does not document the online classifier for every source study, so the score is described here as the cross-validated learnability of that session's calibration data rather than as a property of the specific decoder deployed. This is why the quantity is reported as decoder-calibration quality and not as a physiological marker of user aptitude.

## Results

### Cohort

All 20 documented source studies supplied the shared 16-channel montage at 256 Hz and were screened. Eighteen contributed at least one eligible online outcome. One study contributed none because artificial feedback overrode the selection in all 5,680 reconstructed feedback phases, and one contributed none because the intended character could not be recovered in any of 2,263 phases (Table 1).

The analytic set contained 271 study-scoped participants, 410 participant-sessions, 739 participant-session-condition records, and 19,611 eligible online character selections. The four documented ALS cohorts contributed 47 participants, 113 sessions, 194 records, and 3,318 selections. Observed session-condition accuracy averaged 0.851 and 228 of 739 records (30.9%) were at 100%, with three cohorts near ceiling (mean accuracy 0.963 to 0.997).

Because the calibration score is a property of a session, the 739 records carry 410 distinct predictor values. Session accuracy clustered within participant (intraclass correlation 0.412), giving approximately 338 effective independent sessions.

### Association Between Calibration Discriminability and Online Accuracy

**The association was present in every contributing cohort and was not an artefact of differences between cohorts.** Calibration discriminability correlated with observed session accuracy in all 18 cohorts, with within-cohort Pearson r from 0.083 to 0.920 (median 0.630). Pooling sessions gave r = 0.699 (n = 410, p < 0.001); centring both variables within cohort, which removes every between-cohort difference, gave r = 0.652 (p < 0.001). Collapsing each participant to a single observation gave r = 0.701 (n = 271, p < 0.001; Spearman ρ = 0.749).

### Estimation Error and Its Reference Points

**Pooled across withheld cohorts, estimated session accuracy fell about a third closer to observed accuracy than the development-mean benchmark, and also beat the benchmark of each cohort's own mean.** Across withheld cohorts the mean absolute error was 0.098 (95% CI 0.091 to 0.107), against 0.146 for the development-mean benchmark and 0.123 for the held-out-cohort-mean benchmark, giving a skill of 0.327 against the development-mean benchmark. These are pooled figures, and the per-cohort picture below is less uniform. The character-weighted Brier score was 0.123 (95% CI 0.113 to 0.132), Brier skill 0.110 (95% CI 0.063 to 0.149), and character-weighted area under the curve 0.748 (95% CI 0.719 to 0.771). These intervals are conditional on the 18 observed cohorts.

### Transportability

**Treating the source study as the unit of replication, discrimination transported moderately and calibration did not transport at all.** Across the 18 withheld cohorts the mean absolute error averaged 0.104 with a between-cohort standard deviation of 0.048, giving a 95% interval for the mean of 0.080 to 0.128 and a 95% interval for a cohort not represented in the archive of 0.001 to 0.208 (Figure 1). Area under the curve averaged 0.710 across cohorts, with a new-cohort interval of 0.482 to 0.937, the lower bound of which is chance. Brier skill averaged 0.167 across cohorts with a new-cohort interval of -0.287 to 0.621.

**Calibration slope and intercept varied so widely between cohorts that a single fitted mapping produced miscalibrated estimates in most of them.** The calibration slope ranged from 0.075 to 2.233 and the intercept from -2.445 to 1.870 across withheld cohorts. The between-cohort standard deviation was 0.586 for the slope and 1.073 for the intercept, giving new-cohort intervals of -0.104 to 2.437 and -2.405 to 2.249. The pooled slope of 0.950 (95% CI 0.754 to 1.146) and intercept of 0.080 (95% CI -0.290 to 0.464) arise from averaging these opposing departures and do not describe any individual cohort.

**One cohort was estimated less accurately than the development-mean benchmark, and six were estimated less accurately than their own cohort mean.** Skill against the development-mean benchmark was negative in one of 18 cohorts and positive in the remainder (Figure 2). Against the benchmark of each cohort's own mean, which is the harder target pooled and in 11 of the 18 cohorts, skill was negative in six of 18 (Table S5). Two distinct things produce those six. In StudyH the model was less accurate than both benchmarks, and it is the same cohort that fails the development-mean benchmark. The others are cohorts whose observed accuracy sits high enough that their own mean already tracks nearly every record: in StudyR, StudyS2 and StudyS1, accuracy averages 0.963, 0.976 and 0.997 and the own-mean benchmark errs by 0.047, 0.035 and 0.005, leaving almost no error for any predictor to reduce. StudyS1 is the limiting case, where that near-zero denominator makes the ratio large and negative and not comparable with the rest. In StudyJ the shortfall is -0.008, which is parity rather than failure. All four ALS cohorts had positive skill against both benchmarks, at 0.317, 0.383, 0.448 and 0.502 against the development mean.

### Amyotrophic Lateral Sclerosis Subgroup

**Restricting the analysis to the four ALS cohorts reproduced a more favourable and considerably more precise picture than the full archive supported.** Within the prespecified primary subgroup the mean absolute error was 0.095 (95% CI 0.080 to 0.115), Brier skill 0.287 (95% CI 0.169 to 0.407), area under the curve 0.828 (95% CI 0.761 to 0.866), calibration intercept 0.022 (95% CI -0.301 to 0.378), and slope 0.991 (95% CI 0.783 to 1.201). The between-cohort standard deviation of the calibration slope was 0.204 within this subgroup against 0.586 across all contributing cohorts.

### Transfer From Cohorts Without a Documented ALS Population

**A mapping developed without any ALS data estimated accuracy in the ALS cohorts with modest loss.** With all four ALS cohorts withheld from development simultaneously, mean absolute error in each was 0.089, 0.112, 0.124, and 0.142 (mean 0.117), against 0.101 when other ALS cohorts were available for development. Signed bias ranged from -0.085 to 0.063.

### Cohort Type as a Moderator

**The slope relating calibration discriminability to online accuracy was steeper in the ALS cohorts.** The fitted slope was 1.672 in ALS cohorts and 1.018 in the remaining cohorts, with an interaction of 0.655 (p < 0.001). The same calibration score therefore implied a different expected accuracy depending on cohort type.

### Predictor From a Preceding Session

**Using a calibration recording from a preceding session, rather than from the session being estimated, attenuated but did not remove the association.** Among 139 consecutive session pairs, the earlier session's calibration score correlated with the later session's accuracy at r = 0.525 (p < 0.001), against r = 0.702 for the score recorded in the session being estimated.

### Sensitivity Analyses

Results were similar when records with fewer than 10 eligible selections were excluded (mean absolute error 0.104, between-cohort standard deviation 0.048). Restricting to the 12 cohorts whose session accuracy varied by at least 0.10 raised the mean absolute error to 0.129 and the calibration-slope standard deviation to 0.674, indicating that near-ceiling cohorts contributed low error for reasons unrelated to the predictor. Excluding records in which more than 20% of calibration epochs were rejected lowered the mean absolute error to 0.084 and the calibration-slope standard deviation to 0.438, the only analysis in which transportability improved. Analysing the 14 cohorts without a documented ALS population gave a mean absolute error of 0.104 with a new-cohort interval of -0.012 to 0.219 and a calibration-slope standard deviation of 0.716.

## Discussion

Across 18 independent P300-speller cohorts, the discriminability of a classifier fitted to a session's calibration block was related to that session's subsequent online spelling accuracy in every cohort, at the level of individual participants as well as between cohorts, and when the calibration recording came from an earlier session. A fitted mapping from that score to an expected accuracy did not transport. Calibration slope varied from 0.075 to 2.233 and intercept from -2.445 to 1.870 across withheld cohorts, and in one cohort the score estimated accuracy less well than the development-mean benchmark, and in six it estimated accuracy less well than that cohort's own mean. The association is a stable property of these recordings; the calibrated mapping is not.

That distinction determines what a calibration score can be used for. Ranking sessions within a setting, which requires only that the association hold locally, is supported. Reporting an expected accuracy in a cohort where the mapping was not developed is not supported without local recalibration, because the interval for a cohort outside this archive spans 0.001 to 0.208 for estimation error and includes chance-level discrimination and negative skill.

Mainsah and colleagues derived speller accuracy analytically from a calibration-derived detectability index and validated it within study.[15] The present analysis is the transportability counterpart to that work rather than a replacement for it: the relationship they described is reproduced here in every cohort, and what is added is the finding that the numerical mapping between the two quantities is cohort-specific. Earlier reports relating calibration measures to P300 performance in ALS[11,12] and to brain-computer interface performance more generally[10] are likewise consistent with the association reported here.

The comparison between the four ALS cohorts and the full archive is itself a result. Analysed alone, the ALS cohorts gave a calibration slope of 0.991 with a between-cohort standard deviation of 0.204 and a favourable Brier skill of 0.287. Analysed alongside 14 further cohorts, the between-cohort standard deviation of the slope was 0.586 and Brier skill fell to 0.098. Four cohorts were not merely too few to estimate the spread; they happened to be homogeneous and favourable, and the resulting picture was optimistic in a direction that only became visible with more cohorts. External validation of a brain-computer interface mapping on a small number of cohorts should be expected to understate how much performance will vary elsewhere.

One analysis improved transportability. Excluding records in which more than 20% of calibration epochs exceeded the artifact threshold reduced estimation error from 0.104 to 0.084 and reduced the between-cohort standard deviation of the calibration slope from 0.586 to 0.438. Screening calibration data quality before relying on a calibration-derived estimate is therefore a concrete step, and it is available at no cost because the rejection fraction is computed while the score is computed.

A mapping developed entirely without ALS data estimated accuracy in the ALS cohorts with a mean absolute error of 0.117, against 0.101 when other ALS cohorts were available. The relationship is not specific to the clinical population in the sense of being absent elsewhere. It is population-dependent in a different sense: the slope was steeper in the ALS cohorts than in the others, so the same score implied a different expected accuracy, which is one mechanism by which a single fitted mapping mis-calibrates.

### Study Limitations

First, calibration and online blocks come from the same recording session throughout. Every timestamp in the archive is de-identified, so temporal precedence within a session cannot be verified from the data, and the separation enforced here is between protocol phases rather than demonstrated ordering. The analysis using a preceding session's calibration recording is the closest available approximation and shows an attenuated association.

Second, the archive documents the calibration-then-test structure of these protocols at the level of the collection but does not name the online classifier used in any source study, and the underlying BCI2000 parameter files, which would carry the decoder specification, were withheld from the release. Whether the classifier applied during a given Test phase was fitted on exactly the distributed Train-phase files of that session therefore cannot be verified. The quantity evaluated is the cross-validated learnability of that session's calibration data, measured against the online accuracy recorded in the same session, rather than an independent physiological marker of user aptitude.

Third, the cohorts differ in speller matrix, stimulus paradigm, electrode type, and stopping rule, and paradigm is largely nested within source study, so withholding a cohort also withholds its paradigms. Cohort and paradigm effects cannot be separated in this design. Stimulus presentation and stopping rule are known to change speller accuracy substantially,[28,29,30] so some of the between-cohort variability reported here is attributable to protocol rather than to population.

Fourth, 30.9% of records were at 100% accuracy and three cohorts were near ceiling, where there is little variation to estimate. The sensitivity analysis restricted to cohorts with meaningful outcome variance gave a higher estimation error, so the primary figure is favourably influenced by cohorts in which the task was easy.

Fifth, the outcome is character-level selection accuracy reconstructed from archived event traces. It is an operational endpoint and not communication effectiveness, quality of life, or any clinical outcome, and it does not capture communication rate, for which accuracy alone is known to be an incomplete summary.[31] Sixth, these are legacy protocols, and the analysis does not establish performance with contemporary assistive-communication workflows. Seventh, the archive documentation identifies an ALS population for four cohorts only; the remaining cohorts are described as other cohorts because the documentation does not support a positive characterisation, and no participant-level clinical characteristics were available for the cohort description.

### Conclusion

In 18 independent P300-speller cohorts, calibration discriminability was related to subsequent online spelling accuracy in every cohort and at the level of individual participants, but the fitted mapping between the two did not transport: calibration slope and intercept varied several-fold between cohorts, and estimation performance in a cohort outside the archive cannot be bounded away from no benefit. A calibration score may support ranking sessions within a setting and may support a data-quality screen, and it should not be used to report an expected accuracy in a cohort where the mapping was not developed without local recalibration. Prospective evaluation would need to predefine the recalibration procedure and measure user-centred communication outcomes rather than character accuracy alone.

## Tables and Figure Legends

**Table 1. Source studies screened, and their contribution to the analytic set.** All 20 documented source studies supplied the shared 16-channel montage at 256 Hz. Two contributed no eligible online outcome: Study C, in which artificial feedback overrode the selection in all 5,680 reconstructed feedback phases, and Study P, in which the intended character could not be recovered in any of 2,263 phases. Cohorts are marked according to whether the archive documentation identifies an ALS study population.

| Source study | ALS documented | Phases reconstructed | Eligible selections | Contribution |
|---|---|---:|---:|---|
| Study A | No | 1,404 | 1,404 | Contributed |
| Study B | Yes | 858 | 858 | Contributed |
| Study C | No | 5,680 | 0 | Artificial feedback overrode every selection |
| Study D | No | 1,230 | 1,230 | Contributed |
| Study E | No | 240 | 240 | Contributed |
| Study F | Yes | 1,079 | 1,067 | Contributed |
| Study G | No | 1,198 | 1,198 | Contributed |
| Study H | No | 1,926 | 1,926 | Contributed |
| Study I | No | 948 | 948 | Contributed |
| Study J | No | 1,812 | 1,812 | Contributed |
| Study K | No | 480 | 480 | Contributed |
| Study L | Yes | 990 | 990 | Contributed |
| Study M | No | 1,260 | 1,260 | Contributed |
| Study N | Yes | 480 | 480 | Contributed |
| Study O | No | 1,202 | 1,187 | Contributed |
| Study P | No | 2,263 | 0 | Intended character not recoverable |
| Study Q | No | 3,888 | 1,944 | Contributed |
| Study R | No | 1,440 | 1,440 | Contributed |
| Study S1 | No | 360 | 360 | Contributed |
| Study S2 | No | 864 | 864 | Contributed |
| **Total** | 4 of 20 | **29,602** | **19,688** | 18 cohorts contributed |

**Table 2. Per-cohort composition and withheld-cohort performance.** For each of the 18 contributing cohorts: participants, records, eligible selections, mean observed session-condition accuracy, and, when that cohort was withheld from model development, the mean absolute error, character-weighted area under the curve, and calibration intercept and slope. ALS cohorts are listed first. The calibration slope ranges from 0.075 to 2.233 and the intercept from -2.445 to 1.870.

| Cohort | Participants | Records | Selections | Observed accuracy | MAE | AUC | Calib. intercept | Calib. slope |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Study B | 18 | 56 | 781 | 0.899 | 0.122 | 0.817 | -0.088 | 1.630 |
| Study F | 10 | 89 | 1,067 | 0.778 | 0.107 | 0.860 | -0.863 | 1.488 |
| Study L | 11 | 33 | 990 | 0.839 | 0.086 | 0.803 | -0.816 | 1.750 |
| Study N | 8 | 16 | 480 | 0.694 | 0.136 | 0.799 | -0.694 | 1.168 |
| Study A | 13 | 39 | 1,404 | 0.786 | 0.126 | 0.776 | -2.445 | 2.233 |
| Study D | 17 | 34 | 1,230 | 0.896 | 0.052 | 0.639 | +0.016 | 0.982 |
| Study E | 8 | 8 | 240 | 0.921 | 0.066 | 0.675 | +1.010 | 0.764 |
| Study G | 20 | 40 | 1,198 | 0.886 | 0.071 | 0.731 | -1.257 | 1.485 |
| Study H | 16 | 64 | 1,926 | 0.877 | 0.154 | 0.516 | +1.870 | 0.075 |
| Study I | 13 | 26 | 948 | 0.658 | 0.178 | 0.654 | -0.795 | 1.270 |
| Study J | 20 | 40 | 1,812 | 0.708 | 0.204 | 0.569 | +0.617 | 0.221 |
| Study K | 5 | 16 | 480 | 0.750 | 0.156 | 0.675 | +0.432 | 0.748 |
| Study M | 21 | 42 | 1,260 | 0.823 | 0.122 | 0.671 | +0.422 | 0.837 |
| Study O | 17 | 34 | 1,187 | 0.884 | 0.066 | 0.590 | +0.240 | 0.709 |
| Study Q | 20 | 54 | 1,944 | 0.820 | 0.061 | 0.672 | -0.162 | 1.126 |
| Study R | 20 | 80 | 1,440 | 0.963 | 0.063 | 0.628 | +1.312 | 0.771 |
| Study S1 | 10 | 20 | 360 | 0.997 | 0.050 | 0.851 | +1.019 | 1.787 |
| Study S2 | 24 | 48 | 864 | 0.976 | 0.054 | 0.847 | -1.224 | 1.952 |

**Figure 1. Estimation error in each withheld cohort, with the two uncertainty statements.** Each point is one cohort withheld from model development. The darker band is the 95% interval for the mean across the observed cohorts; the lighter band is the 95% interval for a cohort not represented in the archive. The two answer different questions and only the second describes what a reader should expect in their own setting.

**Figure 2. Error reduction in each withheld cohort against the development-mean benchmark.** Values below zero indicate that the calibration score estimated accuracy less well than estimating every record at the development-set mean. All four ALS cohorts were positive; one cohort without a documented ALS population was negative.

**Figure 3. Calibration discriminability against observed online accuracy, by cohort type.** Each point is one participant-session-condition record, sized by the number of eligible selections. Separate straight-line fits are shown for the ALS cohorts and the remaining cohorts; the drawn lines are bounded at one because the outcome is a proportion. The band of points at 1.0 shows the ceiling described in the Results.

![](../output/expanded/figures/figure_transportability.png){width=88%}

![](../output/expanded/figures/figure_skill_by_cohort.png){width=88%}

![](../output/expanded/figures/figure_cohort_type_relationship.png){width=88%}

## References

1. Farwell LA, Donchin E. Talking off the top of your head: toward a mental prosthesis utilizing event-related brain potentials. *Electroencephalogr Clin Neurophysiol*. 1988;70(6):510-523. doi:10.1016/0013-4694(88)90149-6
2. Wolpaw JR, Birbaumer N, McFarland DJ, Pfurtscheller G, Vaughan TM. Brain-computer interfaces for communication and control. *Clin Neurophysiol*. 2002;113(6):767-791. doi:10.1016/S1388-2457(02)00057-3
3. Sellers EW, Donchin E. A P300-based brain-computer interface: initial tests by ALS patients. *Clin Neurophysiol*. 2006;117(3):538-548. doi:10.1016/j.clinph.2005.06.027
4. Nijboer F, Sellers EW, Mellinger J, et al. A P300-based brain-computer interface for people with amyotrophic lateral sclerosis. *Clin Neurophysiol*. 2008;119(8):1909-1916. doi:10.1016/j.clinph.2008.03.034
5. Sellers EW, Vaughan TM, Wolpaw JR. A brain-computer interface for long-term independent home use. *Amyotroph Lateral Scler*. 2010;11(5):449-455. doi:10.3109/17482961003777470
6. Wolpaw JR, Bedlack RS, Reda DJ, et al. Independent home use of a brain-computer interface by people with amyotrophic lateral sclerosis. *Neurology*. 2018;91(3):e258-e267. doi:10.1212/WNL.0000000000005812
7. Vansteensel MJ, Pels EGM, Bleichner MG, et al. Fully implanted brain-computer interface in a locked-in patient with ALS. *N Engl J Med*. 2016;375(21):2060-2066. doi:10.1056/NEJMoa1608085
8. Chaudhary U, Birbaumer N, Ramos-Murguialday A. Brain-computer interfaces for communication and rehabilitation. *Nat Rev Neurol*. 2016;12(9):513-525. doi:10.1038/nrneurol.2016.113
9. Guger C, Daban S, Sellers E, et al. How many people are able to control a P300-based brain-computer interface (BCI)? *Neurosci Lett*. 2009;462(1):94-98. doi:10.1016/j.neulet.2009.06.045
10. Blankertz B, Sannelli C, Halder S, et al. Neurophysiological predictor of SMR-based BCI performance. *Neuroimage*. 2010;51(4):1303-1309. doi:10.1016/j.neuroimage.2010.03.022
11. Mak JN, McFarland DJ, Vaughan TM, et al. EEG correlates of P300-based brain-computer interface (BCI) performance in people with amyotrophic lateral sclerosis. *J Neural Eng*. 2012;9(2):026014. doi:10.1088/1741-2560/9/2/026014
12. Halder S, Ruf CA, Furdea A, et al. Prediction of P300 BCI aptitude in severe motor impairment. *PLoS One*. 2013;8(10):e76148. doi:10.1371/journal.pone.0076148
13. Riccio A, Simione L, Schettini F, et al. Attention and P300-based BCI performance in people with amyotrophic lateral sclerosis. *Front Hum Neurosci*. 2013;7:732. doi:10.3389/fnhum.2013.00732
14. Kleih SC, Nijboer F, Halder S, Kübler A. Motivation modulates the P300 amplitude during brain-computer interface use. *Clin Neurophysiol*. 2010;121(7):1023-1031. doi:10.1016/j.clinph.2010.01.034
15. Mainsah BO, Collins LM, Throckmorton CS. Using the detectability index to predict P300 speller performance. *J Neural Eng*. 2016;13(6):066007. doi:10.1088/1741-2560/13/6/066007
16. Debray TPA, Vergouwe Y, Koffijberg H, Nieboer D, Steyerberg EW, Moons KGM. A new framework to enhance the interpretation of external validation studies of clinical prediction models. *J Clin Epidemiol*. 2015;68(3):279-289. doi:10.1016/j.jclinepi.2014.06.018
17. Riley RD, Ensor J, Snell KIE, et al. External validation of clinical prediction models using big datasets from e-health records or IPD meta-analysis: opportunities and challenges. *BMJ*. 2016;353:i3140. doi:10.1136/bmj.i3140
18. Mainsah B, Fleeting C, Balmat T, Sellers E, Collins L. bigP3BCI: an open, diverse and machine learning ready P300-based brain-computer interface dataset. Version 1.0.0. PhysioNet. 2025. doi:10.13026/0byy-ry86
19. Collins GS, Reitsma JB, Altman DG, Moons KGM. Transparent reporting of a multivariable prediction model for individual prognosis or diagnosis (TRIPOD): the TRIPOD statement. *BMJ*. 2015;350:g7594. doi:10.1136/bmj.g7594
20. Krusienski DJ, Sellers EW, Cabestaing F, et al. A comparison of classification techniques for the P300 speller. *J Neural Eng*. 2006;3(4):299-305. doi:10.1088/1741-2560/3/4/007
21. Krusienski DJ, Sellers EW, McFarland DJ, Vaughan TM, Wolpaw JR. Toward enhanced P300 speller performance. *J Neurosci Methods*. 2008;167(1):15-21. doi:10.1016/j.jneumeth.2007.07.017
22. Rivet B, Souloumiac A, Attina V, Gibert G. xDAWN algorithm to enhance evoked potentials: application to brain-computer interface. *IEEE Trans Biomed Eng*. 2009;56(8):2035-2043. doi:10.1109/TBME.2009.2012869
23. Barachant A, Bonnet S, Congedo M, Jutten C. Multiclass brain-computer interface classification by Riemannian geometry. *IEEE Trans Biomed Eng*. 2012;59(4):920-928. doi:10.1109/TBME.2011.2172210
24. Congedo M, Barachant A, Bhatia R. Riemannian geometry for EEG-based brain-computer interfaces: a primer and a review. *Brain Comput Interfaces*. 2017;4(3):155-174. doi:10.1080/2326263X.2017.1297192
25. Lotte F, Bougrain L, Cichocki A, et al. A review of classification algorithms for EEG-based brain-computer interfaces: a 10 year update. *J Neural Eng*. 2018;15(3):031005. doi:10.1088/1741-2552/aab2f2
26. Van Calster B, Nieboer D, Vergouwe Y, De Cock B, Pencina MJ, Steyerberg EW. A calibration hierarchy for risk models was defined: from utopia to empirical data. *J Clin Epidemiol*. 2016;74:167-176. doi:10.1016/j.jclinepi.2015.12.005
27. Steyerberg EW, Vickers AJ, Cook NR, et al. Assessing the performance of prediction models: a framework for traditional and novel measures. *Epidemiology*. 2010;21(1):128-138. doi:10.1097/EDE.0b013e3181c30fb2
28. Townsend G, LaPallo BK, Boulay CB, et al. A novel P300-based brain-computer interface stimulus presentation paradigm: moving beyond rows and columns. *Clin Neurophysiol*. 2010;121(7):1109-1120. doi:10.1016/j.clinph.2010.01.030
29. Kaufmann T, Kübler A. Beyond maximum speed: a novel two-stimulus paradigm for brain-computer interfaces based on event-related potentials (P300-BCI). *J Neural Eng*. 2014;11(5):056004. doi:10.1088/1741-2560/11/5/056004
30. Mainsah BO, Collins LM, Colwell KA, et al. Increasing BCI communication rates with dynamic stopping towards more practical use: an ALS study. *J Neural Eng*. 2015;12(1):016013. doi:10.1088/1741-2560/12/1/016013
31. Speier W, Arnold C, Pouratian N. Evaluating true BCI communication rate through mutual information and language models. *PLoS One*. 2013;8(10):e78432. doi:10.1371/journal.pone.0078432
