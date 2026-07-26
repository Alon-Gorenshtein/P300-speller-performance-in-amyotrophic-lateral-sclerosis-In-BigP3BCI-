# Supplementary material

## S1. Study design and data provenance

This retrospective secondary analysis used the BigP3BCI version 1.0.0 public archive. The downloaded archive had SHA256 digest `eea294aa34e9ed11e5a25d07e30aeefdf8b2d467a8309e2c38405a289afcd72f`. Before any signal was processed, the ingestion pipeline checked this archive digest, read the distributor checksum manifest, selected non-AppleDouble EDF files for Studies B, F, L, and N, and checked every selected file against its manifest digest. The analysis cache was atomically materialized after verification. The source archive and cache are not redistributed in this package.

The eligible cohorts had 18 ALS study-scoped records and 56 sessions in Study B, 10 records and 30 sessions in Study F, 11 records and 11 sessions in Study L, and 8 records and 16 sessions in Study N. All four cohorts had 16 shared EEG channels sampled at 256 Hz. The source studies differed in spelling matrix and session protocol. Study-scoped participant identifiers were retained to prevent accidental cross-study linkage. They do not identify unique people across studies.

## S2. Predictor and outcome reconstruction

The primary predictor used Train-phase EDF files only. A calibration event was a rising `StimulusBegin` transition occurring during phase 2. Events were labelled target or non-target using `StimulusType`. For the 16 shared channels, EEG was filtered from 0.5 to 30 Hz with zero-phase filtering. Epochs extended from 200 ms before to 800 ms after the event, were baseline corrected to the prestimulus interval, and were excluded at an absolute amplitude exceeding 150 microvolts. Epochs were temporally downsampled and entered into a regularized logistic classifier. Grouped cross-validated AUC, with EDF file as the grouping unit, was the primary calibration score. The secondary Pz measure was target-minus-nontarget amplitude from 250 to 500 ms.

For each Test-phase transition to phase 3, the intended character was the final nonzero `CurrentTarget` value in the directly preceding phase-2 interval. The selected character was the modal nonzero `SelectedTarget` value in phase 3. A trial was eligible only when feedback was displayed, both values could be recovered, and `FakeFeedback` did not override the selection. Correctness required an exact character match.

**Table S1. Feedback-phase reconstruction and exclusions.**

| Source study | Eligible selections | Excluded phases | Reconstructed phases |
|---|---:|---:|---:|
| Study B | 858 | 0 | 858 |
| Study F | 1,067 | 12 | 1,079 |
| Study L | 990 | 0 | 990 |
| Study N | 480 | 0 | 480 |
| Total | 3,395 | 12 | 3,407 |

Eligibility in this table is defined at the feedback-phase level. The 3,318 selections entering the analysis records are the subset of these 3,395 eligible selections whose participant-session also supplied a usable calibration feature set.

## S3. Validation analysis

For each source study, the primary model was trained using the three other studies. Predictor standardization and fitting occurred only in the training studies. The held-out-study prediction probability was compared with character-level correctness. The pooled out-of-study result combines those predictions, not in-sample predictions. Confidence intervals were 2.5th and 97.5th percentiles from 2,000 deterministic bootstrap replicates. In each replicate, development participant clusters were resampled within source study, the model was refit, and held-out participant clusters were resampled.

Comparator analyses replaced the primary calibration score with posterior amplitude, posterior signed r-squared, calibration accuracy, regularized linear discriminant analysis AUC, and Pz amplitude, each fitted and evaluated under the identical held-out-study protocol. The sensitivity analysis used leave-one-participant-out training and testing within each source study.

**Table S2. Primary calibration-score validation metrics.**

| Held-out study | Records | Selections | AUC (95% CI) | Brier / MAE |
|---|---:|---:|---:|---:|
| Study B | 18 | 781 | 0.817 (0.665-0.910) | 0.080 / 0.114 |
| Study F | 10 | 1,067 | 0.860 (0.662-0.915) | 0.108 / 0.085 |
| Study L | 11 | 990 | 0.803 (0.662-0.877) | 0.110 / 0.076 |
| Study N | 8 | 480 | 0.799 (0.617-0.885) | 0.166 / 0.129 |
| Pooled out-of-study | 47 | 3,318 | 0.828 (0.761-0.866) | 0.110 / 0.095 |

**Table S3. Pooled comparator metrics.**

| Feature | AUC (95% CI) | Brier / MAE |
|---|---:|---:|
| Regularized linear discriminant analysis AUC | 0.823 (0.757-0.862) | 0.111 / 0.095 |
| Calibration accuracy | 0.742 (0.676-0.799) | 0.142 / 0.154 |
| Posterior signed r-squared | 0.583 (0.480-0.723) | 0.150 / 0.184 |
| Posterior amplitude | 0.474 (0.370-0.636) | 0.155 / 0.198 |
| Pz amplitude | 0.444 (0.345-0.610) | 0.155 / 0.197 |

All comparator rows are pooled held-out predictions across 47 study-scoped records and 3,318 selections.

**Table S4. Within-study leave-one-participant-out sensitivity analysis.**

| Source study | Records | Selections | AUC | Brier score | Mean absolute error |
|---|---:|---:|---:|---:|---:|
| Study B | 18 | 781 | 0.806 | 0.073 | 0.080 |
| Study F | 10 | 1,067 | 0.858 | 0.110 | 0.094 |
| Study L | 11 | 990 | 0.801 | 0.110 | 0.075 |
| Study N | 8 | 480 | 0.756 | 0.174 | 0.137 |

## S4. Reproducibility materials

The code executes the following sequence: archive validation, source metadata extraction, feedback-phase reconstruction, calibration feature extraction, held-out-study validation, sensitivity analysis, and figure rendering. The final analysis files are `analysis_records.csv`, `external_validation_predictions.csv`, `external_validation_metrics.csv`, `within_study_lopo_sensitivity.csv`, and `trial_exclusion_summary.csv` in `output/final/`. The accompanying repository test suite contains 19 tests covering file provenance, EDF parsing, event reconstruction, feature extraction, validation, sensitivity analysis, and rendering.

## S5. Transparency statement

The study did not involve new data collection, participant contact, prospective enrolment, or clinical intervention. It does not establish a diagnostic, prognostic, causal, or treatment effect. Character-level online P300-speller correctness is an operational endpoint and should not be presented as real-world communication success, quality of life, or a clinical outcome. The historical source studies vary in protocol and the dataset does not permit cross-study person-level linkage.
