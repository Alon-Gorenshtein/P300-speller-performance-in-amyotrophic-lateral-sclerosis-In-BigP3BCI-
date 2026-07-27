# Supplementary material

## S1. Data provenance

This retrospective secondary analysis used the BigP3BCI version 1.0.0 public archive. The downloaded archive had SHA256 digest `eea294aa34e9ed11e5a25d07e30aeefdf8b2d467a8309e2c38405a289afcd72f`. Before any signal was processed, the ingestion pipeline checked this archive digest, read the distributor checksum manifest, selected non-AppleDouble European Data Format files, and checked every selected file against its manifest digest. The source archive and cache are not redistributed in this package.

All 20 documented source studies were examined. Every study supplied the 16 shared EEG channels sampled at 256 Hz together with the `StimulusBegin`, `StimulusType` and `PhaseInSequence` event channels, so no study was excluded for montage or event-channel incompatibility. Study-scoped participant identifiers were retained to prevent accidental cross-study linkage; they do not identify unique people across studies.

## S2. Predictor and outcome reconstruction

The predictor used Train-phase files only. A calibration event was a rising `StimulusBegin` transition during phase 2, labelled by `StimulusType`. The 16 shared channels were filtered from 0.5 to 30 Hz with a fourth-order zero-phase Butterworth filter, epoched from 200 ms before to 800 ms after the event, baseline corrected to the prestimulus interval, and rejected at an absolute amplitude above 150 microvolts. A session entered the analysis only when at least 10 target and 40 non-target epochs survived rejection.

Epochs were decimated by taking every twelfth sample. At 256 Hz this leaves 22 samples per channel and 352 features, and an effective sampling rate near 21.3 Hz. The effective rate is below twice the 30 Hz filter edge, so frequencies between about 10.7 and 30 Hz are not represented independently in the feature vector. The primary score is a cross-validated discriminability measure rather than a spectral estimate, and the shrinkage linear discriminant comparator computed from the identical features gave an almost identical result, but this remains a deviation from the documented decimation target and is reported rather than corrected.

The number of cross-validation folds was the smaller of five and the number of Train files in the session. Fold count therefore differs between sessions and between studies, so the sampling precision of the predictor is not identical across the cohorts whose transportability is being compared.

For each Test-phase transition to phase 3, the intended character was the final nonzero `CurrentTarget` in the directly preceding phase-2 interval and the selected character was the modal nonzero `SelectedTarget` during phase 3. A trial was eligible when feedback was displayed, both values could be recovered, and `FakeFeedback` did not override the selection. Correctness required an exact character match.

**Table S1. Feedback-phase reconstruction by source study.** Eligible counts are at the feedback-phase level. Records additionally require a usable calibration feature set for the participant-session, which is why 19,611 selections enter the analysis rather than 19,688.

| Source study | Reconstructed | Eligible | Dominant exclusion reason |
|---|---:|---:|---|
| Study A | 1,404 | 1,404 | none |
| Study B | 858 | 858 | none |
| Study C | 5,680 | 0 | artificial feedback override |
| Study D | 1,230 | 1,230 | none |
| Study E | 240 | 240 | none |
| Study F | 1,079 | 1,067 | feedback not displayed |
| Study G | 1,198 | 1,198 | none |
| Study H | 1,926 | 1,926 | none |
| Study I | 948 | 948 | none |
| Study J | 1,812 | 1,812 | none |
| Study K | 480 | 480 | none |
| Study L | 990 | 990 | none |
| Study M | 1,260 | 1,260 | none |
| Study N | 480 | 480 | none |
| Study O | 1,202 | 1,187 | feedback not displayed |
| Study P | 2,263 | 0 | intended character not recoverable |
| Study Q | 3,888 | 1,944 | feedback not displayed |
| Study R | 1,440 | 1,440 | none |
| Study S1 | 360 | 360 | none |
| Study S2 | 864 | 864 | none |
| Total | 29,602 | 19,688 | |

## S3. Model specification

The development model was a logistic regression of character-level correctness on the standardised calibration score, fitted on character-expanded records from the development studies, with standardisation using development-study means and standard deviations only. For a session with calibration score s, the estimated accuracy is the inverse logit of a + b (s - m) / d, where m and d are the development mean and standard deviation of the score.

## S4. Uncertainty

