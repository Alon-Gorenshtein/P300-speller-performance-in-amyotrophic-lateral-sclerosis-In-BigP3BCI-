# JNE-111284 R1 packet round-4 consistency fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the 10 confirmed findings (H1-H10) from a fourth external adversarial review
of the JNE-111284 revision packet, rebuild and re-verify the submission packet.

**Architecture:** Six tasks. Five are pure text substitutions across
`manuscript/manuscript_expanded.md`, `manuscript/manuscript_highlighted.md`,
`manuscript/response_to_reviewers_jne_r1.md`, and `supplementary/supplement_expanded.md`,
grouped by which paragraph/topic they touch so no two tasks in flight ever touch the same
file at the same time. The sixth is a controller-executed rebuild (same reasoning as round
2's Ruling T11-1 and round 3's Task 7: it needs `mcp__word-docx__convert_to_pdf`, which
only the controller holds, and it is integration work with no benefit from a fresh
perspective).

**Tech Stack:** Python 3.11 via `/tmp/calib_venv/bin/python`; pandoc + `_pub_assets/colwidths.lua`
+ `_pub_assets/fix_docx_tables.py` + `mcp__word-docx__convert_to_pdf` +
`_pub_assets/make_portal_pdf.sh` for the packet rebuild.

**Spec:** `docs/superpowers/specs/2026-09-08-jne-r1-round4-fixes.md`

## Global Constraints

- Python interpreter: `/tmp/calib_venv/bin/python`, always by full path.
- Every substitution via a script asserting `text.count(old) == 1` before replacing, per
  file, per string. All OLD strings below were pre-verified `count() == 1` in the live
  files immediately before this plan was written.
- Do NOT modify `src/bigp3_als/features.py` or `src/bigp3_als/recalibration.py` — read-only
  references for H1 and H9's exact numbers.
- `manuscript/manuscript_expanded.md` and `manuscript/manuscript_highlighted.md` must
  remain byte-identical once every `[...]{.mark}` span in the highlighted copy is stripped
  (regex: `\[((?:[^\[\]]|\[[^\]]*\])*)\]\{\.mark\}` → group 1). Verify after every task that
  touches either file.
- Zero em dashes introduced.
- No change to any frozen numeric result, CSV, JSON, or test file. This plan touches no
  code or test file; the baseline test count (235 passed, 1 deselected) must not change.
