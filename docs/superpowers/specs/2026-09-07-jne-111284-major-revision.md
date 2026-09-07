# JNE-111284 Major Revision: Spec

**Manuscript:** JNE-111284, *Journal of Neural Engineering* (IOP), Paper.
**Current title:** "Calibration-derived decoder discriminability is associated with online P300-speller accuracy, but the fitted mapping does not transport across cohorts."
**Decision:** Major revision (`DEC:MajRev:S`), letter from Lucy Joy on behalf of EiC Warren M. Grill.
**Deadline:** 19-Oct-2026 (extension available on request).
**Baseline commit:** `8a56d0c` on local `main`.

---

## 1. What the reviewers asked for

### Referee 1

| # | Ask | Kind |
| --- | --- | --- |
| A1 | Archive homogenization vs. true external validation. BigP3BCI imposes a shared montage and sampling rate. Discuss **prominently in the main text** (not only Methods) whether this curation under- or overstates the heterogeneity a reader would meet across genuinely independent clinical deployments (different amplifiers, sites, electrode caps). The manuscript acknowledges "not external validation in the strict sense" but does not reason about the **direction** of the bias. | Text |
| A2 | Predictor vs. deployed decoder. The score comes from a reconstructed classifier, not the decoder actually used online. Surface this near the **Abstract or Discussion framing**, not only deep in Methods, so readers do not over-trust the clinical implications. | Text |
| A3 | Practical path to local recalibration. The Conclusion recommends "local recalibration" with no operational sense of what it requires (how many subjects or calibration trials?). **A brief simulation or dedicated discussion of operational feasibility.** | **New analysis** |
| A4 | Length. ~30 pages could be streamlined. Discussion recapitulates Results with similar statistical framing. Move the clustered-sandwich-vs-bootstrap estimator-agreement comparison to the supplement, where its tables already live. | Text |
| A5 | ALS clinical characterization. Only three studies carry ALSFRS-R; no disease stage or duration. Given the ALS framing, add an explicit Limitations sentence beyond the current baseline description. | Text |
| B1 | Researcher degrees of freedom. Multiplicity of exploratory configurations (2 paradigms, 7 comparator predictors, ALSFRS-R add-on) is transparent and mostly Holm-corrected, but add a Discussion acknowledgment of **cumulative researcher-degrees-of-freedom risk beyond what formal corrections capture**, given no preregistration. | Text |

### Referee 2

| # | Ask | Kind |
| --- | --- | --- |
| C1 | Literature context. Introduction leans on citations a decade or more old ([15], [37], [38]). Add recent work on calibration-based accuracy prediction. Also: did earlier researchers explicitly flag **why** they did not cross cohorts (suspicion of non-generalization, or convenience)? Add historical context. | Text + new refs |
| C2 | Model scope. L2-regularized logistic and shrinkage LDA are both linear. Linear models are fragile under domain shift. Is relying solely on them enough to claim the mapping cannot transfer, or is it partly a limitation of **linear boundaries**? | **New analysis** |
| C3 | Data alignment. Alignment techniques are the go-to for ironing out inter-subject and inter-cohort differences. **Does the mapping still fail with alignment in the mix?** Discuss or test whether alignment bridges the cross-cohort gap. | **New analysis** |
| C4 | Quantify recalibration. How much local recalibration is actually needed? Quantify the threshold (data volume or subjects) where it flips from non-transferable to workable. | **New analysis** (same as A3) |
| C5 | Title. Could punch harder; spotlight the cross-cohort-limits takeaway immediately. | Text |

### Editor in Chief

> "Additional analyses to consider data re-alignment would substantially increase the impact of the contribution."
> "Please include a detailed Response to Reviewers document."
> "We will ask the Reviewers to again critically review the revised manuscript."

**C3 is the single highest-leverage item.** The EiC named it explicitly and it is the only comment elevated from a referee to the editorial verdict.

---

## 2. Decisions taken (author-confirmed 2026-09-07)

**D1. Alignment scope = Euclidean Alignment + score-space alignment.**
Two families, four arms:

- **Feature-space alignment** on the calibration epochs before the discriminability classifier is fitted:
  - `calibration_auc_ea_session`: Euclidean Alignment (He & Wu 2020) with the reference covariance computed from that session's own calibration epochs. The canonical, unsupervised, site-deployable form.
  - `calibration_auc_ea_cohort`: reference covariance averaged over every session in the cohort. Targets *cohort*-level distribution shift directly, which is the shift the paper's claim is about.
