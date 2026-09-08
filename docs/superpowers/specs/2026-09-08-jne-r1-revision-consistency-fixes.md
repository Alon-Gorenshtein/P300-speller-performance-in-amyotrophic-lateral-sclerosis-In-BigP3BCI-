# JNE-111284 R1 packet — consistency fixes (second fix pass)

## Origin

An external reviewer (a different AI assistant, prompted by the corresponding author) read
the decision letter, the response, both manuscript copies, the supplement, TRIPOD checklist,
both new figures, the current JNE author instructions, and the public GitHub repository, and
returned a 14-point critique. Every point was independently re-verified against the actual
files and code in this repository before being accepted into this spec — the external review
is untrusted input, not ground truth. Findings below are stated only where verification
confirmed them; two of the external review's fourteen points were downgraded or reframed
after verification (see "Points downgraded" at the end).

## Confirmed findings

### F1. GitHub repository is stale (human-only; cannot be fixed from this session)

`git remote -v` in this repository returns nothing — there is no configured remote, and this
session has no push credentials. Fetching the public repository directly
(`raw.githubusercontent.com/.../README.md` and the `scripts/` tree) confirms it stops at
`14_run_reliability.py`, reports "162 tests", and has no `04b`, `15`–`19` scripts and no
revision figures. The manuscript's Data Availability statement
(`manuscript/manuscript_expanded.md:358`) already names this repository as where the code
lives, and the Supplement (S13, pipeline paragraph) now names the four revision scripts
explicitly. **This is a real gap, but it is a `git push` the corresponding author must run;
no plan task attempts it.** The plan's only obligation is to make sure the local repository
is push-ready (it already is — every commit from this revision is local) and to flag it as
blocking, not to leave it as a silent risk.

### F2. Cohort-level Euclidean Alignment weighting: supplement contradicts the code

- Code (`src/bigp3_als/alignment.py:72-80`, `pooled_reference`): docstring says "epoch-count-
  weighted mean"; the caller (`scripts/04b_extract_alignment_features.py:38`) passes
  `n_epochs[mask]` as the weight array. **The implementation is epoch-count-weighted.**
- Manuscript (`manuscript_expanded.md:87`) and Response (`response_to_reviewers_jne_r1.md`,
  the same quoted passage) both say "weighted by epoch count" — **correct, matches code.**
- Supplement (`supplement_expanded.md:413`, current S12) says "participant-count-weighted
  mean of the session references" — **wrong, contradicts the code and the other two
  documents.**

Fix direction: correct the supplement to match the code and the other two documents. Do not
touch the manuscript or response text for this item.

### F3. The two new figures are built but embedded nowhere

`output/expanded/figures/figure_alignment_transport.{png,pdf}` and
`figure_recalibration_curve.{png,pdf}` exist, are copied into the submission packet's
`Figures/` directory, and are described at length in the Response — but a repository-wide
search for `figure_alignment_transport`, `figure_recalibration_curve`, `Figure 5`, and
`Figure 6` inside `manuscript_expanded.md`, `manuscript_highlighted.md`,
`supplement_expanded.md`, and the response returns **zero matches**. The manuscript's Results
subsections "Alignment Did Not Restore Transportability", "A Nonlinear Decision Boundary Did
Not Account for the Result", and "What Local Recalibration Costs" (lines 247–263) cite no
figure at all. JNE's own instructions require figures to be embedded at the point in the text
where they are discussed. This is the most serious finding in the review: real content the
paper claims to have and does not deliver to the reader.

Two subsidiary figure-content problems, both confirmed by reading
`src/bigp3_als/render_expanded.py`:

- `ROLE_STYLE["alignment"]["label"]` (line 92) is `"EEG re-alignment"`, but the `"alignment"`
  role bucket contains all four alignment arms, two of which (`cohort_z`, `cohort_rank`) are
  score-space transformations that never touch the EEG signal. The bucket label
  misrepresents two of its four members.
- `render_recalibration_curve` (lines 499–583) draws the ±MDE dashed envelope
  (`ax.plot(x, mde, ..., linestyle="--", ...)` and its negative, lines 559–560) with no
  `label=` argument, so it never reaches `ax.legend()` (line 582). A reader sees a dashed line
  with no legend entry explaining what it is.