- Commit message trailer, every task:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5
  ```

---

### Task 1: Fix the recalibration mechanism paragraph (H1)

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""H1: the Results, highlighted copy, and response's own paraphrase all claim the
calibration score is "constant within a participant" and that two local participants
therefore give "two distinct points." Verified false for about a third of participants by
querying output/expanded/external_validation_predictions.csv directly (filtered to
model == "calibration_auc"): 271 distinct study_participant_id values, of which 89 have 2
to 6 DISTINCT predicted_probability values (i.e. multiple sessions with different scores),
summing to exactly 410 -- the manuscript's own "410 distinct predictor values" figure.
src/bigp3_als/recalibration.py's recalibration_draws does not collapse a drawn participant
to one point; it passes every row (session) that participant contributed. The fix corrects
the mechanism description without changing any reported number (24.1%, MDE values, tau
values are all untouched)."""
from pathlib import Path

MANUSCRIPT_OLD = (
    "The failure is one of participants rather than of trials. The calibration score is "
    "constant within a participant, so a refit of two parameters on two local "
    "participants fits a line through two distinct points; at two local participants "
    "24.1% of draws returned a negative recalibrated slope (supplement, Table S21), a "
    "mapping in which higher estimated accuracy implies lower observed accuracy. "
    "Collecting more character selections from the same people does not relieve this."
)
MANUSCRIPT_NEW = (
    "The failure tracks participants rather than trials. The calibration score is defined "
    "at the session level (Methods), so a local sample of participants supplies at least "
    "as many distinct predictor values as participants drawn, and often only that many, "
    "since most participants in this archive (182 of 271) contribute a single recorded "
    "session; a refit of two parameters on a local sample this small is consequently fit "
    "on very few distinct points, and at two local participants 24.1% of draws returned a "
    "negative recalibrated slope (supplement, Table S21), a mapping in which higher "
    "estimated accuracy implies lower observed accuracy. Additional character selections "
    "within an already-drawn session add weight at that session's existing predictor "
    "value rather than a new one, so they do not relieve this; drawing participants with "
    "additional recorded sessions would supply new predictor values, which is why the "
    "instability tracks participant count rather than selection count."
)

for path in (Path("manuscript/manuscript_expanded.md"), Path("manuscript/manuscript_highlighted.md")):
    text = path.read_text()
    count = text.count(MANUSCRIPT_OLD)
    assert count == 1, f"{path}: expected 1, found {count}"
    path.write_text(text.replace(MANUSCRIPT_OLD, MANUSCRIPT_NEW))
    print(f"{path}: mechanism paragraph fixed")

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
RESPONSE_OLD = (
    "The mechanism is worth stating because it answers the reviewer's question about "
    "subjects versus trials. The calibration score is constant within a participant, so a "
    "refit of two parameters on two local participants is a line fitted through two "
    "distinct points. At two local participants, 24.1% of draws returned a *negative* "
    "recalibrated slope, that is, a mapping in which higher predicted accuracy implies "
    "lower observed accuracy. The binding constraint is the number of participants, not "
    "the number of character selections; collecting more selections from the same two "
    "people does not help."
)
RESPONSE_NEW = (
    "The mechanism is worth stating because it answers the reviewer's question about "
    "subjects versus trials. The calibration score is defined at the session level "
    "(Methods), and most participants in this archive contribute a single recorded "
    "session, so a local sample of two participants is typically, though not always, a "
    "refit on two distinct points. At two local participants, 24.1% of draws returned a "
    "*negative* recalibrated slope, that is, a mapping in which higher predicted accuracy "
    "implies lower observed accuracy. The binding constraint is the number of distinct "
    "session-level predictor values a local sample supplies, which tracks participant "
    "count far more than character-selection count: additional selections within an "
    "already-drawn session do not add a new predictor value, though drawing a participant "
    "with additional sessions would."
)
text = RESPONSE.read_text()
count = text.count(RESPONSE_OLD)
assert count == 1, f"response: expected 1, found {count}"
RESPONSE.write_text(text.replace(RESPONSE_OLD, RESPONSE_NEW))
print("response: mechanism paraphrase fixed")
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
grep -c "constant within a participant" manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
```
Expected: `PARITY: IDENTICAL`; all three grep counts 0.

Also confirm no reported number changed: `grep -c "24.1%" manuscript/manuscript_expanded.md manuscript/response_to_reviewers_jne_r1.md` must still find the figure (once each, inside the rewritten sentence).

- [ ] **Step 3: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: correct the recalibration mechanism's session-vs-participant claim

