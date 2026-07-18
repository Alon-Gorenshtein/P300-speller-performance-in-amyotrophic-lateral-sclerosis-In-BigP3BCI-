# Supplementary material

## S1. Study design and data provenance

This retrospective secondary analysis used the BigP3BCI version 1.0.0 public archive. The downloaded archive had SHA256 digest `eea294aa34e9ed11e5a25d07e30aeefdf8b2d467a8309e2c38405a289afcd72f`. Before any signal was processed, the ingestion pipeline checked this archive digest, read the distributor checksum manifest, selected non-AppleDouble EDF files for Studies F, L, and N, and checked every selected file against its manifest digest. The analysis cache was atomically materialized after verification. The source archive and cache are not redistributed in this package.

The eligible cohorts had 10 ALS study-scoped records and 30 sessions in Study F, 11 records and 11 sessions in Study L, and 8 records and 16 sessions in Study N. All three cohorts had 16 shared EEG channels sampled at 256 Hz. The source studies differed in spelling matrix and session protocol. Study-scoped participant identifiers were retained to prevent accidental cross-study linkage. They do not identify unique people across studies.

## S2. Predictor and outcome reconstruction

The primary predictor used Train-phase EDF files only. A calibration event was a rising `StimulusBegin` transition occurring during phase 2. Events were labelled target or non-target using `StimulusType`. For the 16 shared channels, EEG was filtered from 0.5 to 30 Hz with zero-phase filtering. Epochs extended from 200 ms before to 800 ms after the event, were baseline corrected to the prestimulus interval, and were excluded at an absolute amplitude exceeding 150 microvolts. Epochs were temporally downsampled and entered into a regularized logistic classifier. Grouped cross-validated AUC, with EDF file as the grouping unit, was the primary calibration score. The secondary Pz measure was target-minus-nontarget amplitude from 250 to 500 ms.

For each Test-phase transition to phase 3, the intended character was the final nonzero `CurrentTarget` value in the directly preceding phase-2 interval. The selected character was the modal nonzero `SelectedTarget` value in phase 3. A trial was eligible only when feedback was displayed, both values could be recovered, and `FakeFeedback` did not override the selection. Correctness required an exact character match.

**Table S1. Feedback-phase reconstruction and exclusions.**

| Source study | Eligible selections | Excluded phases | Reconstructed phases |
|---|---:|---:|---:|
| Study F | 1,067 | 12 | 1,079 |
| Study L | 990 | 0 | 990 |
| Study N | 480 | 0 | 480 |
| Total | 2,537 | 12 | 2,549 |

## S3. Validation analysis

For each source study, the primary model was trained using the two other studies. Predictor standardization and fitting occurred only in the training studies. The held-out-study prediction probability was compared with character-level correctness. The pooled out-of-study result combines those predictions, not in-sample predictions. Confidence intervals were 2.5th and 97.5th percentiles from 1,000 deterministic bootstrap resamples of held-out study-scoped participant clusters. They estimate uncertainty in validation metrics conditional on the frozen held-out predictions.

The prespecified secondary analysis used Pz amplitude instead of the primary calibration score. The exploratory analysis added recorded ALSFRS-R values. The sensitivity analysis used leave-one-participant-out training and testing within each source study.

**Table S2. Primary calibration-score validation metrics.**

| Held-out study | Records | Selections | AUC (95% CI) | Brier / MAE |
|---|---:|---:|---:|---:|
| Study F | 10 | 1,067 | 0.860 (0.694-0.915) | 0.107 / 0.086 |
| Study L | 11 | 990 | 0.803 (0.657-0.884) | 0.112 / 0.092 |
| Study N | 8 | 480 | 0.799 (0.635-0.886) | 0.164 / 0.121 |
| Pooled out-of-study | 29 | 2,537 | 0.829 (0.757-0.872) | 0.120 / 0.091 |

**Table S3. Pooled comparator and exploratory metrics.**

| Feature | AUC (95% CI) | Brier / MAE |
|---|---:|---:|
| Pz amplitude | 0.480 (0.370-0.592) | 0.172 / 0.208 |
| EEG score plus ALSFRS-R | 0.826 (0.753-0.870) | 0.121 / 0.094 |

**Table S4. Within-study leave-one-participant-out sensitivity analysis.**

| Source study | Records | Selections | AUC | Brier score | Mean absolute error |
|---|---:|---:|---:|---:|---:|
| Study F | 10 | 1,067 | 0.858 | 0.110 | 0.094 |
| Study L | 11 | 990 | 0.801 | 0.110 | 0.075 |
| Study N | 8 | 480 | 0.756 | 0.174 | 0.137 |

## S4. Reproducibility materials

The code executes the following sequence: archive validation, source metadata extraction, feedback-phase reconstruction, calibration feature extraction, held-out-study validation, sensitivity analysis, and figure rendering. The final analysis files are `analysis_records.csv`, `external_validation_predictions.csv`, `external_validation_metrics.csv`, `within_study_lopo_sensitivity.csv`, and `trial_exclusion_summary.csv` in `output/final/`. The accompanying repository test suite contains 19 tests covering file provenance, EDF parsing, event reconstruction, feature extraction, validation, sensitivity analysis, and rendering.

## S5. Transparency statement

The study did not involve new data collection, participant contact, prospective enrolment, or clinical intervention. It does not establish a diagnostic, prognostic, causal, or treatment effect. Character-level online P300-speller correctness is an operational endpoint and should not be presented as real-world communication success, quality of life, or a clinical outcome. The historical source studies vary in protocol and the dataset does not permit cross-study person-level linkage.
