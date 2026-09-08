# JNE-111284 R1 packet — consistency fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix twelve verified consistency and completeness defects in the already-built JNE-111284 R1 revision packet — two orphaned figures, a code/text contradiction, an internal Discussion contradiction, a promised-but-missing artifact, two false claims in the response's own header/summary, two false "no participant-level data" overclaims, one scope overreach, one missing supplement metadata block, an under-answered reviewer literature request, and one terminology clarity gap — then rebuild every packet file from the corrected sources.

**Architecture:** All prose edits use the established script-based substitution pattern (Python script asserting each `old` string occurs exactly once per file, then replacing it) rather than hand editing, because five documents (`manuscript_expanded.md`, `manuscript_highlighted.md`, `response_to_reviewers_jne_r1.md`, `supplement_expanded.md`, `tripod_checklist.md`) must stay mutually consistent and any response block quote of edited manuscript text must be re-synced in the same task. The two figures require a small code change to `render_expanded.py` (label text and one legend handle, no numeric logic) followed by re-running the existing figure-render script and re-copying outputs into the submission packet. The final task rebuilds every `.docx`/`.pdf`/`.portal.pdf` in the packet using the pipeline already established in the prior pass (pandoc + `colwidths.lua` + `fix_docx_tables.py` + `make_portal_pdf.sh`).

**Tech Stack:** Python 3.11.14 (`/tmp/calib_venv/bin/python` — **never** a bare `python3`, see Global Constraints), pandas, matplotlib (via `render_expanded.py`), pandoc, LibreOffice/`soffice` (via the `mcp__word-docx__convert_to_pdf` tool), ghostscript (`make_portal_pdf.sh`).

**Spec:** `docs/superpowers/specs/2026-09-08-jne-r1-revision-consistency-fixes.md`

## Global Constraints

