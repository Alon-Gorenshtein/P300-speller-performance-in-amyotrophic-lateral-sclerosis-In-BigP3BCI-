# JNE-111284 R1 packet — round-3 consistency fixes

## Origin

A third external adversarial review (same setup as the round-2 review this repository
already has a spec/plan for: a different AI assistant, given the rebuilt packet, the live
GitHub repository, and the current JNE instructions) returned ten points. Every point was
independently re-verified against the live files, the frozen CSVs, the analysis code, and
the actual built PDF/docx output before being accepted into this spec — exactly as the
round-2 spec required, and for the same reason: three of the ten points did not survive
verification.

## Confirmed findings

### G1. GitHub repository still stale (human-only; unchanged from round 2)

No new information. Still requires a `git push` this session cannot perform. Not a plan
task.

### G2. Response's block quote of the nonlinear-Results paragraph is a paraphrase, not a quote

`manuscript/response_to_reviewers_jne_r1.md:250` block-quotes: "A nonlinear decision
boundary did not account for the result. Two nonlinear calibration decoders, a
radial-basis kernel approximation and a gradient-boosted tree ensemble on a
principal-component reduction, were computed on the identical epochs through the identical
grouped cross-validation. Neither recovered the regularised linear decoder's
discriminability: mean cross-validated AUC was 0.714 for both..." — this reads
substantively the same as, but is not byte-identical to, the manuscript's actual current
Results paragraph (`manuscript_expanded.md:259`, opening "Neither nonlinear decoder
recovered the regularised linear decoder's discriminability. Mean cross-validated
discriminability was 0.714 for the kernel approximation and 0.714 for the gradient-boosted
ensemble, against 0.805 for the linear decoder, which discriminated better than both
nonlinear arms in every one of the 18 cohorts..."). A systematic sweep of every other block
quote in the response (23 quotes checked programmatically) found this to be the only
remaining genuine drift; four other quotes a naive similarity check flagged were false
alarms (verified exact matches once compared correctly). This paragraph was apparently
never a verbatim quote — Task 4 of the round-2 plan touched only the "ceiling" clause
inside it via a targeted substitution, which matched and fixed that one sentence without
addressing that the surrounding paragraph was already a paraphrase.

### G3. "Improvements of that size or larger are excluded" overstates what an 80%-power MDE establishes

`manuscript_expanded.md:267` and the response (`:159`, `:268`) all state or imply that
effects at or above the reported minimum detectable effect (MDE) are "excluded." An
80%-power MDE is the effect size the design has an 80% probability of detecting if it is
truly present — a non-significant result at that power does not categorically exclude true
effects at or above the MDE (a false negative remains possible in the excluded 20%). The
paper's own 95% confidence intervals on the paired improvements are the correct instrument
for stating what is and is not compatible with the data, and the manuscript already reports
them (e.g. `manuscript_expanded.md:263`, "-0.012 (-0.032 to +0.008) at one local
participant to +0.005 (-0.007 to +0.016) at sixteen"). Fix: replace the exclusion framing
with power-based framing ("the design had 80% power to detect...") wherever it currently
claims exclusion.

### G4. Figure 6's caption treats the MDE envelope as an inferential/significance boundary

`manuscript_expanded.md:269`: "No point's interval clears the envelope in the direction
that favours recalibrating at any size from 1 to 16 local participants." This describes the
MDE envelope as something a confidence interval could "clear" in a significance-testing
sense, which is the same category error as G3 applied to the figure. The correct statement
is about whether the 95% CI excludes zero, with the MDE envelope described as contextual
(what the design could detect), not as a threshold the interval is tested against.

### G5. Response's "lower bound" wording is stronger than the manuscript's own already-softened claim

Three places in the response state the archive-homogenisation heterogeneity is a "lower
bound" without qualification: `:35` ("states that the reported heterogeneity is a lower
bound"), `:109` ("The reported tau is therefore a lower bound on what a site meeting a
genuinely independent cohort should expect"), `:209` ("concluding that the reported
heterogeneity is a lower bound"). The manuscript's own Discussion — already deliberately
softened during round 2 (Task 8) for exactly this reason — reads "the heterogeneity
reported here likely understates what a site encountering a genuinely independent cohort
should expect" (`manuscript_expanded.md:326`), a probabilistic claim rather than a
mathematical lower-bound claim, precisely because a true lower bound cannot be established
from an archive with no independent hardware variation to test against. The response's own
prose (not a block quote of the manuscript, so not caught by any exact-quote resync) still
asserts the stronger, already-rejected framing in three places. This is the same "same
overclaim restated in the response's own voice" pattern round 2 found and fixed twice
(Rulings T4-1, T8-1) — a third instance, missed until now.

### G6. GBM-correction wording misattributes a "retained-variance target" to arms that do not have one

`manuscript_expanded.md:328` and the resynced response quote both say the gradient-boosted
arm's initial run "lacked the class rebalancing and the retained-variance target its
comparators used." Verified against the code (`src/bigp3_als/features.py:106-121`): only
the GBM arm's PCA step has a retained-variance-derived component count
(`gbm_pca_components = min(150, smallest_training_fold - 1)`, chosen because 150 components
measured 90-97% cumulative explained variance on probe sessions, against 56-80% for an
earlier 40-component choice — see the code comment and
`docs/pipeline_rerun_2026-09-07_alignment.md`, "GBM arm fairness correction"). Neither the
primary linear decoder (no PCA at all) nor the RBF arm (`Nystroem(kernel="rbf", gamma=None,
n_components=300)`, a fixed component count, not a variance target) has a "retained-variance
target." The supplement's own wording (`supplement_expanded.md:421`) is accurate: "retained
fewer principal components than the measured-variance criterion above specifies." The
manuscript and response should be brought into line with the supplement's correct framing
rather than implying the comparators share a criterion they do not have.

### G7. Supplement S12 lacks the exact GBM PCA numbers needed for reproducibility

`supplement_expanded.md`'s S12 currently says only "The number of retained components was
set from measured retained variance rather than matched to the kernel approximation's
component count, which is a different quantity" — vague. The exact numbers exist in the
code and its comment (`src/bigp3_als/features.py:106-121`): 150 components (floored at
`smallest_training_fold - 1` when a fold is smaller), chosen because it retains 90-97%
cumulative explained variance on probe sessions spanning the archive's size range, against
56-80% for an earlier, rejected 40-component choice. This is exactly the kind of
reproducibility detail Reviewer 2's nonlinear-boundary request exists to be answered with,
and it is missing.

### G8. A second, unfixed instance of the stale word-count claim survives in the response

Round 2's Task 5 fixed one instance of "approximately 6,600 to 8,600 words" to "...8,900
words" (`response_to_reviewers_jne_r1.md:40`, now correct). A second instance at
`response_to_reviewers_jne_r1.md:181` still reads "approximately 8,600 words against 6,600"
— missed because it is phrased differently (words reordered) and so did not match the exact
string the round-2 fix targeted. Verified: `Path.count()` on the exact current string is 1.

### G9. Both markdown tables embedded directly in the response render with mid-word line breaks in the built PDF

Verified by rendering `2_Response_to_Reviewers.pdf` (page 8) and reading the extracted text
directly: the alignment-comparison table's header row renders as "Poole / d MAE", "Slop / e
tau", "Interce / pt tau" (three-way word breaks across cell-wrap lines), and the
recalibration-ladder table's header row (page containing "Median local selections") renders
"Local / participa / nts", "Transpo / rted MAE", "Recalibr / ated MAE". This reproduces the
exact defect class the round-2 plan fixed for the supplement's wide tables (splitting tables
and adding `colwidths.lua`/`fix_docx_tables.py`), but these two response-only tables were
never specifically inspected after `colwidths.lua` was added to the build pipeline — the
generic column-width heuristic does not reliably prevent every long header from breaking
when a table has 6-7 columns including several long header phrases. Fix: shorten the header
text (the numeric content and every other cell are unaffected) rather than restructure the
tables, since these are illustrative summary tables in a response letter, not numbered
supplement tables that other documents cross-reference by exact column name.

## Points downgraded after verification (do not implement as stated)

- **"BLOCKER 2": Abstract/Results "heterogeneity did not fall" contradiction.** Not a
  contradiction. `manuscript_expanded.md:249` (the paragraph the Abstract summarizes)
  already states the nuance explicitly and in detail: "Session-level alignment lowered
  slope tau under all four standard-error specifications and intercept tau under three, the
  exception being the participant-clustered specification..." and the same paragraph
  reports the exact numbers (0.419 vs 0.432 for slope tau, 0.922 vs 0.873 for intercept
  tau). Figure 5's own caption (fixed in round 2's final review) already states the
  session-level exception explicitly. The Abstract's compressed summary ("did not reduce
  this heterogeneity") is a defensible characterization given intercept tau rose while
  slope tau fell only marginally under one arm — net heterogeneity, on balance, did not
  meaningfully improve. A small, low-risk precision edit (adding "meaningfully" or
  equivalent hedging to the Abstract clause) is included as G10 below as a cheap
  strengthening move, but the reviewer's proposed full rewrite is not applied verbatim,
  since it would duplicate detail the Results section already carries and lengthen the
  Abstract for no accuracy gain.
