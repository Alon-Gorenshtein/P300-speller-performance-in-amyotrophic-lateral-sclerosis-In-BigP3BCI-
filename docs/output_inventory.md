# Output inventory

- `analysis_records.csv`: frozen session-condition denominators and features.
- `external_validation_predictions.csv`: all predictions generated in a held-out source study.
- `external_validation_metrics.csv`: primary, secondary, and exploratory validation metrics with cluster-bootstrap intervals.
- `figures/figure_1_study_flow.*`: cohort and validation design flow.
- `figures/figure_2_calibration_relationship.*`: calibration discriminability against observed and held-out predicted online accuracy.
- `figures/figure_3_external_validation_auc.*`: held-out-study and pooled primary-model discrimination.
- `sensitivity_analyses.csv`: the prespecified sensitivity analyses, one row each, including leave-two-studies-out development.
- `comparator_metrics.csv`: withheld-cohort performance of every prespecified predictor, with the exploratory specification and the primary score run on its restricted records.
- `fold_coefficients.csv`: the intercept, slope and standardisation constants of each development fold, enough to recompute any held-out estimate.