- Repository root for all paths below: `/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration`. Submission packet root: `/Volumes/Extreme SSD/Mimic-IV/_submission_ready/study_bigp3_als_calibration/REVISION_R1_JNE-111284`.
- Python interpreter: `/tmp/calib_venv/bin/python`, always by full path. Never `UV_PROJECT_ENVIRONMENT=... python3` (silently runs the system interpreter) and never a bare `python`/`python3`.
- No change to any frozen numeric result or to `heterogeneity.py`, `validation.py`, `alignment.py`, `recalibration.py`, or any `output/expanded/*.csv|json` file. `render_expanded.py` may only have its two label strings and one added legend handle changed (Task 6) — no numeric line changes anywhere in that file.
- Every prose substitution is applied by a Python script that asserts `text.count(old) == 1` before replacing, run with `/tmp/calib_venv/bin/python`. Never `sed`/`perl` in-place on these five files.
- `manuscript_expanded.md` and `manuscript_highlighted.md` must remain byte-identical once every `[...]{.mark}` span in the highlighted copy is stripped (regex: `\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}` → group 1). Any task that edits clean-manuscript text inside a currently-marked span, or adds new text that should be marked as a further revision, must mirror the same edit into the highlighted copy in the same task and verify parity before finishing.
- Any response (`response_to_reviewers_jne_r1.md`) block quote whose source paragraph is edited by this plan must be re-synced to the new text in the same task, not left for a later pass.
- Zero em dashes in any file this plan touches, except inside a reviewer's own verbatim quoted comment.
- Reference numbering: the two new references (Task 9) are appended as 41 and 42; no existing reference number changes.
- Table/section numbering in the supplement does not change in this plan (no new numbered table is added; Task 4's GBM disclosure is prose inside existing S12, not a new table).
- Figure numbering: Figure 5 = `figure_alignment_transport` (cited in "Alignment Did Not Restore Transportability"), Figure 6 = `figure_recalibration_curve` (cited in "What Local Recalibration Costs"). This is the manuscript's reading order and must be used consistently in captions, in-text citations, and the `scripts/13_render_figures.py` print summary.
- After Tasks 1–10 land, Task 11 rebuilds and re-verifies the entire packet. No task before Task 11 touches the packet directory except Task 6 (regenerated figure files only).

---

### Task 1: Fix the cohort-level Euclidean Alignment weighting description in the supplement

**Files:**
- Modify: `supplementary/supplement_expanded.md` (S12, the paragraph describing the two Euclidean Alignment reference choices)

**Interfaces:**
- Consumes: none (pure text fix; no other task depends on the exact wording here).
- Produces: none.

- [ ] **Step 1: Write and run the substitution script**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_ea_weighting.py`:

```python
"""F2: the supplement says 'participant-count-weighted'; the code
(src/bigp3_als/alignment.py:pooled_reference, called from
scripts/04b_extract_alignment_features.py:38 with n_epochs as the weight
array) is epoch-count-weighted, matching the manuscript and response. Fix
the supplement to agree with the code."""
from pathlib import Path

SUPPLEMENT = Path("supplementary/supplement_expanded.md")
OLD = (
    "and the cohort arm uses the participant-count-weighted mean of the session references "
    "within the source study, which removes a cohort-wide rather than a session-wide "
    "covariance offset."
)
NEW = (
    "and the cohort arm uses the epoch-count-weighted mean of the session references within "
    "the source study, which removes a cohort-wide rather than a session-wide covariance "
    "offset."
)
text = SUPPLEMENT.read_text()
count = text.count(OLD)
assert count == 1, f"expected 1 occurrence, found {count}"
SUPPLEMENT.write_text(text.replace(OLD, NEW))
print("fixed EA cohort-weighting description")
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_ea_weighting.py`

- [ ] **Step 2: Verify**

Run: `grep -n "participant-count-weighted\|epoch-count-weighted" supplementary/supplement_expanded.md`
Expected: only the `epoch-count-weighted` line appears; zero occurrences of `participant-count-weighted`.

- [ ] **Step 3: Commit**

```bash
git add supplementary/supplement_expanded.md
git commit -m "fix: correct supplement's EA cohort-reference weighting to match the code

pooled_reference (src/bigp3_als/alignment.py) is epoch-count-weighted,
called with n_epochs as the weight array. The manuscript and response
already said epoch count; the supplement alone said participant count.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 2: Fix the Discussion sentence that contradicts the recalibration finding

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`

**Interfaces:**
- Consumes: none.
- Produces: none. (No response quote reproduces this exact sentence — verified by grep in Task setup below — so no response re-sync is needed for this task.)

- [ ] **Step 1: Confirm no response quote needs re-syncing**

Run: `grep -n "is not supported without local recalibration" manuscript/response_to_reviewers_jne_r1.md`
Expected: no output. If this returns a match, stop and add a re-sync sub-step mirroring Task 5's pattern before proceeding.

- [ ] **Step 2: Write and run the substitution script**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_recalibration_contradiction.py`:

```python
"""F4: this sentence still says transport is usable 'without local recalibration',
which is what the pre-revision manuscript concluded. The revision's own new
finding (Results, 'What Local Recalibration Costs') is that local recalibration
did NOT reliably help at any size from 1 to 16 participants, and was
significantly harmful at 2-3. Apply identically to both manuscript copies so
they stay byte-identical once highlight marks are stripped."""
from pathlib import Path

OLD = (
    "Reporting expected accuracy in a cohort where the mapping was not developed is not "
    "supported without local recalibration, since the interval for a cohort outside this "
    "archive spans 0.032 to 0.254 for estimation error and includes chance-level "
    "discrimination and negative skill."
)
NEW = (
    "Reporting expected accuracy in a cohort where the mapping was not developed is not "
    "supported, since the interval for a cohort outside this archive spans 0.032 to 0.254 "
    "for estimation error and includes chance-level discrimination and negative skill. Local "
    "recalibration does not on its own repair this: the resampling analysis below found no "
    "sample size from 1 to 16 local participants at which recalibrating reliably improved on "
    "transporting the mapping unchanged (Results, What Local Recalibration Costs)."
)

for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(OLD)
    assert count == 1, f"{path}: expected 1 occurrence, found {count}"
    path.write_text(text.replace(OLD, NEW))
    print(f"{path}: fixed")
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_recalibration_contradiction.py`

- [ ] **Step 3: Verify clean/highlighted parity**

Run:
```bash
/tmp/calib_venv/bin/python -c "
import re
from pathlib import Path
h = Path('manuscript/manuscript_highlighted.md').read_text()
c = Path('manuscript/manuscript_expanded.md').read_text()
stripped = re.sub(r'\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}', r'\1', h)
print('IDENTICAL' if stripped == c else 'DIFFER')
"
```
Expected: `IDENTICAL`

- [ ] **Step 4: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md
git commit -m "fix: remove Discussion sentence contradicting the recalibration finding

'Not supported without local recalibration' told a reader the opposite
of what the new Results subsection found: recalibration did not reliably
help at any size from 1 to 16 local participants.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 3: Trim the Discussion's opening paragraph and re-sync the response's quote of it

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Write and run the substitution script**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_discussion_opening.py`:

```python
"""F5: the response claims (line 179) 'the first paragraph no longer re-lists
tau, its confidence interval and the slope range' -- false as the manuscript
stands. Trim the manuscript's opening Discussion paragraph to make the claim
true (these numbers are already given in Results, Transportability,
manuscript lines 202-204), and re-sync the response's own quote of the
surrounding Discussion text if it contains this passage."""
from pathlib import Path

OLD = (
    "A fitted mapping from that score to expected accuracy did not transport: the "
    "calibration intercept had tau = 0.87 (95% CI 0.60 to 1.51) and an unrepresented-cohort "
    "interval of -1.97 to 1.85 log-odds; slope heterogeneity gave the same conclusion, at "
    "tau = 0.43 (0.30 to 0.77) and a range of 0.185 to 2.185. One cohort was estimated less "
    "accurately than the development-mean benchmark, six less accurately than their own mean."
)
NEW = (
    "A fitted mapping from that score to expected accuracy did not transport, with "
    "substantial between-cohort variation in both the calibration intercept and the slope "
    "(Results, Transportability). One cohort was estimated less accurately than the "
    "development-mean benchmark, six less accurately than their own mean."
)

paths = [
    Path("manuscript/manuscript_expanded.md"),
    Path("manuscript/manuscript_highlighted.md"),
]
for path in paths:
    text = path.read_text()
    count = text.count(OLD)
    assert count == 1, f"{path}: expected 1 occurrence, found {count}"
    path.write_text(text.replace(OLD, NEW))
    print(f"{path}: trimmed")

response = Path("manuscript/response_to_reviewers_jne_r1.md")
text = response.read_text()
matches = text.count(OLD)
print(f"response quotes the old passage {matches} time(s)")
if matches:
    text = text.replace(OLD, NEW)
    response.write_text(text)
    print("response: re-synced")
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_discussion_opening.py`

If the response did not quote this exact passage (the printed count is 0), read the surrounding response text near the "no longer re-lists tau" claim (`grep -n "no longer re-lists" manuscript/response_to_reviewers_jne_r1.md`) and confirm by eye that no other block quote in the response still reproduces the old, untrimmed wording; if one does, apply the same OLD→NEW replacement to it by hand-editing the script and re-running.

- [ ] **Step 2: Verify parity and that the response's claim is now true**

Run:
```bash
/tmp/calib_venv/bin/python -c "
import re
from pathlib import Path
h = Path('manuscript/manuscript_highlighted.md').read_text()
c = Path('manuscript/manuscript_expanded.md').read_text()
stripped = re.sub(r'\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}', r'\1', h)
print('PARITY:', 'IDENTICAL' if stripped == c else 'DIFFER')
print('tau=0.87 still in Discussion opening:', 'tau = 0.87' in c.split('## Discussion',1)[1].split('That distinction',1)[0])
"
```
Expected: `PARITY: IDENTICAL` and `tau=0.87 still in Discussion opening: False`

- [ ] **Step 3: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: trim Discussion opening to make the response's own length claim true

The response said the first Discussion paragraph no longer re-lists tau,
its CI, and the slope range; it still did. The numbers are already in
Results (Transportability). Also serves Reviewer 1's length request.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 4: Fix the nonlinear "ceiling" overclaim and the "only quantity varying" self-contradiction, re-sync the response's quote, disclose the GBM correction honestly, and fix TRIPOD's "pre-specified" wording

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`
- Modify: `manuscript/response_to_reviewers_jne_r1.md`
- Modify: `supplementary/tripod_checklist.md`
- Modify: `supplementary/supplement_expanded.md` (S12: add the GBM initial/corrected disclosure as prose, no new table)

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Fix the "only quantity varying" claim in Methods**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_nonlinear_claims.py`:

```python
"""F6: 'the decision boundary is the only quantity varying' is contradicted two
sentences later, where the RBF arm's Nystroem approximation and the GBM arm's
PCA reduction are described -- both are representation changes, not purely
decision-boundary changes. F7 (part 1): the researcher-degrees-of-freedom
paragraph says the nonlinear specifications were 'fixed before being run',
which the response itself contradicts by disclosing a post-hoc GBM
correction. Fix both, on both manuscript copies."""
from pathlib import Path

METHODS_OLD = (
    "Two nonlinear calibration decoders were evaluated on the same epochs, through the same "
    "grouped cross-validation, and scored by the same metric, so that the decision boundary "
    "is the only quantity varying."
)
METHODS_NEW = (
    "Two nonlinear calibration decoders were evaluated on identical epochs, fold assignments "
    "and evaluation metric, with each decoder's feature transformation fitted entirely within "
    "the training fold."
)

CEILING_OLD = (
    "The agreement between two structurally unrelated nonlinear families to within 0.0001 "
    "indicates a ceiling imposed by these data rather than a property of one modelling choice."
)
CEILING_NEW = (
    "The close agreement between two structurally unrelated nonlinear families indicates that "
    "this result is not an artifact of either family's particular modelling choice, though it "
    "does not on its own establish a performance ceiling imposed by the data."
)

RDF_OLD = (
    "The moderator tests are Holm-corrected across the ten descriptors, and the alignment and "
    "nonlinear specifications were each fixed before being run."
)
RDF_NEW = (
    "The moderator tests are Holm-corrected across the ten descriptors. The alignment "
    "specifications were fixed before being run. One nonlinear specification was not: the "
    "gradient-boosted arm's initial run lacked the class rebalancing and the retained-variance "
    "target its comparators used, and was corrected before any transportability analysis used "
    "the column, moving its mean discriminability from 0.655 to 0.714 (supplement, S12)."
)

paths = [
    Path("manuscript/manuscript_expanded.md"),
    Path("manuscript/manuscript_highlighted.md"),
]
for path in paths:
    text = path.read_text()
    for old, new, label in (
        (METHODS_OLD, METHODS_NEW, "methods-only-quantity"),
        (CEILING_OLD, CEILING_NEW, "ceiling"),
        (RDF_OLD, RDF_NEW, "rdf"),
    ):
        count = text.count(old)
        assert count == 1, f"{path} [{label}]: expected 1 occurrence, found {count}"
        text = text.replace(old, new)
    path.write_text(text)
    print(f"{path}: 3 fixes applied")

response = Path("manuscript/response_to_reviewers_jne_r1.md")
text = response.read_text()
for old, new, label in (
    (CEILING_OLD, CEILING_NEW, "response ceiling quote"),
):
    count = text.count(old)
    print(f"response contains [{label}] {count} time(s)")
    if count:
        text = text.replace(old, new)
response.write_text(text)
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_nonlinear_claims.py`

If the response's block quote at line ~250 (the "A nonlinear decision boundary did not account for the result..." quote) contains `METHODS_OLD` rather than `CEILING_OLD`, extend the script with that replacement too — read the current text with `sed -n '246,262p' manuscript/response_to_reviewers_jne_r1.md` first to confirm exactly which of the two changed sentences the quote reproduces (it may contain neither, both, or one).

- [ ] **Step 2: Add the GBM disclosure to the supplement and fix TRIPOD's "pre-specified" wording**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_gbm_disclosure.py`:

```python
"""F7 (parts 2-3): TRIPOD called model updating a 'pre-specified secondary
analysis' -- wrong, since local recalibration was added at the reviewers'
request during revision, and the phrase invites the same objection as the
manuscript's now-fixed 'fixed before being run'. The response promises the
initial/corrected GBM values live in a 'supplementary analysis log' that was
never built; add that disclosure as prose inside supplement S12 (no new
table number) and adjust the response to point at it."""
from pathlib import Path

TRIPOD = Path("supplementary/tripod_checklist.md")
TRIPOD_OLD = (
    "Model updating is evaluated separately as a pre-specified secondary analysis rather than "
    "used to produce the reported performance"
)
TRIPOD_NEW = (
    "Model updating was added during revision at the reviewers' request and is evaluated "
    "separately, not used to produce the reported performance"
)
text = TRIPOD.read_text()
count = text.count(TRIPOD_OLD)
assert count == 1, f"TRIPOD: expected 1 occurrence, found {count}"
TRIPOD.write_text(text.replace(TRIPOD_OLD, TRIPOD_NEW))
print("TRIPOD: fixed")

SUPPLEMENT = Path("supplementary/supplement_expanded.md")
ANCHOR = (
    "The number of retained components was set from measured retained variance rather than "
    "matched to the kernel approximation's component count, which is a different quantity."
)
DISCLOSURE = (
    "\n\nThe gradient-boosted arm's configuration was corrected after its first result was "
    "seen, before any transportability analysis used the column: its initial run lacked the "
    "class rebalancing the other arms carry and retained fewer principal components than the "
    "measured-variance criterion above specifies. The correction moved its mean "
    "cross-validated discriminability from 0.655 to 0.714, that is, it made the arm's "
    "discrimination better and its contrast with the linear decoder smaller, and the "
    "corrected value is the one reported throughout this paper and the one that agrees with "
    "the independently specified kernel arm."
)
text = SUPPLEMENT.read_text()
count = text.count(ANCHOR)
assert count == 1, f"supplement: expected 1 occurrence of anchor, found {count}"
text = text.replace(ANCHOR, ANCHOR + DISCLOSURE)
SUPPLEMENT.write_text(text)
print("supplement S12: GBM disclosure added")

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
RESPONSE_OLD = (
    "We report the change, and both the initial and corrected values, in the supplementary "
    "analysis log."
)
RESPONSE_NEW = (
    "We report the change, and both the initial and corrected values, in the Supplement (S12) "
    "and in the manuscript's account of researcher degrees of freedom (Discussion)."
)
text = RESPONSE.read_text()
count = text.count(RESPONSE_OLD)
assert count == 1, f"response: expected 1 occurrence, found {count}"
RESPONSE.write_text(text.replace(RESPONSE_OLD, RESPONSE_NEW))
print("response: pointer fixed")
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_gbm_disclosure.py`

- [ ] **Step 3: Verify parity and that no false artifact reference remains**

Run:
```bash
/tmp/calib_venv/bin/python -c "
import re
from pathlib import Path
h = Path('manuscript/manuscript_highlighted.md').read_text()
c = Path('manuscript/manuscript_expanded.md').read_text()
stripped = re.sub(r'\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}', r'\1', h)
print('PARITY:', 'IDENTICAL' if stripped == c else 'DIFFER')
"
grep -rn "supplementary analysis log\|pre-specified secondary analysis" manuscript/ supplementary/
```
Expected: `PARITY: IDENTICAL`; the grep returns no output (both phrases fully removed).

- [ ] **Step 4: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md supplementary/tripod_checklist.md supplementary/supplement_expanded.md
git commit -m "fix: nonlinear ceiling overclaim, fixed-before-run contradiction, and orphaned log reference

Two models agreeing does not on its own establish a data-imposed
performance ceiling; softened. 'Only quantity varying' was contradicted
two sentences later by the RBF/GBM representation changes. The
researcher-degrees-of-freedom paragraph said both nonlinear arms were
fixed before running, contradicting the response's own disclosure of a
post-hoc GBM correction; the correction is now disclosed in the
manuscript and in supplement S12, where the response's promised
'supplementary analysis log' now actually points. TRIPOD's
'pre-specified secondary analysis' for model updating was wrong on the
same grounds and is corrected.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 5: Fix the response's header title and its false "shortened" claim

**Files:**
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Write and run the substitution script**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_response_header.py`:

```python
"""F8: the response's own header still carries the pre-revision title, and its
executive-summary bullet says 'the main text was shortened' when the net
change is 6,601 -> 8,628 words (a ~2,000-word increase; only the
estimator-agreement material was actually removed)."""
from pathlib import Path

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
text = RESPONSE.read_text()

TITLE_OLD = (
    "**Calibration-derived decoder discriminability is associated with online P300-speller "
    "accuracy, but the fitted mapping does not transport across cohorts**"
)
TITLE_NEW = (
    "**The calibration-to-accuracy mapping in P300 spellers does not transport across "
    "cohorts, and was not restored by tested alignment or local recalibration**"
)
count = text.count(TITLE_OLD)
assert count == 1, f"title: expected 1 occurrence, found {count}"
text = text.replace(TITLE_OLD, TITLE_NEW)

LENGTH_OLD = (
    "- **Length.** The main text was shortened; the clustered-sandwich-versus-bootstrap "
    "estimator comparison was moved to the Supplement, as Reviewer 1 suggested."
)
LENGTH_NEW = (
    "- **Length.** Redundant statistics were removed from the Discussion and the "
    "clustered-sandwich-versus-bootstrap estimator comparison was moved to the Supplement, as "
    "Reviewer 1 suggested; the three new analyses the reviewers requested increased the net "
    "main-text length from approximately 6,600 to 8,600 words."
)
count = text.count(LENGTH_OLD)
assert count == 1, f"length bullet: expected 1 occurrence, found {count}"
text = text.replace(LENGTH_OLD, LENGTH_NEW)

RESPONSE.write_text(text)
print("response header and length bullet fixed")
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_response_header.py`

Note: `TITLE_NEW` here uses the milder alternative title from the spec's downgraded point 10 discussion, not the packet's current drafted title. This keeps the response internally consistent with whichever title the corresponding author ultimately picks being a small further edit rather than a mismatch; if the author confirms the original drafted title unchanged, re-run this substitution with the original wording instead before the final packet rebuild (Task 11) — flag this explicitly when reporting Task 5 complete.

- [ ] **Step 2: Verify**

Run: `sed -n '1,5p' manuscript/response_to_reviewers_jne_r1.md`
Expected: header no longer contains "but the fitted mapping does not transport across cohorts" as a leading independent clause without the alignment/recalibration finding.

Run: `grep -n "the main text was shortened" manuscript/response_to_reviewers_jne_r1.md`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: response header carried the old title; 'main text was shortened' was false

The header still showed the pre-revision title while the body proposed
the new one. The length bullet claimed shortening when the net change
was a ~2,000-word increase.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 6: Embed the two new figures, fix their legend/label defects, and regenerate them

**Files:**
- Modify: `src/bigp3_als/render_expanded.py` (two label strings, one added legend handle — no numeric logic)
- Modify: `scripts/13_render_figures.py` (print-summary text only, to match the figure numbering this task assigns)
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`
- Regenerate: `output/expanded/figures/figure_alignment_transport.{png,pdf}`, `figure_recalibration_curve.{png,pdf}`

**Interfaces:**
- Consumes: `output/expanded/alignment_transport.csv`, `output/expanded/recalibration_summary_balanced.csv` (unchanged, frozen).
- Produces: two embedded, numbered figures (Figure 5, Figure 6) with accurate legends, cited in their Results subsections.

- [ ] **Step 1: Fix the misleading role label and add the missing MDE legend entry in `render_expanded.py`**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_figure_labels.py`. Both substitutions below were checked against the current file and each occurs exactly once; `ax.legend(loc="lower right", frameon=False, fontsize=9)` alone occurs **twice** in this file (once in this function, once in another figure function), which is why edit 2 matches a much longer, unique block rather than that one line in isolation.

```python
"""F3: 'EEG re-alignment' labels a bucket that contains two score-space arms
(cohort_z, cohort_rank) which never touch the EEG signal. Also give the
+-MDE dashed envelope a legend entry -- it is drawn but never labelled, so a
reader sees an unexplained dashed line. No numeric logic changes in either
edit."""
from pathlib import Path

RENDER = Path("src/bigp3_als/render_expanded.py")
text = RENDER.read_text()

LABEL_OLD = '"alignment": {"color": OTHER_COLOR, "hatch": "//", "label": "EEG re-alignment"},'
LABEL_NEW = '"alignment": {"color": OTHER_COLOR, "hatch": "//", "label": "Signal or score alignment"},'
count = text.count(LABEL_OLD)
assert count == 1, f"role label: expected 1 occurrence, found {count}"
text = text.replace(LABEL_OLD, LABEL_NEW)

COMMENT_OLD = (
    "# Left-to-right reading order the brief specifies: the primary score, then the four EEG\n"
    "# re-alignment variants, then the two nonlinear re-scorings."
)
COMMENT_NEW = (
    "# Left-to-right reading order the brief specifies: the primary score, then the four\n"
    "# alignment variants (two on the signal, two on the score), then the two nonlinear\n"
    "# re-scorings."
)
count = text.count(COMMENT_OLD)
assert count == 1, f"role comment: expected 1 occurrence, found {count}"
text = text.replace(COMMENT_OLD, COMMENT_NEW)

TAIL_OLD = '''    ax.set_xticks(range(len(ticks)))
    tick_labels = [
        f"{n}\\n{int(selections_by_n[n])} sel\\n"
        f"{'/'.join(str(c) for c in sorted(contributing_by_n[n]))} cohorts"
        for n in ticks
    ]
    ax.set_xticklabels(tick_labels, fontsize=8)
    ax.set_xlim(-0.5, len(ticks) - 0.5)

    ax.set_xlabel("Local participants used for recalibration")
    ax.set_ylabel("MAE improvement over the transported mapping\\n(cohort mean, 95% CI)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    _save(fig, directory, "figure_recalibration_curve")'''
TAIL_NEW = '''    ax.set_xticks(range(len(ticks)))
    tick_labels = [
        f"{n}\\n{int(selections_by_n[n])} sel\\n"
        f"{'/'.join(str(c) for c in sorted(contributing_by_n[n]))} cohorts"
        for n in ticks
    ]
    ax.set_xticklabels(tick_labels, fontsize=8)
    ax.set_xlim(-0.5, len(ticks) - 0.5)

    ax.set_xlabel("Local participants used for recalibration")
    ax.set_ylabel("MAE improvement over the transported mapping\\n(cohort mean, 95% CI)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    mde_handle = plt.Line2D(
        [], [], color=LABEL_COLOR, linestyle="--", linewidth=1.0, alpha=0.7,
        label="Minimum detectable effect (80% power)",
    )
    handles, labels = ax.get_legend_handles_labels()
    handles.append(mde_handle)
    labels.append(mde_handle.get_label())
    ax.legend(handles, labels, loc="lower right", frameon=False, fontsize=9)
    _save(fig, directory, "figure_recalibration_curve")'''
count = text.count(TAIL_OLD)
assert count == 1, f"function tail: expected 1 occurrence, found {count}"
text = text.replace(TAIL_OLD, TAIL_NEW)

RENDER.write_text(text)
print("render_expanded.py: 3 edits applied")
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_figure_labels.py`

`plt` and `LABEL_COLOR` are already imported/defined at module level in this file (used elsewhere in the same function and module) — no new import is needed.

- [ ] **Step 2: Regenerate the figures and confirm nothing else moved**

Run: `cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration" && /tmp/calib_venv/bin/python scripts/13_render_figures.py`

Verify the run prints all 8 figure lines with no error, and that the four other figures' files did not change (they are pure functions of unchanged CSVs and unchanged code, but confirm no accidental edit elsewhere in the file touched them):

```bash
git status --porcelain output/expanded/figures/
git diff --stat output/expanded/figures/ | grep -v "figure_alignment_transport\|figure_recalibration_curve"
```
Expected: the second command prints nothing (only the two intended figures changed).

- [ ] **Step 3: Fix the print-summary text in `scripts/13_render_figures.py` to match this task's numbering**

```python
# before
print("  figure_recalibration_curve       Figure 5 (recalibration cost, balanced ladder)")
print("  figure_alignment_transport       Figure 6 (EEG re-alignment does not repair transport)")
# after
print("  figure_alignment_transport       Figure 5 (alignment does not repair transport)")
print("  figure_recalibration_curve       Figure 6 (recalibration cost, balanced ladder)")
```

- [ ] **Step 4: Embed Figure 5 in the manuscript's Alignment subsection**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/embed_figure5.py`:

```python
"""F3: figure_alignment_transport exists and is described at length in the
response but is cited and embedded nowhere. Insert it, with a caption, at
the end of the 'Alignment Did Not Restore Transportability' subsection."""
from pathlib import Path

ANCHOR = (
    "far too wide for a site to act on a transported calibration."
)
INSERTION = (
    "\n\n**Figure 5. Each alignment and nonlinear arm's between-cohort heterogeneity against "
    "the primary arm's own value.** Panel a is the calibration intercept tau, panel b the "
    "slope tau; the dashed line is the primary arm's value from Figure 1. Bars are grouped by "
    "role (primary, alignment, nonlinear) and labelled by arm; the pooled mean absolute error "
    "for each arm is annotated beside its bar. No alignment or nonlinear arm falls to the left "
    "of the primary arm's dashed line on either panel.\n\n"
    "![](../output/expanded/figures/figure_alignment_transport.png){width=100%}"
)

paths = [
    Path("manuscript/manuscript_expanded.md"),
    Path("manuscript/manuscript_highlighted.md"),
]
for path in paths:
    text = path.read_text()
    count = text.count(ANCHOR)
    assert count == 1, f"{path}: expected 1 occurrence of anchor, found {count}"
    text = text.replace(ANCHOR, ANCHOR + INSERTION)
    path.write_text(text)
    print(f"{path}: Figure 5 embedded")
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/embed_figure5.py`

Then cite it from the subsection's opening sentence (Task 2 already changed part of this area — re-check with `grep -n "No re-alignment specification restored transportability" manuscript/manuscript_expanded.md` before editing to get the current exact text):

```python
from pathlib import Path
OLD = "No re-alignment specification restored transportability (supplement, S12; Tables S13 and S14)."
NEW = "No re-alignment specification restored transportability (Figure 5; supplement, S12; Tables S13 and S14)."
for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(OLD)
    assert count == 1, f"{path}: expected 1 occurrence, found {count}"
    path.write_text(text.replace(OLD, NEW))
```

- [ ] **Step 5: Embed Figure 6 in the manuscript's recalibration subsection**

Same pattern, anchored on the paragraph that ends the "What Local Recalibration Costs" subsection (re-check exact current text first, since Task 2 edited a sentence in this subsection's opening — the anchor below targets the subsection's *last* paragraph, on MDE, which Task 2/4 do not touch):

```python
from pathlib import Path

ANCHOR = "against a transported error of 0.089 to 0.093. Improvements of that size or larger are excluded; smaller ones are not."
INSERTION = (
    "\n\n**Figure 6. Paired improvement in mean absolute error from local recalibration, "
    "against zero, on the composition-balanced ladder.** Points are the cohort-mean paired "
    "improvement with 95% confidence interval at each local sample size, for the "
    "intercept-only and the intercept-and-slope refit; the dashed envelope around zero is the "
    "minimum detectable effect at 80% power. No point's interval clears the envelope in the "
    "direction that favours recalibrating at any size from 1 to 16 local participants.\n\n"
    "![](../output/expanded/figures/figure_recalibration_curve.png){width=88%}"
)
for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(ANCHOR)
    assert count == 1, f"{path}: expected 1 occurrence, found {count}"
    path.write_text(text.replace(ANCHOR, ANCHOR + INSERTION))
```

Then cite it from the subsection's opening sentence (re-check exact current text after Task 2's edit before writing the assertion — search `grep -n "did not reliably improve on transporting the fitted mapping"`):