- **"TRIPOD checklist not included in this upload."** False. `6_TRIPOD_Checklist.docx`,
  `.pdf`, and `.portal.pdf` all exist in the packet folder, dated from this session's own
  Task 11 rebuild, and were reviewed and approved (spec-compliant) in round 2's Task 7. No
  action.
- **"'Not attributable to the linearity of the decoder' is too broad."** The sentence
  already reads "what the comparison supports is the **narrower statement** that a
  nonlinear boundary improves neither discrimination nor transport **here**" — already
  explicitly scoped to this study, not a universal claim about all possible nonlinear
  models. No action.
- **"'Unlabeled calibration recordings' is misleading."** A minor, optional clarity
  improvement rather than a defect — the same sentence immediately clarifies "but never its
  online accuracy," disambiguating which label is meant. Included as G11 below as a cheap
  clarity pass, not because the current wording is wrong.
- **"521 vs 468 session denominator inconsistency."** Already fully reconciled in
  `supplement_expanded.md` Table S15's own caption, which explicitly states both numbers
  and why they differ (two cohorts have calibration recordings but no analysable outcome).
  No action beyond what G11 already covers as an optional main-text clarification.
- **"'Published' should be 'previously submitted'."** Cosmetic, correctly labeled low
  priority by the reviewer, high occurrence count, no risk of contradiction or
  misunderstanding in context (each use is adjacent to "the values" or "the file," making
  the referent unambiguous). Not fixed in this pass; noted to the user as optional.

