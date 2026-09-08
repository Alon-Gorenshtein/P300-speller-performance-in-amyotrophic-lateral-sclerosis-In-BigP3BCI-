# JNE-111284 R1 packet round-6 consistency fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the 4 confirmed wording findings (L2-L5) from a sixth external adversarial
review of the JNE-111284 revision packet, rebuild and re-verify the submission packet.

**Architecture:** Four text-fix tasks plus one controller-executed rebuild, run in sequence.

**Tech Stack:** Python 3.11 via `/tmp/calib_venv/bin/python`; pandoc + `_pub_assets/colwidths.lua`
+ `_pub_assets/fix_docx_tables.py` + `mcp__word-docx__convert_to_pdf` +
`_pub_assets/make_portal_pdf.sh` for the packet rebuild.

**Spec:** `docs/superpowers/specs/2026-09-08-jne-r1-round6-fixes.md`

## Global Constraints

- Python interpreter: `/tmp/calib_venv/bin/python`, always by full path.
- Every substitution via a script asserting `text.count(old) == 1` before replacing, per
  file, per string. All OLD strings below were pre-verified `count() == 1` in the live
  files immediately before this plan was written.
- `manuscript/manuscript_expanded.md` and `manuscript/manuscript_highlighted.md` must
  remain byte-identical once every `[...]{.mark}` span in the highlighted copy is stripped
  (regex: `\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}` → group 1). Verify after Task 1.
- Zero em dashes introduced.
- No change to any frozen numeric result, CSV, JSON, or test file. This plan is entirely
  prose rewording.
- Do not change the cover letter's signature line ("[Authors] on behalf of the authors")
  and do not touch the title. Both are deliberate — see the spec's own notes. If any task's
  diff touches either, that is a defect to flag, not a fix to make.
- Commit as normal commits with plain, simple messages — no internal process jargon (no
  "round 6", "L1"-style finding IDs, etc.) and no `Co-Authored-By`/session-link trailers.
- Rebuild scope this round includes the supplement (`5_Supplement.docx/.pdf/.portal.pdf`)
  in addition to the response and both manuscript copies, since Task 4 edits
  `supplementary/supplement_expanded.md`.

---

### Task 1: Soften the recalibration mechanism paragraph's two categorical clauses

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""L2: the paragraph's opening sentence and one later clause are categorical ('tracks
participants rather than trials', 'is why the instability tracks participant count rather
than selection count'), in tension with the paragraph's own final sentence (added in the
prior round), which says the design does not independently vary participant count and
selection count and so cannot itself isolate which one is causally binding. Soften both
categorical clauses to match; change no number, no citation, no other sentence."""
from pathlib import Path

OPEN_OLD = "The failure tracks participants rather than trials."
OPEN_NEW = (
    "The observed instability appears to track participant count more closely than "
    "character-selection count."
)

CLAUSE_OLD = (
    "which is why the instability tracks participant count rather than selection count"
)
CLAUSE_NEW = (
    "which helps explain why instability decreased as participant count increased"
)

for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    c1 = text.count(OPEN_OLD)
    assert c1 == 1, f"{path} [opening sentence]: expected 1, found {c1}"
    text = text.replace(OPEN_OLD, OPEN_NEW)
    c2 = text.count(CLAUSE_OLD)
    assert c2 == 1, f"{path} [later clause]: expected 1, found {c2}"
    text = text.replace(CLAUSE_OLD, CLAUSE_NEW)
    path.write_text(text)
    print(f"{path}: both categorical clauses softened")
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
grep -c "The failure tracks participants rather than trials" manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md
grep -c "is why the instability tracks participant count rather than selection count" manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md
```
Expected: `PARITY: IDENTICAL`; all four grep counts 0.

- [ ] **Step 3: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md
git commit -m "fix: soften two categorical clauses that overstated what a single unreplicated design shows

The recalibration mechanism paragraph opened with a categorical
claim and repeated it mid-paragraph, in tension with its own closing
sentence noting the design varies participant count without
independently varying selection count. Softened both clauses to
match; no number or citation changed."
```

---

### Task 2: Reword the response's "bounded" language around minimum detectable effects

**Files:**
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""L3: 'bounded' describes what a 95% CI does to compatible effects, not what an 80%-power
minimum detectable effect (MDE) does to a null result. The response already correctly says,
in the same sentences, that smaller improvements could have gone undetected -- a power
statement. Reword all three instances to describe reporting the MDE, not bounding the null."""
from pathlib import Path

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
text = RESPONSE.read_text()