Two uncertainty statements are reported and are not interchangeable.

The participant-cluster bootstrap used 2,000 deterministic replicates. In each replicate, development participant clusters were resampled within source study, the model was refitted, and withheld participant clusters were resampled. The resulting intervals describe uncertainty conditional on the observed set of source studies, because the same studies appear in every replicate by construction.

The study-level summary treats the source study as the unit of replication. The withheld-cohort estimates were summarised by their mean and between-study standard deviation, with a t-distributed interval for the mean on k - 1 degrees of freedom and a prediction interval for an unrepresented cohort computed as the mean plus or minus t times the between-study standard deviation times the square root of one plus one over k.

**Table S2. Study-level summaries.** The calibration intercept and slope rows are the uncorrected summary of the 18 cohort estimates, which counts each cohort's sampling error as though it were between-cohort variation. For those two quantities the main text reports the random-effects estimate tau instead, and the intervals here should not be read in its place.

| Quantity | Mean across cohorts | Between-cohort SD | 95% interval for the mean | 95% interval for an unrepresented cohort |
|---|---:|---:|---|---|
| Mean absolute error | 0.101 | 0.047 | 0.077 to 0.124 | -0.002 to 0.203 |
| Brier skill score | 0.174 | 0.217 | 0.066 to 0.282 | -0.296 to 0.644 |
| Character-weighted AUC | 0.713 | 0.102 | 0.662 to 0.764 | 0.491 to 0.935 |
| Calibration intercept | -0.008 | 1.175 | -0.592 to 0.576 | -2.555 to 2.539 |
| Calibration slope | 1.100 | 0.560 | 0.822 to 1.379 | -0.113 to 2.313 |

## S5. Association at three levels

**Table S3. Association between calibration-derived decoder discriminability and observed accuracy, by level and by cohort.** Pearson intervals are two-sided 95% intervals on the Fisher z scale.

*By level.*

| Level | n | Pearson r | 95% CI | Spearman rho |
|---|---:|---:|---|---:|
| Sessions, pooled | 410 | 0.716 | 0.665 to 0.760 | 0.718 |
| Sessions, centred within cohort | 410 | 0.677 | 0.621 to 0.726 | 0.646 |
| Participants | 271 | 0.714 | 0.650 to 0.768 | 0.756 |
| Preceding session to later session | 139 pairs | 0.513 | 0.379 to 0.626 | 0.462 |
| Same session, reference for the row above | 139 pairs | 0.728 | 0.639 to 0.798 | 0.651 |

*By cohort.* ALS cohorts are listed first. The unit is the participant-session, so n is smaller than the record count in Table S2.

| Cohort | Sessions | Pearson r | 95% CI |
|---|---:|---:|---|
| Study B | 56 | 0.678 | 0.505 to 0.798 |
| Study F | 30 | 0.924 | 0.846 to 0.964 |
| Study L | 11 | 0.922 | 0.719 to 0.980 |
| Study N | 16 | 0.823 | 0.553 to 0.937 |
| Study A | 13 | 0.928 | 0.771 to 0.979 |
| Study D | 17 | 0.610 | 0.183 to 0.843 |
| Study E | 8 | 0.683 | -0.042 to 0.937 |
| Study G | 20 | 0.757 | 0.473 to 0.899 |
| Study H | 16 | 0.190 | -0.338 to 0.627 |
| Study I | 13 | 0.513 | -0.053 to 0.830 |
| Study J | 20 | 0.359 | -0.099 to 0.692 |
| Study K | 8 | 0.401 | -0.424 to 0.862 |
| Study M | 21 | 0.660 | 0.320 to 0.850 |
| Study O | 34 | 0.364 | 0.030 to 0.625 |
| Study Q | 53 | 0.773 | 0.636 to 0.863 |
| Study R | 40 | 0.425 | 0.131 to 0.651 |
| Study S1 | 10 | 0.316 | -0.392 to 0.789 |
| Study S2 | 24 | 0.609 | 0.273 to 0.813 |

The point estimate was positive in all 18 contributing cohorts. Within-cohort Pearson r ranged from 0.190 to 0.928 with a median of 0.635, and the 95% interval included zero in 6 of the 18: Study E, Study H, Study I, Study J, Study K and Study S1. All six carry 20 sessions or fewer, so the imprecision is largely a matter of cohort size rather than of a different relationship.

