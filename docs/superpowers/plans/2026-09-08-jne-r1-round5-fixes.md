# JNE-111284 R1 packet round-5 consistency fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the 6 confirmed findings (K1-K6) from a fifth external adversarial review of
the JNE-111284 revision packet, rebuild and re-verify the submission packet.

**Architecture:** Five text-fix tasks plus one controller-executed rebuild, run strictly in
sequence (multiple tasks touch the same files).

**Tech Stack:** Python 3.11 via `/tmp/calib_venv/bin/python`; pandoc + `_pub_assets/colwidths.lua`
+ `_pub_assets/fix_docx_tables.py` + `mcp__word-docx__convert_to_pdf` +
`_pub_assets/make_portal_pdf.sh` for the packet rebuild.

**Spec:** `docs/superpowers/specs/2026-09-08-jne-r1-round5-fixes.md`

## Global Constraints

- Python interpreter: `/tmp/calib_venv/bin/python`, always by full path.
- Every substitution via a script asserting `text.count(old) == 1` before replacing, per
  file, per string. All OLD strings below were pre-verified `count() == 1` in the live
  files immediately before this plan was written.
- `manuscript/manuscript_expanded.md` and `manuscript/manuscript_highlighted.md` must
  remain byte-identical once every `[...]{.mark}` span in the highlighted copy is stripped
  (regex: `\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}` → group 1). Verify after every task that
  touches either file.
- Zero em dashes introduced.
- No change to any frozen numeric result, CSV, JSON, or test file. This plan touches no
  code or test file; the baseline test count must not change.
- Do not change the cover letter's signature line ("[Authors] on behalf of the authors") —
  this is deliberate, per the spec's own note. If any task's diff touches it, that is a
  defect to flag, not a fix to make.
- Commit as normal commits with plain, simple messages — no internal process jargon (no
  "round 5", "K1"-style finding IDs, "whole-branch review", etc.) per this project's
  standing convention, and no `Co-Authored-By`/session-link trailers.

---

### Task 1: Fix the cover letter's imprecise "repaired the reported heterogeneity" sentence

**Files:**
- Modify: `manuscript/cover_letter_jne_r1.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""K6: local recalibration's outcome is local estimation error, not between-cohort
heterogeneity in the sense the alignment/nonlinear arms were evaluated against; lumping all
three under one clause blurs a distinction the manuscript itself is careful about."""
from pathlib import Path

COVER = Path("manuscript/cover_letter_jne_r1.md")
OLD = (
    "None of these interventions restored transportability or repaired the reported "
    "heterogeneity; we report all three as negative results"
)
NEW = (
    "None restored a usable transported mapping: the alignment and nonlinear alternatives "
    "did not meaningfully reduce heterogeneity, and local recalibration did not reliably "
    "improve estimation error. We report all three as negative results"
)
text = COVER.read_text()
count = text.count(OLD)
assert count == 1, f"expected 1 occurrence, found {count}"
COVER.write_text(text.replace(OLD, NEW))
print("cover letter: heterogeneity/recalibration sentence precised")
```

Run with `/tmp/calib_venv/bin/python`.

- [ ] **Step 2: Verify**

```bash
grep -n "restored a usable transported mapping" manuscript/cover_letter_jne_r1.md
grep -c "repaired the reported heterogeneity" manuscript/cover_letter_jne_r1.md
tail -3 manuscript/cover_letter_jne_r1.md
```
Expected: the new sentence appears; the old phrase count is 0; the final two lines are
UNCHANGED — still exactly `Sincerely,` and `[Authors] on behalf of the authors`. Do not
touch the signature line under any circumstance; if you find yourself tempted to fill in a
name, stop — that is explicitly out of scope for this task.

- [ ] **Step 3: Commit**

