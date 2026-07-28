# TRIPOD checklist for prediction model development and validation

Completed against `manuscript/manuscript_expanded.md` (this study is a validation of a previously
proposed calibration-to-accuracy relationship, not a development of a new model; items specific to
model development are marked not applicable and the reason is given). Section and table references
below follow the manuscript's current headings; where a checklist item is only partly addressed in
the text, that gap is stated rather than papered over.

| Section | Item | # | Checklist item | Reported on page/section |
|---|---|---|---|---|
| Title and abstract | Title | 1 | Identify as a validation study; specify the target population and outcome | Title; Abstract, Objective |
| | Abstract | 2 | Structured summary of objectives, design, setting, participants, predictor, outcome, statistical analysis, results, conclusions | Abstract |
| Introduction | Background | 3a | Explain the medical context and rationale | Introduction, paragraphs 1-2 |
| | Objectives | 3b | State study objectives, including whether developing or validating | Introduction, final paragraph; Methods, Study Design and Reporting |
| Methods | Source of data | 4a | Study design, data source | Methods, Study Design and Reporting (design); Methods, Data Source and Cohort (archive) |
| | | 4b | Study dates | Methods, Data Source and Cohort (archive version and digest; no recruitment dates, because this is a legacy public archive) |
| | Participants | 5a | Setting and locations of centres | Not fully reported; the archive documentation does not specify recording sites or locations for the individual source studies (Methods, Data Source and Cohort) |
| | | 5b | Eligibility criteria | Methods, Data Source and Cohort |
| | | 5c | Treatments received, if relevant | Not applicable; this is a retrospective secondary analysis of archived P300-speller task-performance data with no clinical treatment or intervention (Methods, Ethics: "no new data collection, no participant contact, and no intervention") |
| | Outcome | 6a | Outcome definition and how/when assessed | Methods, Outcome |
| | | 6b | Blinding of outcome assessment | Not applicable; outcome is a deterministic reconstruction from archived event logs, not an assessor judgement |
| | Predictors | 7a | Definition and measurement of predictors | Methods, Calibration Predictor; Methods, What the Calibration Score Is, and What It Is Not |
| | | 7b | Blinding of predictor assessment | Methods, Study Design and Reporting (calibration and outcome data are kept to separate protocol phases, not a demonstrated temporal precedence) |
| | Sample size | 8 | Explain how sample size was arrived at | Methods, Data Source and Cohort (all eligible archive studies used, not a powered sample) |
| | Missing data | 9 | Handling of missing predictor/outcome data | Methods, Calibration Predictor (epoch- and session-level inclusion thresholds); Methods, Outcome (feedback-phase eligibility); Results, Cohort; Table 1 |
| | Statistical analysis methods | 10a | Development: how predictors were handled in the analyses | Methods, Model Specification (calibration score standardised to the development-study mean and standard deviation and entered as a single continuous term) |
| | | 10b | Development: type of model, model-building procedures (including predictor selection), and method for internal validation | Methods, Model Specification (logistic regression of character-level correctness on the single, pre-defined calibration score; no predictor-selection procedure, because only one predictor was evaluated). This design has no internal-validation step distinct from the leave-one-cohort-out procedure itself; that procedure is the validation and is reported under 10c |
| | | 10c | Validation: how the predictions were calculated | Methods, Model Specification (predicted accuracy is the inverse logit of a + b(s-m)/d, using that fold's fitted coefficients, Supplementary Table S9); Methods, Validation Design (one source study withheld at a time) |
| | | 10d | Measures used to assess model performance | Methods, Statistical Analysis (mean absolute error against development-mean and held-out-cohort-mean benchmarks; root mean squared error; character-weighted Brier score and Brier skill score; calibration intercept and slope; character-weighted area under the curve) |
| | | 10e | Validation: any model updating | Not applicable; the fitted mapping from each development fold is applied as-is to its withheld cohort, not updated or recalibrated |
| | Risk groups | 11 | How risk groups were created | Not applicable; outcome is a continuous accuracy proportion, not a risk category |
| | Development vs. validation | 12 | Differences between development and validation data | Methods, Study Design and Reporting (every cohort comes from one harmonised archive; the source study, not a separately assembled dataset, is the withheld unit); Discussion, Study Limitations (cohorts differ in speller matrix, stimulus paradigm, electrode type, and stopping rule) |
| Results | Participants | 13a | Flow of participants, with reasons for exclusion | Results, Cohort; Table 1 |
| | | 13b | Characteristics of participants | Results, Cohort (participant, session and selection counts); Table 2 (per-cohort composition, embedded under Results, Transportability) |
| | | 13c | Comparison of development vs. validation participants | Discussion, Study Limitations (cohort heterogeneity discussed; no separate person-level comparison table because cohorts, not held-out individuals, are the unit withheld) |
| | Model development | 14a | Number of participants and outcome events in each analysis | Results, Cohort (271 participants, 410 sessions, 739 records, 19,611 analysed character selections; the outcome is a continuous per-record accuracy proportion rather than a discrete event count, see item 11) |
| | | 14b | Unadjusted association between each candidate predictor and outcome, if done | Results, Association Between Calibration-Derived Decoder Discriminability and Online Accuracy |
| | Model specification | 15a | Full prediction model (all coefficients) | Supplementary Table S9 (fitted coefficients of every development fold) |
| | | 15b | Explanation of how to use the model | Methods, Model Specification (closed-form estimate, a + b(s-m)/d); Supplementary Table S9 (worked numeric example) |
| | Model performance | 16 | Performance measures with confidence intervals | Results, Estimation Error and Its Reference Points (pooled measures); Results, Transportability (per-cohort heterogeneity, including Brier skill; Table 2; Table S11; Figures 1-4) |
| | Model updating | 17 | Details of model updating | Not applicable; see item 10e |
| Discussion | Limitations | 18 | Study limitations, sources of bias | Discussion, Study Limitations |
| | Interpretation | 19a | Interpretation for validation studies, with reference to performance in the development data | Discussion, paragraph 6 (fold-coefficient stability: development-fold intercept and slope coefficients vary by only 2.5% and 3.3% across folds, against 49.4% for the held-out cohort-specific validated slopes in Table S11) |
| | | 19b | Overall interpretation, implications for practice | Discussion, Conclusion |
| | Implications | 20 | Potential clinical use, implications for future research | Discussion, Conclusion; Abstract, Significance |
| Other information | Supplementary information | 21 | Availability of supplementary resources | Data and Code Availability (data and code); the Supplementary Information document (`supplementary/supplement_expanded.md`) and this checklist (`supplementary/tripod_checklist.md`) are submitted as separate companion files alongside the manuscript, not referenced by filename in the main text |
| | Funding | 22 | Source of funding | Acknowledgements |