The Results, highlighted copy, and response's own paraphrase all
claimed the calibration score is constant within a participant,
used to justify a "two participants equals two points" mechanism
for recalibration instability. Verified false by querying the
actual predictions CSV directly: 89 of 271 participants have 2 to
6 distinct session-level scores, summing to exactly 410, the
manuscript's own distinct-predictor-value count. The analysis
itself is unaffected (the code never collapses a participant to
one point); only the prose description of the mechanism was wrong.
No reported number changes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 2: Fix the heterogeneity-contradiction sentence and all three AUC-conflation instances (H2, H6)

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""H6: "Both aligned scores discriminated marginally better" / "carry a marginally better
score" cites character-level AUC (0.756/0.753 vs 0.748, a downstream quantity) as evidence
of a better SCORE, but "the score" and "discriminated" are this paper's own defined terms
for calibration-block discriminability, which the response itself separately and correctly
reports as 0.801/0.802 against 0.805 (essentially unchanged). These exact figures are
already tabulated in Supplement Table S15's own caption (0.8046/0.8005/0.8021), so citing
them here is not new content. Three instances: one shared verbatim between the manuscript
and a response block quote, two independent in the response's own prose.
H2: "Between-cohort heterogeneity did not fall" immediately precedes "lowered slope tau,"
reading as self-contradictory on first pass (flagged independently by two reviewers across
rounds 3 and 4, though ruled defensible-as-is twice before). Fix only the opening clause;
the following specification-robustness sentence is untouched."""
from pathlib import Path

# H6, instance 1: shared between manuscript_expanded, manuscript_highlighted, and the
# response's verbatim block quote of this Results paragraph.
AUC_OLD = (
    "Both aligned scores discriminated marginally better than the unaligned one "
    "(character-level AUC 0.756 and 0.753 against 0.748) and accordingly produced a "
    "marginally lower pooled estimation error (0.095 and 0.097 against 0.098), which is "
    "what a better score produces rather than evidence that the mapping was repaired."
)
AUC_NEW = (
    "Both alignment arms yielded marginally higher downstream character-level AUC (0.756 "
    "and 0.753 against 0.748) and a marginally lower pooled estimation error (0.095 and "
    "0.097 against 0.098), despite calibration-block discriminability that was "
    "essentially unchanged (0.801 and 0.802 against 0.805; supplement, Table S15); a "
    "downstream improvement of this kind is not evidence that the mapping was repaired."
)

# H2: the sentence immediately preceding AUC_OLD/AUC_NEW in the same paragraph.
HET_OLD = (
    "Between-cohort heterogeneity did not fall: slope tau was 0.419 and 0.461 against "
    "0.432, and intercept tau 0.922 and 0.941 against 0.873."
)
HET_NEW = (
    "Overall calibration heterogeneity was not meaningfully repaired, even though "
    "session-level alignment's slope tau moved slightly in the favourable direction: "
    "slope tau was 0.419 and 0.461 against 0.432, and intercept tau 0.922 and 0.941 "
    "against 0.873."
)

for path in (
    Path("manuscript/manuscript_expanded.md"),
    Path("manuscript/manuscript_highlighted.md"),
    Path("manuscript/response_to_reviewers_jne_r1.md"),
):
    text = path.read_text()
    for old, new, label in ((HET_OLD, HET_NEW, "heterogeneity"), (AUC_OLD, AUC_NEW, "AUC")):
        count = text.count(old)
        assert count == 1, f"{path} [{label}]: expected 1, found {count}"
        text = text.replace(old, new)
    path.write_text(text)
    print(f"{path}: heterogeneity + AUC sentences fixed")

# H6, instances 2 and 3: response-only prose, independently worded, not verbatim quotes.
RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
text = RESPONSE.read_text()

R85_OLD = (
    "Both Euclidean Alignment arms carry a marginally better score than the unaligned "
    "one, with a character-level AUC of 0.756 and 0.753 against 0.748, and a better score "
    "produces a lower pooled error more or less mechanically."
)
R85_NEW = (
    "Both Euclidean Alignment arms yielded a marginally higher downstream character-level "
    "AUC than the unaligned one, 0.756 and 0.753 against 0.748, despite calibration-block "
    "discriminability that was essentially unchanged (0.801 and 0.802 against 0.805; "
    "supplement, Table S15), and a higher downstream AUC produces a lower pooled error "
    "more or less mechanically."
)
count = text.count(R85_OLD)
assert count == 1, f"response line ~85: expected 1, found {count}"
text = text.replace(R85_OLD, R85_NEW)

R260_OLD = (
    "Both Euclidean Alignment arms carry a marginally better score than the unaligned one "
    "(character-level AUC 0.756 and 0.753 against 0.748) and accordingly a lower pooled "
    "mean absolute error (0.095 and 0.097 against 0.098), which is what a better score "
    "produces and is not evidence that transport was repaired."
)
R260_NEW = (
    "Both Euclidean Alignment arms yielded a marginally higher downstream character-level "
    "AUC than the unaligned one (0.756 and 0.753 against 0.748) and accordingly a lower "
    "pooled mean absolute error (0.095 and 0.097 against 0.098), despite calibration-block "
    "discriminability that was essentially unchanged (0.801 and 0.802 against 0.805; "
    "supplement, Table S15); a downstream improvement of this kind is not evidence that "
    "transport was repaired."
)
count = text.count(R260_OLD)
assert count == 1, f"response line ~260: expected 1, found {count}"
text = text.replace(R260_OLD, R260_NEW)

RESPONSE.write_text(text)
print("response: two further AUC-conflation instances fixed")
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
grep -c "did not fall" manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
grep -c "a marginally better score\|a better score produces\|discriminated marginally better" manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
```
Expected: `PARITY: IDENTICAL`; both grep families return 0 everywhere.

- [ ] **Step 3: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: resolve heterogeneity-contradiction reading and AUC/discriminability conflation

'Between-cohort heterogeneity did not fall' read as contradicting
the very next sentence's 'lowered slope tau' -- two independent
reviewers flagged this exact spot across two rounds. Named the
favourable slope-tau movement up front instead. Separately, three
places (a shared manuscript/response passage plus two independent
response-only instances) called a downstream character-level AUC
improvement 'a better score,' this paper's own defined term for
calibration-block discriminability, which was actually essentially
unchanged (0.801/0.802 against 0.805, already tabulated in
Supplement Table S15). Relabelled all three as the downstream
quantity they actually are.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 3: Scope the nonlinear-decoder conclusion to the two tested alternatives (H7)

**Files:**
- Modify: `manuscript/manuscript_expanded.md`
- Modify: `manuscript/manuscript_highlighted.md`
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""H7: "not attributable to the linearity of the decoder" reads as a universal claim about
every possible nonlinear architecture, when the paper tested exactly two. Scope the
conclusion explicitly to what was tested."""
from pathlib import Path

