# JNE-111284 R1 packet — round-4 consistency fixes

## Origin

A fourth external adversarial review (same setup as rounds 2 and 3: a different AI
assistant, given the rebuilt packet) returned 8 substantive points plus several small
wording cleanups and two "conditional" items it could not verify itself. Every point was
independently re-verified against the live files, the code, and the underlying data
(`output/expanded/external_validation_predictions.csv`) before being accepted into this
spec — exactly as rounds 2 and 3 required. Unlike prior rounds, one finding here required
reading and testing the actual analysis code and data, not just prose — the reviewer
flagged a real defect in how the paper *describes* its own recalibration mechanism.

## Confirmed findings

### H1. "Constant within a participant" contradicts the Methods' own session-level definition, AND is factually wrong per the actual data

`manuscript_expanded.md:69` and `:152` define the calibration score as "a property of a
session, constant across its recorded conditions" and note the 739 records carry 410
distinct predictor values (i.e., more sessions than the count of records-per-session would
suggest, because participants can have multiple sessions). But `manuscript_expanded.md:265`
and the response's own paraphrase both assert "The calibration score is constant within a
**participant**," used to justify a "two participants = two points" mechanism for
recalibration instability.

Verified directly against the code and data, not just the prose: `src/bigp3_als/recalibration.py`'s
`recalibration_draws` selects `is_local = block[PARTICIPANT_COLUMN].isin(chosen)` and passes
ALL of that participant's rows to `_fit_local` — it does not collapse a participant to one
point. Querying `output/expanded/external_validation_predictions.csv` (filtered to
`model == "calibration_auc"`, the same file `18_run_recalibration.py` reads) directly:
271 distinct `study_participant_id` values (matching the manuscript's headline participant
count), of which 89 have 2 to 6 **distinct** `predicted_probability` values — i.e., 89 of
271 participants have multiple sessions with different scores. The distinct-probability
counts per participant (182×1 + 54×2 + 28×3 + 4×6 + 3×4) sum to exactly 410, matching the
manuscript's own "410 distinct predictor values" figure. So "constant within a participant"
is false for about a third of participants, and "two participants → exactly two points" is
not generally true — a drawn participant with multiple sessions contributes multiple
points.

This does not invalidate the recalibration analysis or its numbers (the code operates
correctly on the real session-level data; the 24.1%-negative-slope figure and every MDE
number are unaffected). It is a wrong description of the mechanism, in the manuscript's own
Results, the highlighted copy, and the response's independent paraphrase (not a verbatim
quote of the manuscript, so not caught by any exact-quote resync). Fix: rewrite the
mechanism explanation in all three files to be accurate — the score is session-level, most
participants (182/271, 67%) contribute exactly one session, so a small local sample
typically but not always supplies as few distinct points as participants drawn; additional
character selections within an already-drawn session add weight at an existing point
rather than a new one, which is the actual reason selection count does not relieve the
instability (this part of the original claim is correct and is preserved).

### H2. "Between-cohort heterogeneity did not fall" reads as self-contradicting the very next sentence

`manuscript_expanded.md:249` (block-quoted verbatim in `response:91`): "Between-cohort
heterogeneity did not fall: slope tau was 0.419 and 0.461 against 0.432..." immediately
followed by "Session-level alignment lowered slope tau under all four standard-error
specifications and intercept tau under three...". This exact passage was examined twice
before in this packet's history — the original round-3 spec's "BLOCKER 2" downgrade and
round 3's own final review (Finding 6) both concluded it is not a logical contradiction,
since the surrounding text and Figure 5's caption already state the nuance. A fourth
independent reviewer has now flagged the identical sentence as a "MUST FIX." Two
independent reviewers stumbling on the same specific sentence, even when each occurrence
was individually defensible, is itself a signal worth acting on, and the fix is a single
clause with zero risk to the paper's substance. Fix: replace only the opening clause so the
favourable slope-tau movement is named before the reader reaches the "lowered" sentence,
removing the apparent contradiction without touching the correct, more nuanced
specification-robustness sentence that follows (that sentence is left untouched — it
correctly qualifies session-level alignment's effect across the four standard-error
conventions, a claim more precise than the single "0.419 vs 0.432" headline number and not
safe to casually rephrase).

### H3. Response's "unlabeled calibration recordings" contradicts the manuscript's own already-fixed wording

