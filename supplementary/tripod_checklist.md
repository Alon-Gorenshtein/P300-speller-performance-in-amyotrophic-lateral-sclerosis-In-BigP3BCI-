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
| | Participants | 5a | Eligibility criteria | Methods, Data Source and Cohort |
| | | 5b | Setting and locations | Not fully reported; the archive documentation does not specify recording sites or locations for the individual source studies (Methods, Data Source and Cohort) |
| | | 5c | Dates of recruitment | Not applicable; legacy public archive with de-identified timestamps (Methods, Study Design and Reporting) |
| | Outcome | 6a | Outcome definition and how/when assessed | Methods, Outcome |
| | | 6b | Blinding of outcome assessment | Not applicable; outcome is a deterministic reconstruction from archived event logs, not an assessor judgement |
| | Predictors | 7a | Definition and measurement of predictors | Methods, Calibration Predictor; Methods, What the Calibration Score Is, and What It Is Not |
| | | 7b | Blinding of predictor assessment | Methods, Study Design and Reporting (calibration and outcome data are kept to separate protocol phases, not a demonstrated temporal precedence) |
| | Sample size | 8 | Explain how sample size was arrived at | Methods, Data Source and Cohort (all eligible archive studies used, not a powered sample) |
| | Missing data | 9 | Handling of missing predictor/outcome data | Methods, Calibration Predictor (epoch- and session-level inclusion thresholds); Methods, Outcome (feedback-phase eligibility); Results, Cohort; Table 1 |
| | Statistical analysis methods | 10a | Development: relationship modelling | Methods, Model Specification |
| | | 10b | Internal validation | Not applicable to this design; see 10c |
| | | 10c | External validation methods | Methods, Study Design and Reporting (internal-external cross-validation across source studies); Methods, Validation Design (one source study withheld at a time) |
| | | 10d | Any model updating | Not applicable; the fitted mapping is applied as-is to the withheld cohort, not updated |
| | Risk groups | 11 | How risk groups were created | Not applicable; outcome is a continuous accuracy proportion, not a risk category |
| | Development vs. validation | 12 | Differences between development and validation data | Methods, Study Design and Reporting (every cohort comes from one harmonised archive; the source study, not a separately assembled dataset, is the withheld unit); Discussion, Study Limitations (cohorts differ in speller matrix, stimulus paradigm, electrode type, and stopping rule) |
| Results | Participants | 13a | Flow of participants, with reasons for exclusion | Results, Cohort; Table 1 |
| | | 13b | Characteristics of participants | Results, Cohort (participant, session and selection counts); Table 2 (per-cohort composition, embedded under Results, Transportability) |
| | | 13c | Comparison of development vs. validation participants | Discussion, Study Limitations (cohort heterogeneity discussed; no separate person-level comparison table because cohorts, not held-out individuals, are the unit withheld) |
| | Model development | 14a | Unadjusted association between predictors and outcome | Results, Association Between Calibration-Derived Decoder Discriminability and Online Accuracy |
| | | 14b | Model specification | Methods, Model Specification |
| | Model specification | 15a | Full prediction model (all coefficients) | Supplementary Table S9 (fitted coefficients of every development fold) |
| | | 15b | Explanation of how to use the model | Methods, Model Specification (closed-form estimate, a + b(s-m)/d); Supplementary Table S9 (worked numeric example) |
| | Model performance | 16 | Performance measures with confidence intervals | Results, Estimation Error and Its Reference Points (pooled measures); Results, Transportability (per-cohort heterogeneity; Table 2; Figures 1-3) |
| | Model updating | 17 | Details of model updating | Not applicable; see item 10d |
| Discussion | Limitations | 18 | Study limitations, sources of bias | Discussion, Study Limitations |
| | Interpretation | 19a | Interpretation for validation studies, considering objectives, limitations, results from similar studies | Discussion, paragraphs 1-3 |
| | | 19b | Overall interpretation, implications for practice | Discussion, Conclusion |
| | Implications | 20 | Potential clinical use, implications for future research | Discussion, Conclusion; Abstract, Significance |
| Other information | Supplementary information | 21 | Availability of supplementary resources | Data and Code Availability (data and code); the Supplementary Information document (`supplementary/supplement_expanded.md`) and this checklist (`supplementary/tripod_checklist.md`) are submitted as separate companion files alongside the manuscript, not referenced by filename in the main text |
| | Funding | 22 | Source of funding | Acknowledgements |