Session accuracy clustered within participant with an intraclass correlation of 0.412 across 410 sessions in 271 participants, giving approximately 338 effective independent sessions. The predictor is constant within a session, so the 739 session-condition records carry 410 distinct predictor values.

## S6. Sensitivity analyses

**Table S4. Prespecified sensitivity analyses.** Each analysis re-runs the complete withheld-cohort procedure on the retained data. In the last row every pair of cohorts is withheld together, so development runs on 16 cohorts rather than the 17 of the primary analysis; each cohort appears in 17 of the 153 pairs and its 17 estimates are averaged into a single value before the same across-cohort pooling is applied, because a pair shares a cohort with 32 other pairs and the pairs are not independent units. Every row therefore summarises 18 cohort-level values, or fewer where the analysis drops cohorts, and the columns carry the same meaning throughout.

| Analysis | Cohorts | Mean absolute error | Between-cohort SD | Interval for an unrepresented cohort | Calibration-slope SD |
|---|---:|---:|---:|---|---:|
| Primary, all contributing cohorts | 18 | 0.101 | 0.047 | -0.002 to 0.203 | 0.560 |
| Cohorts with outcome SD at least 0.10 | 12 | 0.124 | 0.042 | 0.029 to 0.220 | 0.601 |
| Records with artifact rejection at most 20% | 18 | 0.087 | 0.035 | 0.011 to 0.164 | 0.465 |
| Records with at least 10 eligible selections | 18 | 0.100 | 0.047 | -0.002 to 0.203 | 0.560 |
| Cohorts without a documented ALS population | 14 | 0.101 | 0.052 | -0.015 to 0.216 | 0.663 |
| ALS cohorts, prespecified primary subgroup | 4 | 0.093 | 0.016 | 0.035 to 0.151 | 0.223 |
| Leave-two-studies-out development, 153 splits | 18 | 0.101 | 0.047 | -0.002 to 0.203 | 0.560 |

Artifact rejection had a median of 0.002 across records, but 110 of 739 records exceeded 20% and the maximum was 0.97. The analysis restricted to records at or below 20% rejection is the only one in which both estimation error and calibration-slope variability improved.

Observed session-condition accuracy was at 100% in 228 of 739 records (30.9%). Three cohorts had mean accuracy at or above 0.96, where there is little variation to estimate.

The leave-two-studies-out row is indistinguishable from the primary row at the precision printed above, and that is the result rather than a rounding artefact. At four decimal places the mean absolute error is 0.1007 against 0.1006, its between-cohort standard deviation 0.0473 against 0.0472, and the uncorrected calibration-slope standard deviation 0.5599 against 0.5596. Removing one cohort from a development set of 17 neither raises the estimation error nor widens the between-cohort spread, so the transportability failure is not a consequence of the development set being too small at this scale. It says nothing about development sets much smaller than 16, which this design cannot examine while still leaving enough cohorts to withhold.

## S7. The two no-predictor benchmarks, per cohort

Skill in the main text is computed against the development-mean benchmark, which estimates every withheld record at the development-set mean accuracy. A second benchmark estimates every withheld record at that cohort's own mean, which no deployment would know. The two are different comparisons and give different counts of cohorts with negative skill, so both are given here per cohort.

Pooled, the own-mean benchmark is the harder of the two, at 0.123 against 0.146. That ordering does not hold cohort by cohort. Mean absolute error is minimised by the median rather than the mean, so a cohort's own mean is not guaranteed to beat any other constant, and it is in fact the easier target in Study A, Study F, Study K, Study L, Study M, Study N and Study Q.

Skill against the development mean is negative in one cohort, Study H. Skill against the cohort's own mean is negative in six: Study E, Study H, Study J, Study R, Study S1 and Study S2. Study S1's value is an artefact of a near-zero denominator rather than a comparable failure, because its own-mean benchmark errs by 0.005; it is reported for completeness and should not be read on the same scale as the others.

**Table S5. Model error against both no-predictor benchmarks, by withheld cohort.** ALS cohorts are listed first. Skill is one minus the ratio of the model's mean absolute error to that benchmark's.