`response:65` still reads "requires only the target cohort's unlabeled calibration
recordings and never its online accuracy," while `manuscript_expanded.md:87` (fixed in
round 3, G11) already says the score-space arms "require the target cohort's calibration
recordings, using only their usual target/non-target labels, but never its online
accuracy." Round 3's own Task 5 reviewer flagged this exact spot as an FYI (not a verbatim
quote of G11's target sentence, so out of scope for that task's literal trigger) and the
controller ruled no action, since the ambiguity is locally disambiguated in both places by
"never its online accuracy." A second independent reviewer has now flagged the same spot
again, at "STRONGLY FIX" priority. Fix: bring the response into line with the manuscript's
wording, same as G11 already did for the manuscript.

### H4. Response overclaims where the transportability failure "does not live"

`response:81`: "The consequence is that the transportability failure does not live in the
signal's scale or channel geometry, which is the only thing Euclidean Alignment can
remove." This asserts an exclusionary claim about the cause of a null result from two
specific EA variants, echoing the same category of overreach round 2 already found and
fixed once for a related archive-homogenisation sentence (Ruling T8-1). Fix: reframe as
what the comparison rules out (a simple scale/geometry explanation) rather than a claim
about where the failure categorically does not live.

### H5. Response's "removes precisely what a cohort's recording chain shares" is an outlier

`response:111` uniquely adds "precisely" to a phrase that appears three other times in this
same document and the manuscript ("removes what a cohort's recording chain shares," no
"precisely," at `response:63`, `response:115`, `manuscript_expanded.md:326`) — the same
"one instance restated more strongly" pattern rounds 2 and 3 each found and fixed multiple
times. Fix: drop "precisely" to match the other three instances.

### H6. Three instances conflate calibration-block discriminability with downstream character-level AUC

`manuscript_expanded.md:249` (block-quoted in `response:91`) and two further, independently
worded instances in the response's own prose (`response:85`, `response:260`) each say the
aligned arms have "a marginally better score" or "discriminated marginally better," citing
**character-level AUC** (0.756/0.753 vs 0.748) in support — but "the score" and
"discriminated" are this paper's own defined terms for **calibration-block
discriminability** (the classifier's own cross-validated AUC), which the response itself
reports separately, correctly, at `response:81`, as 0.801/0.802 against 0.805 — essentially
unchanged, not "better." Character-level AUC is a different, downstream quantity (how well
the *transported prediction* ranks characters), not the calibration score's own quality.
Verified the 0.801/0.802/0.805 figures are already tabulated and citable: `supplementary/supplement_expanded.md`
Table S15's caption states the exact main-text-quoted means (0.8046 primary, 0.8005
session-alignment, 0.8021 cohort-alignment), matching 0.805/0.801/0.802 to three decimal
places. Fix: in all three locations, relabel the improvement as downstream character-level
AUC, and state calibration-block discriminability was essentially unchanged, citing the
already-tabulated numbers.

### H7. Nonlinear-decoder conclusion reads as broader than what two tested alternatives establish

`manuscript_expanded.md:259` (block-quoted verbatim in `response:250`): "...so the failure
of the mapping to transport is not attributable to the linearity of the decoder." Round 3's
final review already checked a related clause in the same sentence ("the narrower statement
... here") and found it adequately scoped; this reviewer flags the trailing conclusion
specifically, which does not carry its own "here"/"tested" qualifier as directly. A cheap,
zero-risk rewording removes the ambiguity outright rather than relying on an implicit scope
carried over from an earlier clause in the same sentence. Fix: replace with a conclusion
explicitly scoped to the two tested alternatives.

### H8. Response's opening summary overstates which refit is "significantly worse"

`response:17`: "Local recalibration does not reliably improve on simply transporting the
fitted mapping at any local sample size we could evaluate, and at the smallest sample sizes
it is significantly worse." The paper's own later, more careful statement
(`manuscript_expanded.md:264`) is that only the **two-parameter** refit is significantly
worse at small sizes; the intercept-only refit was never significantly worse. "It" in the
opening summary is ambiguous and could be read as both refits. Fix: name the two-parameter
refit explicitly.

### H9. Supplement S12 does not list the RBF/GBM classifiers' own hyperparameters

S12 gives the Nystroem component count (300) and the GBM PCA numbers (added in round 3),
but not gamma, the RBF arm's logistic head settings, or the GBM ensemble's own
hyperparameters. Verified directly against `src/bigp3_als/features.py:130-165` and the
installed scikit-learn 1.9.0's actual defaults (checked by introspecting
`HistGradientBoostingClassifier.__init__` and `Nystroem.__init__` directly, not from
memory): `gamma=None` matches scikit-learn's own default; `n_components=300` (Nystroem) and
`max_leaf_nodes=15`, `l2_regularization=1.0`, `early_stopping=False` (all three
HistGradientBoostingClassifier settings) are deliberately chosen values narrower than or
different from scikit-learn's defaults (100 for `Nystroem.n_components`, 31 leaves, 0.0 L2,
`'auto'` early stopping); `max_iter=100` and `learning_rate=0.1` happen to already match
scikit-learn's defaults. Fix: add one sentence per arm to S12 disclosing the exact values
and which ones coincide with library defaults — do not claim all of them are defaults,
since three explicitly are not.

