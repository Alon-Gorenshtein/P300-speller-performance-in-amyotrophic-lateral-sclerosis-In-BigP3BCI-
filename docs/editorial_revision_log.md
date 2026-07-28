# Editorial Revision Log

The attached editorial assessment was treated as a major revision before any revised submission package is built.

## Changes implemented

1. The primary outcome is the participant-session-condition proportion of correct eligible online selections, modeled as a binomial count. Character-expanded AUC is retained only as a secondary, character-weighted ranking measure.
2. The cohort now includes every ALS-labelled BigP3BCI source study with the shared 16-channel montage and recoverable Train and Test phases: B, F, L, and N. Numerical ALSFRS-R was removed as an eligibility criterion because it is exploratory only.
3. The validation terminology is source-study-held-out or cross-study. The manuscript will not describe the legacy source studies as independent external clinical cohorts.
4. Primary model evaluation now reports session-level MAE, RMSE, Brier score, Brier skill score, calibration intercept, and calibration slope. Every confidence interval uses 2,000 participant-cluster bootstrap replicates that refit the development model and resample the held-out source study.
5. The analysis records raw-score and logistic-probability character AUCs side by side. With a single monotonic predictor they are equal within each held-out source study; the pooled difference reflects source-specific probability transformations.
6. Comparator features now include posterior target-minus-nontarget amplitude, posterior signed r-squared, grouped calibration accuracy, regularized LDA AUC, Pz amplitude, usable calibration epoch count, and artifact-rejection fraction.
7. The revised manuscript will cite direct ALS P300 performance-prediction literature and frame the contribution as transparent cross-study evaluation with strict Train/Test phase separation, not as the first evidence that EEG and P300-BCI performance are related.

## Remaining production work

The manuscript, supplement, figures, AMA bibliography, cover letter, and rendered submission folder must be regenerated from the revised outputs. The prior submission package is superseded and must not be submitted.

## 2026-07-28: JNE pre-submission review response

A second, pre-submission editorial review of the 18-cohort widened design (`manuscript/manuscript_expanded.md`, `supplementary/supplement_expanded.md`) produced a 16-task revision pass, tracked in `.superpowers/sdd/2026-07-27-jne-presubmission-review-fixes/`. It addressed six numbered scientific and statistical concerns, cut manuscript length, rebuilt the render and figure pipeline, consolidated the front-matter declarations, added a TRIPOD checklist, and rewrote the cover letter.

### Scientific and statistical fixes

1. Added a participant-cluster bootstrap as a second, non-asymptotic standard-error method for cohort calibration (`cohort_calibration(..., se_method="bootstrap")`, 2,000 participant-cluster replicates), addressing the concern that the clustered sandwich estimator understates variance at the 5-24 participants per cohort seen here.
2. Added explicit prose stating that the 18 development folds are themselves stable (intercept and slope coefficients of variation 2.5% and 3.3% across folds, against 49.4% for the held-out cohort-specific validated slopes in Table 2, from the already-committed Table S9), and a matching Limitations point stating that the 18 held-out estimates are not fully independent, since each development fold shares 16 of the other 17 cohorts with every other fold.
3. Fixed the mean absolute error prediction interval so it cannot cross zero: MAE is bounded at zero, and the symmetric raw-scale interval previously reported ran -0.002 to 0.203. Pooling is now done on the log scale and back-transformed (`random_effects_pooling(..., transform="log")`), giving a 95% interval for an unrepresented cohort of 0.032 to 0.254. AUC and Brier skill score, which are not bounded at zero the same way (Brier skill is legitimately negative), were left on the identity scale.
4. Reworded the stopping-rule moderator finding from causal ("accounted for two thirds of the between-cohort variance") to associational ("was associated with a reduction in estimated residual between-cohort variance"), de-duplicated the phrase across the abstract and two Results subsections, and reduced its prominence in the abstract and cover letter, since it is a secondary, exploratory finding and the paper's principal result is the lack of transportability.
5. Softened "subsequent online accuracy" to same-session phrasing everywhere the primary analysis is described, since the archive's timestamps are de-identified and recording order cannot be established from file headers (already stated in Methods). The one analysis with genuine temporal separation, the preceding-session secondary analysis, kept its precedence language.
6. Reframed the ALS "primary subgroup" language: the chronology (no analysis plan was registered; the four ALS cohorts were the project's own working note before the design widened) is now stated once, in Methods, rather than repeated as "primary" through the manuscript.

### Length

Prose-only main-text body word count (Introduction through Conclusion, tables/figures/captions excluded) was cut from 9,247 to 8,011 words, by moving dense moderator- and sensitivity-analysis detail into the supplement (verified line by line so no number was lost) and condensing three further Discussion/Limitations paragraphs to single supporting numbers with supplement cross-references.

### Figures and formatting

- Replaced the prior manual/ad hoc rendering process, which had produced a stale PDF with literal `{width=NN%}` text visible in the output, with a reproducible pandoc render pipeline (`scripts/15_build_manuscript.py`) that is now the only way the manuscript, cover letter, and supplement are rendered to `.pdf`/`.docx`.
- Split the 18-panel calibration-curve figure into a 6-panel main-text Figure 2 (the four ALS cohorts plus the two non-ALS cohorts at the extremes of the calibration-slope range) and a full 18-panel Figure S2 in the supplement, so the main-text figure is legible.
- Distinguished ALS cohorts from other cohorts by marker shape (diamond versus circle) as well as by color, wherever cohort type is plotted, for grayscale and color-vision accessibility.
- Moved every table and figure from a single trailing "Tables and Figure Legends" section to sit near its first in-text citation, in ascending order, with each caption immediately adjacent to its image.

### Declarations

Moved Funding, Competing interests, Ethics approval, and Author contributions out of the front matter and into a new `## Acknowledgements` section immediately before `## Data and Code Availability`, per IOP Publishing's stated policy that this information belongs in the cover letter at submission and in an acknowledgements section after acceptance, not on the manuscript's front page.

### TRIPOD checklist

Added `supplementary/tripod_checklist.md`, a completed TRIPOD (2015) checklist with one row per item, citing the exact manuscript section that reports it; items specific to model development rather than validation are marked not applicable with the reason given.

### Cover letter

Rewrote the cover letter from 1,143 words and 4 rendered pages to approximately 472 words and 1-2 pages, in the five-part structure the review specifies, with an explicit competing-interests sentence and the public-dataset-rule paragraph removed. Per an explicit author decision, the companion-manuscript disclosure paragraph was cut entirely rather than reworded.
