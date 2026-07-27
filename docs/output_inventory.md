# Output inventory

Paths are relative to `output/`.

## Frozen outputs of the 18-cohort design

These are the outputs the current manuscript and supplement are written from.

- `expanded/analysis_records.csv`: frozen session-condition denominators and features.
- `expanded/external_validation_predictions.csv`: all predictions generated in a withheld source study.
- `expanded/external_validation_metrics.csv`: primary, secondary, and exploratory validation metrics with cluster-bootstrap intervals.
- `expanded/sensitivity_analyses.csv`: the sensitivity analyses, one row each, including leave-two-studies-out development.
- `expanded/comparator_metrics.csv`: withheld-cohort performance of every predictor named in the Methods, with the exploratory specification and the primary score run on its restricted records.
- `expanded/fold_coefficients.csv`: the intercept, slope and standardisation constants of each development fold, enough to recompute any held-out estimate.

## Figures of the 18-cohort design

Labelled by manuscript figure number, which is not part of the filename. All five are written by
`scripts/13_render_figures.py`.

- `expanded/figures/figure_calibration_forest.*`: **Figure 1**, every cohort's calibration slope and intercept with its interval, the pooled value and the new-cohort interval.
- `expanded/figures/figure_calibration_curves.*`: **Figure 2**, observed against estimated session accuracy in equal-count bins of the estimate, one panel per withheld cohort.
- `expanded/figures/figure_transportability.*`: **Figure 3**, withheld-cohort estimation error with the mean and the new-cohort interval.
- `expanded/figures/figure_skill_by_cohort.*`: **Figure 4**, error reduction against the development-mean benchmark.
- `expanded/figures/figure_cohort_type_relationship.*`: **Figure S1**, the records by cohort type, descriptive and unfitted.

## Superseded four-cohort outputs, do not submit

The four-cohort design these belong to was replaced by the 18-cohort design above, and nothing in this
group is cited by the current manuscript or supplement. Their filenames carry the numbers 1 to 3,
which do **not** correspond to the manuscript's Figure 1 to Figure 4 listed above, so they must never
be matched to a figure number at upload time.

- `final/figures/figure_1_study_flow.*`: cohort and validation design flow. Superseded.
- `final/figures/figure_2_calibration_relationship.*`: calibration discriminability against observed and held-out predicted online accuracy. Superseded.
- `final/figures/figure_3_external_validation_auc.*`: held-out-study and pooled primary-model discrimination. Superseded.
- `final/figures_revised/*`: a later four-cohort redraw of the first two of those. Superseded.
- `final/*.csv`, `final/*.json`: the four-cohort frozen outputs the figures above were drawn from. Superseded. The four-cohort *intermediates* they came from, `intermediate/*_with_b.csv`, are not superseded: `tests/test_regression_baseline.py` reads them as a statistical-code drift guard.