S1_OLD = (
    "We also report what the study could have detected, so that this null is bounded "
    "rather than merely absent."
)
S1_NEW = (
    "We also report the minimum detectable effect so that the power of the analysis to "
    "detect improvement is explicit."
)
c = text.count(S1_OLD)
assert c == 1, f"S1: expected 1, found {c}"
text = text.replace(S1_OLD, S1_NEW)

S2_OLD = (
    "We are aware that a null of this kind is only useful if it is bounded, so we report "
    "the minimum detectable effect at 80% power alongside it"
)
S2_NEW = (
    "Because a null result is most informative when its precision and power are made "
    "explicit, we report the minimum detectable effect at 80% power alongside it"
)
c = text.count(S2_OLD)
assert c == 1, f"S2: expected 1, found {c}"
text = text.replace(S2_OLD, S2_NEW)

S3_OLD = "bounded that null by reporting minimum detectable effects at 80% power"
S3_NEW = (
    "reported minimum detectable effects at 80% power to quantify the magnitude of "
    "improvement the analysis was powered to detect"
)
c = text.count(S3_OLD)
assert c == 1, f"S3: expected 1, found {c}"
text = text.replace(S3_OLD, S3_NEW)

RESPONSE.write_text(text)
print("response: all 3 'bounded' instances reworded")
```

Run with `/tmp/calib_venv/bin/python`.

- [ ] **Step 2: Verify**

```bash
grep -c "bounded" manuscript/response_to_reviewers_jne_r1.md
grep -n "minimum detectable effect so that the power\|most informative when its precision and power\|reported minimum detectable effects at 80% power to quantify" manuscript/response_to_reviewers_jne_r1.md
```
Expected: first count 0; all three new phrases present.

- [ ] **Step 3: Commit**

```bash
git add manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: describe what a minimum detectable effect does, not a confidence interval's bound

'Bounded' described what a 95% CI does to compatible effects, not
what reporting an 80%-power minimum detectable effect does to a
null result. Reworded all three instances to describe the actual
power statement, matching what the surrounding sentences already
say."
```

---

### Task 3: Scope two categorical claims in the response's alignment discussion

**Files:**
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: nothing from other tasks (Task 2 already committed its own separate edits in
  this same file; verified no overlap with this task's OLD strings).
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""L4: two overclaims. (1) The opening executive summary says no alignment or nonlinear
method restores transportability -- a universal claim, when 4 alignment specifications and
2 nonlinear decoders were tested; the response's own later, more careful framing already
scopes this correctly. (2) 'The result is negative, and uniformly so' precedes a table
showing two Euclidean Alignment arms improving pooled MAE and downstream AUC relative to
the primary arm, which the response itself discusses two paragraphs later. Scope both to
what the evidence actually establishes."""
from pathlib import Path

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
text = RESPONSE.read_text()

SUMMARY_OLD = "No alignment method restores transportability. No nonlinear decision boundary restores it."
SUMMARY_NEW = "None of the alignment specifications tested restored transportability. Neither nonlinear decision boundary tested restored it."
c = text.count(SUMMARY_OLD)
assert c == 1, f"executive summary: expected 1, found {c}"
text = text.replace(SUMMARY_OLD, SUMMARY_NEW)

TABLE_LEADIN_OLD = "The result is negative, and uniformly so (PI denotes the 95% prediction interval in the table below):"
TABLE_LEADIN_NEW = "None of the specifications restored transportability; the full results are shown below (PI denotes the 95% prediction interval in the table below):"
c = text.count(TABLE_LEADIN_OLD)
assert c == 1, f"table lead-in: expected 1, found {c}"
text = text.replace(TABLE_LEADIN_OLD, TABLE_LEADIN_NEW)

RESPONSE.write_text(text)
print("response: both overclaims scoped")
```