OLD = (
    "so the failure of the mapping to transport is not attributable to the linearity of "
    "the decoder."
)
NEW = (
    "the transportability failure was not rescued by either nonlinear alternative tested."
)

for path in (
    Path("manuscript/manuscript_expanded.md"),
    Path("manuscript/manuscript_highlighted.md"),
    Path("manuscript/response_to_reviewers_jne_r1.md"),
):
    text = path.read_text()
    count = text.count(OLD)
    assert count == 1, f"{path}: expected 1, found {count}"
    path.write_text(text.replace(OLD, NEW))
    print(f"{path}: nonlinear conclusion scoped")
```

Run with `/tmp/calib_venv/bin/python`. Note the replacement sentence starts a new
independent clause after the colon-equivalent that precedes it in context (the OLD text's
leading "so " is dropped along with it) — read the full sentence in context after
substitution to confirm it still reads grammatically (it should: "...improves neither
discrimination nor transport here: the transportability failure was not rescued by either
nonlinear alternative tested.").

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
grep -c "not attributable to the linearity" manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
```
Expected: `PARITY: IDENTICAL`; all three grep counts 0.

- [ ] **Step 3: Commit**

```bash
git add manuscript/manuscript_expanded.md manuscript/manuscript_highlighted.md manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: scope the nonlinear-decoder conclusion to the two alternatives tested

'Not attributable to the linearity of the decoder' reads as a
claim about every possible nonlinear architecture; the study
tested exactly two. Reworded to name what was actually tested.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 4: Four independent response-only wording fixes (H3, H4, H5, H8, H10)

**Files:**
- Modify: `manuscript/response_to_reviewers_jne_r1.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write and run the substitution script**