## Additional cheap, low-risk item bundled in

### H10. Response's closing-summary phrasing ("bounded that null...")

`response:291`: "bounded that null with minimum detectable effects at 80% power" is an odd
verb choice left over from before the MDE framing was corrected (rounds 2/3). The
underlying MDE interpretation is already correct everywhere it matters; this is a pure
phrasing cleanup with zero substantive content. Fix: reword to remove the residual
ambiguity, bundled into the response-only fix task at zero marginal cost.

## Points confirmed already correct — no action

- **TRIPOD checklist "prespecified"/ALSFRS-R claims.** The reviewer flagged these as
  "conditional, not checked this pass." Verified directly:
  `supplementary/tripod_checklist.md` item 10e already says "Model updating was added
  during revision at the reviewers' request... without updating" (correctly not calling it
  prespecified), and item 13b already says "An ALSFRS-R score, a participant-level clinical
  characteristic, is available for a subset of participants in 3 of 18 cohorts" (correctly
  identifying it as a participant-level clinical characteristic). Both were fixed in round
  2 and remain correct. No action.
- **Live GitHub repository state.** The reviewer flagged this as unverifiable from their
  side and asked the author to check manually before submission. Unchanged standing
  blocker — `git remote -v` in this repository returns nothing; there is still no remote
  configured and no credentials to push. Not a new finding; already tracked in the
  packet's `0_README.md`.
- **DOCX comments/tracked changes.** The reviewer checked the DOCX internals and found none
  in the three current files — consistent with this packet's build pipeline, which never
  introduces either.

## Points not adopted as stated

- **Title wording** ("...was not restored by tested alignment or local recalibration" vs.
  the current "...and neither alignment nor local recalibration repairs it"). This is an
  explicit human decision, already flagged as such in `0_README.md` across all three prior
  rounds. Not changed in this pass; noted to the user, as in every prior round.
- **Methods' "which requires at least two [participants]"** wording tweak
  (`manuscript_expanded.md:91`). This sentence describes the code's own enforced gating
  rule (`intercept_and_slope` is only attempted when the local draw size is ≥2), not the
  "two points" mechanism claim H1 fixes — it is accurate as written. The reviewer's
  suggested rewording is a pure style preference with no accuracy gain. Not applied.

## Global constraints

- No change to any frozen numeric result, CSV, JSON, or test file. `src/bigp3_als/features.py`
  and `src/bigp3_als/recalibration.py` are read to verify H1 and H9's exact mechanism and
  hyperparameters, but not modified.
- Every text substitution uses the established scripted-substitution-with-uniqueness-assertion
  pattern (`text.count(old) == 1` before replacing). Never hand-edit with `sed`.
- `manuscript_expanded.md` and `manuscript_highlighted.md` must remain identical once every
  `[...]{.mark}` span in the highlighted copy is stripped, checked after every edit. All of
  H1, H2, H6's manuscript instance, and H7's manuscript instance fall entirely inside
  pre-existing single-paragraph `{.mark}` spans (verified before this spec was written) —
  edits stay inside the existing span boundaries; no span is split, closed early, or
  extended across a paragraph break, image, or caption (the exact failure mode round 2's
  Task 11 found and fixed).
- Zero em dashes introduced, except inside a reviewer's own verbatim quoted comment
  (already true and must remain true).
- The full submission packet (`2_Response_to_Reviewers.docx/.pdf/.portal.pdf`,
  `3_Manuscript_CLEAN.docx/.pdf/.portal.pdf`, `4_Manuscript_HIGHLIGHTED.docx/.pdf/.portal.pdf`,
  `5_Supplement.docx/.pdf/.portal.pdf`) must be rebuilt from corrected sources and
  re-verified at the end, using the exact pipeline established in rounds 2 and 3.
- H1's fix must not change any reported number (24.1%, MDE values, tau values) — it
  corrects only the mechanism description, which the code and data confirm was inaccurate.