- **Score-space alignment** on the predictor, using only the target cohort's **unlabeled** calibration scores (no online-accuracy labels required, so it is deployable):
  - `calibration_auc_cohort_z`: within-cohort standardisation of the predictor.
  - `calibration_auc_cohort_rank`: within-cohort rank mapped to a normal quantile.

Every arm is put through the identical leave-one-study-out procedure and the identical random-effects heterogeneity summary, so the reported quantity is the same tau the paper's claim rests on.

Riemannian Procrustes Analysis was considered and **excluded**: it would add `pyriemann` as a new dependency to a codebase whose full result set has been rebuilt eight times, and its unsupervised form (recentring only) is what Euclidean Alignment already delivers.

**D2. Title decided after the analyses land.** Three candidates drafted in the last content task; the author picks. Committing now risks a title that contradicts the alignment result.

**D3. Length: trim to offset.** Net body word count must end at or below the current **6,601** words even after the new Methods and Results text. Achieved by doing exactly what A4 asked (estimator-agreement to supplement) plus cutting Discussion passages that restate Results. No aggressive structural cut to 5,000 words; the risk of breaking cross-references in a manuscript through this many revision rounds is not worth it, and JNE's cap is 12,000.

---

## 3. Deliverables (JNE revised-submission checklist, `reproting checklist.pdf`)

Required files, in the packet directory
`/Volumes/Extreme SSD/Mimic-IV/_submission_ready/study_bigp3_als_calibration/REVISION_R1_JNE-111284/`,
following the house numbered-file convention already used by
`_submission_ready/study_command_following/REVISION_R1_NECA-D-26-00849/`:

| File | JNE designation | Checklist requirements |
| --- | --- | --- |
| `1_Cover_Letter.docx` | (submission form) | Single-spaced correspondence, one page. |
| `2_Response_to_Reviewers.docx` | **Author Response** (required) | Point-by-point response to **every** reviewer comment **and the Editor report**. Uploaded on "Step 1 - View and Respond to Decision Letter". |
| `3_Manuscript_CLEAN.docx` | **Source File** (required) | Word format. Clean: no tracked changes, no coloured or highlighted text, no comments. Must contain the full author list with affiliations, the corresponding author clearly marked with email, funding/acknowledgements, and the ethical statement. Tables, figure captions and equations editable. No colour or grey-scale in tables. |
| `4_Manuscript_HIGHLIGHTED.pdf` | **Highlighted PDF** (required), designation "Complete Document for Review (PDF Only)" | PDF. Changes highlighted. Figures and tables included. |
| `PDF_PREVIEW_manuscript.pdf` -> `3_Manuscript_CLEAN.pdf` | **Clean PDF version** (required), designation "Source Files" | Unmarked PDF built from the clean source file; becomes the Accepted Manuscript. |
| `5_Supplement.docx` | **Supplementary material**, designation "Supplementary Data Files" | Clean. Title and description included. |
| `6_TRIPOD_Checklist.docx` | Supplementary Data Files | Updated for the new analyses. |
| `Figures/` | Additional Source Files, designation "Source Files" | High-resolution images, uploaded on "Step 3 - File Upload". |

Peer review at JNE for this manuscript was **not** double-anonymous (the submitted manuscript carries the full author block), so the anonymisation checkboxes do not apply. Confirm against the Author Centre before upload.

Every PDF and figure must additionally pass `_pub_assets/make_portal_pdf.sh` before upload: IOP's portal rejects the xelatex output over CID/Identity-H fonts.

---

## 4. Constraints inherited from the codebase

- `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run` is **mandatory**, not conventional. A project-local `.venv` on this exFAT volume accumulates AppleDouble `._*.mplstyle` sidecars that break `import matplotlib.pyplot`.
- Hold `caffeinate -ims` for any run over an hour. The two extraction passes are ~45 min each.
- Cluster-robust is the primary standard-error method. `cohort_calibration.csv` carries 54 rows in three `se_method` blocks; filter to `cluster`.
- **Never write a sentence that needs I-squared above 75.** The slope's I-squared clears 75 by 4 points and a 20% variance understatement puts it at 74.9. The intercept (tau 0.873, I-squared 86.1) leads the transportability claim.
- Missing is not zero. `(s < thr).astype(float)` turns NaN into a negative.
- `pytest tests/test_regression_baseline.py` alone collects zero tests; the slow guard needs `-m slow`.
- House writing rules: no em dashes, no AI tells, AMA-numbered references, statistics formatted per the existing manuscript.