## Additional cheap, low-risk items bundled from the downgraded points

### G10. Abstract precision (bundled from the downgraded "BLOCKER 2")

Add a single hedging word to the Abstract's alignment/nonlinear sentence so a literal
reading of "did not reduce" cannot be set against the one arm whose slope tau (not overall
heterogeneity) moved slightly in the helpful direction while its intercept tau moved
against it.

### G11. "Unlabeled calibration recordings" clarity (bundled from the downgraded item)

One clarifying parenthetical, cheap and unambiguous, removing a plausible (if already
locally disambiguated) misreading.

## Global constraints

- No change to any frozen numeric result, CSV, JSON, or test file. `src/bigp3_als/features.py`
  is read for G6/G7's exact numbers but not modified — the numbers already exist in its code
  comment; this pass only transcribes them into prose.
- Every text substitution across `manuscript_expanded.md`, `manuscript_highlighted.md`,
  `response_to_reviewers_jne_r1.md`, and `supplementary/supplement_expanded.md` uses the
  established scripted-substitution-with-uniqueness-assertion pattern from both prior
  rounds. Never hand-edit with `sed`.
- `manuscript_expanded.md` and `manuscript_highlighted.md` must remain identical once every
  `[...]{.mark}` span in the highlighted copy is stripped, checked after every edit that
  touches either file.
- G2's fix and G5's three fixes must each be checked against the CURRENT manuscript text at
  dispatch time, not against the text quoted in this spec, in case an earlier task in this
  same plan already changed the target sentence.
- Zero em dashes introduced, except inside a reviewer's own verbatim quoted comment
  (already true and must remain true).
- After all text tasks land, the two response tables (G9) must be verified by an actual
  docx build and PDF text extraction — not just the markdown source — since that is the
  only way this exact defect class is visible, as this round's own discovery of G9
  demonstrates.
- The full submission packet (`2_Response_to_Reviewers.docx/.pdf/.portal.pdf`,
  `3_Manuscript_CLEAN.docx/.pdf/.portal.pdf`, `4_Manuscript_HIGHLIGHTED.docx/.pdf/.portal.pdf`,
  `5_Supplement.docx/.pdf/.portal.pdf`) must be rebuilt from corrected sources and
  re-verified at the end, using the exact pipeline established in round 2 (pandoc +
  `colwidths.lua` + `fix_docx_tables.py` + `make_portal_pdf.sh` + `mcp__word-docx__convert_to_pdf`).
- G1 (GitHub push) is out of scope for any task.
