---
title: "Cover letter"
---

Re: Submission of "Source-study-held-out estimation of online P300-speller session accuracy from calibration EEG in amyotrophic lateral sclerosis" as a Research Article

Dear Editors of *Journal of Neural Engineering*,

We submit "Source-study-held-out estimation of online P300-speller session accuracy from calibration EEG in amyotrophic lateral sclerosis" for consideration as a Research Article. P300 spellers remain a route to communication for people with amyotrophic lateral sclerosis when motor access is limited, and online accuracy varies between users and across sessions. Mak and colleagues showed in this journal that EEG features relate to P300-BCI performance in ALS (*J Neural Eng* 2012;9:026014). That work established the premise using in-sample association. It left open whether a score derived only from the calibration recording that precedes a session estimates the accuracy of that later session in a cohort the model has never seen. We evaluated exactly that, with the calibration and feedback phases held apart by construction.

The analysis used the public BigP3BCI archive. All 20 documented source studies were screened, and the four documented ALS cohorts with compatible Train and Test phases entered the primary analysis, giving 47 study-scoped records, 113 participant-sessions, 194 session-condition records, and 3,318 eligible online character selections. Training used the remaining source studies each time one was held out. The pooled held-out model estimated session-condition accuracy with mean absolute error 0.095 (95% CI, 0.080-0.115), root mean squared error 0.128, character-weighted Brier score 0.110, and Brier skill score 0.287 against development prevalence. The calibration slope was 0.991 (95% CI, 0.783-1.201) and the intercept 0.022 (95% CI, -0.301 to 0.378). Held-out-study error ranged from 0.076 to 0.129. Two results temper this. The intervals are wide and only four source studies were available, so transportability is estimated coarsely. And while a regularized linear discriminant analysis score performed similarly (mean absolute error 0.095), single-summary comparators did not: Pz amplitude and posterior amplitude gave errors near 0.197 and 0.198.

We believe this work carries three implications relevant to *Journal of Neural Engineering*'s readership. First, it uses only the data that exist before an online session begins, rather than reusing online labels to build an optimistic predictor, and the reconstruction of every feedback outcome from source event traces is reported in full so that others can apply the same separation. Second, holding out an entire source study tests transport across legacy protocols that differ in spelling matrix, electrode type and session design, which is a stricter question than within-cohort cross-validation and is now answerable because multi-study archives are public. Third, we would encourage groups making calibration-based prediction claims to report probability-scale error, Brier skill and calibration slope rather than discrimination alone; our character-weighted AUC of 0.828 is the least informative number in the paper. The findings support testing a calibration-quality review as a preparation aid before a session. They do not support using an automated score to restrict access to a communication option, and we state that in the manuscript.

In keeping with ICMJE guidance on overlapping publications, we disclose two related manuscripts from our group that draw on the same public archive and are provided with this submission. The first asks a different question of the same recordings, namely how much of each emitted character selection is determined by a language-model prior rather than by the neural signal, and is being submitted to *npj Digital Medicine*; it reuses the calibration score reported here as a moderator and cites the present work as the source of its classifier and trial-reconstruction procedure. The second uses the Study F, L and N selections analysed here to build a character-confusion matrix for a simulation study of language-model post-editing. The three studies have different units of analysis and different outcomes, and an identical cohort-derivation statement reconciling their analytic samples appears in the supplement of each.

We thank the editors for their time and consideration of this submission. The work has not been submitted elsewhere and is not under consideration by any other journal. We are happy to provide any additional information that would help editorial assessment, including the archive provenance record with checksum verification, the analysis code, the frozen derived outputs, and the source-event reconstruction detail.

Sincerely,

[Submitting author name, degree]

[Institution, department]

[Corresponding-author email]
