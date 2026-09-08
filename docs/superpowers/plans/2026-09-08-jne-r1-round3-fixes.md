# JNE-111284 R1 packet — round-3 consistency fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix eight verified defects from a third external adversarial review of the JNE-111284 R1 packet — a stale block quote, an overclaimed statistical-exclusion framing repeated in a caption and two prose locations, three unqualified restatements of an already-softened claim, a wording inaccuracy about a GBM correction plus a missing exact number for it, a second unfixed instance of a stale word count, and two response tables that render with mid-word line breaks in the actual built PDF — then rebuild and re-verify the packet.

**Architecture:** Same scripted-substitution-with-uniqueness-assertion pattern as both prior rounds. Small same-shape fixes are batched into fewer, larger dispatches per the subagent-driven-development skill's batching guidance, since most of this plan's work is independent single-file or two-file text edits with no design judgment required. The final task is a controller-executed rebuild (as in round 2's Task 11), because it needs the `mcp__word-docx__convert_to_pdf` tool and is integration work, not fresh implementation.

**Tech Stack:** Python 3.11.14 via `/tmp/calib_venv/bin/python` (never a bare `python3`), pandoc, LibreOffice/`soffice` (via `mcp__word-docx__convert_to_pdf`), ghostscript (`make_portal_pdf.sh`).

**Spec:** `docs/superpowers/specs/2026-09-08-jne-r1-round3-fixes.md`

## Global Constraints

- Repository root: `/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration`. Packet root: `/Volumes/Extreme SSD/Mimic-IV/_submission_ready/study_bigp3_als_calibration/REVISION_R1_JNE-111284`.
- Python interpreter: `/tmp/calib_venv/bin/python`, always by full path.
- No change to any frozen numeric result, CSV, JSON, test file, or `src/bigp3_als/features.py` (its code is read for exact numbers, never modified).
- Every substitution via a script asserting `text.count(old) == 1` immediately before replacing — check against the CURRENT file, not a value copied from this plan, since an earlier task in this same plan may have already changed nearby text.
- `manuscript_expanded.md` and `manuscript_highlighted.md` must remain byte-identical once every `[...]{.mark}` span in the highlighted copy is stripped (regex: `\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}` → keep group 1). Verify after every task that touches either file.
- Zero em dashes introduced, except inside a reviewer's own verbatim quoted comment (must remain true).
- After all text tasks land, rebuild the entire packet from corrected sources and re-verify with an actual docx build and PDF text extraction — not just the markdown source — since this round's own G9 finding was only visible that way.

---

### Task 1: Resync the response's nonlinear-Results quote, and fix the second stale word-count instance

**Files:**
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Write and run the substitution script**

```python
"""G2: response line ~250 block-quotes a paraphrase of the manuscript's nonlinear-Results
paragraph, not the paragraph itself -- a systematic sweep of all 23 block quotes in this
file found this the only remaining genuine drift. G8: a second, differently-worded instance
of the stale word-count claim (round 2 fixed only the first)."""
from pathlib import Path

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
text = RESPONSE.read_text()

QUOTE_OLD = (
    "> A nonlinear decision boundary did not account for the result. Two nonlinear "
    "calibration decoders, a radial-basis kernel approximation and a gradient-boosted tree "
    "ensemble on a principal-component reduction, were computed on the identical epochs "
    "through the identical grouped cross-validation. Neither recovered the regularised "
    "linear decoder's discriminability: mean cross-validated AUC was 0.714 for both, "
    "against 0.805 for the linear decoder, and the close agreement between two "
    "structurally unrelated nonlinear families indicates that this result is not an "
    "artifact of either family's particular modelling choice, though it does not on its "
    "own establish a performance ceiling imposed by the data. Neither improved transport "
    "(slope tau 0.461 and 0.514, intercept tau 1.034 and 1.162, against 0.432 and 0.873). "
    "Because these scores discriminate less well than the linear one, their higher "
    "heterogeneity is not on its own evidence about nonlinear boundaries; the claim "
    "supported is the narrower one, that a nonlinear boundary improves neither "
    "discrimination nor transport here, so the failure of the mapping to transport is not "
    "attributable to the linearity of the decoder."
)
QUOTE_NEW = (
    "> Neither nonlinear decoder recovered the regularised linear decoder's "
    "discriminability. Mean cross-validated discriminability was 0.714 for the kernel "
    "approximation and 0.714 for the gradient-boosted ensemble, against 0.805 for the "
    "linear decoder, which discriminated better than both nonlinear arms in every one of "
    "the 18 cohorts (supplement, S12; Table S15). The close agreement between two "
    "structurally unrelated nonlinear families indicates that this result is not an "
    "artifact of either family's particular modelling choice, though it does not on its "
    "own establish a performance ceiling imposed by the data. Neither improved transport: "
    "slope tau was 0.461 and 0.514 and intercept tau 1.034 and 1.162, against 0.432 and "
    "0.873. Because these scores discriminate less well than the linear one, their higher "
    "heterogeneity is not on its own evidence about nonlinear boundaries; what the "
    "comparison supports is the narrower statement that a nonlinear boundary improves "
    "neither discrimination nor transport here, so the failure of the mapping to transport "
    "is not attributable to the linearity of the decoder."
)
count = text.count(QUOTE_OLD)
assert count == 1, f"quote resync: expected 1 occurrence, found {count}"
text = text.replace(QUOTE_OLD, QUOTE_NEW)

WORDCOUNT_OLD = "approximately 8,600 words against 6,600"
WORDCOUNT_NEW = "approximately 8,900 words against 6,600"
count = text.count(WORDCOUNT_OLD)
assert count == 1, f"word count: expected 1 occurrence, found {count}"
text = text.replace(WORDCOUNT_OLD, WORDCOUNT_NEW)

RESPONSE.write_text(text)
print("both fixes applied")
```

- [ ] **Step 2: Verify**

Run: `grep -n "8,600 words against\|8,600 words\b" manuscript/response_to_reviewers_jne_r1.md` — expected: no output, or only the corrected "8,900" wording.

Run this to confirm the quote now matches the manuscript exactly (content after stripping "> "):
```bash
/tmp/calib_venv/bin/python -c "
from pathlib import Path
r = Path('manuscript/response_to_reviewers_jne_r1.md').read_text()
m = Path('manuscript/manuscript_expanded.md').read_text()
quote = [l for l in r.splitlines() if l.startswith('> Neither nonlinear decoder recovered')][0][2:]
print('quote in manuscript:', quote in m)
"
```
Expected: `quote in manuscript: True`

- [ ] **Step 3: Commit**

```bash
git add manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: resync stale nonlinear-Results quote and second stale word count

The response's block quote for Reviewer 2 comment 2.2 was a paraphrase
of the manuscript's Results paragraph, not the paragraph itself -- a
systematic sweep of all 23 block quotes in the file found this the
only remaining drift. A second, differently-worded instance of the
stale 6,600-to-8,600 word count (round 2 fixed only the first) is
also corrected to 8,900.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 2: Fix the MDE-as-exclusion overclaim in the manuscript, the response, and Figure 6's caption

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Write and run the substitution script**

```python
"""G3: 'Improvements of that size or larger are excluded' overstates what an 80%-power
minimum detectable effect (MDE) establishes -- a non-significant result at 80% power does
not categorically exclude true effects at or above the MDE. G4: Figure 6's caption makes
the same category error, describing the MDE envelope as something a CI 'clears', which is
significance-testing language applied to a design-sensitivity quantity."""
from pathlib import Path

MDE_OLD = "Improvements of that size or larger are excluded; smaller ones are not."
MDE_NEW = (
    "The design had 80% power to detect improvements at or above these sizes; smaller "
    "improvements could have gone undetected."
)

for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(MDE_OLD)
    assert count == 1, f"{path} [MDE]: expected 1 occurrence, found {count}"
    text = text.replace(MDE_OLD, MDE_NEW)
    path.write_text(text)
    print(f"{path}: MDE sentence fixed")

response = Path("manuscript/response_to_reviewers_jne_r1.md")
text = response.read_text()
count = text.count(MDE_OLD)
assert count == 1, f"response [MDE]: expected 1 occurrence, found {count}"
response.write_text(text.replace(MDE_OLD, MDE_NEW))
print("response: MDE sentence fixed")

CAPTION_OLD = (
    "No point's interval clears the envelope in the direction that favours recalibrating "
    "at any size from 1 to 16 local participants."
)
CAPTION_NEW = (
    "No point's 95% confidence interval excludes zero in the direction that favours "
    "recalibrating at any size from 1 to 16 local participants; the dashed envelope is "
    "shown for context, not as a significance threshold."
)
for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(CAPTION_OLD)
    assert count == 1, f"{path} [caption]: expected 1 occurrence, found {count}"
    text = text.replace(CAPTION_OLD, CAPTION_NEW)
    path.write_text(text)
    print(f"{path}: Figure 6 caption fixed")
```

Run with `/tmp/calib_venv/bin/python`.

If the response's block quote of the Figure-6-adjacent Results paragraph (search
`grep -n "Improvements of that size or larger"` in the response after Step 1's first
substitution) shows a SECOND occurrence you did not expect, or the response quotes the
Figure 6 caption text verbatim anywhere, stop and report the exact match — do not assume
it is already handled.

- [ ] **Step 2: Verify parity and check for the caption fix in both manuscript copies**

```bash
/tmp/calib_venv/bin/python -c "
import re
from pathlib import Path
h = Path('manuscript/manuscript_highlighted.md').read_text()
c = Path('manuscript/manuscript_expanded.md').read_text()
stripped = re.sub(r'\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}', r'\1', h)
print('PARITY:', 'IDENTICAL' if stripped == c else 'DIFFER')
"
grep -c "are excluded; smaller ones are not" manuscript/manuscript_expanded.md manuscript/response_to_reviewers_jne_r1.md
grep -c "clears the envelope" manuscript/manuscript_expanded.md
```
Expected: `PARITY: IDENTICAL`; both grep counts 0.

- [ ] **Step 3: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: replace MDE-as-exclusion overclaim with power-based framing

An 80%-power minimum detectable effect is not a hard exclusion
boundary -- a non-significant result does not categorically exclude
true effects at or above it. Replaced the 'are excluded' framing in
the manuscript and response, and Figure 6's caption language treating
the MDE envelope as something a CI 'clears', with accurate power- and
CI-based statements.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 3: Soften the response's three unqualified "lower bound" restatements

**Files:**
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Write and run the substitution script**

```python
"""G5: the manuscript's own archive-homogenisation claim was already softened in round 2
(Task 8) from an unqualified 'lower bound' to 'likely understates', because a true lower
bound cannot be established from an archive with no independent hardware variation to test
against. The response's own prose (not a block quote, so untouched by any quote resync)
still asserts the stronger, already-rejected framing in three places."""
from pathlib import Path

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
text = RESPONSE.read_text()

OLD_A = (
    "The Discussion now reasons about the direction of the bias introduced by the "
    "archive's shared montage, sampling rate and amplifier, and states that the reported "
    "heterogeneity is a lower bound."
)
NEW_A = (
    "The Discussion now reasons about the direction of the bias introduced by the "
    "archive's shared montage, sampling rate and amplifier, and states that the reported "
    "heterogeneity likely understates what an independent deployment would show."
)
count = text.count(OLD_A)
assert count == 1, f"A: expected 1, found {count}"
text = text.replace(OLD_A, NEW_A)

OLD_B = (
    "The reported tau is therefore a lower bound on what a site meeting a genuinely "
    "independent cohort should expect, and the transportability failure is, if anything, "
    "understated."
)
NEW_B = (
    "The reported tau therefore likely understates what a site meeting a genuinely "
    "independent cohort should expect, and the transportability failure is, if anything, "
    "understated rather than overstated; what an independent site's amplifier or montage "
    "would additionally contribute is not something this archive can quantify."
)
count = text.count(OLD_B)
assert count == 1, f"B: expected 1, found {count}"
text = text.replace(OLD_B, NEW_B)

OLD_C = (
    "concluding that the reported heterogeneity is a lower bound, and cross-referencing "
    "the new cohort-level alignment result as evidence for that direction."
)
NEW_C = (
    "concluding that the reported heterogeneity likely understates what an independent "
    "deployment would show, and cross-referencing the new cohort-level alignment result as "
    "evidence for that direction."
)
count = text.count(OLD_C)
assert count == 1, f"C: expected 1, found {count}"
text = text.replace(OLD_C, NEW_C)

RESPONSE.write_text(text)
print("all three lower-bound instances softened")
```

Run with `/tmp/calib_venv/bin/python`.

- [ ] **Step 2: Verify**

Run: `grep -n "is a lower bound\|is therefore a lower bound" manuscript/response_to_reviewers_jne_r1.md`
Expected: no output (all three unqualified instances gone; the word "understates" now appears in their place).

- [ ] **Step 3: Commit**

```bash
git add manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: align response's homogenisation wording with the manuscript's softened claim

The manuscript already says the heterogeneity 'likely understates' an
independent deployment's true value, deliberately softened in round 2
because a true lower bound cannot be established from an archive with
no independent hardware variation to test against. The response's own
prose, in three separate places, still asserted the stronger,
already-rejected 'lower bound' framing.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 4: Fix the GBM wording inaccuracy and add the exact retained-variance numbers to S12

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`
- Modify: `manuscript/response_to_reviewers_jne_r1.md`
- Modify: `supplementary/supplement_expanded.md`

**Interfaces:**
- Consumes: `src/bigp3_als/features.py:106-121` (read only, not modified) for the exact numbers: 150 components, floored at `smallest_training_fold - 1`, chosen because it retains 90-97% cumulative explained variance on probe sessions, against 56-80% for an earlier, rejected 40-component choice.
- Produces: none.

- [ ] **Step 1: Fix the manuscript's and response's misattribution of a "retained-variance target" to arms that don't have one**

```python
"""G6: 'the retained-variance target its comparators used' implies the primary decoder and
the RBF arm share a retained-variance target with GBM. Verified against the code: the
primary decoder uses no PCA at all, and the RBF arm's Nystroem approximation uses a fixed
component count (300), not a variance target -- only GBM's PCA step has one. The
supplement's own wording is already accurate ('the measured-variance criterion above
specifies'); bring the manuscript and response into line with it."""
from pathlib import Path

OLD = (
    "the gradient-boosted arm's initial run lacked the class rebalancing and the "
    "retained-variance target its comparators used, and was corrected before any "
    "transportability analysis used the column"
)
NEW = (
    "the gradient-boosted arm's initial run lacked the class rebalancing its comparators "
    "use and retained fewer principal components than the measured-variance criterion "
    "specifies, and was corrected before any transportability analysis used the column"
)

for path in (
    Path("manuscript/manuscript_expanded.md"),
    Path("manuscript/manuscript_highlighted.md"),
    Path("manuscript/response_to_reviewers_jne_r1.md"),
):
    text = path.read_text()
    count = text.count(OLD)
    assert count == 1, f"{path}: expected 1 occurrence, found {count}"
    path.write_text(text.replace(OLD, NEW))
    print(f"{path}: GBM wording fixed")
```

The manuscript sentence's existing trailing citation, "(supplement, S12)", already sits at
the end of the same sentence (after "...moving its mean discriminability from 0.655 to
0.714 (supplement, S12)") and is left untouched by this substitution — it now serves as the
pointer for both the variance-criterion detail and the discriminability numbers. Do not add
a second citation.

- [ ] **Step 2: Add the exact numbers to supplement S12**

```python
"""G7: S12 says only 'measured retained variance' and 'a large majority of the variance'
without the actual numbers. Add them, transcribed from the code comment at
src/bigp3_als/features.py:106-121 -- read that file yourself to confirm these numbers
before using them, since a transcription error here would misreport what the code does."""
from pathlib import Path

SUPPLEMENT = Path("supplementary/supplement_expanded.md")
OLD = (
    "The number of retained components was set from measured retained variance rather "
    "than matched to the kernel approximation's component count, which is a different "
    "quantity."
)
NEW = (
    "The number of retained components, 150, floored at one less than the smallest "
    "training fold's size when a fold is smaller than that, was set from measured "
    "retained variance rather than matched to the kernel approximation's component count, "
    "which is a different quantity: on probe sessions spanning the archive's size range, "
    "150 components retained 90 to 97% of cumulative explained variance in this "
    "downsampled feature representation, against 56 to 80% for an earlier, rejected "
    "40-component choice."
)
text = SUPPLEMENT.read_text()
count = text.count(OLD)
assert count == 1, f"expected 1 occurrence, found {count}"
SUPPLEMENT.write_text(text.replace(OLD, NEW))
print("S12: exact GBM PCA numbers added")
```

Run both scripts with `/tmp/calib_venv/bin/python`.

- [ ] **Step 3: Verify**

```bash
/tmp/calib_venv/bin/python -c "
import re
from pathlib import Path
h = Path('manuscript/manuscript_highlighted.md').read_text()
c = Path('manuscript/manuscript_expanded.md').read_text()
stripped = re.sub(r'\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}', r'\1', h)
print('PARITY:', 'IDENTICAL' if stripped == c else 'DIFFER')
"
grep -n "the retained-variance target its comparators used" manuscript/manuscript_expanded.md manuscript/response_to_reviewers_jne_r1.md
grep -n "90 to 97%\|150 components" supplementary/supplement_expanded.md
```
Expected: `PARITY: IDENTICAL`; the first grep returns no output; the second finds the new numbers.

- [ ] **Step 4: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md supplementary/supplement_expanded.md
git commit -m "fix: correct GBM-correction wording and add its exact PCA numbers to S12

'The retained-variance target its comparators used' implied the
primary decoder and the RBF arm share a criterion with GBM; neither
does (no PCA for the primary; a fixed 300-component Nystroem count for
RBF). Brought the manuscript and response into line with the
supplement's already-accurate wording. Also added the exact numbers
S12 was missing: 150 components, chosen because they retain 90-97%
cumulative explained variance against 56-80% for an earlier
40-component choice, transcribed from the code comment at
src/bigp3_als/features.py.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 5: Abstract precision and "unlabeled calibration recordings" clarity

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Write and run the substitution script**

```python
"""G10: 'did not reduce this heterogeneity' is a defensible Abstract-level summary (the
Results paragraph already gives the full nuance: session-level EA's slope tau moved
slightly in the helpful direction while its intercept tau moved against it, so net
heterogeneity did not meaningfully improve), but a literal reading of the two numbers
(0.419 < 0.432) could be set against the unqualified word 'reduce'. Add one hedging word.
G11: 'unlabeled calibration recordings' already disambiguates via the next clause ('but
never its online accuracy'), but is cheap to make unambiguous outright."""
from pathlib import Path

ABSTRACT_OLD = (
    "Neither signal- nor score-space alignment, nor either of two nonlinear decision "
    "boundaries, reduced this heterogeneity."
)
ABSTRACT_NEW = (
    "Neither signal- nor score-space alignment, nor either of two nonlinear decision "
    "boundaries, meaningfully reduced this heterogeneity."
)

LABEL_OLD = (
    "Both score-space specifications require the target cohort's unlabeled calibration "
    "recordings but never its online accuracy"
)
LABEL_NEW = (
    "Both score-space specifications require the target cohort's calibration recordings, "
    "using only their usual target/non-target labels, but never its online accuracy"
)

for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(ABSTRACT_OLD)
    assert count == 1, f"{path} [abstract]: expected 1 occurrence, found {count}"
    text = text.replace(ABSTRACT_OLD, ABSTRACT_NEW)
    count = text.count(LABEL_OLD)
    assert count == 1, f"{path} [label]: expected 1 occurrence, found {count}"
    text = text.replace(LABEL_OLD, LABEL_NEW)
    path.write_text(text)
    print(f"{path}: both fixes applied")
```

Run with `/tmp/calib_venv/bin/python`. If the response quotes either of these two exact
sentences verbatim anywhere (check with `grep` before assuming it does not), extend the
script to resync that quote too, following the same pattern as every prior task in this
plan and the round-2 plan.

- [ ] **Step 2: Verify**

```bash
/tmp/calib_venv/bin/python -c "
import re
from pathlib import Path
h = Path('manuscript/manuscript_highlighted.md').read_text()
c = Path('manuscript/manuscript_expanded.md').read_text()
stripped = re.sub(r'\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}', r'\1', h)
print('PARITY:', 'IDENTICAL' if stripped == c else 'DIFFER')
"
```
Expected: `PARITY: IDENTICAL`

- [ ] **Step 3: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md
git commit -m "fix: precise the Abstract's heterogeneity claim and disambiguate 'unlabeled'

Added 'meaningfully' to the Abstract's alignment/nonlinear sentence so
a literal 0.419-vs-0.432 reading of one arm's slope tau (which moved
slightly favourably while its intercept tau moved against it) cannot
be set against an unqualified 'reduce'. Clarified that the score-space
alignment arms use the usual target/non-target calibration labels,
never the online-accuracy outcome, removing a plausible (if already
locally disambiguated) misreading of 'unlabeled'.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 6: Shorten the response's two table header rows so they stop breaking mid-word in the built PDF

**Files:**
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Write and run the substitution script**

```python
"""G9: rendering 2_Response_to_Reviewers.pdf and reading the extracted text directly
confirmed both response-embedded tables break header words mid-cell ('Poole/d MAE',
'Slop/e tau', 'Interce/pt tau', 'Local/participa/nts', 'Transpo/rted MAE',
'Recalibr/ated MAE'). These are illustrative summary tables in a response letter, not
supplement tables other documents cross-reference by exact column name, so the fix is to
shorten the headers -- no data cell changes, no table restructuring."""
from pathlib import Path

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
text = RESPONSE.read_text()

HEADER1_OLD = "| Arm | Pooled MAE | Slope tau | Slope 95% prediction interval | Intercept tau | Intercept 95% prediction interval |"
HEADER1_NEW = "| Arm | Pooled MAE | Slope tau | Slope 95% PI | Intercept tau | Intercept 95% PI |"
count = text.count(HEADER1_OLD)
assert count == 1, f"header1: expected 1 occurrence, found {count}"
text = text.replace(HEADER1_OLD, HEADER1_NEW)

HEADER2_OLD = "| Refit | Local participants | Median local selections | Transported MAE | Recalibrated MAE | Improvement (95% CI) | 80% power to detect |"
HEADER2_NEW = "| Refit | Local n | Median local sel. | MAE, transported | MAE, recalibrated | Improvement (95% CI) | 80% power |"
count = text.count(HEADER2_OLD)
assert count == 1, f"header2: expected 1 occurrence, found {count}"
text = text.replace(HEADER2_OLD, HEADER2_NEW)

RESPONSE.write_text(text)
print("both table headers shortened")
```

Run with `/tmp/calib_venv/bin/python`.

- [ ] **Step 2: Verify the markdown table structure is still valid**

Run: `grep -A2 "^| Arm | Pooled MAE" manuscript/response_to_reviewers_jne_r1.md` and `grep -A2 "^| Refit | Local n" manuscript/response_to_reviewers_jne_r1.md` — confirm each header row is still followed by a `| --- | --- | ... |` separator row with the same number of columns as the header (6 for the first table, 7 for the second). A column-count mismatch between the header and separator row would break the table's rendering entirely, which is a more serious defect than the one being fixed — count the `|` characters in both rows and confirm they match before proceeding.

Note: this task's own verification is necessarily incomplete — whether the shortened headers actually stop breaking mid-word can only be confirmed by an actual docx/PDF rebuild, which happens in Task 7 (the final rebuild), not here. Report this task DONE on the markdown-level checks passing; the real verification is Task 7's job.

- [ ] **Step 3: Commit**

```bash
git add manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: shorten response table headers that were breaking mid-word in the built PDF

Rendering 2_Response_to_Reviewers.pdf and reading the extracted text
directly showed both embedded tables' header rows breaking mid-word
('Poole/d MAE', 'Local/participa/nts', etc). Shortened the header text
only; no data cells or table structure changed.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 7: Rebuild and re-verify the entire submission packet (controller-executed)

**Files:**
- Rebuild: all `.docx`/`.pdf`/`.portal.pdf` files in the packet directory.
- Rewrite: `0_README.md` in the packet directory.

**Interfaces:**
- Consumes: every file touched by Tasks 1–6 (must all be committed first).
- Produces: the round-3-corrected packet.

**Ruling (recorded in advance, matching round 2's Ruling T11-1):** This task is executed
directly by the controller rather than dispatched to a subagent, for the same reason as
before — it requires the `mcp__word-docx__convert_to_pdf` tool the controller already
holds, and it is integration work with no benefit from a fresh perspective.

- [ ] **Step 1: Confirm all six tasks are committed and the test suite is unaffected**

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration"
git log --oneline -7
git status --porcelain
/tmp/calib_venv/bin/python -m pytest tests/ -q
```
Expected: 6 new commits, clean tree, 235 passed / 1 deselected (unchanged — this plan touches no code or test file).

- [ ] **Step 2: Rebuild the four affected docx files** (manuscript clean/highlighted, response, supplement — TRIPOD is untouched by this plan and does not need rebuilding)

```bash
P="/Volumes/Extreme SSD/Mimic-IV/_submission_ready/study_bigp3_als_calibration/REVISION_R1_JNE-111284"
A="/Volumes/Extreme SSD/Mimic-IV/_pub_assets"
F="gfm+superscript+raw_attribute+attributes+bracketed_spans"
R="$A/reference_cmu.docx"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" manuscript/manuscript_expanded.md -o "$P/3_Manuscript_CLEAN.docx" --resource-path="manuscript:.:output/expanded/figures" --reference-doc="$R"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" manuscript/manuscript_highlighted.md -o "$P/4_Manuscript_HIGHLIGHTED.docx" --resource-path="manuscript:.:output/expanded/figures" --reference-doc="$R"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" manuscript/response_to_reviewers_jne_r1.md -o "$P/2_Response_to_Reviewers.docx" --reference-doc="$R"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" supplementary/supplement_expanded.md -o "$P/5_Supplement.docx" --resource-path="supplementary:.:output/expanded/figures" --reference-doc="$R"
for f in 2_Response_to_Reviewers 3_Manuscript_CLEAN 4_Manuscript_HIGHLIGHTED 5_Supplement; do
  /usr/bin/python3 "$A/fix_docx_tables.py" "$P/$f.docx"
done
```

- [ ] **Step 3: Convert to PDF and portal PDF**

Call `mcp__word-docx__convert_to_pdf` on each of `3_Manuscript_CLEAN.docx`,
`4_Manuscript_HIGHLIGHTED.docx`, `2_Response_to_Reviewers.docx`, `5_Supplement.docx` (four
separate calls). Then:

```bash
cd "$P" && bash "/Volumes/Extreme SSD/Mimic-IV/_pub_assets/make_portal_pdf.sh" \
  3_Manuscript_CLEAN.docx 4_Manuscript_HIGHLIGHTED.docx 2_Response_to_Reviewers.docx 5_Supplement.docx
```

- [ ] **Step 4: Verify G9's fix actually landed in the rebuilt PDF**

```bash
cd "$P"
pdftotext 2_Response_to_Reviewers.pdf - | grep -n "^Poole\|^Slop$\|^Interce\|^Local$\|^participa\|^Transpo\|^Recalibr"
```
Expected: no output (none of the previously-broken word fragments survive). If any still
appear, the header text is still too long for the column width `colwidths.lua` assigns it —
shorten further (e.g. "MAE, transp." / "MAE, recal.") and rebuild before proceeding; do not
report this task done with a known-broken table still in the PDF.

- [ ] **Step 5: Re-run the clean-vs-highlighted PDF text diff**

```bash
diff <(pdftotext 3_Manuscript_CLEAN.pdf -) <(pdftotext 4_Manuscript_HIGHLIGHTED.pdf -)
```
Expected: no output (0 lines of diff) — this is the check round 2's own final review demonstrated is the only reliable way to catch a broken highlight span, and this plan's Task 2/4/5 all touch manuscript text that may fall inside or adjacent to existing `{.mark}` spans.

- [ ] **Step 6: Re-verify structural counts**

```bash
/tmp/calib_venv/bin/python - <<'PYEOF'
import re, zipfile
from pathlib import Path
base = Path(".")
pattern = '<w:highlight w:val="yellow"'
for name in sorted(p for p in base.glob("*.docx") if not p.name.startswith("._")):
    with zipfile.ZipFile(name) as z:
        xml = z.read("word/document.xml").decode("utf-8")
        images = [n for n in z.namelist() if n.startswith("word/media/")]
    text = re.sub(r"<[^>]+>", " ", xml)
    print(f"{name.name:32s} tables={xml.count('<w:tbl>'):3d} images={len(images):2d} "
          f"yellow={xml.count(pattern):3d} words={len(text.split())}")
PYEOF
```
Expected: clean and highlighted manuscript word counts identical to each other (may differ
slightly from round 2's 10,946 given Task 2/5's wording changes — record whatever the new
number is); highlighted carries 21 yellow runs (this plan adds no new `{.mark}` spans);
clean carries 0.

- [ ] **Step 7: Rewrite `0_README.md`**

Update: (a) the "Fixes applied" section to add a new subsection for this round's 8 fixes,
referencing this plan's task numbers, in the same one-line-per-item style as the round-2
section; (b) refresh every word/table/figure count from Step 6's actual output rather than
copying round 2's numbers; (c) keep the GitHub-push blocker as the top item, unchanged in
substance; (d) keep the title-confirmation item; (e) note that the TRIPOD checklist was
reviewed as part of this round's verification and required no changes (G7's claim that it
was "not included" was checked and found false — it is present and was already correct).

- [ ] **Step 8: Final test run and commit**

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration"
/tmp/calib_venv/bin/python -m pytest tests/ -q
git status --porcelain
```
If anything inside this git repository changed (the README lives outside it, under
`_submission_ready/`, so likely nothing will), commit it; otherwise report that only the
packet directory changed, matching round 2's Task 11 precedent.

- [ ] **Step 9: Report to the user**

Summarize which of the eight findings were fixed, the downgraded points and why, and
confirm the GitHub-push and title-confirmation blockers remain exactly as before (this
round changes neither).
