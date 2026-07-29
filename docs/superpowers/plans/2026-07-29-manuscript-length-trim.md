# Manuscript Length Trim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Note on this plan's risk profile (read before choosing an execution mode):** this is a prose-trimming task on a heavily-reviewed, statistically dense manuscript, not a code-writing task. The risk is not "does it compile," it is "did a number silently change or a cross-reference silently break." A fresh subagent per task has no memory of the paper's argument or its many earlier review rounds; the plan author's assessment is that **inline execution (`superpowers:executing-plans`, single continuous editor) is materially safer than subagent-driven-development for this specific plan**, because the person/session doing the cutting needs to hold the whole paper's cross-references and numeric inventory in view at once, not just one task's slice. Presetning this to the human partner as a recommendation, not a mandate — the standard two-option choice still applies at the Execution Handoff.

**Goal:** Cut `manuscript/manuscript_expanded.md`'s main-text body word count (currently ~9,294 words by the house `_pub_assets/wordcount.py` convention: Introduction through Data availability statement, excluding Abstract, table rows, figure/table captions handled separately, and References) to a **4,000-5,000 word target**, by removing prose redundancy and over-explanation, with **zero change to any reported statistic, confidence interval, p-value, or cross-reference**.

**Architecture:** One task per major section (Introduction, Methods split in two, Results split in two, Discussion+Limitations+Conclusion), each with an explicit redundancy checklist, a "must survive unchanged" numeric inventory, and a target word count. A final task rebuilds both output pipelines (plain `build_expanded/` and the CMU-Serif `_submission_ready/` packet), re-verifies every cross-reference, and confirms the test suite and de-AI-writing scan are still clean.

**Tech Stack:** Markdown source edited in place; `scripts/15_build_manuscript.py` (plain pandoc/xelatex build); `_pub_assets/build_pub.sh` plus this study's two local pandoc-extension/header workarounds (see `_submission_ready/study_bigp3_als_calibration/0_README.md`, "Build notes") for the CMU-Serif house build; `_pub_assets/wordcount.py` for the body word count; `pytest` for the test suite; `~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py` for the em-dash/AI-tell scan.

## Global Constraints

- **No statistic may change.** Every point estimate, confidence interval, p-value, tau, I², sample size, count, and percentage that appears in the current manuscript must appear in the trimmed version with byte-identical digits. Cutting *prose around* a number is the entire point of this plan; touching the number itself is never in scope. If a task's brief and this rule conflict, this rule wins — stop and ask rather than "fixing" a number to make a sentence read better.
- **No cross-reference may break.** Every `Table 1`, `Table 2`, `Figure 1`-`Figure 4`, `Table S1`-`Table S12`, `Figure S1`-`Figure S2`, and every bracketed reference number `[1]` through `[39]` must still resolve after the edit. Do not renumber or reorder any table, figure, or reference as part of this plan — only cut and tighten prose within the existing structure. (This project has twice already recovered from stray renumbering incidents; this plan deliberately avoids reopening that risk.)
- **Zero em-dashes**, per this project's established house style (verified throughout via the de-AI-writing scan).
- **Preserve deliberately precise hedges.** Phrases like "reported as a description only," "no claim here rests on it," "not a corrected or dependence-aware version of tau itself," and "that argument is not tested here" were shaped by several earlier review rounds specifically to avoid over- or under-claiming. A shorter paraphrase is fine; a paraphrase that states a stronger or weaker claim than the original is not. When in doubt, keep the hedge and cut somewhere else instead.
- **Figure/table captions may be tightened but must stay standalone-readable.** A reader should still understand each figure without reading the surrounding prose. Moderate cuts only, aimed at removing sentences that are pure repeats of body-text content, not at gutting the caption.
- **Word count is measured with `_pub_assets/wordcount.py`** run against `manuscript/manuscript_expanded.md`, the same convention already cited in the submission-ready packet's `0_README.md`. Report the number after every task.
- **After every task:** rebuild the plain PDF (`UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`, run from the repo root), run `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest -q`, and confirm both are clean before moving on.
- **Do not touch** `manuscript/references_expanded_*`, `manuscript/manuscript_refs_*`, the Abstract, the Acknowledgements section, or the Data availability statement — none of those are in scope for this plan.

---

### Task 1: Trim the Introduction

**Files:**
- Modify: `manuscript/manuscript_expanded.md`, the `## Introduction` section (currently lines 36-46, ~623 words)

**Current text** (read directly from the file at those line numbers before editing — do not work from memory of an earlier version).

