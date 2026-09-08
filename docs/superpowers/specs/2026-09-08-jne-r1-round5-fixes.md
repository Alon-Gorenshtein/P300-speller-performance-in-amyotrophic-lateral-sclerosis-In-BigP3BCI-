# JNE-111284 R1 packet — round-5 consistency fixes

## Origin

A fifth external adversarial review, given the packet including the cover letter for the
first time, returned 6 points (2 "must fix", 1 "strongly fix", plus 3 smaller notes folded
into the same items). Every point was independently re-verified against the live files and
the underlying frozen data before being accepted into this spec.

## Confirmed findings

### K1. Two response-table MAE cells disagree with the frozen data (and the Supplement)

`response_to_reviewers_jne_r1.md`'s composition-balanced ladder table states, for the
intercept-only refit: n=2, recalibrated MAE 0.098; n=4, transported MAE 0.091. Verified
against `output/expanded/recalibration_summary_balanced.csv` directly (not just against the
Supplement, in case both were wrong the same way): at n=2, `recalibrated_mae` = 0.097479 →
rounds to 0.097, not 0.098; at n=4, `transported_mae` = 0.090471 → rounds to 0.090, not
0.091. `supplementary/supplement_expanded.md` Table S17 already has the correct values
(0.097 and 0.090 respectively) — the error is confined to two transcribed cells in the
response's own table. The already-correct "Improvement" column values in both rows are
internally consistent with the CORRECT numbers, not the erroneous ones (independently
recomputed: at n=2, 0.093 − 0.097 rounds to the table's own "-0.004"; the erroneous 0.098
would not). Fix: correct both cells in the response table only.

### K2. "The failure tracks participants rather than trials" still slightly overclaims what an unreplicated design establishes

The manuscript's recalibration mechanism paragraph (fixed in a prior round to remove a
false "constant within a participant" claim) now correctly says additional character
selections within an already-drawn session "do not relieve" the instability. That is true
for design-matrix rank (an additional selection does not add a new distinct predictor
value), but the paragraph does not distinguish this from a separate, also-true point: more
selections at an existing predictor value could still improve the *precision* of the
observed accuracy estimated there, which the current wording does not concede. Separately,
because this analysis varies participant count without independently varying
character-selection count, the paragraph's implicit claim that instability "tracks
participant count rather than selection count" is not something the design can isolate
causally — both facts happen to co-vary in this resampling scheme. The response's parallel,
independently-worded paragraph has the same two gaps. Fix: in both files, concede the
precision point explicitly and add one sentence noting the design does not independently
vary the two counts, without weakening the paragraph's correct core claim (the code and
underlying data already confirm participant count is what determines the number of distinct
predictor values available — that mechanism claim is unchanged).

### K3. "There is no crossing point" is literally imprecise

Verified directly against `output/expanded/recalibration_summary_balanced.csv`: the
cohort-mean point estimate (not the confidence interval) crosses from negative to positive
somewhere in the tested range for both refits (intercept-only: -0.0118 at n=1 to +0.0047 at
n=16, crossing between n=4 and n=6; intercept-and-slope: -0.0730 at n=2 to +0.0026 at n=16,
crossing between n=8 and n=12). So a literal point-estimate crossing exists; what does not
exist is a *statistically supported* one (no confidence interval at any tested size excludes
zero in the direction favouring recalibration), which is the claim the rest of the paragraph
and the paper's whole framing actually rely on. Fix: change the opening sentence only, to
state what is actually true.

### K4. Cohort-level Euclidean Alignment's mechanistic description over-attributes to hardware

Four instances (`manuscript_expanded.md:87` Methods, `manuscript_expanded.md:326` and its
verbatim block quote at `response:115` Discussion, `response:63` and `response:111`
independent paraphrases) say cohort-level EA "removes what a cohort's recording chain
shares." A cohort's pooled covariance reference reflects more than recording-chain
properties — it can also carry biological, paradigm, and preprocessing structure shared
within a cohort. Round 4's own review already flagged an outlier instance carrying
"precisely" and that was removed; this finding is about the underlying claim itself, raised
independently again here. Fix: reword all four instances to describe what the method
targets (cohort-wide covariance structure, which could include recording-chain effects)
rather than asserting it removes a specific named physical cause.

### K5. Figure 6's caption describes two method-specific MDE envelopes as one shared "the dashed envelope"

Verified against `src/bigp3_als/render_expanded.py`'s recalibration-curve renderer: the MDE
envelope is drawn per-method inside a loop over both refits (`ax.plot(x, mde, ...)` and
`ax.plot(x, -mde, ...)`, once per method, in that method's own colour) — there are two
distinct, differently-coloured dashed envelopes, not one shared curve. The caption's
singular "the dashed envelope... is the minimum detectable effect at 80% power" does not
reflect this. Fix: reword to describe two method-specific envelopes. The response does not
quote this caption verbatim, so only the two manuscript copies need the fix.

### K6. Cover letter: an "interventions...repaired the reported heterogeneity" claim is imprecise for local recalibration

Local recalibration's outcome measure is local estimation error, not between-cohort
heterogeneity in the sense the alignment and nonlinear arms were evaluated against; lumping
all three under one "restored transportability or repaired the reported heterogeneity"
clause blurs a distinction the manuscript itself is careful about elsewhere. Fix: restate
the sentence to attribute the correct finding to each class of intervention.

## Point raised but not actioned as a text fix: the cover letter's signature line

The cover letter's closing reads "Sincerely, [Authors] on behalf of the authors" — the
reviewer calls this a placeholder error and asks for it to be filled with the corresponding
author's typed name. This was deliberate, not an oversight: per this project's standing rule
([[no-signing-on-users-behalf]]), the assistant does not fill a signature or attestation
field with the user's name even when asked directly. The wording is left as the generic
placeholder the response-to-reviewers house template already uses; the corresponding author
fills in their own name before submission. Flagged to the user directly rather than changed
here.

## Global constraints

- No change to any frozen numeric result, CSV, JSON, or test file. This plan corrects two
  transcribed table cells to match already-frozen, unchanged output; it does not regenerate
  or alter any pipeline output.
- Every text substitution uses the established scripted-substitution-with-uniqueness-assertion
  pattern (`text.count(old) == 1` before replacing). Never hand-edit with `sed`.
- `manuscript/manuscript_expanded.md` and `manuscript/manuscript_highlighted.md` must remain
  identical once every `[...]{.mark}` span in the highlighted copy is stripped, checked after
  every edit that touches either file. All three K2/K4 manuscript instances fall inside
  pre-existing single-paragraph `{.mark}` spans (verified before this spec was written). K5's
  Figure 6 caption is not inside a mark span in either copy (verified — it was never marked
  even when the figure was originally added) and stays that way; this is consistent with the
  document's existing practice for figure/table captions.
- Zero em dashes introduced.
- The full submission packet (`2_Response_to_Reviewers.docx/.pdf/.portal.pdf`,
  `3_Manuscript_CLEAN.docx/.pdf/.portal.pdf`, `4_Manuscript_HIGHLIGHTED.docx/.pdf/.portal.pdf`,
  `1_Cover_Letter.docx/.pdf/.portal.pdf`) must be rebuilt from corrected sources and
  re-verified at the end. The supplement is unchanged by this plan and does not need
  rebuilding.