```python
from pathlib import Path
OLD = "at any local sample size this archive can evaluate (supplement, S13; Tables S17 to S20)."
NEW = "at any local sample size this archive can evaluate (Figure 6; supplement, S13; Tables S17 to S20)."
for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(OLD)
    assert count == 1, f"{path}: expected 1 occurrence, found {count}"
    path.write_text(text.replace(OLD, NEW))
```

- [ ] **Step 6: Verify figures are embedded, numbered correctly, and parity holds**

Run:
```bash
grep -n "Figure 5\|Figure 6\|figure_alignment_transport.png\|figure_recalibration_curve.png" manuscript/manuscript_expanded.md
/tmp/calib_venv/bin/python -c "
import re
from pathlib import Path
h = Path('manuscript/manuscript_highlighted.md').read_text()
c = Path('manuscript/manuscript_expanded.md').read_text()
stripped = re.sub(r'\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}', r'\1', h)
print('PARITY:', 'IDENTICAL' if stripped == c else 'DIFFER')
"
```
Expected: two caption lines, two citation lines, two image-embed lines (4 matches total, or more if the citation and caption fall on lines matched twice — inspect by eye); `PARITY: IDENTICAL`.

- [ ] **Step 7: Run the full test suite to confirm the render_expanded.py edit broke nothing**