Run with `/tmp/calib_venv/bin/python`.

- [ ] **Step 2: Verify**

```bash
grep -c "No alignment method restores transportability" manuscript/response_to_reviewers_jne_r1.md
grep -c "The result is negative, and uniformly so" manuscript/response_to_reviewers_jne_r1.md
grep -n "None of the alignment specifications tested restored\|None of the specifications restored transportability; the full results" manuscript/response_to_reviewers_jne_r1.md
```
Expected: first two counts 0; both new phrases present.

- [ ] **Step 3: Commit**

```bash
git add manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: scope two response claims to the specifications actually tested

The executive summary and the alignment-results lead-in both stated
universal or uniform claims (every alignment/nonlinear method; a
uniformly negative result) that the response's own later, more
careful discussion already narrows to what was actually tested and
found. Brought the two overclaiming sentences into line with the
response's own more careful text."
```

---

### Task 4: Remove "published" as a description of the pre-decision primary analysis

**Files:**
- Modify: `manuscript/response_to_reviewers_jne_r1.md`
- Modify: `supplementary/supplement_expanded.md`

**Interfaces:**
- Consumes: nothing from other tasks (verified no overlap with Tasks 2-3's OLD strings in
  the response file).
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""L5: 'published' inaccurately describes a not-yet-accepted primary analysis. 6 total
instances (4 in the response, 2 in the supplement) all refer to the same original/primary
analysis, none to an external already-published source. Reworded using 'previously
submitted' or 'primary-analysis' as fits each sentence. One supplement instance uses
'previously submitted values' rather than 'previously submitted primary values' specifically
to avoid an adjacent repetition of 'primary' next to 'The primary row reproduces...' --
a copy-editing judgment call, not a substantive deviation."""
from pathlib import Path

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
text = RESPONSE.read_text()

R1_OLD = "so every reported tau is directly comparable to the published values."
R1_NEW = "so every reported tau is directly comparable to the previously submitted primary values."
c = text.count(R1_OLD)
assert c == 1, f"response R1: expected 1, found {c}"
text = text.replace(R1_OLD, R1_NEW)

R2_OLD = "the tau it returns is directly comparable to the published tau of 0.432 for the slope and 0.873 for the intercept"
R2_NEW = "the tau it returns is directly comparable to the primary-analysis tau of 0.432 for the slope and 0.873 for the intercept"
c = text.count(R2_OLD)
assert c == 1, f"response R2: expected 1, found {c}"
text = text.replace(R2_OLD, R2_NEW)

R3_OLD = "reproduced the published values to thirteen significant digits, with per-cohort fits matching the published file to within 5.3e-15."
R3_NEW = "reproduced the previously submitted primary values to thirteen significant digits, with per-cohort fits matching the previously submitted output to within 5.3e-15."
c = text.count(R3_OLD)
assert c == 1, f"response R3: expected 1, found {c}"
text = text.replace(R3_OLD, R3_NEW)

RESPONSE.write_text(text)
print("response: all 4 'published' instances reworded")

SUPPLEMENT = Path("supplementary/supplement_expanded.md")
text = SUPPLEMENT.read_text()

S1_OLD = "The five published outputs named above are byte-identical to the submitted version"
S1_NEW = "The five primary-analysis outputs named above are byte-identical to the submitted version"
c = text.count(S1_OLD)
assert c == 1, f"supplement S1: expected 1, found {c}"
text = text.replace(S1_OLD, S1_NEW)

S2_OLD = "The primary row reproduces the published values to thirteen significant figures."
S2_NEW = "The primary row reproduces the previously submitted values to thirteen significant figures."
c = text.count(S2_OLD)
assert c == 1, f"supplement S2: expected 1, found {c}"
text = text.replace(S2_OLD, S2_NEW)

SUPPLEMENT.write_text(text)
print("supplement: both 'published' instances reworded")
```

Run with `/tmp/calib_venv/bin/python`.

- [ ] **Step 2: Verify**

```bash
grep -o "published [a-z]*" manuscript/response_to_reviewers_jne_r1.md supplementary/supplement_expanded.md
```
Expected: no output (0 remaining instances of "published X" in either file).

- [ ] **Step 3: Commit**

```bash
git add manuscript/response_to_reviewers_jne_r1.md supplementary/supplement_expanded.md
git commit -m "fix: stop describing the pre-decision primary analysis as 'published'

The manuscript is under review, not published. Reworded all six
instances (four in the response, two in the supplement) to
'previously submitted' or 'primary-analysis' as the sentence
requires."
```

---

### Task 5: Rebuild and re-verify the entire submission packet (controller-executed)

**Files:**
- Rebuild: `2_Response_to_Reviewers`, `3_Manuscript_CLEAN`, `4_Manuscript_HIGHLIGHTED`,
  `5_Supplement` `.docx`/`.pdf`/`.portal.pdf` in the packet directory. The cover letter and
  TRIPOD checklist are unchanged by this plan and do not need rebuilding.
- Rewrite: `0_README.md` in the packet directory.

**Interfaces:**
- Consumes: every file touched by Tasks 1-4 (must all be committed first).
- Produces: the round-6-corrected packet.

**Ruling (recorded in advance, matching every prior round):** executed directly by the
controller, not dispatched — it needs `mcp__word-docx__convert_to_pdf`, which only the
controller holds, and it is integration work with no benefit from a fresh perspective.

- [ ] **Step 1: Confirm all four tasks are committed and the test suite is unaffected**

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration"
git log --oneline -4
git status --porcelain
/tmp/calib_venv/bin/python -m pytest tests/ -q
```
Expected: 4 new commits, clean tree, 235 passed / 1 deselected (unchanged).

- [ ] **Step 2: Rebuild the four affected docx files**

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

Call `mcp__word-docx__convert_to_pdf` on each of the four docx files. Then:

```bash
cd "$P" && bash "/Volumes/Extreme SSD/Mimic-IV/_pub_assets/make_portal_pdf.sh" \
  2_Response_to_Reviewers.docx 3_Manuscript_CLEAN.docx 4_Manuscript_HIGHLIGHTED.docx 5_Supplement.docx
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
pdftotext 3_Manuscript_CLEAN.pdf - | grep -c "The failure tracks participants rather than trials"
pdftotext 3_Manuscript_CLEAN.pdf - | grep -i "track participant count more closely"
pdftotext 2_Response_to_Reviewers.pdf - | grep -c "bounded"
pdftotext 2_Response_to_Reviewers.pdf - | grep -c "No alignment method restores transportability"
pdftotext 2_Response_to_Reviewers.pdf - | grep -c "uniformly so"
pdftotext 2_Response_to_Reviewers.pdf - | grep -o "published [a-z]*"
pdftotext 5_Supplement.pdf - | grep -o "published [a-z]*"
```
Expected: first count 0; second present; "bounded" count 0; "No alignment method" count 0;
"uniformly so" count 0; both `published`-grep lines empty.

- [ ] **Step 6: Rewrite `0_README.md`**

Add a short new subsection for this round's 4 fixes (matching prior rounds' style), note
again that the cover letter's signature line and the title were both raised again and both
deliberately left unchanged, and refresh word/page counts for any file whose count changed.

- [ ] **Step 7: Final test run and commit**

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration"
/tmp/calib_venv/bin/python -m pytest tests/ -q
git status --porcelain
```
The README lives outside this git repository under `_submission_ready/`, so this repo's
tree should have nothing new to commit beyond what Tasks 1-4 already committed.

- [ ] **Step 8: Report to the user**

Summarize which of the 4 findings were fixed, restate that the signature line and the title
were both raised again and both deliberately left unchanged (and why), and confirm no new
analysis was run, matching this reviewer's own explicit recommendation.
