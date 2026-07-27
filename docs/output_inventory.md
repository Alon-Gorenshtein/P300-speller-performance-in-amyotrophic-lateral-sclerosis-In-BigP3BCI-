# Output inventory

- `analysis_records.csv`: frozen session-condition denominators and features.
- `external_validation_predictions.csv`: all predictions generated in a held-out source study.
- `external_validation_metrics.csv`: primary, secondary, and exploratory validation metrics with cluster-bootstrap intervals.
- `figures/figure_1_study_flow.*`: cohort and validation design flow.
- `figures/figure_2_calibration_relationship.*`: calibration discriminability against observed and held-out predicted online accuracy.
- `figures/figure_3_external_validation_auc.*`: held-out-study and pooled primary-model discrimination.
- `expanded/figures/figure_calibration_forest.*`: Figure 1, every cohort's calibration slope and intercept with its interval, the pooled value and the new-cohort interval.
- `expanded/figures/figure_calibration_curves.*`: Figure 2, observed against estimated session accuracy in deciles, one panel per withheld cohort.
- `expanded/figures/figure_transportability.*`: Figure 3, withheld-cohort estimation error with the mean and the new-cohort interval.
- `expanded/figures/figure_skill_by_cohort.*`: Figure 4, error reduction against the development-mean benchmark.
- `expanded/figures/figure_cohort_type_relationship.*`: Figure S1, the records by cohort type, descriptive and unfitted. All five are written by `scripts/13_render_figures.py`.
- `sensitivity_analyses.csv`: the prespecified sensitivity analyses, one row each, including leave-two-studies-out development.
- `comparator_metrics.csv`: withheld-cohort performance of every prespecified predictor, with the exploratory specification and the primary score run on its restricted records.
- `fold_coefficients.csv`: the intercept, slope and standardisation constants of each development fold, enough to recompute any held-out estimate.