Run: `cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration" && /tmp/calib_venv/bin/python -m pytest tests/ -x -q`
Expected: 235 passed (same count as before this plan — this task adds no test and changes no numeric logic).

- [ ] **Step 8: Commit**

```bash
git add src/bigp3_als/render_expanded.py scripts/13_render_figures.py manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md output/expanded/figures/figure_alignment_transport.png output/expanded/figures/figure_alignment_transport.pdf output/expanded/figures/figure_recalibration_curve.png output/expanded/figures/figure_recalibration_curve.pdf
git commit -m "fix: embed the two revision figures, which existed but were cited nowhere

figure_alignment_transport and figure_recalibration_curve were built,
described at length in the response, and copied into the submission
packet, but never embedded or cited in the manuscript. Added as Figure
5 and Figure 6 with captions, cited from their Results subsections.
Also fixed the alignment figure's legend, which called a bucket
containing two score-space arms 'EEG re-alignment', and added a
missing legend entry for the recalibration figure's minimum-detectable-
effect envelope, which was drawn but never labelled.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 7: Fix the two "no participant-level clinical characteristics" overclaims

**Files:**
- Modify: `supplementary/tripod_checklist.md`
- Modify: `supplementary/supplement_expanded.md` (S14, Transparency statement)

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Write and run the substitution script**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_als_participant_level.py`:

```python
"""F9: alsfrs_r is extracted per study_participant_id (src/bigp3_als/edf.py,
validation.py:284) -- it is a participant-level clinical characteristic,
available for a subset of participants in 3 of 18 cohorts. Both TRIPOD 13b
and Supplement S14 currently claim none exists for any cohort. The
manuscript's own Discussion (line 332) already states the precise fact;
bring these two into line with it."""
from pathlib import Path

TRIPOD = Path("supplementary/tripod_checklist.md")
TRIPOD_OLD = (
    "No participant-level clinical characteristics are available in the archive for any "
    "cohort, which is stated as a limitation rather than left implicit (Discussion, Study "
    "Limitations)"
)
TRIPOD_NEW = (
    "An ALSFRS-R score, a participant-level clinical characteristic, is available for a "
    "subset of participants in 3 of 18 cohorts (138 records); no other participant-level "
    "clinical characteristic is available for any cohort, and no cohort carries disease "
    "duration, stage, or bulbar-versus-limb onset. This is stated as a limitation rather than "
    "left implicit (Discussion, Study Limitations)"
)
text = TRIPOD.read_text()
count = text.count(TRIPOD_OLD)
assert count == 1, f"TRIPOD: expected 1 occurrence, found {count}"
TRIPOD.write_text(text.replace(TRIPOD_OLD, TRIPOD_NEW))
print("TRIPOD 13b fixed")

SUPPLEMENT = Path("supplementary/supplement_expanded.md")
SUPPLEMENT_OLD = (
    "Four source studies carry a documented ALS population; the remaining cohorts are "
    "described as other cohorts because the documentation does not support a positive "
    "characterisation, and no participant-level clinical characteristics were available."
)
SUPPLEMENT_NEW = (
    "Four source studies carry a documented ALS population; the remaining cohorts are "
    "described as other cohorts because the documentation does not support a positive "
    "characterisation. An ALSFRS-R score, a participant-level clinical characteristic, is "
    "available for a subset of participants in 3 of those 18 cohorts; no other "
    "participant-level clinical characteristic is available for any cohort."
)
text = SUPPLEMENT.read_text()
count = text.count(SUPPLEMENT_OLD)
assert count == 1, f"supplement: expected 1 occurrence, found {count}"
SUPPLEMENT.write_text(text.replace(SUPPLEMENT_OLD, SUPPLEMENT_NEW))
print("supplement S14 fixed")
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_als_participant_level.py`