| Cohort | Mean observed accuracy | Model MAE | Development-mean benchmark MAE | Skill vs development mean | Own-mean benchmark MAE | Skill vs own mean |
|---|---:|---:|---:|---:|---:|---:|
| Study B | 0.899 | 0.108 | 0.158 | 0.317 | 0.132 | 0.185 |
| Study F | 0.778 | 0.101 | 0.203 | 0.502 | 0.221 | 0.543 |
| Study L | 0.839 | 0.084 | 0.137 | 0.383 | 0.140 | 0.397 |
| Study N | 0.694 | 0.124 | 0.226 | 0.448 | 0.228 | 0.454 |
| Study A | 0.786 | 0.126 | 0.173 | 0.271 | 0.178 | 0.291 |
| Study D | 0.896 | 0.056 | 0.092 | 0.394 | 0.071 | 0.211 |
| Study E | 0.921 | 0.063 | 0.079 | 0.205 | 0.049 | -0.286 |
| Study G | 0.886 | 0.066 | 0.113 | 0.417 | 0.099 | 0.336 |
| Study H | 0.877 | 0.153 | 0.121 | -0.268 | 0.109 | -0.407 |
| Study I | 0.658 | 0.172 | 0.226 | 0.236 | 0.208 | 0.171 |
| Study J | 0.708 | 0.186 | 0.187 | 0.003 | 0.185 | -0.008 |
| Study K | 0.750 | 0.173 | 0.193 | 0.104 | 0.206 | 0.160 |
| Study M | 0.823 | 0.121 | 0.134 | 0.093 | 0.138 | 0.118 |
| Study O | 0.884 | 0.067 | 0.081 | 0.181 | 0.070 | 0.046 |
| Study Q | 0.820 | 0.058 | 0.096 | 0.394 | 0.099 | 0.409 |
| Study R | 0.963 | 0.059 | 0.131 | 0.547 | 0.047 | -0.263 |
| Study S1 | 0.997 | 0.043 | 0.151 | 0.717 | 0.005 | -7.090 |
| Study S2 | 0.976 | 0.048 | 0.141 | 0.657 | 0.035 | -0.363 |
| Pooled | 0.851 | 0.098 | 0.146 | 0.327 | 0.123 | 0.203 |

## S8. Comparator predictors

Comparator scores were computed from the identical calibration epochs and evaluated under the identical withheld-cohort protocol: regularised linear discriminant analysis area under the curve, grouped cross-validated classification accuracy, mean target-minus-non-target amplitude at Pz between 250 and 500 ms, the same contrast averaged over six posterior channels, and the maximum posterior signed r-squared. An exploratory specification adds ALSFRS-R to the primary score.

**Table S6. Withheld-cohort performance of every prespecified predictor.** Pooled values are computed over all withheld predictions, as in the main text. The last four columns summarise the cohort-level results and are the transportability quantities: the interval is for a cohort not represented in the archive, and the calibration-slope spread is uncorrected, as in Table S4. Rows are ordered by pooled error within each role.

| Predictor | Role | Cohorts | Records | Pooled MAE | Brier skill | AUC | Pooled slope | Between-cohort MAE SD | Interval for an unrepresented cohort | Calibration-slope SD | Calibration-slope range |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| Calibration-derived decoder discriminability | Primary | 18 | 739 | 0.098 | 0.110 | 0.748 | 0.967 | 0.047 | -0.002 to 0.203 | 0.560 | 0.185 to 2.185 |
| Shrinkage linear discriminant AUC | Comparator | 18 | 739 | 0.100 | 0.105 | 0.745 | 0.960 | 0.046 | 0.001 to 0.202 | 0.562 | 0.112 to 2.077 |
| Calibration classification accuracy | Comparator | 18 | 739 | 0.106 | 0.105 | 0.734 | 0.930 | 0.047 | 0.006 to 0.208 | 1.104 | 0.051 to 4.018 |
| Maximum posterior signed r-squared | Comparator | 18 | 739 | 0.134 | 0.037 | 0.656 | 0.643 | 0.041 | 0.045 to 0.225 | 2.209 | -0.467 to 7.297 |
| Posterior target-minus-non-target amplitude | Comparator | 18 | 739 | 0.148 | 0.003 | 0.517 | 0.275 | 0.040 | 0.061 to 0.236 | 2.459 | -4.745 to 6.387 |
| Pz target-minus-non-target amplitude | Comparator | 18 | 739 | 0.150 | 0.001 | 0.465 | -0.238 | 0.040 | 0.063 to 0.238 | 4.490 | -8.235 to 9.007 |
| Primary score plus ALSFRS-R | Exploratory | 3 | 138 | 0.085 | 0.313 | 0.834 | 0.982 | 0.009 | 0.046 to 0.133 | 0.293 | 0.771 to 1.336 |
| Primary score, same restricted records | Exploratory reference | 3 | 138 | 0.085 | 0.315 | 0.833 | 0.995 | 0.010 | 0.038 to 0.142 | 0.303 | 0.765 to 1.355 |