```bash
git add manuscript/cover_letter_jne_r1.md
git commit -m "fix: attribute the cover letter's negative findings to the right intervention

The letter said all three interventions 'restored transportability
or repaired the reported heterogeneity.' Local recalibration's
outcome is local estimation error, not between-cohort heterogeneity
in the sense the alignment and nonlinear arms were evaluated
against. Restated so each class of intervention is described by
what it was actually shown not to do."
```

---

### Task 2: Correct two transcribed MAE cells and one imprecise sentence in the response table/text

**Files:**
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: `output/expanded/recalibration_summary_balanced.csv` (read only, not modified) —
  the numbers below are already independently verified against it.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""K1: two response-table cells disagree with the frozen recalibration_summary_balanced.csv
(and with the Supplement's own already-correct Table S17). Verified: n=2 recalibrated MAE
is 0.097 (0.097479), not 0.098; n=4 transported MAE is 0.090 (0.090471), not 0.091.
K3: 'There is no crossing point' is imprecise -- the point ESTIMATE crosses zero for both
refits in the tested range (verified against the same CSV); no confidence interval ever
excludes zero in the favourable direction, which is the claim that actually matters."""
from pathlib import Path

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
text = RESPONSE.read_text()

ROW2_OLD = "| Intercept only | 2 | 120 | 0.093 | 0.098 | -0.004 (-0.020 to +0.013) | 0.022 |"
ROW2_NEW = "| Intercept only | 2 | 120 | 0.093 | 0.097 | -0.004 (-0.020 to +0.013) | 0.022 |"
count = text.count(ROW2_OLD)
assert count == 1, f"row n=2: expected 1, found {count}"
text = text.replace(ROW2_OLD, ROW2_NEW)

ROW4_OLD = "| Intercept only | 4 | 246 | 0.091 | 0.091 | -0.000 (-0.014 to +0.014) | 0.019 |"
ROW4_NEW = "| Intercept only | 4 | 246 | 0.090 | 0.091 | -0.000 (-0.014 to +0.014) | 0.019 |"
count = text.count(ROW4_OLD)
assert count == 1, f"row n=4: expected 1, found {count}"
text = text.replace(ROW4_OLD, ROW4_NEW)

CROSSING_OLD = "There is no crossing point. At no local sample size we could evaluate"
CROSSING_NEW = "We found no statistically supported crossing point. At no local sample size we could evaluate"
count = text.count(CROSSING_OLD)
assert count == 1, f"crossing point: expected 1, found {count}"
text = text.replace(CROSSING_OLD, CROSSING_NEW)

RESPONSE.write_text(text)
print("response: 2 MAE cells corrected, crossing-point sentence precised")
```

Run with `/tmp/calib_venv/bin/python`.

- [ ] **Step 2: Verify**

```bash
grep -n "Intercept only | 2 | 120" manuscript/response_to_reviewers_jne_r1.md
grep -n "Intercept only | 4 | 246" manuscript/response_to_reviewers_jne_r1.md
grep -c "^There is no crossing point" manuscript/response_to_reviewers_jne_r1.md
```
Expected: the two rows show `0.093 | 0.097` and `0.090 | 0.091` respectively; the old
crossing-point sentence count is 0.

Independently re-derive the two corrected numbers yourself before committing, do not just
trust the OLD/NEW strings above:

```bash
/tmp/calib_venv/bin/python -c "
import pandas as pd
df = pd.read_csv('output/expanded/recalibration_summary_balanced.csv')
sub = df[(df['method']=='intercept_only') & (df['n_local_participants'].isin([2,4]))]
print(sub[['n_local_participants','transported_mae','recalibrated_mae']].to_string())
"
```
Expected: n=2 row shows `recalibrated_mae` rounding to 0.097; n=4 row shows
`transported_mae` rounding to 0.090.

- [ ] **Step 3: Commit**

```bash
git add manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: correct two transcribed MAE values and an imprecise crossing-point claim

Two cells in the composition-balanced recalibration table did not
match the frozen output (recalibrated_mae at n=2, transported_mae at
n=4) -- verified against output/expanded/recalibration_summary_balanced.csv
directly, matching the Supplement's own already-correct table.
Separately, 'there is no crossing point' overstated what the
confidence intervals show: the point estimate does cross zero for
both refits within the tested range, even though no interval ever
excludes zero in the favourable direction. Restated to say what is
actually true."
```

---

### Task 3: Refine the recalibration mechanism paragraph's precision-vs-design-flexibility claim

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: nothing from other tasks (Task 2 already committed its own separate response
  edits; this task's OLD strings are unaffected by them — verified no overlap).
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""K2: the mechanism paragraph correctly says additional selections don't add a new
predictor value, but doesn't concede they can still improve the precision of the estimate
at an existing value, and doesn't note the design varies participant count without
independently varying selection count, so it cannot itself isolate which one is causally
binding. The core mechanism claim (participant count determines the number of distinct
points) is correct and is preserved unchanged."""
from pathlib import Path

MANUSCRIPT_OLD = (
    "Additional character selections within an already-drawn session add weight at that "
    "session's existing predictor value rather than a new one, so they do not relieve "
    "this; drawing participants with additional recorded sessions would supply new "
    "predictor values, which is why the instability tracks participant count rather than "
    "selection count."
)
MANUSCRIPT_NEW = (
    "Additional character selections within an already-drawn session add weight at that "
    "session's existing predictor value rather than a new one; they can improve the "
    "precision of the observed accuracy at that value but do not supply the additional "
    "distinct point a two-parameter fit needs, which is why the instability tracks "
    "participant count rather than selection count. Because this analysis varies "
    "participant count without independently varying selection count, it does not by "
    "itself isolate the two."
)

for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(MANUSCRIPT_OLD)
    assert count == 1, f"{path}: expected 1, found {count}"
    path.write_text(text.replace(MANUSCRIPT_OLD, MANUSCRIPT_NEW))
    print(f"{path}: mechanism paragraph refined")

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
RESPONSE_OLD = (
    "The binding constraint is the number of distinct session-level predictor values a "
    "local sample supplies, which tracks participant count far more than "
    "character-selection count: additional selections within an already-drawn session do "
    "not add a new predictor value, though drawing a participant with additional sessions "
    "would."
)
RESPONSE_NEW = (
    "The instability appears to reflect sparse support in distinct session-level "
    "predictor values, which in this archive tracks participant count closely: "
    "additional selections within an already-drawn session do not add a new predictor "
    "value, though they can improve the precision of the observed accuracy at that value, "
    "and drawing a participant with additional sessions would add one. Because this "
    "analysis varies participant count rather than independently varying selection count, "
    "it does not separately identify the effect of increasing character-selection count."
)
text = RESPONSE.read_text()
count = text.count(RESPONSE_OLD)
assert count == 1, f"response: expected 1, found {count}"
RESPONSE.write_text(text.replace(RESPONSE_OLD, RESPONSE_NEW))
print("response: mechanism paraphrase refined")
```

Run with `/tmp/calib_venv/bin/python`.

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
grep -c "so they do not relieve this" manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md
grep -c "The binding constraint is the number" manuscript/response_to_reviewers_jne_r1.md
```
Expected: `PARITY: IDENTICAL`; both grep counts 0.

- [ ] **Step 3: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: concede a precision point and a design limitation in the recalibration mechanism

The mechanism paragraph correctly said additional character
selections don't add a new distinct predictor value, but didn't
concede they can still improve the precision of the estimate at an
existing value, and didn't note that participant count and
selection count were not varied independently, so the analysis
cannot by itself isolate which one is causally binding. The core
mechanism claim, that participant count determines the number of
distinct points available to the refit, is unchanged."
```

---

### Task 4: Reword the Euclidean Alignment mechanistic over-attribution (4 locations)

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""K4: 'removes what a cohort's recording chain shares' over-attributes cohort-level EA's
effect specifically to hardware. A pooled cohort covariance reference reflects more than
recording-chain properties (biological, paradigm, and preprocessing structure too). Reword
to describe what the method targets rather than assert what it physically removes, in all
four instances: Methods (manuscript + response paraphrase), and Discussion (manuscript +
its verbatim block quote in the response, plus a second independent response paraphrase)."""
from pathlib import Path

# Methods, instance 1: manuscript (both copies).
METHODS_OLD = (
    "a cohort-level reference pooled across every session in the cohort and weighted by "
    "epoch count, which removes what a cohort's recording chain shares while leaving "
    "between-session variation inside the cohort intact."
)
METHODS_NEW = (
    "a cohort-level reference pooled across every session in the cohort and weighted by "
    "epoch count, which targets cohort-wide covariance structure, including covariance "
    "differences that could arise from the recording chain, while leaving between-session "
    "variation inside the cohort intact."
)
for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(METHODS_OLD)
    assert count == 1, f"{path} [Methods]: expected 1, found {count}"
    path.write_text(text.replace(METHODS_OLD, METHODS_NEW))
    print(f"{path}: Methods EA wording fixed")

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
text = RESPONSE.read_text()

# Methods, instance 2: response's own paraphrase.
R_METHODS_OLD = (
    "A **cohort-level** reference pools every session in the cohort, weighted by epoch "
    "count, which removes what a cohort's recording chain shares while leaving "
    "between-session variation inside the cohort intact."
)
R_METHODS_NEW = (
    "A **cohort-level** reference pools every session in the cohort, weighted by epoch "
    "count, which targets cohort-wide covariance structure, including covariance "
    "differences that could arise from the recording chain, while leaving between-session "
    "variation inside the cohort intact."
)
count = text.count(R_METHODS_OLD)
assert count == 1, f"response [Methods paraphrase]: expected 1, found {count}"
text = text.replace(R_METHODS_OLD, R_METHODS_NEW)

# Discussion, instance 1: response's own independent paraphrase (not a block quote).
R_DISC_OLD = (
    "Cohort-level Euclidean Alignment removes what a cohort's recording chain shares, "
    "which is the class of difference the archive has already suppressed."
)
R_DISC_NEW = (
    "Cohort-level Euclidean Alignment targets cohort-wide covariance differences that "
    "could include recording-chain effects, which is the class of difference the archive "
    "has already suppressed."
)
count = text.count(R_DISC_OLD)
assert count == 1, f"response [Discussion paraphrase]: expected 1, found {count}"
text = text.replace(R_DISC_OLD, R_DISC_NEW)
RESPONSE.write_text(text)
print("response: both EA instances fixed")

# Discussion, instance 2: manuscript, and its verbatim block quote in the response.
DISC_OLD = (
    "cohort-level Euclidean Alignment removes what a cohort's recording chain shares, "
    "which is the class of covariance difference the archive's shared hardware could "
    "still leave behind within its own harmonisation, and it did not reduce "
    "between-cohort heterogeneity (Results, Alignment Did Not Restore Transportability)."
)
DISC_NEW = (
    "cohort-level Euclidean Alignment targets cohort-wide covariance differences that "
    "could include recording-chain effects, and it did not reduce between-cohort "
    "heterogeneity (Results, Alignment Did Not Restore Transportability)."
)
for path in (
    Path("manuscript/manuscript_expanded.md"),
    Path("manuscript/manuscript_highlighted.md"),
    Path("manuscript/response_to_reviewers_jne_r1.md"),
):
    text = path.read_text()
    count = text.count(DISC_OLD)
    assert count == 1, f"{path} [Discussion]: expected 1, found {count}"
    path.write_text(text.replace(DISC_OLD, DISC_NEW))
    print(f"{path}: Discussion EA wording fixed")
```

Run with `/tmp/calib_venv/bin/python`.

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
grep -c "removes what a cohort's recording chain shares" manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
```
Expected: `PARITY: IDENTICAL`; all three grep counts 0.

- [ ] **Step 3: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: soften Euclidean Alignment's mechanistic attribution to hardware

'Removes what a cohort's recording chain shares' over-attributes a
pooled cohort covariance reference specifically to hardware, when it
also reflects biological, paradigm, and preprocessing structure
shared within a cohort. Reworded all four instances (Methods and
Discussion, in the manuscript and the response) to describe what the
method targets rather than assert what it physically removes."
```

---

### Task 5: Clarify Figure 6's caption to describe two method-specific MDE envelopes

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`

**Interfaces:**
- Consumes: `src/bigp3_als/render_expanded.py` (read only, not modified) — already verified
  the MDE envelope is drawn once per method, in that method's own colour, i.e. two distinct
  envelopes, not one shared curve.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""K5: the MDE envelope is drawn per-method (once for intercept-only, once for
intercept-and-slope, each in its own colour) -- verified in render_expanded.py's
recalibration-curve renderer. The caption's singular 'the dashed envelope' does not
reflect this. The response does not quote this caption verbatim, so only the two
manuscript copies need the fix."""
from pathlib import Path

OLD = (
    "the dashed envelope around zero is the minimum detectable effect at 80% power. No "
    "point's 95% confidence interval excludes zero in the direction that favours "
    "recalibrating at any size from 1 to 16 local participants; the dashed envelope is "
    "shown for context, not as a significance threshold."
)
NEW = (
    "the dashed curves show each refit's own method-specific minimum detectable effect "
    "envelope at 80% power. No point's 95% confidence interval excludes zero in the "
    "direction that favours recalibrating at any size from 1 to 16 local participants; "
    "the dashed curves are shown for context, not as significance thresholds."
)

for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(OLD)
    assert count == 1, f"{path}: expected 1, found {count}"
    path.write_text(text.replace(OLD, NEW))
    print(f"{path}: Figure 6 caption fixed")
```

Run with `/tmp/calib_venv/bin/python`.

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
grep -c "the dashed envelope around zero" manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md
```
Expected: `PARITY: IDENTICAL`; both grep counts 0.

- [ ] **Step 3: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md
git commit -m "fix: describe Figure 6's two method-specific MDE envelopes, not one shared curve

The minimum-detectable-effect envelope is drawn once per refit, in
that refit's own colour, not as one shared curve. The caption's
singular phrasing did not reflect this."
```

---

### Task 6: Rebuild and re-verify the entire submission packet (controller-executed)

**Files:**
- Rebuild: `1_Cover_Letter`, `2_Response_to_Reviewers`, `3_Manuscript_CLEAN`,
  `4_Manuscript_HIGHLIGHTED` `.docx`/`.pdf`/`.portal.pdf` in the packet directory. The
  supplement and TRIPOD checklist are unchanged by this plan and do not need rebuilding.
- Rewrite: `0_README.md` in the packet directory.

**Interfaces:**
- Consumes: every file touched by Tasks 1-5 (must all be committed first).
- Produces: the round-5-corrected packet.

**Ruling (recorded in advance, matching every prior round):** executed directly by the
controller, not dispatched — it needs `mcp__word-docx__convert_to_pdf`, which only the
controller holds, and it is integration work with no benefit from a fresh perspective.

- [ ] **Step 1: Confirm all five tasks are committed and the test suite is unaffected**

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration"
git log --oneline -5
git status --porcelain
/tmp/calib_venv/bin/python -m pytest tests/ -q
```
Expected: 5 new commits, clean tree (aside from any untracked plan/spec docs), 235 passed /
1 deselected (unchanged).

- [ ] **Step 2: Rebuild the four affected docx files**

```bash
P="/Volumes/Extreme SSD/Mimic-IV/_submission_ready/study_bigp3_als_calibration/REVISION_R1_JNE-111284"
A="/Volumes/Extreme SSD/Mimic-IV/_pub_assets"
F="gfm+superscript+raw_attribute+attributes+bracketed_spans"
R="$A/reference_cmu.docx"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" manuscript/manuscript_expanded.md -o "$P/3_Manuscript_CLEAN.docx" --resource-path="manuscript:.:output/expanded/figures" --reference-doc="$R"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" manuscript/manuscript_highlighted.md -o "$P/4_Manuscript_HIGHLIGHTED.docx" --resource-path="manuscript:.:output/expanded/figures" --reference-doc="$R"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" manuscript/response_to_reviewers_jne_r1.md -o "$P/2_Response_to_Reviewers.docx" --reference-doc="$R"
pandoc -f "gfm+superscript+raw_attribute+attributes" manuscript/cover_letter_jne_r1.md -o "$P/1_Cover_Letter.docx" --reference-doc="$R"
for f in 1_Cover_Letter 2_Response_to_Reviewers 3_Manuscript_CLEAN 4_Manuscript_HIGHLIGHTED; do
  /usr/bin/python3 "$A/fix_docx_tables.py" "$P/$f.docx"
done
```

- [ ] **Step 3: Convert to PDF and portal PDF**

Call `mcp__word-docx__convert_to_pdf` on each of the four docx files. Then:

```bash
cd "$P" && bash "/Volumes/Extreme SSD/Mimic-IV/_pub_assets/make_portal_pdf.sh" \
  1_Cover_Letter.docx 2_Response_to_Reviewers.docx 3_Manuscript_CLEAN.docx 4_Manuscript_HIGHLIGHTED.docx
```

- [ ] **Step 4: Re-run the clean-vs-highlighted PDF text diff**

```bash
cd "$P"
diff <(pdftotext 3_Manuscript_CLEAN.pdf -) <(pdftotext 4_Manuscript_HIGHLIGHTED.pdf -)
```
Expected: no output.

- [ ] **Step 5: Verify each fix landed in the actual rendered PDF text**

```bash
cd "$P"
pdftotext 2_Response_to_Reviewers.pdf - | grep -A1 "Intercept only"  | head -20
pdftotext 2_Response_to_Reviewers.pdf - | grep -c "There is no crossing point"
pdftotext 3_Manuscript_CLEAN.pdf - | grep -c "removes what a cohort's recording chain shares"
pdftotext 3_Manuscript_CLEAN.pdf - | grep -ci "method-specific minimum detectable effect"
pdftotext 1_Cover_Letter.pdf - | grep -c "restored a usable transported mapping"
```
Expected: the response table renders the corrected MAE cells (allow for PDF cell-wrap
splitting numbers across lines the way prior rounds' rebuilds saw — check by eye if a grep
returns fewer matches than expected); "There is no crossing point" count 0; "removes what a
cohort's recording chain shares" count 0 in the manuscript; the method-specific-envelope
phrase present at least once; the cover letter's new sentence present.

- [ ] **Step 6: Rewrite `0_README.md`**

Update: (a) add a short new subsection for this round's 6 fixes, referencing this plan's
task numbers, in the same style as prior rounds' sections; (b) note explicitly that the
cover letter's signature line was NOT changed and why (per
[[no-signing-on-users-behalf]]), so this is visible to the human without them having to ask
again; (c) refresh the cover letter's page/word count in the file table if it changed.

- [ ] **Step 7: Final test run and commit**

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration"
/tmp/calib_venv/bin/python -m pytest tests/ -q
git status --porcelain
```
The README lives outside this git repository under `_submission_ready/`, so this repo's
tree should have nothing new to commit beyond what Tasks 1-5 already committed.

- [ ] **Step 8: Report to the user**

Summarize which of the 6 findings were fixed, explicitly restate that the signature line
was deliberately left as a placeholder and why, and confirm the packet is otherwise
unchanged in scope (no new analyses, matching the reviewer's own recommendation not to add
any).