- [ ] **Step 2: Verify**

Run: `grep -rn "no participant-level clinical characteristics were available\|No participant-level clinical characteristics are available in the archive for any cohort" supplementary/`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add supplementary/tripod_checklist.md supplementary/supplement_expanded.md
git commit -m "fix: TRIPOD and Transparency statement overclaimed no participant-level clinical data

alsfrs_r is extracted per study_participant_id and is available for a
subset of participants in 3 of 18 cohorts -- a participant-level
characteristic. Both files said none existed for any cohort; the
manuscript's own Discussion already had the precise version.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 8: Soften the archive-homogenisation overreach

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Write and run the substitution script**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_homogenization_overreach.py`:

```python
"""F10: BigP3BCI imposes a *shared* montage/amplifier across every source
study, so there is no independent amplifier/montage variation anywhere in
the archive for Euclidean Alignment to have acted on. The EA-cohort arm's
null result is real evidence that within-archive covariance differences do
not explain the residual heterogeneity; it cannot establish what a
genuinely independent deployment's hardware difference (a source of
variation absent from this archive by construction) would contribute."""
from pathlib import Path

OLD = (
    "The between-cohort variation reported in this study is therefore a lower bound on what a "
    "site encountering a genuinely independent cohort should expect, and the failure of the "
    "mapping to transport is if anything understated. The alignment analyses bear on this "
    "directly: cohort-level Euclidean Alignment removes what a cohort's recording chain "
    "shares, which is the class of difference the archive has already suppressed, and it did "
    "not reduce between-cohort heterogeneity (Results, Alignment Did Not Restore "
    "Transportability). The residual spread is therefore not of the kind that an amplifier or "
    "montage difference would contribute."
)
NEW = (
    "Because BigP3BCI suppresses several technical sources of between-site variation, the "
    "heterogeneity reported here likely understates what a site encountering a genuinely "
    "independent cohort should expect; the mapping's failure to transport is if anything "
    "understated rather than overstated. What this archive can quantify is narrower: "
    "cohort-level Euclidean Alignment removes what a cohort's recording chain shares, which is "
    "the class of covariance difference the archive's shared hardware could still leave behind "
    "within its own harmonisation, and it did not reduce between-cohort heterogeneity (Results, "
    "Alignment Did Not Restore Transportability). Within the harmonised archive, that class of "
    "covariance difference does not explain the residual spread; what an independent site's "
    "amplifier or montage would additionally contribute is a source of variation this archive "
    "does not contain and cannot quantify."
)

paths = [
    Path("manuscript/manuscript_expanded.md"),
    Path("manuscript/manuscript_highlighted.md"),
]
for path in paths:
    text = path.read_text()
    count = text.count(OLD)
    assert count == 1, f"{path}: expected 1 occurrence, found {count}"
    path.write_text(text.replace(OLD, NEW))
    print(f"{path}: softened")

response = Path("manuscript/response_to_reviewers_jne_r1.md")
text = response.read_text()
count = text.count(OLD)
print(f"response contains this passage {count} time(s)")
if count:
    response.write_text(text.replace(OLD, NEW))
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_homogenization_overreach.py`

- [ ] **Step 2: Verify parity**

Run:
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
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: soften archive-homogenisation claim beyond what the EA-cohort result supports

The manuscript concluded residual heterogeneity is 'not of the kind
that an amplifier or montage difference would contribute'. BigP3BCI has
no independent amplifier/montage variation for Euclidean Alignment to
have acted on, so the EA-cohort null result cannot establish what a
genuinely independent deployment's hardware difference would
contribute -- only that within-archive covariance differences do not
explain the residual spread.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 9: Add a supplement title/description block, add the "supervised recalibration" clarification, and add the two recent-literature citations

**Files:**
- Modify: `supplementary/supplement_expanded.md`
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`

**Interfaces:**
- Consumes: none.
- Produces: reference numbers 41, 42 (new; no existing number changes).

- [ ] **Step 1: Add the supplement title/description block**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_supplement_and_lit.py`:

```python
"""F11: JNE's supplementary-file instructions require a title and a <=30-word
description; the supplement currently opens with a bare heading and no
description. F14: 'local calibration set' does not make explicit that the
refit is supervised (uses observed online outcomes, not just the P300
calibration block). F13: add two verified, on-topic recent citations
(Mowla 2020, Khan 2023) that Reviewer 2's request for recent
performance-prediction literature is currently under-served by."""
from pathlib import Path

SUPPLEMENT = Path("supplementary/supplement_expanded.md")
OLD = "# Supplementary material\n\n## S1. Data provenance"
NEW = (
    "# Supplementary material\n\n"
    "**Description:** Methods detail, sensitivity analyses, reproducibility, data-alignment "
    "and nonlinear-decoder analyses, and local-recalibration resampling analyses.\n\n"
    "## S1. Data provenance"
)
text = SUPPLEMENT.read_text()
count = text.count(OLD)
assert count == 1, f"supplement heading: expected 1 occurrence, found {count}"
SUPPLEMENT.write_text(text.replace(OLD, NEW))
print("supplement title/description added")

SUPERVISED_OLD = (
    "For each of nine local sample sizes from 1 to 16 participants, participants were drawn "
    "without replacement as a local calibration set, the mapping was refitted on them alone, "
    "and the refit was evaluated on the participants not drawn, with at least three retained "
    "for evaluation."
)
SUPERVISED_NEW = (
    "For each of nine local sample sizes from 1 to 16 participants, participants were drawn "
    "without replacement as a local set; refitting the mapping on them is a supervised "
    "procedure, using both their calibration-derived score and their observed online "
    "selection accuracy, and the refit was evaluated on the participants not drawn, with at "
    "least three retained for evaluation."
)
for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(SUPERVISED_OLD)
    assert count == 1, f"{path}: expected 1 occurrence, found {count}"
    path.write_text(text.replace(SUPERVISED_OLD, SUPERVISED_NEW))
    print(f"{path}: supervised clarification added")

LIT_OLD = (
    "A projected-accuracy measure and a separate multi-feature predictor have made related "
    "within-session or within-study predictions.[37,38]"
)
LIT_NEW = (
    "A projected-accuracy measure and a separate multi-feature predictor have made related "
    "within-session or within-study predictions,[37,38] and more recent work has compared "
    "linear and nonlinear classifiers, including for P300-speller accuracy specifically, for "
    "this same prediction task.[41,42]"
)
for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(LIT_OLD)
    assert count == 1, f"{path}: expected 1 occurrence, found {count}"
    path.write_text(text.replace(LIT_OLD, LIT_NEW))
    print(f"{path}: literature citations added")

