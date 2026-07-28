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

### Deliberately deferred, not yet done

Two items were identified during this revision pass and deliberately left for the submitting author rather than implemented here: a DOI-backed code archive (a Zenodo or OSF deposit of this repository, cited in the manuscript's Data and Code Availability statement) and an optional shortening of the manuscript title. Neither blocks submission on its own, but both should be resolved, or consciously accepted as-is, before upload. Both are also listed as pending action items in `submission/AUTHOR_ACTIONS.md`.

## 2026-07-28: Second pre-submission review pass (14-task plan)

A further, second pre-submission editorial review of the same 18-cohort widened design was addressed by a 14-task revision pass, tracked in `.superpowers/sdd/2026-07-28-jne-second-presubmission-review/` (commits `dfdd15e..45fedf9` on `worktree-jne-second-presubmission-review`, this entry's own rebuild and verification following as the closing task). It addressed ten items: a matched-cohort bootstrap comparison, a new joint-bootstrap covariance analysis, log-scale MAE labeling, independence wording, practical-use softening, figure/table legibility, a protocol-descriptor metadata correction, a commit-hash citation, novelty citations, and minor textual fixes.

### Scientific and statistical fixes

1. **Protocol-descriptor metadata (Task 1).** Wired the archive's own documented speller grid size and use of a checkerboard-variant stimulus paradigm into the protocol-descriptor moderator analysis (`documented_protocol_metadata()`, `src/bigp3_als/protocol.py`), alongside the two existing empirical matrix-size proxies. Both new descriptors returned a share of the between-cohort variance indistinguishable from zero (Holm-adjusted p = 1.00), the most likely outcome anticipated going in. The ALS-cohort/grid-size confound is stated explicitly, and an equipment-invariance caveat was added; the stopping-rule moderator sentence itself was preserved verbatim with one distinguishing clause appended.
2. **Matched-cohort bootstrap comparison (Task 2).** Added `random_effects_matched_cohorts`, repeating the cluster-robust pooling on the identical 17 cohorts the participant-cluster bootstrap could identify (excluding Study S1, which the bootstrap could not identify): tau = 0.44/0.87 (slope/intercept) versus the bootstrap's own 0.37/0.77 and the all-18 cluster-robust values of 0.43/0.87. Most of the gap between the cluster-robust and bootstrap estimators reflects the estimator itself, not Study S1's exclusion; this was verified rather than assumed. Per-cohort bootstrap replicate diagnostics were exposed via a new `n_bootstrap_replicates` return value. **The Firth/penalized-regression alternative for the bootstrap, raised as a further possible sensitivity check, was consciously deferred and not implemented, per Task 2's own brief** — it remains an open item for a future revision, not an oversight.
3. **Joint-bootstrap covariance analysis (Task 3).** Added `joint_bootstrap_fold_covariance`, jointly resampling participants once per replicate (not once per fold) across all 18 leave-one-study-out development folds, producing a 36x36 covariance/correlation matrix over the fold-level intercept and slope estimates, to characterize the dependence induced by folds sharing development data. A first implementation lacked the separation guard used elsewhere in the codebase and inflated Study S1's contribution to the summary standard deviations 9-20x; caught in review and corrected before being reported anywhere (corrected `replicate_between_cohort_sd_intercept` mean 1.62 [0.94, 3.36], `_slope` mean 0.79 [0.49, 1.56]). The corrected quantity is documented as `sqrt(tau^2 + within-cohort sampling variance)`, not a substitute for tau.
4. **Reporting the joint-bootstrap findings (Task 4).** Added the corrected numbers above to the manuscript and a new Table S10 describing the largest cross-cohort correlations; fixed an imprecise "seven of eight" pair-count in the Table S10 description to the exact count (all eight listed pairs contain at least one of Study F/J/L/Q; six of eight pair two of them against each other).
5. **Log-scale MAE labeling (Task 5).** Added an explicit Methods sentence stating that cohort-level MAE is pooled after natural-log transformation and back-transformed as a geometric mean, and labeled every subsequent use of "mean absolute error" across the manuscript Results, Figure 3's caption, and Supplementary Tables S2/S4/S6 as the geometric mean, with the arithmetic mean (0.101) given alongside the geometric mean (0.090) at its first appearance, so a reader cannot mistake which averaging convention produced the reported prediction interval.
6. **Independence wording (Task 6).** Corrected two remaining overreaching uses of "independent" (Discussion opener, Conclusion) to "source-study cohorts", leaving the separate, already-correct "not fully independent" sentence (about shared development data across folds) untouched. Added a Data-Source-and-Cohort caveat and an eleventh Limitations point stating that participant identifiers are study-scoped, so cross-study participant overlap could not be ruled out.
7. **Practical-use softening (Task 7).** Reworded "a concrete step" to "a candidate step that warrants prospective evaluation" in the Discussion, and softened the Conclusion's ranking/data-quality-screen claims with "after local validation" / "warrants prospective evaluation; neither use has been prospectively validated here"; the firm statement against reporting expected accuracy without recalibration was kept verbatim.

### Figures and tables

- Enlarged Figure 1's legend and axis text and Figure 2's main-text panel grid for legibility, and made Figure 4's ALS/non-ALS encoding grayscale-safe with hatching in addition to color (Task 9).
- Moved the full 18-row per-cohort table to a new Supplementary Table S11 (adding the documented grid-size and checkerboard-paradigm columns, and splitting the combined slope-CI cell into separate low/high columns), shortening the main-text Table 2 to composition and observed-performance columns only, with calibration intercept/slope redirected to Figure 1 and Table S11 (Task 10).

### Citations and provenance

- Cited the exact commit hash (`bb07fb994b0d776101afaef9f0f3dd9c12596124`) in the Data and Code Availability statement, and documented a DOI-backed Zenodo/OSF archival deposit as a remaining human action in `submission/AUTHOR_ACTIONS.md` (Task 11).
- Added citations to Colwell 2014 and Won 2019 (further within-study/within-session performance-prediction work) alongside the existing Mainsah citation, an explicit priority statement that, to our knowledge, no published study has evaluated whether a fitted calibration-to-accuracy mapping transports across cohorts, and a distinguishing sentence for Song 2024 (a related but different cross-archive question, classification transfer rather than calibration-to-accuracy transportability) (Task 13).

### Minor textual fixes (Task 12)

Tightened several sentences' phrasing, replaced every "I-squared" with the raw Unicode I² glyph (verified surviving in the rendered PDF text layer, a rasterized page image, and the DOCX XML) across both the manuscript and supplement, and fixed inconsistent no-space cohort-label spacing ("StudyX" to "Study X") throughout both documents.

### Verification (Task 14, this entry)

- Rebuilt all three documents together with `scripts/15_build_manuscript.py` (no `--only` flag), so the manuscript, cover letter, and supplement were rendered in one pass rather than three separate per-document runs.
- Confirmed the main-text body word count (Introduction through Conclusion, headers and the Acknowledgements/Data-and-Code-Availability/References matter excluded) at 10,147 words, comfortably under JNE's 12,000-word ceiling.
- Reconfirmed the abstract at 289/300 words, unchanged by this round (Tasks 12 and 13, the only tasks near the abstract's immediate vicinity, touched Results/Discussion phrasing and the Introduction respectively, not the Abstract section itself).
- Ran the full test suite: 182 passed, 1 deselected, 0 failed.
- Ran the de-AI-writing scan on the manuscript, supplement, and cover letter: zero em dashes in all three. The manuscript and supplement's remaining Tier 1/Tier 2 hits ("robust"/"robustness", "dynamic") are all legitimate statistical or domain terminology (cluster-robust standard errors, robustness checks, dynamic stopping, a term also used in a cited paper's own title), not AI-writing tells; the cover letter scanned clean with zero tells of any kind.