### F4. Discussion sentence contradicts the new recalibration finding

`manuscript_expanded.md:299`: "Reporting expected accuracy in a cohort where the mapping was
not developed is not supported **without local recalibration**..." This sentence is
unchanged from the pre-revision manuscript. The revision's own new finding (Results, "What
Local Recalibration Costs", lines 257–263) is that local recalibration did **not** reliably
restore accuracy at any size from 1 to 16 participants this archive could evaluate, and was
significantly harmful at 2–3 participants. The sentence as written tells a reader the opposite
of what the paper's own new analysis shows.

### F5. Discussion's opening paragraph still repeats stats the Response claims were removed

`response_to_reviewers_jne_r1.md:179`: "The first paragraph no longer re-lists tau, its
confidence interval and the slope range..." This is false as the manuscript currently stands:
`manuscript_expanded.md:297` reads "...the calibration intercept had tau = 0.87 (95% CI 0.60
to 1.51) and an unrepresented-cohort interval of -1.97 to 1.85 log-odds; slope heterogeneity
gave the same conclusion, at tau = 0.43 (0.30 to 0.77) and a range of 0.185 to 2.185." Every
one of those numbers is already given in the Results (Transportability subsection,
lines 202–204). Fix by making the claim true: trim the manuscript paragraph (this also serves
Reviewer 1's length request), then re-sync the response's quoted block to the trimmed text
using the same substitution-with-uniqueness-assertion method used throughout this revision.

### F6. "Genuine ceiling" is an unsupported overclaim; "only quantity varying" is self-contradicted two sentences later

`manuscript_expanded.md:255`: "The agreement between two structurally unrelated nonlinear
families to within 0.0001 indicates a ceiling imposed by these data rather than a property of
one modelling choice." Two models trained on the same epochs, same folds, same metric, with
limited hyperparameter search, agreeing with each other is evidence the *result is not an
artifact of one model family* — it is not evidence of a data-imposed performance ceiling
(which would require, e.g., a Bayes-error argument or an exhaustive search this paper does not
run). Separately, `manuscript_expanded.md:89` states "so that the decision boundary is the
only quantity varying," immediately before describing that the RBF arm uses a Nystroem
approximation and the GBM arm uses a PCA reduction — both are representation changes, not
purely decision-boundary changes. The sentence is contradicted by the sentences that follow
it in the same paragraph.

The response's own block quote of this passage (`response_to_reviewers_jne_r1.md:250`) must
be re-synced after the manuscript text changes.

### F7. Researcher-degrees-of-freedom paragraph and TRIPOD both contradict the disclosed GBM correction

- `manuscript_expanded.md:320`: "...the alignment and nonlinear specifications were each fixed
  before being run."
- `tripod_checklist.md:30` (item 10e): "Model updating is evaluated separately as a
  **pre-specified secondary analysis**..."
- `response_to_reviewers_jne_r1.md:300`: "**A specification was corrected after its first
  result was seen.** The gradient-boosted arm was initially run with a configuration that
  differed from the other arms... We corrected both and re-ran the extraction before any
  transportability analysis used the column... We report the change, and both the initial and
  corrected values, **in the supplementary analysis log**."

Three problems: (a) "fixed before being run" is contradicted by the GBM correction the
response itself discloses; (b) "pre-specified secondary analysis" is wrong on two counts —
local recalibration was requested by the reviewers during revision, not pre-specified, and
the phrase invites exactly the same "fixed before being run" objection; (c) **no
"supplementary analysis log" exists anywhere in the submitted files.** The response promises
an artifact that was never built. Verified by grep across `manuscript/` and `supplementary/`.

Fix: state the GBM correction honestly in the manuscript's researcher-degrees-of-freedom
paragraph (one clause), fix the TRIPOD wording to describe reality, and either (i) add the
initial/corrected GBM values as a short prose note inside supplement S12 (no new table
number, to avoid re-triggering the renumbering churn from the last pass) or (ii) change the
response's wording to point at the manuscript disclosure instead of a nonexistent log. Do
(i) and simplify the response's phrasing to match — the disclosure is a genuine strength of
the paper and deserves to actually exist where it is pointed to.

### F8. Response header carries the old title; "the main text was shortened" is false; both are self-inconsistent within the response itself

- `response_to_reviewers_jne_r1.md:3`: the document's own header block still shows
  **"Calibration-derived decoder discriminability is associated with online P300-speller
  accuracy, but the fitted mapping does not transport across cohorts"** — the pre-revision
  title. The response later proposes the new title in answer to Reviewer 2 comment 5, and the
  manuscript already carries the new title. The header contradicts the body of the same
  document.
- `response_to_reviewers_jne_r1.md:40`: "**Length.** The main text was shortened..." The body
  count is 6,601 → 8,628 words (a net increase of over 2,000 words); only the
  estimator-agreement material was actually removed (moved to Supplement), which is a much
  smaller effect than the sentence implies, and is contradicted a few paragraphs later in the
  same document where the true 6,600→8,600 figures are given honestly.

### F9. TRIPOD 13b and Supplement S14 both overclaim "no participant-level clinical characteristics"

`src/bigp3_als/edf.py:50,81-98` extracts `alsfrs_r` as a per-patient field
(`study_participant_id`-keyed, per `validation.py:284`,
`metadata_table[["study", "study_participant_id", "alsfrs_r"]].drop_duplicates()`) — this is
unambiguously a **participant-level clinical characteristic**, available for a subset of
participants in 3 of 18 cohorts (138 records, per `supplement_expanded.md:290`). Both
`tripod_checklist.md:34` ("No participant-level clinical characteristics are available in the
archive for any cohort") and `supplement_expanded.md` S14 ("no participant-level clinical
characteristics were available") are false as written. The manuscript's own Discussion
(`manuscript_expanded.md:332`, "An ALSFRS-R score is recorded for three of the eighteen
cohorts...") already states the true, more precise fact — the two overclaims elsewhere need
to be brought into line with it, not the other way around.

### F10. Archive-homogenisation claim overreaches in its final sentence

`manuscript_expanded.md:318`, last sentence: "The residual spread is therefore not of the
kind that an amplifier or montage difference would contribute." BigP3BCI imposes a *shared*
montage, sampling rate, and amplifier across every source study — there is no independent
amplifier/montage variation anywhere in the archive for Euclidean Alignment (which addresses
covariance structure) to have acted on. The EA-cohort arm's failure to reduce heterogeneity is
real evidence that *within-archive* covariance differences do not explain the residual
spread, but it cannot establish what a genuinely independent deployment's amplifier/montage
difference — a source of variation absent from this archive by construction — would or would
not contribute. This is a scope overreach beyond what the analysis in this paper can support.

### F11. Supplement has no title/description block

JNE's supplementary-file instructions require a title and a ≤30-word description on
supplementary files. `supplement_expanded.md` currently opens directly with
`# Supplementary material` followed immediately by `## S1. Data provenance` — no description.
Confirmed absent.

### F12. Abstract omits the two major-revision analyses that the title is now built on

The title (`manuscript_expanded.md:15`, drafted, pending author confirmation) is entirely
about alignment and local recalibration not repairing transport. The Abstract's Main Results
(`manuscript_expanded.md:27-29`) and Significance (`31`) sections mention neither. A reader of
the Abstract alone — which is what most readers and all indexing databases see — would not
learn the paper's two headline negative findings from the major revision. Also,
`manuscript_expanded.md:29`, "The association was positive in all 18 cohorts" states a point
estimate as if it were a certain fact; the Results body (`manuscript_expanded.md:159`) already
uses the more careful "point estimate was positive in all 18... several cohort-specific
estimates were imprecise" — the Abstract should match that precision.

### F13. Reviewer 2's request for recent calibration/performance-prediction literature is thinly answered

The Introduction's performance-prediction literature (`manuscript_expanded.md:41`) cites
Colwell 2014 [37] and Won 2019 [38] as the "recent" work, plus one 2024 citation (Song et al.,
ref 39) that is signal alignment, not performance prediction — already distinguished as such
in the same sentence. Two directly on-topic, correctly verified papers exist and are not
cited:

- Mowla MR, Gonzalez-Morales JD, Rico-Martinez J, Ulichnie DA, Thompson DE. A Comparison of
  Classification Techniques to Predict Brain-Computer Interfaces Accuracy Using
  Classifier-Based Latency Estimation. *Brain Sci*. 2020;10(10):734.
  doi:10.3390/brainsci10100734. (Verified via Crossref bibliographic search.) Directly
  relevant: compares linear and nonlinear classifiers, including a sparse-autoencoder variant,
  for predicting BCI accuracy — a useful anchor for this paper's own nonlinear-decoder result.
- Khan NN, Sweet T, Harvey CA, Warschausky S, Huggins JE, Thompson DE. P300-Based
  Brain-Computer Interface Speller Performance Estimation with Classifier-Based Latency
  Estimation. *J Vis Exp*. 2023;(199):e64959. doi:10.3791/64959. (Verified via Crossref.)
  Directly relevant: P300-speller accuracy estimation specifically.

### F14. "Local calibration set" does not make explicit that the refit is supervised

`manuscript_expanded.md:91` (Methods) uses "local calibration set" for the participants used
to refit intercept/slope. Refitting a calibration-to-accuracy mapping requires those
participants' **observed online accuracy**, not merely their calibration-block EEG — i.e. the
procedure is supervised recalibration, using outcome data a real deployment would also need to
collect. The term "calibration set" on its own could be misread as needing only the P300
calibration block (unsupervised), which is not what the procedure does. One clarifying
sentence removes the ambiguity.

## Points downgraded after verification (do not implement as stated)

- **External review point 10 (soften the title).** Not a defect — the title is already
  flagged in the packet README as a drafted suggestion pending the corresponding author's
  confirmation, not a finalized claim. This spec does not change the title; a milder-wording
  alternative is offered to the author as a discussion point, not applied as an edit.
- **External review point 6, "Discussion no longer repeats exact statistics."** The review
  treated this as one item together with the false "shortened" claim. Verification split it:
  the "shortened" claim is a documentation bug (F8); the "no longer repeats statistics" claim
  is actually about a **real content defect in the manuscript** (F5) that must be fixed by
  editing the manuscript, not merely reworded in the response.

## Global constraints

- No change to any frozen numeric result. `heterogeneity.py`, `validation.py`,
  `alignment.py`, `recalibration.py`, `render_expanded.py`'s numeric logic, and every
  `output/expanded/*.csv|json` file are out of scope except: `render_expanded.py`'s two
  label/legend strings (F3) and one added `label=` kwarg — no numeric line changes.
- Every text substitution across `manuscript_expanded.md`, `manuscript_highlighted.md`,
  `response_to_reviewers_jne_r1.md`, `supplement_expanded.md`, and `tripod_checklist.md` uses
  the established pattern from the prior fix pass: apply via a script that asserts each `old`
  string occurs exactly once in the target file before replacing it. Never hand-edit these
  files with ad hoc `sed`.
- `manuscript_expanded.md` and `manuscript_highlighted.md` must remain identical once every
  `[...]{.mark}` span in the highlighted copy is stripped. Any edit to the clean manuscript
  that touches highlighted-region text must be mirrored into the highlighted copy in the same
  task, and the parity check (strip marks, diff) must pass before the task is considered done.
- Any response block quote whose source paragraph is edited in this pass must be re-synced to
  the new manuscript/supplement text in the same task (do not leave a second pass of drift).
- Zero em dashes in any file this pass touches, except inside a reviewer's own verbatim quoted
  comment (already true and must remain true).
- After all text tasks land, the entire packet (`2_Response_to_Reviewers.docx`,
  `3_Manuscript_CLEAN.docx/.pdf`, `4_Manuscript_HIGHLIGHTED.docx/.pdf`, `5_Supplement.docx/.pdf`,
  `6_TRIPOD_Checklist.docx/.pdf`, all `*.portal.pdf`, and `0_README.md`) must be rebuilt from
  the corrected sources using the exact pandoc/lua-filter/fix_docx_tables.py/
  make_portal_pdf.sh pipeline established in the prior pass, and re-verified (word counts,
  table/figure counts, highlight-run counts, PDF page/text parity, visual inspection of the
  two new figure pages and at least one new-table page).
- F1 (GitHub push) is out of scope for any task — it requires credentials this session does
  not have. It is reported to the user as a blocking human-only item, not attempted.