REF_ANCHOR = (
    "40. He H, Wu D. Transfer learning for brain-computer interfaces: a Euclidean space data "
    "alignment approach. *IEEE Trans Biomed Eng*. 2020;67(2):399-410. "
    "doi:10.1109/TBME.2019.2913914"
)
REF_ADDITION = (
    "\n41. Mowla MR, Gonzalez-Morales JD, Rico-Martinez J, Ulichnie DA, Thompson DE. A "
    "comparison of classification techniques to predict brain-computer interfaces accuracy "
    "using classifier-based latency estimation. *Brain Sci*. 2020;10(10):734. "
    "doi:10.3390/brainsci10100734\n"
    "42. Khan NN, Sweet T, Harvey CA, Warschausky S, Huggins JE, Thompson DE. P300-based "
    "brain-computer interface speller performance estimation with classifier-based latency "
    "estimation. *J Vis Exp*. 2023;(199):e64959. doi:10.3791/64959"
)
for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(REF_ANCHOR)
    assert count == 1, f"{path}: expected 1 occurrence of reference 40, found {count}"
    path.write_text(text.replace(REF_ANCHOR, REF_ANCHOR + REF_ADDITION))
    print(f"{path}: references 41-42 added")
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_supplement_and_lit.py`

- [ ] **Step 2: Verify**

Run:
```bash
grep -n "^\*\*Description:\*\*" supplementary/supplement_expanded.md
grep -n "\[41,42\]\|^41\.\|^42\." manuscript/manuscript_expanded.md
/tmp/calib_venv/bin/python -c "
import re
from pathlib import Path
h = Path('manuscript/manuscript_highlighted.md').read_text()
c = Path('manuscript/manuscript_expanded.md').read_text()
stripped = re.sub(r'\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}', r'\1', h)
print('PARITY:', 'IDENTICAL' if stripped == c else 'DIFFER')
"
```
Expected: description line found; citation and both new reference entries found; `PARITY: IDENTICAL`.

- [ ] **Step 3: Commit**

```bash
git add supplementary/supplement_expanded.md manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md
git commit -m "fix: add supplement title/description, clarify supervised recalibration, cite recent literature

JNE requires supplementary files to carry a title and <=30-word
description; added. 'Local calibration set' could be misread as
needing only the unsupervised P300 calibration block; clarified that
the refit also uses observed online accuracy. Reviewer 2 asked for
more recent calibration/performance-prediction literature; added two
verified, directly on-topic 2020 and 2023 citations.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 10: Add the two major-revision findings to the Abstract, and precise the "positive in all 18 cohorts" claim

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Write and run the substitution script**

Create `/private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_abstract.py`:

```python
"""F12: the title is entirely about alignment and local recalibration not
repairing transport, but the Abstract's Main Results and Significance never
mention either analysis -- a reader of the Abstract alone would not learn
either headline finding. Also precise 'positive in all 18 cohorts' to match
the more careful wording the Results body already uses (manuscript line
159: 'point estimate was positive in all 18... several ... imprecise')."""
from pathlib import Path

MAIN_RESULTS_OLD = (
    "The association was positive in all 18 cohorts but varied widely in magnitude and "
    "precision (Pearson r 0.190 to 0.928; participant-level r = 0.714, p < 0.001). Pooled "
    "estimation error was 0.098 (95% CI 0.091 to 0.107) against a benchmark of 0.146. "
    "Calibration did not transport: the intercept had tau 0.87, with a 95% interval for an "
    "unrepresented cohort of -1.97 to 1.85 on the log-odds scale, and the slope varied more "
    "than tenfold across cohorts (tau 0.43, unrepresented-cohort interval 0.111 to 2.005). A "
    "protocol proxy for the stopping rule, median time per selection, reduced the "
    "between-cohort slope variance by 66%. The four ALS cohorts alone gave an uncorrected "
    "between-cohort slope spread of 0.223, against 0.560 overall."
)
MAIN_RESULTS_NEW = (
    "The point estimate of the association was positive in all 18 cohorts but varied widely "
    "in magnitude and precision, and its confidence interval excluded zero in 12 of the 18 "
    "(Pearson r 0.190 to 0.928; participant-level r = 0.714, p < 0.001). Pooled estimation "
    "error was 0.098 (95% CI 0.091 to 0.107) against a benchmark of 0.146. Calibration did not "
    "transport: the intercept had tau 0.87, with a 95% interval for an unrepresented cohort of "
    "-1.97 to 1.85 on the log-odds scale, and the slope varied more than tenfold across "
    "cohorts (tau 0.43, unrepresented-cohort interval 0.111 to 2.005). Neither signal- nor "
    "score-space alignment, nor either of two nonlinear decision boundaries, reduced this "
    "heterogeneity. Local recalibration using up to 16 participants did not reliably improve "
    "estimation error over the transported mapping; refitting both the intercept and slope was "
    "significantly worse than transporting at the smallest sample sizes. A protocol proxy for "
    "the stopping rule, median time per selection, reduced the between-cohort slope variance "
    "by 66%. The four ALS cohorts alone gave an uncorrected between-cohort slope spread of "
    "0.223, against 0.560 overall."
)
text = Path("manuscript/manuscript_expanded.md").read_text()
count = text.count(MAIN_RESULTS_OLD)
assert count == 1, f"manuscript: expected 1 occurrence, found {count}"

paths = [
    Path("manuscript/manuscript_expanded.md"),
    Path("manuscript/manuscript_highlighted.md"),
]
for path in paths:
    text = path.read_text()
    count = text.count(MAIN_RESULTS_OLD)
    assert count == 1, f"{path}: expected 1 occurrence, found {count}"
    path.write_text(text.replace(MAIN_RESULTS_OLD, MAIN_RESULTS_NEW))
    print(f"{path}: Abstract Main Results expanded")
```

Run: `/tmp/calib_venv/bin/python /private/tmp/claude-503/-Volumes-Extreme-SSD-Mimic-IV/ab1a847c-1d40-4123-9d2f-596d211c1c0d/scratchpad/fix_abstract.py`

Before running, confirm "confidence interval excluded zero in 12 of the 18" is the correct count: the manuscript Results already states "the 95% confidence interval included zero in 6 of the 18 cohorts" (line 156) — 18 minus 6 is 12; this substitution derives its number from that existing, already-verified sentence rather than a new computation, so no new arithmetic needs independent checking here, only that 18 - 6 = 12 is applied correctly.

- [ ] **Step 2: Verify parity and word count**

Run:
```bash
/tmp/calib_venv/bin/python -c "
import re
from pathlib import Path
h = Path('manuscript/manuscript_highlighted.md').read_text()
c = Path('manuscript/manuscript_expanded.md').read_text()
stripped = re.sub(r'\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}', r'\1', h)
print('PARITY:', 'IDENTICAL' if stripped == c else 'DIFFER')
abstract = c.split('## Abstract',1)[1].split('## Introduction',1)[0]
print('Abstract word count (approx, includes headings):', len(abstract.split()))
"
```
Expected: `PARITY: IDENTICAL`. Note the Abstract word count for later reference in Task 11's README update — JNE's usual structured-abstract limit is checked against this number, minus the four section-heading words (Objective/Approach/Main Results/Significance), when the packet README is refreshed.

- [ ] **Step 3: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md
git commit -m "fix: add the two major-revision findings to the Abstract

The title is built entirely on alignment and local recalibration not
repairing transport, but neither appeared in Main Results or
Significance. A reader of the Abstract alone would not learn either
headline finding. Also precised 'positive in all 18 cohorts' to match
the more careful point-estimate wording already used in the Results
body.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 11: Rebuild and re-verify the entire submission packet; refresh the README; report the GitHub blocker

**Files:**
- Rebuild: all `.docx`/`.pdf`/`.portal.pdf` files in `_submission_ready/study_bigp3_als_calibration/REVISION_R1_JNE-111284/`
- Rewrite: `_submission_ready/study_bigp3_als_calibration/REVISION_R1_JNE-111284/0_README.md`

**Interfaces:**
- Consumes: every file touched by Tasks 1–10 (must all be committed first).
- Produces: the final packet, ready for the corresponding author to review, confirm the title, and push to GitHub.