**Redundancy/compression targets, specific to this section:**
1. Paragraph 1 (background: P300 speller, ALS, home use, implanted systems, refs [1]-[8]) is establishing-context prose with four citation clusters. Compress to 2-3 sentences without dropping any of the eight citations — e.g. combine "it remains one of the few communication routes..." and "it sits alongside implanted systems..." into one sentence.
2. Paragraph 2 (prior calibration-prediction literature, refs [9]-[15],[37],[38]) can lose some of its scene-setting language ("This variability motivated a line of work asking whether...") while keeping every citation and the specific characterization of what Mainsah et al. did (this is the paper's key prior-art comparator, referenced again in Discussion — keep the description precise enough that a reader recognizes it when it recurs).
3. Paragraph 3 ("Two features of that literature limit what it can support...") is the paper's core novelty argument (within-cohort only; discrimination not calibration) — this is load-bearing, tighten sentence-level wording only, do not cut either of the two numbered points.
4. Paragraph 4 (why many cohorts are needed for transportability, ref [16],[17],[18],[39]) now partly overlaps with the abstract's "largest published evaluation of this relationship to date" framing (added 2026-07-29) — this paragraph can be shortened since the abstract already sets up the scale argument; keep the citations and the one-sentence description of ref [39] (the cross-dataset alignment paper, since the sentence explicitly distinguishes what that paper does NOT do, which matters for the novelty claim).
5. Paragraph 5 (aims) — keep in full; this is the explicit aims statement TRIPOD expects. May tighten "The documented ALS cohorts were the originally planned subgroup, before the design widened..." since this exact sentence is fully restated in Methods (Study Design and Reporting) and was already trimmed out of the Abstract for the same reason — one clause here is enough ("the ALS cohorts were the originally planned subgroup, see Methods"), not the full explanation.

**Target:** ~380-420 words (from ~623).

**Numbers that must survive unchanged:** none — this section has no statistics, only citations. Every bracketed number `[1]` through `[18]`, `[37]`, `[38]`, `[39]` that currently appears must still appear (do not drop a citation just because its sentence got shorter).

- [ ] **Step 1:** Read the current Introduction section directly from the file.
- [ ] **Step 2:** Rewrite per the five points above, targeting ~380-420 words.
- [ ] **Step 3:** Verify every citation number `[1]`-`[18]`, `[37]`-`[39]` from the original section still appears somewhere in the new text.
- [ ] **Step 4:** Run `_pub_assets/wordcount.py` against the full manuscript and report the new total.
- [ ] **Step 5:** Rebuild the plain PDF and run pytest per Global Constraints; confirm both clean.
- [ ] **Step 6:** Commit: `git add manuscript/manuscript_expanded.md build_expanded/manuscript.pdf build_expanded/manuscript.docx && git commit -m "edit: trim Introduction for length"`.

---

### Task 2: Trim Methods Part 1 (Study Design and Reporting, Data Source and Cohort, Calibration Predictor, Outcome)

**Files:**
- Modify: `manuscript/manuscript_expanded.md`, from `### Study Design and Reporting` through the end of `### Outcome` (currently lines 50-82, ~1,120 words)

**Redundancy/compression targets:**
1. **Study Design and Reporting** (~150 words): keep the TRIPOD-statement sentence (reference [19] must survive) and the internal-external cross-validation framing; the "no analysis plan was registered" paragraph can lose some of its date-by-date narrative detail (the commit-history sentence can be one clause, not a full sentence) while keeping the substantive fact that the ALS subgroup was the pre-widening plan and that the sensitivity/comparator/moderator analyses are exploratory in that order.
2. **Data Source and Cohort** (~200 words): the Study C / Study P exclusion facts (artificial feedback override; character not recoverable) are stated here AND in Results ("Cohort" subsection) AND in Table 1's own legend — that is three copies of the same two facts. Keep the full detail in Table 1's legend (already there, untouched by this plan) and reduce this Methods mention to a single clause identifying that two studies were excluded and pointing to Table 1, rather than re-explaining the two specific mechanisms again. Keep the SHA256/checksum-manifest sentence (discussed with the user directly this session, keep as is) and the participant-overlap caveat (supplement S1 cross-reference).
3. **Calibration Predictor** (~470 words, the largest chunk here): this is the section with the most defensible detail to keep (decimation/Nyquist justification exists because of a real historical aliasing bug this project caught and fixed — do not remove the *fact* that the decimation factor was chosen to avoid folding, but the multi-sentence justification can compress to one sentence). The classifier-family justification paragraph ("The regularised logistic classifier and the linear discriminant comparator were chosen because...") can shorten to one sentence naming the two refs [20],[21] and briefly why Riemannian/spatially-filtered methods (refs [22]-[25]) were out of scope, without walking through the full reasoning. The comparator-score list paragraph can be compressed to a single sentence naming the five comparators plus the ALSFRS-R exploratory specification and its 3-of-18-cohort caveat (the caveat's number, 3 of 18, must survive).
4. **Outcome** (~100 words): already tight, light tightening only.

**Numbers/facts that must survive unchanged:** SHA256 digest string `eea294aa34e9ed11e5a25d07e30aeefdf8b2d467a8309e2c38405a289afcd72f`; 16-channel montage at 256 Hz; the two exclusion mechanisms (even if compressed to a clause, both studies' fates must remain distinguishable via Table 1, which is untouched); 0.5-30 Hz bandpass, fourth-order zero-phase Butterworth; epoch window -200 to 800 ms; 150 microvolt rejection threshold; minimum 10 target / 40 non-target epochs; decimation factor of 4, 64 samples per channel, 1,024 features, 64 Hz effective rate, 32 Hz Nyquist, 30 Hz bandpass edge, 240 Hz minimum sampling rate; C = 1.0, lbfgs solver; five comparator scores named; ALSFRS-R exploratory specification's "3 of the 18 cohorts" restriction; references [16] through [25].

**Target:** ~600-680 words (from ~1,120).

- [ ] **Step 1:** Read the current text for this range directly from the file.
- [ ] **Step 2:** Rewrite per the four points above.
- [ ] **Step 3:** Grep the new text for each number in the "must survive unchanged" list above; confirm every one is present.
- [ ] **Step 4:** Run `_pub_assets/wordcount.py`; report the new total.
- [ ] **Step 5:** Rebuild the plain PDF and run pytest; confirm clean.
- [ ] **Step 6:** Commit: `git commit -m "edit: trim Methods (Study Design through Outcome) for length"`.

---

### Task 3: Trim Methods Part 2 (Model Specification, Validation Design, Statistical Analysis, Ethics, What the Calibration Score Is/Is Not)

**Files:**
- Modify: `manuscript/manuscript_expanded.md`, from `### Model Specification` through the end of `### What the Calibration Score Is, and What It Is Not` (currently lines 84-116, ~2,126 words) — this is the single largest task in the plan.

**Redundancy/compression targets:**
1. **Model Specification** (~200 words): keep the closed-form estimate (a + b(s-m)/d), the Table S12 cross-reference (reproducibility promise), and the character-level-weighting fact; the equal-weighting sensitivity sentence can compress to one clause (keep the "less than 0.003" number, cut some of the surrounding explanation of why it was tested).
2. **Validation Design** (~330 words): the three-way ALS-vs-other test description (Welch t-test, exact permutation test enumerating 3,060 assignments, random-effects meta-regression with Knapp-Hartung adjustment) is dense but each of the three names and their key parameter (3,060 permutations; Knapp-Hartung) must survive, since Results reports numbers from all three and a reader needs to know what they are. Compress the *justification* for using three tests (currently explained at length) to one sentence; keep the *description* of each test.
3. **Statistical Analysis** (~950 words, by far the largest subsection in the paper): this is where most of this task's cutting must happen.
   - The primary-metric/three-benchmarks paragraph: keep all three benchmark definitions and the "harder target in 7 of the 18 cohorts" fact, tighten surrounding prose.
   - The two-uncertainty-statements paragraph (bootstrap vs. cohort-as-unit-of-replication): keep both methods named and the log-transform-for-MAE fact (this exact point was hard-won during an earlier review pass — do not lose "the reported mean is the back-transformed geometric mean, and its between-cohort standard deviation is reported on the log scale, not back-transformed"), tighten the surrounding explanation of *why* by about half.
   - The tau/I²/Q/Paule-Mandel paragraph: keep every named quantity and the Study S1 bootstrap-non-identification fact with its two numbers (tau=0.44 slope / 0.87 intercept on the matched-17 comparison vs. 0.43/0.87 on all 18, and the bootstrap's own 0.37/0.77) — this specific comparison is one of this paper's hard-fought clarifications (it is what shows the bootstrap-vs-cluster gap is mostly the estimator, not Study S1's absence) and must not be shortened away, only its surrounding prose tightened.
   - The cluster-robust-vs-quasi-binomial paragraph: keep the "up to 40%" and "3 of 18 cohorts" figures, tighten surrounding prose by about half.
   - The I²-as-upper-estimate paragraph: keep the "20% understatement... below the conventional 75% threshold" sentence verbatim or near-verbatim (this is the paper's single most load-bearing hedge, referenced in the plan's Global Constraints and reused almost word-for-word in Results and Discussion — consider whether it can be stated ONCE with a cross-reference from its other two occurrences instead of restated in full three times; if so, this is the biggest single word-count win available in the whole Methods section, but only do this if it does not weaken the hedge at either of its other appearances — check Results and Discussion when this task is done, not just Methods).
   - The protocol-descriptors-as-moderators paragraph (~330 words): this explains the methodology behind what Results calls "the two-thirds reduction" finding. Keep the ten-descriptors count, the stopping-rule proxy definition (median inter-selection interval, never taken across a file boundary), the fixed-interval classification threshold (1e-6, with its 8e-16/0.050 sensitivity-check numbers), the grid-size/checkerboard-paradigm sourcing (from the archive's own data descriptor, 2 of 18 studies lacking checkerboard), the equipment-code fact (gUSBAmp, constant, untestable), and the Holm correction. Tighten the prose explaining *why* each choice was made to about half its current length; do not drop any of the listed facts, since Results and Discussion both refer back to several of them.
   - The intraclass-correlation/power/sensitivity-analyses paragraph: keep the ICC framing, the "2.80 times the standard error... detected a departure of at least 0.34 with 80% power" sentence, and the four named sensitivity analyses with the leave-two-studies-out mechanics (16 cohorts, 153 pairs, 17 of 153, 32 other pairs) — tighten surrounding prose.
   - The software/threshold paragraph (~20 words): keep as is, already minimal.
4. **Ethics** (~60 words): keep as is, required disclosure, already minimal.
5. **What the Calibration Score Is, and What It Is Not** (~150 words): this construct-validity caveat (the predictor is not the deployed online decoder; BCI2000 parameter files were withheld) is **also stated in Methods' own Calibration Predictor subsection in brief, and restated in full in Discussion's Study Limitations, Second** — a three-way repeat of the same point. Keep the FULL statement here (this is its natural home, a dedicated Methods subsection), and when Task 6 reaches Discussion's Second limitation, that one should shrink to a one-sentence cross-reference back to this subsection rather than restating the argument. Note this dependency explicitly in this task's commit message so Task 6's implementer (if different) knows to check it.

**Numbers/facts that must survive unchanged:** the closed-form estimate a + b(s-m)/d; "less than 0.003"; 3,060 permutations; Knapp-Hartung adjustment name; all three benchmark definitions; the log-transform-for-MAE fact; tau=0.44 (slope, matched-17) / 0.87 (intercept, matched-17) vs. all-18 cluster-robust 0.43/0.87 vs. bootstrap's own 0.37/0.77; "up to 40%" and "3 of 18 cohorts" (cluster-robust vs quasi-binomial); "20% understatement... below the conventional 75% threshold"; ten protocol descriptors; the stopping-rule proxy definition; 1e-6 threshold with 8e-16/0.050 sensitivity numbers; 2 of 18 studies lacking checkerboard paradigm; gUSBAmp equipment code; Holm correction; ICC framing; "2.80 times... 0.34... 80% power"; four sensitivity analyses named; 16 cohorts / 153 pairs / 17 of 153 / 32 other pairs; references [26] through [36].

**Target:** ~950-1,050 words (from ~2,126) — the largest single cut in the plan.

- [ ] **Step 1:** Read the current text for this range directly from the file.
- [ ] **Step 2:** Rewrite per the five points above. If collapsing the I²-upper-estimate hedge to one canonical statement plus two cross-references, make a clear note of exactly which of the three occurrences (Methods/Results/Discussion) is now canonical, for Task 6 (Discussion) to reference correctly.
- [ ] **Step 3:** Grep the new text for each item in the "must survive unchanged" list; confirm every one is present.
- [ ] **Step 4:** Run `_pub_assets/wordcount.py`; report the new total.
- [ ] **Step 5:** Rebuild the plain PDF and run pytest; confirm clean.
- [ ] **Step 6:** Commit: `git commit -m "edit: trim Methods (Model Specification through score-is-not) for length"`.

---

### Task 4: Trim Results Part 1 (Cohort, Association, Estimation Error and Its Reference Points, Transportability incl. Figures 1-3)

**Files:**
- Modify: `manuscript/manuscript_expanded.md`, from `### Cohort` through the end of the paragraph following Figure 3 (currently lines 120-201, ~1,290 words including the three figure captions)

**Redundancy/compression targets:**
1. **Cohort** (~230 words): the Study C / Study P exclusion mechanisms are restated here in full, having already been trimmed to a clause in Methods by Task 2, and are ALSO in Table 1's legend. Reduce this Results paragraph to the aggregate counts (271 participants, 410 sessions, 739 records, 19,611 selections; 47/113/194/3,318 for the ALS subset; 0.851 mean accuracy; 228/739 30.9% at ceiling; three cohorts 0.963-0.997) plus a pointer to Table 1, without re-explaining the two exclusion mechanisms a third time.
2. **Association Between Calibration-Derived Decoder Discriminability and Online Accuracy** (~280 words): keep the bolded headline sentence and every reported correlation (within-cohort r 0.190-0.928, median 0.635, 6 of 18 CIs include zero, widest CI -0.42 to 0.86; pooled r=0.716 [0.665,0.760] n=410 p<0.001; centred-within-cohort r=0.677 [0.621,0.726] p<0.001; participant-level r=0.714 [0.650,0.768] n=271 p<0.001; Spearman rho=0.756). Tighten the prose explaining *why* the centring analysis was done (it rules out cohort-mean confounding) to one clause instead of a full sentence.
3. **Estimation Error and Its Reference Points** (~200 words): keep every number (MAE 0.098 [0.091,0.107]; benchmarks 0.146 and 0.123; skill 0.327; Brier 0.123 [0.113,0.132]; Brier skill 0.110 [0.063,0.149]; AUC 0.748 [0.719,0.770]); tighten the "this pools every withheld record... is a different quantity" clarification to one shorter sentence, since the pooled-vs-cohort-mean distinction is also made in the supplement (Table S2/S4 already carry this exact caveat per the supplement's own text) and does not need full re-derivation here.
4. **Transportability** (~230 words of prose plus three figure captions ~460 words): keep every number in the prose (MAE geometric mean 0.090, arithmetic mean 0.101, log-scale SD 0.477, mean interval [0.071,0.115], new-cohort interval [0.032,0.254]; AUC average 0.713, new-cohort interval [0.491,0.935]; Brier skill average 0.174, new-cohort interval [-0.296,0.644]). Tighten the prose by about a third. For the three figure captions (Figures 1, 2, 3): tighten each by removing sentences that purely restate what the axis labels already show, while keeping the standalone-readability requirement from Global Constraints — e.g. Figure 1's caption can lose some of the explanation of why the band is computed at tau's point estimate (already explained in Methods) but must keep what each panel shows, what the dashed line means, and what tau/I² mean at the bottom of each panel.

**Numbers that must survive unchanged:** every number listed in points 1-4 above, in full.

**Target:** ~750-820 words (from ~1,290).

- [ ] **Step 1:** Read the current text for this range directly from the file.
- [ ] **Step 2:** Rewrite per the four points above.
- [ ] **Step 3:** Grep the new text for every number listed; confirm each is present with identical digits.
- [ ] **Step 4:** Confirm Figures 1-3's image references (`![](../output/expanded/figures/...)`) and `{width=...}` attributes are untouched — only the caption prose above each image may change.
- [ ] **Step 5:** Run `_pub_assets/wordcount.py`; report the new total.
- [ ] **Step 6:** Rebuild the plain PDF and run pytest; confirm clean.
- [ ] **Step 7:** Commit: `git commit -m "edit: trim Results (Cohort through Transportability) for length"`.

---

### Task 5: Trim Results Part 2 (intercept/slope paragraphs, Table 2, skill-per-cohort, ALS Subgroup, Transfer, Cohort Type, Protocol Descriptors incl. Figure 4, Preceding Session, Sensitivity Analyses)

**Files:**
- Modify: `manuscript/manuscript_expanded.md`, from the "calibration intercept varied so widely" paragraph through the end of `### Sensitivity Analyses` (currently lines 203-276, ~2,249 words) — the second-largest task in the plan.

**Redundancy/compression targets:**
1. **Intercept paragraph** (~200 words): keep tau=0.87 [0.60,1.51], pooled intercept -0.06, Q=122.6 df=17 p<0.001, I²=86.1 [79.5,90.6], observed range [-2.169,1.995], new-cohort interval [-1.97,1.85], and the two robustness numbers (tau's lower CI limit gives [-1.39,1.26]; fivefold-inflated variance gives [-1.37,1.06]). The "13 of 18... at least half a log-odds unit... 7... at least a full unit... 6... excluded zero" sentence and the I²-as-upper-estimate hedge can compress — if Task 3 made the I² hedge canonical in Methods, this occurrence becomes a one-clause cross-reference instead of the full explanation.
2. **Slope paragraph** (~230 words): keep tau=0.43 [0.30,0.77], pooled slope 1.06 [0.82,1.30], Q=81.3 df=17 p<0.001, I²=79.1 [67.6,86.5], observed range [0.185,2.185], new-cohort interval [0.111,2.005], tau-lower-limit interval [0.394,1.704], tau-upper-limit interval [-0.603,2.759], "4 of 18" CIs include zero, and the pooled-fit numbers (slope 0.967 [0.791,1.127], intercept 0.054 [-0.264,0.395]). Tighten the explanatory prose around each, especially the "that exclusion is a property of this interval at one value of tau rather than a finding" sentence, which can shorten without losing its hedge.
3. **Table 2 legend** (~100 words): keep the cross-reference to Table S2 and Figure 1; tighten slightly.
4. **"Small average departure of slope from unity" paragraph** (~100 words): keep the 0.34/80%/0.24 numbers; tighten surrounding explanation by about half.
5. **Uncorrected-SD paragraph** (~60 words): keep 0.560/1.175; already tight.
6. **"One cohort was estimated less accurately..." paragraph** (~280 words): this is the single best compression target in Results Part 2. It walks through Study H, Study E, Study R, Study S2, Study S1, and Study J individually with their exact numbers (0.921/0.963/0.976/0.997 accuracy; 0.049/0.047/0.035/0.005 own-mean error; -0.008 for Study J), and the four ALS-cohort skill values (0.317, 0.383, 0.448, 0.502). All of this per-cohort detail already lives in Table S8 (cross-referenced in the current text). Compress to: the headline sentence (keep verbatim, it is bolded), the aggregate fact ("one of 18" vs "six of 18"), one sentence summarizing the *pattern* across the three mechanisms (near-ceiling cohorts / one genuine underperformer / one near-parity case) without naming every cohort and every number individually, the four ALS skill values (these matter enough to keep, since Task 4/Discussion refer to ALS cohorts performing favourably), and the Table S8 cross-reference. This one paragraph alone can likely drop from ~280 to ~90 words.
7. **ALS Subgroup** (~130 words): keep every number (MAE 0.091 [0.076,0.108], Brier skill 0.303 [0.184,0.424], AUC 0.831 [0.768,0.869], intercept 0.025 [-0.240,0.341], slope 0.985 [0.786,1.188], uncorrected slope SD 0.223 vs 0.560); tighten surrounding prose only.
8. **Transfer From Cohorts Without a Documented ALS Population** (~80 words): keep 0.087/0.106/0.109/0.131 (mean 0.108), 0.104, bias range -0.086 to 0.049; already tight, light tightening only.
9. **Cohort Type as a Moderator** (~330 words across two paragraphs): keep 1.479/0.266 (ALS), 0.992/0.580 (other 14), difference 0.487 [0.040,0.933], Welch t=2.38 df=11.7 p=0.035, permutation p=0.058, meta-regression difference 0.559 [-0.009,1.127] p=0.053, residual SD 0.349 vs 0.432. The leave-one-out sensitivity ranges (p between 0.008-0.111 dropping an ALS cohort; 0.013-0.060 dropping another) must survive. Tighten the explanation of why three tests were used (already stated once in Methods by Task 3; this can be a shorter cross-reference here) and the paragraph distinguishing the 0.266/0.223 figures (keep the distinction, since it prevents a real misread, but state it in fewer words).
10. **Protocol Descriptors as Moderators** (~370 words): this is the stopping-rule finding, one of the paper's most important results — keep 0.406 per SD [0.181,0.632] t=3.82 df=16 p=0.002 Holm p=0.015; tau-squared 0.187 to 0.063 (66% share); rho=0.72 p<0.001 Holm p=0.007; log-scale share 71% p<0.001; leave-one-cohort-out share range 54%-82% with uncorrected p never exceeding 0.010; rho=0.16 p=0.52 (accuracy-tracking check). The mechanism-speculation sentence ("A mechanism is available, in that accumulated evidence grows with the square root...") is explicitly flagged as untested and can shorten to one clause. Figure 4's caption: tighten lightly, keep standalone-readable.
11. **Predictor From a Preceding Session** (~60 words): keep 139 pairs, r=0.513 [0.379,0.626] p<0.001 vs r=0.728 [0.639,0.798]; already tight.
12. **Sensitivity Analyses** (~140 words): keep the four named checks, the 16-of-17-cohorts leave-two-out mechanic, the 153-splits fact, and the "within 0.007... two exceptions" comparator-agreement fact; tighten surrounding prose.

**Numbers that must survive unchanged:** every number listed in points 1-12 above, in full — this is the longest such list in the plan; check it item by item rather than skimming.

**Target:** ~1,150-1,250 words (from ~2,249).

- [ ] **Step 1:** Read the current text for this range directly from the file.
- [ ] **Step 2:** Rewrite per the twelve points above, with point 6 (the per-cohort skill paragraph) as the single biggest compression target.
- [ ] **Step 3:** Grep the new text for every number listed; confirm each is present with identical digits. This is the largest numeric-inventory check in the plan; do it systematically (e.g. paragraph by paragraph against this brief), not by eye.
- [ ] **Step 4:** Confirm Figure 4's image reference and `{width=88%}` attribute are untouched.
- [ ] **Step 5:** Run `_pub_assets/wordcount.py`; report the new total.
- [ ] **Step 6:** Rebuild the plain PDF and run pytest; confirm clean.
- [ ] **Step 7:** Commit: `git commit -m "edit: trim Results (intercept/slope through Sensitivity Analyses) for length"`.

---

### Task 6: Trim Discussion, Study Limitations, and Conclusion

**Files:**
- Modify: `manuscript/manuscript_expanded.md`, the entire `## Discussion` section including `### Study Limitations` and `### Conclusion` (currently lines 278-322, ~2,212 words)

**Redundancy/compression targets:**
1. **Opening summary paragraph** (~140 words): largely restates the Abstract/Conclusion. Tighten by about a third; keep tau=0.87 [0.60,1.51], the new-cohort interval [-1.97,1.85], tau=0.43 [0.30,0.77], observed range [0.185,2.185], "one... six" skill figures.
2. **"That distinction determines what a calibration score can be used for" paragraph** (~70 words): this is an important interpretive statement, keep close to verbatim; it is short already.
3. **Mainsah/prior-literature comparison paragraph** (~100 words): keep references [10],[11],[12],[15]; tighten prose.
4. **Measurement-error paragraph** (~110 words): keep 0.008-0.031 (fourfold spread), reliability range 0.848-0.992, tau 0.432→0.422 (supplement S9 cross-reference). Tighten the explanation of the stress test to one clause.
5. **Stopping-rule-doesn't-restore-transportability paragraph** (~110 words): keep the interpretive point in close to full; this is one of the paper's more original observations (a moderator can explain heterogeneity without restoring usability) and deserves to stay clear rather than cryptic.
6. **Fold-stability paragraph** (~145 words): keep the 2.5%/3.3% coefficients of variation vs. 49.4% (Table S12/Table S2 cross-references); this methodological detail is not repeated in full elsewhere, so keep the numbers but tighten surrounding prose by about a third.
7. **Joint bootstrap paragraph** (~220 words, the longest in Discussion): this already has a full methodological description in Methods (Task 3 territory) and a first mention in Results (Task 5, tau/I² area) — Discussion's job here is interpretation, not re-derivation. Keep 0.79 [0.49,1.56] (slope), 1.62 [0.94,3.36] (intercept), the "structurally at least as large as tau" conclusion, and the explicit "not... a dependence-aware version of tau itself" hedge (this exact phrasing was corrected during an earlier review pass specifically because an intermediate draft mis-framed it — do not lose it or reword it into something that reads as a tau substitute again). Cut the mechanical re-explanation of *how* the joint bootstrap resamples (already in Methods); keep only the interpretation of what the resulting numbers mean. Target roughly half its current length.
8. **ALS-cohorts-favourable-picture paragraph** (~45 words): already short, keep as is.
9. **Artifact-rejection-improves-transportability paragraph** (~85 words): keep 0.090→0.081 and 0.560→0.465; tighten prose slightly.
10. **ALS-transfer/cohort-type-mechanism paragraph** (~150 words): keep 0.108 vs 0.104; tighten the cohort-type mechanism speculation, which already has full numeric support in Results (Task 5) and does not need to re-list every number here, just the interpretive conclusion.
11. **Study Limitations, eleven numbered items** (~1,400 words total, the single largest compression target in the entire plan): keep all eleven points — do not delete a limitation — but cut each one's prose substantially, especially where it re-explains methodology already stated in full earlier in the paper:
    - First (session ordering): keep close to current length, it is already short.
    - Second (predictor is not the deployed decoder): **per Task 3's note, this becomes a one-sentence cross-reference to the Methods subsection "What the Calibration Score Is, and What It Is Not," which now carries the full statement** — do not restate the BCI2000/parameter-files argument here again.
    - Third (protocol confounding): keep the specific facts (2 of 18 lacking checkerboard; the two recoverable traces named; what remains untestable) but cut roughly a third of the surrounding prose, since Methods (Task 3) and Results (Task 5) already carry the same numbers.
    - Fourth (ceiling effects): keep 30.9%, three cohorts; already short.
    - Fifth/Sixth/Seventh (outcome construct, legacy protocols, ALS documentation): these three can likely merge into a shorter combined passage without losing any of the three distinct points; keep reference [36].
    - Eighth (cohort-type comparison's two further limitations): keep the two specific limitations (development-set composition; correlated standard errors) but tighten by about a third.
    - Ninth (fold non-independence): this is now substantially covered by the joint-bootstrap paragraph earlier in Discussion (point 7 above) — compress to 2-3 sentences that point back to it rather than re-explaining the correlation structure again in full.
    - Tenth (tau imprecision): this repeats the I²-upper-estimate hedge and the bootstrap-tau numbers (0.37/0.77) already stated in Methods (Task 3, now canonical) and Results (Task 5) — compress to 2-3 sentences with a cross-reference rather than restating in full a third/fourth time.
    - Eleventh (participant overlap): keep as is, already one sentence.
12. **Conclusion** (~185 words): this is already a tight, well-constructed summary. Light tightening only (~10-15%); keep every number (intercept spanning understate/overstate, slope "more than tenfold," the prediction-interval-does-not-exclude-chance-or-negative-skill fact) and the explicit non-overclaiming statement about neither use being prospectively validated.

**Numbers/hedges that must survive unchanged:** every number listed in points 1-12 above; the exact hedge phrasing flagged in point 7 (joint bootstrap "not a dependence-aware version of tau itself"); the Global Constraints' load-bearing-hedge rule applies with particular force to this task, since Limitations is where several of this paper's most carefully negotiated qualifications live.

**Target:** ~900-1,000 words (from ~2,212) — the second-largest cut in the plan, concentrated almost entirely in Study Limitations.

- [ ] **Step 1:** Read the current text for this range directly from the file.
- [ ] **Step 2:** Confirm what Task 3 did with the I²-upper-estimate hedge (canonical location) and what Task 5 did with the joint-bootstrap first mention, so this task's cross-references point to the right place.
- [ ] **Step 3:** Rewrite per the twelve points above.
- [ ] **Step 4:** Grep the new text for every number listed; confirm each is present with identical digits.
- [ ] **Step 5:** Confirm all eleven limitations are still present as distinct points (even if some are merged in presentation, the substance of all eleven must be findable).
- [ ] **Step 6:** Run `_pub_assets/wordcount.py`; report the new total and the running total against the ~4,000-5,000 word target.
- [ ] **Step 7:** Rebuild the plain PDF and run pytest; confirm clean.
- [ ] **Step 8:** Commit: `git commit -m "edit: trim Discussion, Study Limitations, and Conclusion for length"`.

---

### Task 7: Final Verification and Rebuild

**Files:**
- Read/verify only: `manuscript/manuscript_expanded.md`, `manuscript/manuscript_refs_verified.json` (do not modify)
- Rebuild: `build_expanded/manuscript.{pdf,docx}`, `_submission_ready/study_bigp3_als_calibration/2_Manuscript.docx`, `_submission_ready/study_bigp3_als_calibration/PDF_PREVIEW_manuscript.pdf`, `_submission_ready/study_bigp3_als_calibration/0_README.md`

This task is a whole-document consistency pass — the equivalent of the final whole-branch review this project's earlier plans have used, adapted for a prose-editing plan rather than a code plan.

- [ ] **Step 1:** Read the full, now-trimmed manuscript end to end in one pass. Confirm it still reads as a coherent argument (not just individually-correct trimmed paragraphs) — check that every cross-reference introduced by Tasks 1-6's compressions (e.g. Task 6's Discussion Second limitation pointing to Task 3's Methods subsection; Task 6's Ninth/Tenth limitations pointing to Task 5's Results and Task 3's Methods) actually lands on a passage that still says what it's pointed at.
- [ ] **Step 2:** Confirm every Table (`Table 1`, `Table 2`, `Table S1`-`Table S12`), Figure (`Figure 1`-`Figure 4`, `Figure S1`-`Figure S2`), and reference number (`[1]`-`[39]`) cited anywhere in the trimmed main text still exists and is used the same way it was before trimming started (run a diff of citation counts against the pre-Task-1 version of the file, via `git show <commit-before-task-1>:manuscript/manuscript_expanded.md`, if easier than manual inspection).
- [ ] **Step 3:** Run `_pub_assets/wordcount.py manuscript/manuscript_expanded.md`; confirm the final total is in the 4,000-5,000 word range. If it is not, identify which task undershot or overshot its target and do one more focused pass on that section only (do not reopen every task).
- [ ] **Step 4:** Run the full test suite (`UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run pytest -q`); confirm 182 passed / 1 deselected, same as before this plan started.
- [ ] **Step 5:** Run the de-AI-writing scan (`python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py manuscript/manuscript_expanded.md`); confirm zero em-dashes and no new tells beyond the pre-existing "robust"/"dynamic" Tier 1/2 hits already present before this plan.
- [ ] **Step 6:** Rebuild the plain PDF: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`. Visually spot-check the rendered PDF (render at least the title page and one page from Methods, Results, and Discussion each as PNGs and read them) to confirm no broken cross-references or garbled sentences from the edits.
- [ ] **Step 7:** Rebuild the CMU-Serif submission-ready copy: stage the updated `manuscript_expanded.md` into the CMU build scratch directory (see this session's prior CMU-Serif rebuild commands for the exact `pandoc`/`fix_docx_tables.py` invocation, including the `gfm+superscript+raw_attribute+attributes` format string and the study-specific extra header for `pdflscape`/`singlespacing`), copy the result to `_submission_ready/study_bigp3_als_calibration/2_Manuscript.docx` and `PDF_PREVIEW_manuscript.pdf`, and verify the docx opens cleanly (`unzip -t`).
- [ ] **Step 8:** Update `_submission_ready/study_bigp3_als_calibration/0_README.md`: the body-word-count line (currently "~9,300 body words"), the commit hash in the header line, and add one line to the Headline Findings or Build Notes area documenting that the main text was trimmed to fit standard journal length norms on 2026-07-29.
- [ ] **Step 9:** Update the memory file for this study (`study-bigp3-als-calibration.md` in the user's memory directory) and the `MEMORY.md` index line with the new word count and commit hash, following this project's established pattern for recording each revision pass.
- [ ] **Step 10:** Commit: `git add -A && git commit -m "docs: rebuild after manuscript length trim, update submission-ready packet"`.
