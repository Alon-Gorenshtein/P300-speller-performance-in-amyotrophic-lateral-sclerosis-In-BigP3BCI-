# JNE-111284 R1 packet — round-6 consistency fixes

## Origin

A sixth external adversarial review, given the current four-file package, confirmed every
substantive fix from rounds 1-5 held up and found no methodological blocker and no
unanswered reviewer request. It identified one submission-blocking placeholder, one
manuscript-internal tension introduced by round 5's own fix, and three smaller wording
cleanups in the response. It also raised one optional title suggestion, explicitly not a
blocker.

## Confirmed findings

### L1. Cover letter's "[Authors]" signature placeholder — NOT a text fix, flagged only

The cover letter still closes "Sincerely, [Authors] on behalf of the authors." Verified by
reading `manuscript/cover_letter_jne_r1.md`'s last two lines directly. This is deliberate,
not an oversight: per this project's standing rule ([[no-signing-on-users-behalf]]), the
assistant does not fill a signature or attestation field with the user's name even when
asked directly, as this reviewer (like the fifth) explicitly asks. Left as-is; flagged to
the user directly, again, as a human-only item.

### L2. The recalibration mechanism paragraph's opening sentence is now categorical, in tension with its own later hedge

Round 5 added, to the same paragraph, "Because this analysis varies participant count
without independently varying selection count, it does not by itself isolate the two." The
paragraph's *opening* sentence, unchanged since before round 5, still states flatly "The
failure tracks participants rather than trials," and a later clause states "which is why the
instability tracks participant count rather than selection count" — both categorical claims
the paragraph's own final sentence just qualified. Verified directly in
`manuscript/manuscript_expanded.md:265` (identical in `manuscript_highlighted.md:265`, both
inside the same pre-existing `{.mark}` span). Fix: soften both clauses to match the
hedged claim already in the paragraph's last sentence, changing no number and no other
sentence. The response's own independently-worded paraphrase of this mechanism (fixed in
round 5) already carries the correct hedge and needs no further change — verified by
re-reading it, it does not repeat either categorical phrase.

### L3. "Bounded" language in the response no longer matches what an MDE analysis establishes

Three instances in `manuscript/response_to_reviewers_jne_r1.md` (lines ~159, ~270, ~291)
use "bounded" to describe what reporting a minimum detectable effect (MDE) at 80% power
does to a null result. A 95% confidence interval bounds compatible effects; an 80%-power
MDE characterizes the design's sensitivity, and the response elsewhere (both of these two
locations, in the very same sentences) already correctly states "smaller improvements could
have gone undetected" — which is a power statement, not a bound. Fix: reword all three
instances to describe what was actually done (report the MDE to make the design's power
explicit) rather than claim the null was "bounded."

### L4. Two overclaims in the response's own executive summary and results narration

1. **Response line 17 (cover-summary-equivalent opening paragraph):** "No alignment method
   restores transportability. No nonlinear decision boundary restores it." states a
   universal claim about every conceivable alignment or nonlinear method, when the study
   tested exactly four alignment specifications and two nonlinear decoders. Verified by
   reading the same response document's own later, more careful framing ("What the numbers
   support is the narrower claim that no arm *restores transportability*"), which already
   scopes correctly — only the opening summary overclaims.
2. **Response, alignment-results table lead-in:** "The result is negative, and uniformly
   so" immediately precedes a table showing the two Euclidean Alignment arms *improving*
   pooled MAE (0.098→0.095/0.097) and downstream AUC relative to the primary arm, which the
   response itself discusses at length two paragraphs later ("we do not claim that no arm
   improves anything"). "Uniformly negative" contradicts the response's own subsequent,
   more careful discussion. Verified by reading the full surrounding paragraph (`sed -n
   '60,95p'`). Fix both instances to state the narrower, already-correct claim (no arm
   restored transportability) rather than a universal or uniform one.

### L5. "Published" terminology is inaccurate pre-decision language

The response (4 instances) and the supplement (2 instances) refer to the original,
not-yet-accepted primary analysis as "published values," "published tau," "published
file," and "published outputs." The manuscript is under review, not published. Verified via
`grep -o "published [a-z]*"` across both files: exactly 6 occurrences, all referring to the
same primary/original analysis, none referring to an actually-published external source.
Fix: reword all 6 to avoid the word "published," using "previously submitted" or
"primary-analysis" as the context requires (see the plan for the exact phrase chosen per
instance — one supplement instance uses "previously submitted values" rather than
"previously submitted primary values" specifically to avoid an adjacent-"primary"
repetition against "The primary row reproduces...", a copy-editing judgment call that keeps
the substance of the fix, not a deviation from it).

## Point raised but not actioned as a text fix: the title

The reviewer offered an alternative title ("...and was not restored by tested alignment or
local recalibration") but explicitly said "I do not consider the current title a blocker."
Per every prior round's identical ruling, title wording is the corresponding author's
decision, not a defect to fix unilaterally. Not applied; noted for the user alongside L1.

## Global constraints

- No change to any frozen numeric result, CSV, JSON, or test file. This plan is entirely
  prose rewording; no number, citation, or cross-reference changes.
- Every text substitution uses the established scripted-substitution-with-uniqueness-assertion
  pattern (`text.count(old) == 1` before replacing). Never hand-edit with `sed`.
- `manuscript/manuscript_expanded.md` and `manuscript/manuscript_highlighted.md` must remain
  identical once every `[...]{.mark}` span in the highlighted copy is stripped, checked after
  the one edit that touches both (L2). That edit falls entirely inside the paragraph's
  pre-existing single `{.mark}` span (verified before this spec was written).
- Zero em dashes introduced.
- The full submission packet (`2_Response_to_Reviewers.docx/.pdf/.portal.pdf`,
  `3_Manuscript_CLEAN.docx/.pdf/.portal.pdf`, `4_Manuscript_HIGHLIGHTED.docx/.pdf/.portal.pdf`)
  must be rebuilt from corrected sources and re-verified at the end. The cover letter and
  supplement's numbered files are unchanged by this plan (L1 is not actioned; L5's two
  supplement instances are source-only changes to a file whose packet copy, `5_Supplement`,
  should also be rebuilt since its rendered content does change).