- [ ] **Step 1: Confirm all prior tasks are committed**

Run: `cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration" && git log --oneline -12 && git status --porcelain`
Expected: 10 new commits from Tasks 1–10 (this task's own changes are not yet made) and a clean working tree (no uncommitted changes from earlier tasks).

- [ ] **Step 2: Rebuild every docx with the established pipeline**

Run (adjust the packet path/venv path if they differ from the prior pass — confirm both exist first with `ls`):

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration"
P="/Volumes/Extreme SSD/Mimic-IV/_submission_ready/study_bigp3_als_calibration/REVISION_R1_JNE-111284"
A="/Volumes/Extreme SSD/Mimic-IV/_pub_assets"
F="gfm+superscript+raw_attribute+attributes+bracketed_spans"
R="$A/reference_cmu.docx"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" supplementary/supplement_expanded.md -o "$P/5_Supplement.docx" --resource-path="supplementary:.:output/expanded/figures" --reference-doc="$R"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" supplementary/tripod_checklist.md -o "$P/6_TRIPOD_Checklist.docx" --reference-doc="$R"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" manuscript/response_to_reviewers_jne_r1.md -o "$P/2_Response_to_Reviewers.docx" --reference-doc="$R"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" manuscript/manuscript_expanded.md -o "$P/3_Manuscript_CLEAN.docx" --resource-path="manuscript:.:output/expanded/figures" --reference-doc="$R"
pandoc -f "$F" --lua-filter="$A/colwidths.lua" manuscript/manuscript_highlighted.md -o "$P/4_Manuscript_HIGHLIGHTED.docx" --resource-path="manuscript:.:output/expanded/figures" --reference-doc="$R"
for f in 2_Response_to_Reviewers 3_Manuscript_CLEAN 4_Manuscript_HIGHLIGHTED 5_Supplement 6_TRIPOD_Checklist; do
  /usr/bin/python3 "$A/fix_docx_tables.py" "$P/$f.docx"
done
```

- [ ] **Step 3: Convert every docx to PDF (via the word-docx MCP `convert_to_pdf` tool, one call per file) and then to portal-safe PDF**

For each of `3_Manuscript_CLEAN.docx`, `4_Manuscript_HIGHLIGHTED.docx`, `5_Supplement.docx`, `6_TRIPOD_Checklist.docx`, `2_Response_to_Reviewers.docx`: call `mcp__word-docx__convert_to_pdf` with `filename` set to the full path inside `$P`.

Then:
```bash
cd "$P"
bash "/Volumes/Extreme SSD/Mimic-IV/_pub_assets/make_portal_pdf.sh" \
  3_Manuscript_CLEAN.docx 4_Manuscript_HIGHLIGHTED.docx 5_Supplement.docx \
  6_TRIPOD_Checklist.docx 2_Response_to_Reviewers.docx \
  Figures/figure_alignment_transport.pdf Figures/figure_recalibration_curve.pdf
```
(Re-copy the two figure PDFs from `output/expanded/figures/` into `$P/Figures/` first if Task 6 regenerated them and the packet copy is now stale — diff the two directories to check.)

- [ ] **Step 4: Verify the rebuild**

```bash
cd "$P"
for f in *.pdf; do [[ "$f" == *.portal.pdf ]] && continue; printf "%-32s %s pages\n" "$f" "$(pdfinfo "$f" | awk '/^Pages/{print $2}')"; done
diff <(pdftotext 3_Manuscript_CLEAN.pdf -) <(pdftotext 4_Manuscript_HIGHLIGHTED.pdf -) >/dev/null && echo "CLEAN/HIGHLIGHTED PDF TEXT IDENTICAL" || echo "PDF TEXT DIFFERS"
grep -n "Figure 5\|Figure 6" <(pdftotext 3_Manuscript_CLEAN.pdf -)
grep -n "Description:" <(pdftotext 5_Supplement.pdf -)
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
Expected: page counts reported for all five; `CLEAN/HIGHLIGHTED PDF TEXT IDENTICAL`; at least one "Figure 5" and one "Figure 6" match in the clean PDF text; the supplement's description line found; the clean manuscript's `images` count is now 6 (4 original + 2 new), the highlighted copy's `images` count also 6, and both `yellow` counts unchanged from the prior pass unless a Task above added new marked spans (Tasks 1–10 in this plan generally trim or fix existing text rather than add new revision markers — confirm the exact expected yellow count by counting `[...]{.mark}` spans in `manuscript_highlighted.md` directly with `grep -o` before comparing, since this plan does not itself add new `{.mark}` spans and the count should equal whatever it was after the prior pass).

- [ ] **Step 5: Visually inspect the two new figure pages and the supplement's new description line**

Render the pages containing Figure 5 and Figure 6 in the clean PDF with `pdftoppm -f <page> -l <page> -r 100 -png 3_Manuscript_CLEAN.pdf <scratch-prefix>` (find the page numbers from the `grep -n` output in Step 4, converting the pdftotext line number to a page via the same `awk 'BEGIN{p=1} /\f/{p++} ...'` pattern used throughout this project), then view each rendered PNG with the Read tool to confirm the figure renders, the legend text is the corrected "Signal or score alignment" / "Minimum detectable effect (80% power)" wording, and the caption text matches what was embedded in Task 6.

- [ ] **Step 6: Rewrite `0_README.md`**

Update the packet README to: (a) remove or update any prior-pass verification claims that are now superseded (word counts, figure counts, table counts — recompute from the Step 4 output rather than copying old numbers); (b) add a new top section, "Fixes applied in this pass," listing the 12 items from this plan in one line each, referencing the Task numbers; (c) add a prominent, first-priority item under Human-only: **"Push the repository to GitHub before submitting."** State plainly that the public repository at the URL named in the Data Availability statement does not yet contain the revision's scripts, outputs, or figures, that this session has no push credentials or configured remote, and that `git log` in this working tree already has every commit needed — the only remaining step is `git push`; (d) keep the title-confirmation block from the prior README, updated only if Task 5's title substitution changed which title currently appears in the response versus the manuscript (reconcile these — see the Task 5 note about re-running with the original title if the author has not chosen the milder alternative); (e) update the "What is ready" table with the new word counts, table counts, and figure counts from Step 4.

- [ ] **Step 7: Final full-repository test run**

Run: `cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration" && /tmp/calib_venv/bin/python -m pytest tests/ -q`
Expected: 235 passed (unchanged from before this plan).

- [ ] **Step 8: Commit the README and any regenerated packet files that live inside the repository (the figures already committed in Task 6; the packet directory itself is outside this git repository and is not committed here — confirm with `git status` that only README-adjacent or in-repo files remain to stage)**

```bash
git add -A
git status
git commit -m "docs: rebuild the R1 submission packet after the consistency-fix pass

Rebuilds all five docx/pdf/portal-pdf files from the corrected sources
and refreshes the packet README with the fixes applied in this pass
and the outstanding GitHub-push blocker.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```
(If `git status` shows nothing to commit inside the repository — because the packet lives entirely under `_submission_ready/`, outside this repo — skip the commit and note in the final report that only the packet directory changed, with no corresponding in-repo commit needed.)

- [ ] **Step 9: Report to the user**

Summarize: which of the 12 findings were fixed, the two downgraded external-review points and why, the exact Task-5 title caveat (this plan drafted a milder title into the response header as a placeholder — flag this explicitly, since the corresponding author has not yet confirmed any title), and the GitHub-push blocker in one clear sentence with no hedging.