```python
"""Five independent, disjoint one-sentence fixes in the response only, bundled since each
is small, mechanical, and touches no other file:
H3: "unlabeled calibration recordings" contradicts the manuscript's own already-fixed
    (round 3, G11) target/non-target-label wording.
H4: an exclusionary claim about where the transportability failure "does not live" is an
    overreach from a single non-significant comparison.
H5: "removes precisely what a cohort's recording chain shares" is the only instance of this
    phrase (of four total, in this document and the manuscript) carrying "precisely."
H8: the opening summary says local recalibration "is significantly worse" at small sizes
    when only the two-parameter refit is; the intercept-only refit never was.
H10: "bounded that null with minimum detectable effects" is an odd verb choice, pure
    phrasing cleanup."""
from pathlib import Path

RESPONSE = Path("manuscript/response_to_reviewers_jne_r1.md")
text = RESPONSE.read_text()

H3_OLD = "requires only the target cohort's unlabeled calibration recordings and never its online accuracy."
H3_NEW = "requires the target cohort's calibration recordings, using only their usual target/non-target labels, but never its online accuracy."
count = text.count(H3_OLD)
assert count == 1, f"H3: expected 1, found {count}"
text = text.replace(H3_OLD, H3_NEW)

H4_OLD = (
    "The consequence is that the transportability failure does not live in the signal's "
    "scale or channel geometry, which is the only thing Euclidean Alignment can remove."
)
H4_NEW = (
    "One candidate explanation this rules out is that the transportability failure is a "
    "simple consequence of the signal's scale or channel geometry, since Euclidean "
    "Alignment targets exactly that class of covariance difference and removing it left "
    "the score, and the transportability result, essentially unchanged."
)
count = text.count(H4_OLD)
assert count == 1, f"H4: expected 1, found {count}"
text = text.replace(H4_OLD, H4_NEW)

H5_OLD = "Cohort-level Euclidean Alignment removes precisely what a cohort's recording chain shares, which is the class of difference the archive has already suppressed."
H5_NEW = "Cohort-level Euclidean Alignment removes what a cohort's recording chain shares, which is the class of difference the archive has already suppressed."
count = text.count(H5_OLD)
assert count == 1, f"H5: expected 1, found {count}"
text = text.replace(H5_OLD, H5_NEW)

H8_OLD = "and at the smallest sample sizes it is significantly worse."
H8_NEW = "and at the smallest sample sizes the two-parameter refit is significantly worse."
count = text.count(H8_OLD)
assert count == 1, f"H8: expected 1, found {count}"
text = text.replace(H8_OLD, H8_NEW)

H10_OLD = "bounded that null with minimum detectable effects at 80% power, and revised the Conclusion accordingly."
H10_NEW = "reported minimum detectable effects at 80% power to quantify the study's power to detect an improvement, and revised the Conclusion accordingly."
count = text.count(H10_OLD)
assert count == 1, f"H10: expected 1, found {count}"
text = text.replace(H10_OLD, H10_NEW)

RESPONSE.write_text(text)
print("all five response-only fixes applied")
```

Run with `/tmp/calib_venv/bin/python`.

- [ ] **Step 2: Verify**

```bash
grep -c "unlabeled calibration recordings\|does not live in the signal's scale\|removes precisely what\|it is significantly worse\.\|bounded that null" manuscript/response_to_reviewers_jne_r1.md
```
Expected: 0 (all five old phrasings gone).

- [ ] **Step 3: Commit**

```bash
git add manuscript/response_to_reviewers_jne_r1.md
git commit -m "fix: five independent response-only wording corrections

Unlabeled-recordings wording brought into line with the manuscript's
own already-fixed phrasing (round 3, G11); an overreaching claim
about where the transportability failure "does not live" reframed
as what the comparison rules out; a stray "precisely" removed to
match three other instances of the same phrase; the opening summary
now names the two-parameter refit specifically, since the
intercept-only refit was never significantly worse; and a leftover
odd verb choice in the closing summary reworded for clarity.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 5: Disclose the RBF/GBM classifiers' exact hyperparameters in S12 (H9)

**Files:**
- Modify: `supplementary/supplement_expanded.md`

**Interfaces:**
- Consumes: `src/bigp3_als/features.py:130-165` (read only, not modified) for the exact
  values; scikit-learn 1.9.0's actual defaults (introspected directly from the installed
  library at `/tmp/calib_venv`, not from memory or documentation, since library defaults
  can change across versions).
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Confirm the values before transcribing**

Run this and confirm it prints exactly the values below before proceeding — if any differs,
STOP and report BLOCKED, since this task's whole point is not to introduce a new
transcription error into a submission document:

```bash
/tmp/calib_venv/bin/python -c "
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.kernel_approximation import Nystroem
import inspect
sig = inspect.signature(HistGradientBoostingClassifier.__init__)
for name in ['max_iter', 'max_leaf_nodes', 'learning_rate', 'l2_regularization', 'early_stopping']:
    print(name, '=', sig.parameters[name].default)