No confidence intervals from the participant bootstrap are reported in this table. The primary predictor's intervals are given in the main text from 2,000 replicates, and rerunning that bootstrap at a smaller replicate count for a seven-specification sweep would put a second, slightly different interval for the same primary quantity into the same paper. The uncertainty reported instead is the between-cohort spread, which requires no resampling and is the quantity the transportability question turns on. The primary row reproduces the pooled values reported in the main text on every column shown here, which is the consistency check this table can offer.

The regularised linear discriminant computed from the identical decimated features is indistinguishable from the primary score on every column, including the between-cohort spread of the calibration slope, 0.562 against 0.560. The primary result is therefore a property of how separable the calibration data are and not of the classifier family used to measure that, which is also the reason the decimation deviation recorded in S2 does not drive it.

Scoring the same classifier by classification accuracy rather than by area under the curve costs little in pooled error, 0.106 against 0.098, but doubles the spread of the calibration slope, to 1.104 across a range of 0.051 to 4.018. A thresholded summary of the same calibration data transports worse than the ranking one.

The three summaries computed without fitting a classifier are much weaker. The maximum posterior signed r-squared reaches an area under the curve of 0.656, and neither amplitude contrast separates outcomes in a cohort it was not developed on, at 0.517 and 0.465 with Brier skill of 0.003 and 0.001. Their pooled calibration slopes of 0.275 and -0.238, and per-cohort slope ranges of -4.7 to 6.4 and -8.2 to 9.0, are what the calibration parameters look like when a predictor carries almost no transportable signal. They are reported so that the primary score's own spread is read against that scale rather than in isolation.

The exploratory ALSFRS-R specification is restricted to the 138 records in 3 cohorts that carry an observed value, so its figures are not comparable with the rows above. Against the primary score run on those same 138 records it changes nothing: pooled error 0.085 against 0.085, area under the curve 0.834 against 0.833, Brier skill 0.313 against 0.315, and calibration-slope spread 0.293 against 0.303. The better appearance of both rows relative to the full archive belongs to the restriction and not to ALSFRS-R. At 3 cohorts the interval for an unrepresented cohort rests on two degrees of freedom and carries no transportability claim.

## S9. Reproducibility

The analysis pipeline executes archive validation, source metadata extraction, feedback-phase reconstruction, calibration feature extraction, withheld-cohort validation, the widened-design analyses, sensitivity analyses, and the comparator-predictor sweep. Frozen outputs are written to `output/expanded/`: `study_inventory.csv`, `analysis_records.csv`, `external_validation_metrics.csv`, `external_validation_predictions.csv`, `random_effects_pooling.csv`, `als_subgroup_metrics.csv`, `transfer_to_als.csv`, `als_meta_regression.json`, `null_benchmark.csv`, `within_study_association.csv`, `participant_level_association.csv`, `across_session_association.csv`, `across_session_pairs.csv`, `session_clustering.json`, `sensitivity_analyses.csv`, `comparator_metrics.csv`, `protocol_covariates.csv` and `protocol_meta_regression.json`. The repository test suite contains 149 tests covering provenance, European Data Format parsing, event reconstruction, feature extraction, validation, the widened-design analyses, the promised sensitivity and comparator analyses, and rendering.

## S10. Transparency statement

The study involved no new data collection, participant contact, prospective enrolment, or intervention. It does not establish a diagnostic, prognostic, causal, or treatment effect. Character-level online selection accuracy is an operational endpoint and should not be presented as communication success, quality of life, or a clinical outcome. The source studies vary in protocol, and the archive does not permit cross-study person-level linkage. Four source studies carry a documented ALS population; the remaining cohorts are described as other cohorts because the documentation does not support a positive characterisation, and no participant-level clinical characteristics were available.