sig2 = inspect.signature(Nystroem.__init__)
print('n_components', '=', sig2.parameters['n_components'].default)
"
```
Expected exactly: `max_iter = 100`, `max_leaf_nodes = 31`, `learning_rate = 0.1`,
`l2_regularization = 0.0`, `early_stopping = auto`, `n_components = 100`. Cross-reference
against `src/bigp3_als/features.py:130-165`'s actual instantiation (`Nystroem(kernel="rbf",
gamma=None, n_components=300, ...)` and `HistGradientBoostingClassifier(max_iter=100,
max_leaf_nodes=15, learning_rate=0.1, l2_regularization=1.0, early_stopping=False,
class_weight="balanced", ...)`) before writing Step 2's text.

- [ ] **Step 2: Write and run the substitution script**

```python
"""H9: S12 names the Nystroem component count and the GBM PCA numbers but not gamma, the
RBF arm's own logistic-head settings, or the GBM ensemble's own hyperparameters. Added,
transcribed from features.py and cross-checked against the installed scikit-learn's actual
defaults in Step 1 -- max_iter and learning_rate happen to already match scikit-learn's
defaults; max_leaf_nodes, l2_regularization, and early_stopping do not, and must not be
described as defaults."""
from pathlib import Path

SUPPLEMENT = Path("supplementary/supplement_expanded.md")
OLD = (
    "The two nonlinear arms replace the regularised linear decoder with, respectively, a "
    "Nystroem radial-basis kernel approximation at 300 components followed by the same "
    "regularised linear head, and a histogram-based gradient-boosted tree ensemble on a "
    "principal-component reduction of the same epochs."
)
NEW = (
    "The two nonlinear arms replace the regularised linear decoder with, respectively, a "
    "Nystroem radial-basis kernel approximation at 300 components followed by the same "
    "regularised linear head, and a histogram-based gradient-boosted tree ensemble on a "
    "principal-component reduction of the same epochs. The Nystroem approximation leaves "
    "gamma at scikit-learn's default (`None`, which resolves to the inverse of the "
    "feature count) and uses 300 components; its logistic head uses C = 1.0, matching the "
    "primary decoder. The gradient-boosted ensemble is scikit-learn's "
    "HistGradientBoostingClassifier configured with 100 boosting iterations and a "
    "learning rate of 0.1 (both scikit-learn's defaults), a maximum of 15 leaves per tree "
    "and an L2 regularisation strength of 1.0 (narrower than scikit-learn's defaults of "
    "31 leaves and no L2 penalty), and early stopping disabled, where scikit-learn "
    "decides automatically by default."
)
text = SUPPLEMENT.read_text()
count = text.count(OLD)
assert count == 1, f"expected 1 occurrence, found {count}"
SUPPLEMENT.write_text(text.replace(OLD, NEW))
print("S12: RBF/GBM hyperparameters disclosed")
```

Run with `/tmp/calib_venv/bin/python`.

- [ ] **Step 3: Verify**

```bash
grep -n "scikit-learn's default\|31 leaves\|no L2 penalty" supplementary/supplement_expanded.md
```
Expected: the new sentences appear once each.

- [ ] **Step 4: Commit**

```bash
git add supplementary/supplement_expanded.md
git commit -m "fix: disclose the RBF and GBM arms' exact hyperparameters in S12

S12 named the Nystroem component count and the GBM PCA numbers but
not gamma, the RBF logistic head's own settings, or the GBM
ensemble's own hyperparameters. Added, cross-checked against the
installed scikit-learn's actual introspected defaults rather than
assumed from memory -- two of the five GBM settings happen to
match scikit-learn's defaults, three (leaf count, L2 penalty, early
stopping) are deliberately chosen values that do not.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DBVHexcRQ67bXA2yHpVCc5"
```

---

### Task 6: Rebuild and re-verify the entire submission packet (controller-executed)

**Files:**
- Rebuild: all `.docx`/`.pdf`/`.portal.pdf` files in the packet directory.
- Rewrite: `0_README.md` in the packet directory.

**Interfaces:**
- Consumes: every file touched by Tasks 1-5 (must all be committed first).
- Produces: the round-4-corrected packet.

**Ruling (recorded in advance, matching round 2's Ruling T11-1 and round 3's Task 7):**
executed directly by the controller, not dispatched, for the same reason as before — it
needs `mcp__word-docx__convert_to_pdf`, which only the controller holds, and it is
integration work with no benefit from a fresh perspective.

- [ ] **Step 1: Confirm all five tasks are committed and the test suite is unaffected**

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration"
git log --oneline -5
git status --porcelain
/tmp/calib_venv/bin/python -m pytest tests/ -q
```
Expected: 5 new commits, clean tree, 235 passed / 1 deselected (unchanged).

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
  3_Manuscript_CLEAN.docx 4_Manuscript_HIGHLIGHTED.docx 2_Response_to_Reviewers.docx 5_Supplement.docx
```

- [ ] **Step 4: Re-run the clean-vs-highlighted PDF text diff**

```bash
cd "$P"
diff <(pdftotext 3_Manuscript_CLEAN.pdf -) <(pdftotext 4_Manuscript_HIGHLIGHTED.pdf -)
```
Expected: no output. All three of Tasks 1-3's manuscript edits sit inside pre-existing
`{.mark}` spans (verified in the spec before this plan was written), so this should be
unaffected, but re-verify against the actual rendered PDF regardless — this is the check
that has caught a real bug in every prior round it was skipped or shortcut.

- [ ] **Step 5: Re-verify structural counts**

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
Expected: clean and highlighted manuscript word counts identical to each other (likely
different from round 3's final 10,983 given Task 1/2/3's wording changes — record whatever
the new number is); highlighted carries 21 yellow runs (this plan edits inside existing
spans, adds none); clean carries 0.

- [ ] **Step 6: Verify each fix landed in the actual rendered PDF, not just markdown source**

```bash
cd "$P"
pdftotext 2_Response_to_Reviewers.pdf - | grep -c "constant within a participant"
pdftotext 3_Manuscript_CLEAN.pdf - | grep -c "constant within a participant"
pdftotext 2_Response_to_Reviewers.pdf - | grep -c "unlabeled calibration recordings"
pdftotext 5_Supplement.pdf - | grep -c "scikit-learn's default\|31 leaves"
```
Expected: first three all 0; the last returns at least one match (allow for PDF line-wrap
splitting a phrase across lines the way round 3's rebuild saw with "69 / to 81%" — if a
grep here returns 0 unexpectedly, check with a shorter substring before concluding the fix
did not land).

- [ ] **Step 7: Rewrite `0_README.md`**

Update: (a) the "Fixes applied" section to add a new subsection for this round's 10 fixes,
referencing this plan's task numbers, in the same one-line-per-item style as rounds 2 and
3's sections; (b) refresh every word/table/figure count from Step 5's actual output rather
than copying round 3's numbers; (c) keep the GitHub-push blocker as the top item, unchanged
in substance; (d) keep the title-confirmation item, noting this round's reviewer again
suggested a wording change that was not applied, same as prior rounds; (e) note that the
TRIPOD checklist's "prespecified"/ALSFRS-R wording was checked again this round (a
different reviewer's conditional item) and confirmed still correct, no changes needed.

- [ ] **Step 8: Final test run and commit**

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration"
/tmp/calib_venv/bin/python -m pytest tests/ -q
git status --porcelain
```
The README lives outside this git repository under `_submission_ready/`, so this repo's
tree should be clean with nothing to commit — matching rounds 2 and 3's precedent.

- [ ] **Step 9: Report to the user**

Summarize which of the 10 findings were fixed, the points confirmed already-correct (TRIPOD,
GitHub-remote status), the points not adopted (title wording, the Methods "at least two"
style tweak), and confirm the GitHub-push and title-confirmation blockers remain exactly as
before.
