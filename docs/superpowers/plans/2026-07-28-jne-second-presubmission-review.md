# JNE Second Pre-Submission Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address a second external pre-submission review of the calibration-transportability manuscript (target *Journal of Neural Engineering*), which found the protocol-descriptor moderator analysis omits archive-documented fields, the bootstrap-vs-cluster heterogeneity comparison mixes cohort sets, the 18 leave-one-study-out estimates' shared-development dependence is undiscussed quantitatively, the log-scale MAE pooling is mislabelled, several claims and phrasings overreach what the data support, and multiple figures/tables have legibility or structural problems.

**Architecture:** Each major comment maps to one or two tasks that touch the narrowest set of files needed. Statistical fixes land in `src/bigp3_als/` with new tests, get run to produce real numbers, and those numbers then get threaded through `manuscript/manuscript_expanded.md` and `supplementary/supplement_expanded.md`. Text-only fixes (wording softening, phrasing) are grouped into a small number of bundled tasks. The plan ends with a full rebuild, a whole-branch review, and the same finishing steps used in the prior revision round.

**Tech Stack:** Python 3, pandas, numpy, scipy, statsmodels, scikit-learn, pandoc + xelatex (`scripts/15_build_manuscript.py`), pytest, `uv` with `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv`.

## Global Constraints

- **Environment:** every Python invocation MUST be prefixed `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run ...` — a project-local `.venv` on this exFAT volume accumulates AppleDouble sidecar files that break `matplotlib.pyplot` imports.
- **Determinism:** the existing pipeline uses `RANDOM_SEED = 20260718` and `BOOTSTRAP_REPETITIONS = 2000`, both defined in `src/bigp3_als/validation.py:16-17`. Any new bootstrap must import and reuse these constants, not invent new ones.
- **No analysis plan was registered.** The manuscript's existing disclaimer (`manuscript/manuscript_expanded.md:53`, `supplementary/supplement_expanded.md:3`) must remain accurate. Never introduce the word "prespecified" to describe an analysis; a prior revision round already had to remove a reintroduced instance of exactly this word (see `docs/editorial_revision_log.md`).
- **Study-label prose convention:** in manuscript/supplement running text, cohorts are written "Study X" (with a space): "Study A", "Study S1", "Study H". Internal code and CSV columns use "StudyX" (no space): `StudyA`, `StudyS1`. Never let the no-space internal form leak into prose — this plan's Task 12 fixes 8 pre-existing instances where it already has.
- **Archive-documented protocol metadata (verified against three independent sources: the PhysioNet BigP3BCI v1.0.0 landing page, the locally cached archive descriptor `tmp/pdfs/bigp3bci_v1_0_0.pdf`, and this repository's own `docs/source_study_screening.md`, which all agree)** — for the 18 cohorts that contribute eligible online outcomes (internal labels `StudyA, StudyB, StudyD, StudyE, StudyF, StudyG, StudyH, StudyI, StudyJ, StudyK, StudyL, StudyM, StudyN, StudyO, StudyQ, StudyR, StudyS1, StudyS2`; `StudyC` and `StudyP` are excluded, they contribute zero eligible selections):

  | Study | Grid rows × cols | Grid size (cells) | Documented paradigm(s) | Checkerboard present? |
  |---|---|---:|---|---|
  | StudyA | 9×8 | 72 | RC, CB, RD | yes |
  | StudyB | 6×6 | 36 | CB | yes |
  | StudyD | 9×8 | 72 | RC | no |
  | StudyE | 9×8 | 72 | CB | yes |
  | StudyF | 9×8 | 72 | CB | yes |
  | StudyG | 9×8 | 72 | CB | yes |
  | StudyH | 9×8 | 72 | CB | yes |
  | StudyI | 9×8 | 72 | CB, PB | yes |
  | StudyJ | 6×6 | 36 | RC, PB | no |
  | StudyK | 9×8 | 72 | CB, AD | yes |
  | StudyL | 6×6 | 36 | RC, CB, CBcol | yes |
  | StudyM | 9×8 | 72 | CB, ADdiff | yes |
  | StudyN | 6×6 | 36 | CB | yes |
  | StudyO | 9×8 | 72 | CB, sCB | yes |
  | StudyQ | 9×8 | 72 | CB, CBc | yes |
  | StudyR | 9×8 | 72 | CB | yes |
  | StudyS1 | 9×8 | 72 | CB | yes |
  | StudyS2 | 9×8 | 72 | CB | yes |

  Only `StudyD` and `StudyJ` (2 of 18) lack a checkerboard variant. Grid size takes exactly two values (36 for `StudyB, StudyJ, StudyL, StudyN`; 72 for the other 14) and is confounded with ALS-cohort status: 3 of the 4 ALS cohorts (`StudyB, StudyL, StudyN`) use the 36-cell grid, while the fourth (`StudyF`) uses 72. Any task reporting an association with grid size must note this confound explicitly.
- **Equipment model is documented but constant.** The archive's own EDF+ header dictionary (Table 2 of `tmp/pdfs/bigp3bci_v1_0_0.pdf`) names "Equipment code" as a field whose value is `gUSBAmp` for the entire archive — it does not vary by study. It cannot be tested as a between-cohort moderator because a constant has no variance to associate with anything. This must be stated in text (inventoried, found invariant), not silently skipped.
- **Word budget:** the abstract (`manuscript/manuscript_expanded.md:17-33`) is currently 289 words of prose (300 including its four subheadings), both at or under JNE's 300-word structured-abstract limit — already compliant, verified directly against the file; do not cut it further on the strength of the external review's separate count of "approximately 312," which does not reproduce against the current text. The main text is approximately 10,983 words, against JNE's 12,000-word ceiling for a Paper; the tasks below add real content, so Task 14 re-checks the total.
- **Rendering:** `manuscript/manuscript_expanded.md`, `manuscript/cover_letter_expanded.md`, and `supplementary/supplement_expanded.md` are rendered to PDF and DOCX by `scripts/15_build_manuscript.py`. Figure/table captions that must not be separated from their image across a page break use the existing `{=latex}` \begin{minipage}{\textwidth} ... \end{minipage} pattern (precedent: `manuscript/manuscript_expanded.md` Figure 1/2/3/4 blocks, `supplementary/supplement_expanded.md` Figure S1/S2 blocks). A prior round found that a raw Unicode glyph (Greek rho) silently failed to render in the PDF and needed inline LaTeX math (`$\rho$`) instead — any new symbol (e.g. I²) must be verified against the actual rendered PDF text, not just the markdown source.
- **Backgrounding rule:** a subagent's own backgrounded Bash process is killed the instant the subagent's turn ends and returns a result to the controller. Any command expected to run more than ~2-3 minutes (this plan's Task 3 joint bootstrap, in particular) must run in the implementer's own foreground with a generous timeout (the existing pooled-bootstrap step in `scripts/06_run_expanded.py` already performs a comparable number of model fits and completes in a few minutes, so this is the expected order of magnitude).
- **Test discipline:** every new statistical function gets a test that would fail against the pre-fix behavior, matching the existing test style in `tests/test_expanded.py`, `tests/test_heterogeneity.py`, `tests/test_protocol.py`, and `tests/test_validation.py` — all four files already exist.

---

### Task 1: Wire archive-documented grid size and paradigm into the protocol-descriptor moderator analysis

**Files:**
- Modify: `src/bigp3_als/protocol.py`
- Test: `tests/test_protocol.py` (already exists, 454 lines — extend it; it already imports `protocol_covariates` and several other `bigp3_als.protocol` names in one parenthesized `from ... import (...)` block, and already has `numpy`/`pandas`/`pytest` imported at the top and `_trials()`/`_records()` fixtures used by several existing tests — match this style, do not add a second import block or reimport already-imported names)
- Modify: `scripts/10_run_protocol.py`
- Modify: `manuscript/manuscript_expanded.md:265,301`
- Modify: `supplementary/supplement_expanded.md:148`

**Interfaces:**
- Consumes: the `study` column values already produced throughout the pipeline (`StudyA`, `StudyB`, ... — no space), matching `COVARIATES`/`DESCRIPTOR_KIND`/`PROTOCOL_DESCRIPTORS` already defined in `protocol.py:75-105`.
- Produces: two new entries in `COVARIATES` (`"grid_size"`, `"has_checkerboard_paradigm"`), both classified `"protocol descriptor"` in `DESCRIPTOR_KIND`, both merged into the covariate frame `protocol_covariates()` returns. Every downstream consumer (`explains_heterogeneity`, `joint_moderator_fit`, `leave_one_cohort_out`, `family_composition_sensitivity`, `protocol_report`) iterates `COVARIATES`/`PROTOCOL_DESCRIPTORS` already, so no other function signature changes.

The reviewer found that `protocol.py`'s own docstring and the manuscript both claim the archive "records no matrix dimension" and that stimulus paradigm is untested, when the archive's own Table 1 documents both `Grid Size` and `Stimulus Paradigm(s)` per study (verified directly against `tmp/pdfs/bigp3bci_v1_0_0.pdf` and cross-checked against `docs/source_study_screening.md`; see Global Constraints for the exact per-study table). The existing `max_target_index`/`n_distinct_targets` proxies, built empirically from trial data in `_matrix_size_proxies()` (`protocol.py:160-178`), remain useful (they bound the alphabet actually spelled, which can differ from the grid) and should NOT be removed — they are complementary to, not replaced by, the two new documented fields.

- [ ] **Step 1: Write the failing tests**

Extend the existing `from bigp3_als.protocol import (...)` block at the top of `tests/test_protocol.py` to add `COVARIATES, DESCRIPTOR_KIND, PROTOCOL_DESCRIPTORS, documented_protocol_metadata` alongside the names it already imports (`_holm, explains_heterogeneity, family_composition_sensitivity, joint_moderator_fit, leave_one_cohort_out, protocol_covariates, protocol_report, stopping_rule_subgroups`) — do not add a separate import statement. Then add these test functions (the file's existing `numpy`/`pandas`/`pytest` imports already cover everything these need):

```python
def test_documented_protocol_metadata_covers_all_eighteen_contributing_cohorts() -> None:
    metadata = documented_protocol_metadata()
    expected_studies = {
        "StudyA", "StudyB", "StudyD", "StudyE", "StudyF", "StudyG", "StudyH", "StudyI",
        "StudyJ", "StudyK", "StudyL", "StudyM", "StudyN", "StudyO", "StudyQ", "StudyR",
        "StudyS1", "StudyS2",
    }
    assert set(metadata["study"]) == expected_studies


def test_documented_grid_size_matches_the_archive_table() -> None:
    metadata = documented_protocol_metadata().set_index("study")
    assert metadata.loc["StudyB", "grid_size"] == 36
    assert metadata.loc["StudyJ", "grid_size"] == 36
    assert metadata.loc["StudyL", "grid_size"] == 36
    assert metadata.loc["StudyN", "grid_size"] == 36
    assert metadata.loc["StudyA", "grid_size"] == 72
    assert metadata.loc["StudyF", "grid_size"] == 72


def test_checkerboard_indicator_is_false_only_for_the_two_row_column_only_studies() -> None:
    metadata = documented_protocol_metadata().set_index("study")
    assert metadata.loc["StudyD", "has_checkerboard_paradigm"] == False  # noqa: E712
    assert metadata.loc["StudyJ", "has_checkerboard_paradigm"] == False  # noqa: E712
    non_checkerboard = metadata.loc[~metadata["has_checkerboard_paradigm"]]
    assert set(non_checkerboard.index) == {"StudyD", "StudyJ"}


def test_grid_size_and_checkerboard_are_registered_as_protocol_descriptors() -> None:
    assert "grid_size" in COVARIATES
    assert "has_checkerboard_paradigm" in COVARIATES
    assert DESCRIPTOR_KIND["grid_size"] == "protocol descriptor"
    assert DESCRIPTOR_KIND["has_checkerboard_paradigm"] == "protocol descriptor"
    assert "grid_size" in PROTOCOL_DESCRIPTORS
    assert "has_checkerboard_paradigm" in PROTOCOL_DESCRIPTORS


def test_protocol_covariates_merges_documented_metadata_onto_the_empirical_covariates() -> None:
    # A minimal trials/records pair with two studies, enough for protocol_covariates() to run.
    # protocol_covariates is already imported at the top of this file.
    trials = pd.DataFrame({
        "study": ["StudyA", "StudyA", "StudyD", "StudyD"],
        "eligible": [True, True, True, True],
        "condition": ["c1", "c1", "c1", "c1"],
        "relative_path": ["a1", "a1", "d1", "d1"],
        "trial_number": [1, 2, 1, 2],
        "phase3_time_seconds": [0.0, 5.0, 0.0, 6.0],
        "target": [1, 2, 1, 2],
    })
    records = pd.DataFrame({
        "study": ["StudyA", "StudyD"],
        "correct": [8, 9],
        "n": [10, 10],
    })
    covariates = protocol_covariates(trials, records)
    merged = covariates.set_index("study")
    assert merged.loc["StudyA", "grid_size"] == 72
    assert merged.loc["StudyD", "grid_size"] == 72
    assert merged.loc["StudyA", "has_checkerboard_paradigm"] == True  # noqa: E712
    assert merged.loc["StudyD", "has_checkerboard_paradigm"] == False  # noqa: E712
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_protocol.py -v`
Expected: `FAIL` — `ImportError: cannot import name 'documented_protocol_metadata'`.

- [ ] **Step 3: Add the documented-metadata table and wire it in**

In `src/bigp3_als/protocol.py`, add near the top (after the existing module docstring, before `COVARIATES`):

```python
# Grid size and stimulus paradigm(s), transcribed from Table 1 of the archive's own descriptor
# (tmp/pdfs/bigp3bci_v1_0_0.pdf, "Summary of BCI Studies in bigP3BCI v1.0.0 Dataset"), restricted to
# the 18 studies that contribute an eligible online outcome. Grid size is rows times columns. A study
# is coded checkerboard-present if any of its documented paradigms is a checkerboard variant (CB,
# CBcol, sCB/CBs), because those variants share the flash-adjacency-avoidance design the checkerboard
# paradigm was built for, regardless of what else that study also administered. Only StudyD (RC alone)
# and StudyJ (RC, PB) lack a checkerboard variant among the 18 contributing cohorts.
_DOCUMENTED_PROTOCOL_METADATA = {
    "StudyA": (72, True),
    "StudyB": (36, True),
    "StudyD": (72, False),
    "StudyE": (72, True),
    "StudyF": (72, True),
    "StudyG": (72, True),
    "StudyH": (72, True),
    "StudyI": (72, True),
    "StudyJ": (36, False),
    "StudyK": (72, True),
    "StudyL": (36, True),
    "StudyM": (72, True),
    "StudyN": (36, True),
    "StudyO": (72, True),
    "StudyQ": (72, True),
    "StudyR": (72, True),
    "StudyS1": (72, True),
    "StudyS2": (72, True),
}


def documented_protocol_metadata() -> pd.DataFrame:
    """Return the archive's own documented grid size and checkerboard-paradigm indicator, per study.

    Unlike ``_matrix_size_proxies``, these values are not reconstructed from trial data — they are
    transcribed from the archive's own data descriptor and are exact rather than a lower bound.
    """
    return pd.DataFrame(
        [
            {"study": study, "grid_size": size, "has_checkerboard_paradigm": checkerboard}
            for study, (size, checkerboard) in _DOCUMENTED_PROTOCOL_METADATA.items()
        ]
    )
```

Update `COVARIATES` (`protocol.py:75-84`) to:

```python
COVARIATES = (
    "median_inter_selection_interval",
    "median_selections_per_record",
    "n_conditions",
    "max_target_index",
    "n_distinct_targets",
    "grid_size",
    "has_checkerboard_paradigm",
    "mean_accuracy",
    "accuracy_sd",
    "fraction_at_ceiling",
)
```

Update `DESCRIPTOR_KIND` (`protocol.py:89-98`) to add:

```python
    "grid_size": "protocol descriptor",
    "has_checkerboard_paradigm": "protocol descriptor",
```

(inserted among the other `"protocol descriptor"` entries, keeping `mean_accuracy`/`accuracy_sd`/`fraction_at_ceiling` as `"outcome summary"`).

In `protocol_covariates()` (`protocol.py:181-212`), extend the merge loop:

```python
    for extra in (_selection_timing(trials), _matrix_size_proxies(trials), documented_protocol_metadata()):
        if extra is not None:
            covariates = covariates.merge(extra, on="study", how="left")
```

(only the tuple passed to the `for extra in (...)` line changes — add `documented_protocol_metadata()` as a third element).

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_protocol.py -v`
Expected: all 5 new tests pass.

- [ ] **Step 5: Run the full test suite to confirm nothing existing broke**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest -v 2>&1 | tail -20`
Expected: all previously-passing tests still pass (adding two new columns to `COVARIATES` changes the Holm-correction family size from 5 protocol descriptors to 7, and from 8 total to 10 — any existing test that hardcodes those counts needs updating to match; if one does, update the hardcoded count, don't work around it).

- [ ] **Step 6: Regenerate the protocol-descriptor output and read off the real numbers**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/10_run_protocol.py --help` first to confirm its actual arguments, then run it with the real inputs/output directory it already expects (matching how `scripts/06_run_expanded.py`/`scripts/08_run_heterogeneity.py` are invoked elsewhere in this repo's build — check `docs/editorial_revision_log.md` or an existing Makefile/README for the exact invocation used last time rather than guessing flags).

Read the regenerated protocol-descriptor JSON/CSV output. Confirm: (a) `grid_size` and `has_checkerboard_paradigm` each appear as their own row in the descriptor table with a real Holm-corrected p-value; (b) whether either descriptor's `meta_p_value_holm` is below 0.05.

- [ ] **Step 7: Update the manuscript and supplement to reflect the real fields and the real output**

In `manuscript/manuscript_expanded.md:265`, the sentence "No other descriptor was associated with a share of the between-cohort variance distinguishable from zero, including both available proxies for matrix size (supplement, S6)." needs updating to name the two new fields and report whatever Step 6 actually found — if both are null (the likely outcome, given `StudyD`/`StudyJ` is a 2-vs-16 split with very little power and grid size is confounded with only 4 cohorts at the minority value), the sentence becomes something like: "No other descriptor was associated with a share of the between-cohort variance distinguishable from zero, including the archive's own documented grid size and its documented use of a checkerboard-variant paradigm, alongside both empirical proxies for matrix size (supplement, S6)." If either turns out non-null, do not write that sentence — report the actual coefficient/CI/Holm p exactly as Step 6 produced it, and add one sentence noting the grid-size/ALS-cohort confound (Global Constraints) if `grid_size` is the one that came back non-null.

In `manuscript/manuscript_expanded.md:301`, the sentence "The archive records none of these rules as fields, but two of them leave a recoverable trace that was tested here: the time taken per selection (the signature of the stopping rule; Results, Protocol Descriptors as Moderators), and the range of target indices, which bounds the speller alphabet from below and was not associated with a share distinguishable from zero." is about STOPPING RULES specifically — that part remains true and verified (Global Constraints; no stopping-rule field exists in the archive's documentation) and should NOT change. But do not let a reader infer from this sentence that matrix dimensions are equally undocumented — add one clause distinguishing the two: something like "...and the range of target indices, which bounds the speller alphabet from below and was not associated with a share distinguishable from zero. The archive does document a grid size and a stimulus paradigm per study, unlike the stopping rule; both were tested directly and are reported in the Results." Add one sentence to the Methods (`### Statistical Analysis`, line 89 onward — read the current text first) explaining the checkerboard-paradigm coding rule: a study is coded checkerboard-present if any of its documented paradigms is a checkerboard variant (CB, CBcol, sCB), because those variants share the flash-adjacency-avoidance design; document that only `StudyD` and `StudyJ` (of 18) lack one. Also add, wherever the equipment-code point best fits (likely the same paragraph, or the Limitations), one sentence: the archive's own EDF+ header dictionary documents equipment code, but as a single value (`gUSBAmp`) applying to the entire archive rather than a per-study field, so it cannot be tested as a moderator because it does not vary.

In `supplementary/supplement_expanded.md:148` (the "Protocol-descriptor moderator robustness" subsection under S6), the sentence "**No other descriptor was associated with a share distinguishable from zero, including both proxies for matrix size.** The archive records no matrix dimension, but the largest target index and the number of distinct characters copied bound the alphabet from below, and both were flat: 0.003 per standard deviation (p = 0.98) and -0.019 (p = 0.89), each leaving the residual between-cohort variance at or above its unmoderated value." needs the same correction as the manuscript: state that the archive DOES document grid size and stimulus paradigm, report their actual coefficients/CIs/Holm p from Step 6, and keep the existing empirical-proxy numbers (0.003, -0.019) as they are — those don't change, they're just no longer described as covering "matrix size" without documented values also being tested. Update the joint-fit sentence later in the same paragraph (the "five protocol descriptors together accounting for 43%..." sentence) to reflect the new 7-descriptor family size (was 5), rerunning `joint_moderator_fit`/`family_composition_sensitivity` numbers via Step 6's actual output rather than hand-editing the existing percentages.

- [ ] **Step 8: Re-render and re-scan**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"` and the same for `supplementary/supplement_expanded.md`.
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript --only supplement` (check `--help` — the flag may only accept one value at a time; if so, run it twice).

- [ ] **Step 9: Commit**

```bash
git add src/bigp3_als/protocol.py tests/test_protocol.py scripts/10_run_protocol.py \
  manuscript/manuscript_expanded.md supplementary/supplement_expanded.md \
  output/expanded/ build_expanded/
git commit -m "fix: wire archive-documented grid size and paradigm into the protocol-descriptor moderator analysis"
```

---

### Task 2: Matched-cohort bootstrap-vs-cluster heterogeneity comparison, and bootstrap wording/diagnostics

**Files:**
- Modify: `src/bigp3_als/heterogeneity.py`
- Test: `tests/test_heterogeneity.py`
- Modify: `scripts/08_run_heterogeneity.py`
- Modify: `manuscript/manuscript_expanded.md:95,311`
- Modify: `supplementary/supplement_expanded.md:57`

**Interfaces:**
- Consumes: `random_effects(slope, slope_se)` and the existing `_bootstrap_standard_errors`/`_fit_cohort` machinery in `heterogeneity.py` (added in the prior revision round).
- Produces: a new function, e.g. `random_effects_matched_cohorts(slopes: pd.Series, slope_se: pd.Series, exclude: tuple[str, ...]) -> dict[str, float]` — a thin wrapper that drops the named cohorts before pooling, so the SAME pooling estimator can be run on an explicit subset. Also produces per-cohort bootstrap replicate diagnostics (successful-replicate counts) as a new column or output file.

The reviewer's point: the manuscript already reports cluster-robust pooling on all 18 cohorts (tau slope 0.43, intercept 0.87) and bootstrap pooling on 17 cohorts (StudyS1 dropped; tau slope 0.37, intercept 0.77), and reads the difference as evidence about the variance estimator — but StudyS1 has one of the most extreme calibration intercepts, so part of that gap could be the missing cohort rather than the estimator. The fix is a three-way comparison: cluster-robust on all 18, cluster-robust on the SAME 17 (excluding StudyS1), and bootstrap on 17 — isolating the estimator's own contribution.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_heterogeneity.py`:

```python
def test_matched_cohort_pooling_excludes_the_named_study_from_cluster_robust_pooling() -> None:
    """Cluster-robust pooling restricted to the same 17 cohorts the bootstrap identified must
    exclude exactly StudyS1, matching random_effects()'s own dropped-cohort bookkeeping."""
    calibration = pd.read_csv("output/expanded/cohort_calibration.csv")
    cluster = calibration.loc[calibration["se_method"] == "cluster"]
    full = random_effects(
        cluster.set_index("held_out_study")["slope"], cluster.set_index("held_out_study")["slope_se"]
    )
    matched = random_effects_matched_cohorts(
        cluster.set_index("held_out_study")["slope"],
        cluster.set_index("held_out_study")["slope_se"],
        exclude=("StudyS1",),
    )
    assert full["n_studies"] == 18
    assert matched["n_studies"] == 17
    # Excluding one cohort must change the pooled tau from the all-18 value, or the test fixture
    # is not exercising anything.
    assert matched["tau"] != pytest.approx(full["tau"])
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_heterogeneity.py -k matched_cohort -v`
Expected: `FAIL` — `NameError: name 'random_effects_matched_cohorts' is not defined`.

- [ ] **Step 3: Implement the matched-cohort wrapper**

`random_effects` is defined at `heterogeneity.py:285` as `def random_effects(estimates: pd.Series, standard_errors: pd.Series) -> dict[str, object]`, indexes both Series by cohort label, and returns a dict with keys including `n_studies`, `pooled`, `pooled_se`, `tau_squared`, `tau`, `i_squared`, `q_statistic`, `q_p_value`, `prediction_interval_low`, `prediction_interval_high`, `n_dropped`, `dropped_labels` (confirmed by reading the function directly — use these exact key names, do not guess others). Add, immediately after it:

```python
def random_effects_matched_cohorts(
    estimates: pd.Series, standard_errors: pd.Series, exclude: tuple[str, ...]
) -> dict[str, object]:
    """Pool the same random-effects estimator as ``random_effects``, on an explicit cohort subset.

    Isolates the contribution of dropping cohorts (e.g. those a bootstrap could not identify) from
    the contribution of the variance-estimation method itself, by letting the same cluster-robust
    pooling run on the identical cohort set the alternative method used.
    """
    kept = estimates.index.difference(exclude)
    return random_effects(estimates.loc[kept], standard_errors.loc[kept])
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_heterogeneity.py -v`
Expected: all pass, including the new test.

- [ ] **Step 5: Expose per-cohort bootstrap replicate diagnostics**

The existing `_bootstrap_standard_errors` (`heterogeneity.py`, added in the prior revision round) already computes, internally, how many of the 2,000 replicates survived the `FITTED_BOUNDARY` separation guard per cohort (the `len(draws)` value that decides whether a cohort is reported at all). Add a return value or a side-output exposing this count per cohort — read the current function first to find the least invasive way to surface it (e.g. a second return value, or writing a small diagnostics CSV alongside the existing heterogeneity summary) rather than restructuring the function's primary return contract.

Regenerate via `scripts/08_run_heterogeneity.py` (check `--help` for its actual arguments) and confirm the new diagnostics show `StudyS1`'s successful-replicate count below 1,000 (the `repetitions // 2` threshold already documented in the code) and every other cohort's count is close to 2,000.

- [ ] **Step 6: Rerun and get the matched-cohort numbers for the manuscript**

Using `random_effects_matched_cohorts` on the real `cohort_calibration.csv` data (both slope and intercept, `exclude=("StudyS1",)`), record the three-way comparison:
1. Cluster-robust, all 18 cohorts (already in the manuscript: tau slope 0.43, intercept 0.87).
2. Cluster-robust, the same 17 cohorts the bootstrap identified (NEW — compute via Step 5's function).
3. Bootstrap, 17 cohorts (already in the manuscript: tau slope 0.37, intercept 0.77).

- [ ] **Step 7: Update the manuscript and supplement**

In `manuscript/manuscript_expanded.md:95`, after the existing sentence about StudyS1 being dropped under the bootstrap, add the matched-cohort cluster-robust numbers from Step 6 so a reader can see all three values side by side, e.g.: "Cluster-robust pooling restricted to the same 17 cohorts gave tau = {X} for the slope and {Y} for the intercept — {closer to / no closer to} the all-18 value than the bootstrap's own {0.37 / 0.77}, so {most / only part} of the difference reflects StudyS1's exclusion rather than the variance estimator." (fill in the actual comparison the real numbers support — do not assume the direction in advance).

In `manuscript/manuscript_expanded.md:311`, change "a participant-cluster bootstrap that makes no asymptotic assumption" to "a participant-cluster bootstrap sensitivity analysis that does not rely on the sandwich standard-error approximation" (the reviewer's exact suggested wording — the bootstrap is not assumption-free, particularly at 5-24 participant clusters per cohort with one cohort's separation problem).

In `supplementary/supplement_expanded.md:57`, add the same matched-cohort three-way comparison, and add the per-cohort replicate-success counts from Step 5 (at minimum StudyS1's count out of 2,000 and the threshold it fell below; ideally all 18 cohorts' counts in a small table or inline list) — this directly answers the reviewer's ask to "report the bootstrap estimator's handling of failed/separated replicates more completely: number of successful replicates per cohort, criterion used to deem an estimate identified, whether the standard error was calculated from all finite replicates or after another filter."

Note explicitly, as a deliberately deferred item (do not implement): the reviewer's "preferably, use a penalized calibration model such as Firth logistic regression... to retain Study S1 during resampling" is offered as a "preferably," not a requirement, and is a materially larger change (a different estimator for every bootstrap replicate across every cohort, not just StudyS1). Record in the ledger that this was consciously not pursued in this round.

- [ ] **Step 8: Re-render and re-scan**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"` and the supplement equivalent.
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript` then `--only supplement`.

- [ ] **Step 9: Commit**

```bash
git add src/bigp3_als/heterogeneity.py tests/test_heterogeneity.py scripts/08_run_heterogeneity.py \
  manuscript/manuscript_expanded.md supplementary/supplement_expanded.md output/expanded/ build_expanded/
git commit -m "fix: matched-cohort bootstrap-vs-cluster heterogeneity comparison, soften bootstrap wording, expose replicate diagnostics"
```

---

### Task 3: Joint bootstrap across all 18 leave-one-study-out folds — empirical covariance of the held-out estimates

**Files:**
- Modify: `src/bigp3_als/validation.py`
- Test: `tests/test_validation.py` (already exists, 27 lines, one test, imports only `leave_one_study_out` — extend it)
- Create: `scripts/16_run_joint_bootstrap.py`

**Interfaces:**
- Consumes: `records` (the analysis-records DataFrame already used by `run_source_study_held_out_validation`), `ModelSpecification` (`validation.py:21-42`), the existing `_resample_clusters`, `leave_one_study_out`, `_fit_probability_model`, `_fit_calibration_model`, `_expanded_binary`, `RANDOM_SEED`, `BOOTSTRAP_REPETITIONS` (all already defined in `validation.py`).
- Produces: `joint_bootstrap_fold_covariance(records: pd.DataFrame, specification: ModelSpecification, repetitions: int = BOOTSTRAP_REPETITIONS) -> dict[str, object]`, returning: `n_replicates`, `studies` (sorted list), `covariance_matrix` and `correlation_matrix` (each a `pd.DataFrame` indexed/columned by `f"{study}_intercept"`/`f"{study}_slope"`), `n_finite_per_study` (dict of study -> count of the `repetitions` replicates that produced a finite calibration fit for that cohort), and `replicate_between_cohort_sd_intercept`/`replicate_between_cohort_sd_slope` (each a dict with `mean`, `ci_low`, `ci_high` from the 2.5th/97.5th percentiles across replicates).

This is the "best solution" the reviewer offered for Major Comment 3 (chosen over the cheaper wording-softening alternative): the existing per-fold bootstraps in this codebase (both `_bootstrap_intervals` in `validation.py` and `_bootstrap_standard_errors` in `heterogeneity.py`) resample and refit each held-out cohort's own participants independently — they do NOT preserve the fact that cohort C's data is shared, identically, across every OTHER fold's development set within one draw. This task builds that: one joint resample of every cohort's participants per replicate, all 18 leave-one-study-out folds refit from that SAME resampled dataset, so the correlation induced by shared development data is captured directly in the resulting empirical covariance rather than assumed away.

**Cost note:** this performs `repetitions x 18` calls to `_fit_probability_model` — the same order of magnitude as the pooled-bootstrap loop already inside `run_source_study_held_out_validation` (`validation.py:281-306`), which already runs successfully as part of `scripts/06_run_expanded.py`. Expect a few minutes of runtime, not hours. Run this in the foreground with a generous timeout (10+ minutes) — do not background it inside a subagent turn (Global Constraints).

- [ ] **Step 1: Write the failing test**

Extend `tests/test_validation.py`'s existing `from bigp3_als.validation import leave_one_study_out` line to also import `MODEL_SPECS, joint_bootstrap_fold_covariance`, and add `import numpy as np`, `import pytest` at the top alongside the existing `import pandas as pd` (neither is currently imported in this file). Then add:

```python


def _toy_records(n_studies: int = 4, n_participants: int = 6, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(n_studies):
        study = f"Study{chr(ord('A') + s)}"
        for p in range(n_participants):
            score = rng.normal(0.6 + 0.1 * s, 0.15)
            n = 10
            correct = int(rng.binomial(n, min(max(score, 0.05), 0.95)))
            rows.append({
                "study": study, "study_participant_id": f"{study}_{p}", "session_id": "S1",
                "calibration_auc": score, "correct": correct, "n": n,
            })
    return pd.DataFrame(rows)


def test_joint_bootstrap_returns_a_covariance_matrix_indexed_by_every_study() -> None:
    records = _toy_records()
    spec = next(s for s in MODEL_SPECS if s.role == "primary")
    result = joint_bootstrap_fold_covariance(records, spec, repetitions=25)
    assert result["n_replicates"] == 25
    assert set(result["studies"]) == {"StudyA", "StudyB", "StudyC", "StudyD"}
    expected_columns = {f"{s}_intercept" for s in result["studies"]} | {f"{s}_slope" for s in result["studies"]}
    assert set(result["covariance_matrix"].columns) == expected_columns
    assert set(result["covariance_matrix"].index) == expected_columns
    # A covariance matrix is symmetric.
    assert result["covariance_matrix"].to_numpy() == pytest.approx(
        result["covariance_matrix"].to_numpy().T, abs=1e-9
    )


def test_joint_bootstrap_replicate_spread_intervals_are_ordered() -> None:
    records = _toy_records()
    spec = next(s for s in MODEL_SPECS if s.role == "primary")
    result = joint_bootstrap_fold_covariance(records, spec, repetitions=25)
    for key in ("replicate_between_cohort_sd_intercept", "replicate_between_cohort_sd_slope"):
        block = result[key]
        assert block["ci_low"] <= block["mean"] <= block["ci_high"]


def test_joint_bootstrap_is_deterministic_across_repeated_calls() -> None:
    records = _toy_records()
    spec = next(s for s in MODEL_SPECS if s.role == "primary")
    first = joint_bootstrap_fold_covariance(records, spec, repetitions=10)
    second = joint_bootstrap_fold_covariance(records, spec, repetitions=10)
    assert first["covariance_matrix"].to_numpy() == pytest.approx(
        second["covariance_matrix"].to_numpy(), nan_ok=True
    )


def test_joint_bootstrap_reports_finite_replicate_counts_per_study() -> None:
    records = _toy_records()
    spec = next(s for s in MODEL_SPECS if s.role == "primary")
    result = joint_bootstrap_fold_covariance(records, spec, repetitions=25)
    for study in result["studies"]:
        assert 0 <= result["n_finite_per_study"][study] <= 25
```

(If `pytest.approx(..., nan_ok=True)` is not a valid kwarg in the pytest version this repo pins, use `np.testing.assert_allclose(..., equal_nan=True)` instead — check `pytest --version` / existing test files for the pattern already in use.)

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_validation.py -v`
Expected: `FAIL` — `ImportError: cannot import name 'joint_bootstrap_fold_covariance'`.

- [ ] **Step 3: Implement the joint bootstrap**

In `src/bigp3_als/validation.py`, add after `run_source_study_held_out_validation` (reusing every helper already defined above it in the same file — no new imports needed):

```python
def joint_bootstrap_fold_covariance(
    records: pd.DataFrame,
    specification: ModelSpecification,
    repetitions: int = BOOTSTRAP_REPETITIONS,
) -> dict[str, object]:
    """Jointly bootstrap every leave-one-study-out fold to capture their shared-development covariance.

    A bootstrap run independently per held-out cohort (as ``_bootstrap_intervals`` and
    ``heterogeneity._bootstrap_standard_errors`` both do) cannot see that up to 16 of 17 development
    cohorts are shared between any two folds: each fold resamples its own development set separately,
    so a cohort appearing in two different folds' development sets gets two independent draws instead
    of the same one. This function resamples every cohort's participants once per replicate, then
    refits all 18 folds from that single resampled dataset, so the correlation the shared development
    data induces between folds is captured directly in the resulting empirical covariance rather than
    assumed away by treating the 18 held-out estimates as independent, which the primary random-effects
    pooling does.
    """
    modeled = records.dropna(subset=list(specification.features)).copy()
    studies = sorted(modeled["study"].unique())
    rng = np.random.default_rng(RANDOM_SEED)

    intercepts: dict[str, list[float]] = {study: [] for study in studies}
    slopes: dict[str, list[float]] = {study: [] for study in studies}
    replicate_spread_intercept: list[float] = []
    replicate_spread_slope: list[float] = []

    for _ in range(repetitions):
        resampled = _resample_clusters(modeled, rng, stratify_study=True)
        this_replicate_intercepts: list[float] = []
        this_replicate_slopes: list[float] = []
        for held_out, development, validation in leave_one_study_out(resampled):
            validation = validation.copy()
            validation["predicted_probability"] = _fit_probability_model(
                development, validation, specification.features
            )
            labels, expanded_probabilities = _expanded_binary(validation)
            intercept, slope = _fit_calibration_model(labels, expanded_probabilities)
            intercepts[held_out].append(intercept)
            slopes[held_out].append(slope)
            if np.isfinite(intercept) and np.isfinite(slope):
                this_replicate_intercepts.append(intercept)
                this_replicate_slopes.append(slope)
        if len(this_replicate_intercepts) >= 2:
            replicate_spread_intercept.append(float(np.std(this_replicate_intercepts, ddof=1)))
        if len(this_replicate_slopes) >= 2:
            replicate_spread_slope.append(float(np.std(this_replicate_slopes, ddof=1)))

    frame = pd.DataFrame(
        {f"{study}_intercept": intercepts[study] for study in studies}
        | {f"{study}_slope": slopes[study] for study in studies}
    )
    covariance = frame.cov()
    correlation = frame.corr()
    n_finite_per_study = {
        study: int(np.sum(np.isfinite(intercepts[study]) & np.isfinite(slopes[study])))
        for study in studies
    }

    def _spread_summary(values: list[float]) -> dict[str, float]:
        if not values:
            return {"mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
        return {
            "mean": float(np.mean(values)),
            "ci_low": float(np.quantile(values, 0.025)),
            "ci_high": float(np.quantile(values, 0.975)),
        }

    return {
        "n_replicates": repetitions,
        "studies": studies,
        "covariance_matrix": covariance,
        "correlation_matrix": correlation,
        "n_finite_per_study": n_finite_per_study,
        "replicate_between_cohort_sd_intercept": _spread_summary(replicate_spread_intercept),
        "replicate_between_cohort_sd_slope": _spread_summary(replicate_spread_slope),
    }
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_validation.py -v`
Expected: all pass.

Run the full suite: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest -v 2>&1 | tail -20`
Expected: no regressions.

- [ ] **Step 5: Run the real computation and write outputs**

Create `scripts/16_run_joint_bootstrap.py`, matching the argument-parsing style of `scripts/06_run_expanded.py` (same `--trials`/`--features`/`--metadata`/`--output-directory` defaults), that: builds `records` the same way `scripts/06_run_expanded.py` does (`build_analysis_records` + `label_cohort_type`), calls `joint_bootstrap_fold_covariance(records, primary_spec, bootstrap_repetitions=2000)` where `primary_spec = next(s for s in MODEL_SPECS if s.role == "primary")`, and writes:
- `output/expanded/joint_bootstrap_covariance.csv` (the covariance matrix, with the index as its own column)
- `output/expanded/joint_bootstrap_correlation.csv` (same shape, correlation matrix)
- `output/expanded/joint_bootstrap_summary.json` (`n_replicates`, `n_finite_per_study`, the two `replicate_between_cohort_sd_*` blocks)

Run it: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/16_run_joint_bootstrap.py --output-directory output/expanded` **in the foreground**, with a timeout of at least 900000ms (15 minutes) — this is the step the Global Constraints backgrounding rule applies to.

Read the resulting `joint_bootstrap_summary.json` and note: the mean and 95% range of the replicate-level between-cohort SD for both intercept and slope (this is the key new number — an empirical, dependence-aware alternative/companion to the meta-analytic tau), and which off-diagonal cells of the correlation matrix are largest in magnitude (i.e. which pairs of held-out cohorts are most correlated because of shared development data — likely small-cohort pairs, since a small cohort's removal from a 17-cohort development set moves that set's fit more than a large cohort's would).

- [ ] **Step 6: Commit**

```bash
git add src/bigp3_als/validation.py tests/test_validation.py scripts/16_run_joint_bootstrap.py \
  output/expanded/joint_bootstrap_covariance.csv output/expanded/joint_bootstrap_correlation.csv \
  output/expanded/joint_bootstrap_summary.json
git commit -m "feat: joint bootstrap across all 18 leave-one-study-out folds, empirical covariance of held-out estimates"
```

---

### Task 4: Report the joint-bootstrap findings in the manuscript and supplement

**Files:**
- Modify: `manuscript/manuscript_expanded.md:287,309`
- Modify: `supplementary/supplement_expanded.md` (extend S4. Uncertainty, lines 51-70)

**Interfaces:**
- Consumes: `output/expanded/joint_bootstrap_summary.json`, `output/expanded/joint_bootstrap_correlation.csv` (Task 3's outputs).

- [ ] **Step 1: Read Task 3's actual output**

Read `output/expanded/joint_bootstrap_summary.json` and `output/expanded/joint_bootstrap_correlation.csv` in full before writing any prose — every number below must come from these files, not be estimated or assumed.

- [ ] **Step 2: Update the manuscript's Discussion**

In `manuscript/manuscript_expanded.md:287`, the existing paragraph ends "...That distinction is evidence against development-fit noise as an alternative explanation for the heterogeneity." Add, as new sentences immediately after: report the joint bootstrap's replicate-level between-cohort SD for slope and intercept (mean and 95% range) alongside the existing meta-analytic tau (0.43 slope / 0.87 intercept), and state plainly whether the two agree — e.g. "A joint bootstrap that resamples every cohort once per replicate and refits all 18 folds from that single resampled draw, so that shared development data is held identical across folds within a replicate rather than independently redrawn, gives a directly comparable but assumption-light estimate: the within-replicate between-cohort standard deviation of the slope averaged {X} (95% range {Y} to {Z}) across 2,000 replicates, and of the intercept {A} ({B} to {C}), {consistent with / smaller than / larger than} the meta-analytic tau above." Fill in the real numbers; do not guess the direction of the comparison before reading Step 1's output.

In `manuscript/manuscript_expanded.md:309` (the Ninth limitation, "the 18 held-out estimates are not fully independent..."), update the closing sentence "The fold-coefficient stability reported above bounds how much this can be inflating the observed spread." to also reference the joint bootstrap as a direct (not merely bounding) quantification: e.g. "The fold-coefficient stability reported above bounds how much this can be inflating the observed spread, and the joint bootstrap in the Discussion measures it directly rather than only bounding it."

- [ ] **Step 3: Extend the supplement's S4. Uncertainty**

In `supplementary/supplement_expanded.md`, after the existing paragraph at line 57 (ending "...narrower than but consistent in span with the clustered-sandwich intervals reported in the main text."), add a new paragraph and a new table:

- A paragraph explaining the joint-bootstrap mechanism (one joint resample of every cohort's participants per replicate, all 18 folds refit from that one resample, 2,000 replicates, same `RANDOM_SEED`/`BOOTSTRAP_REPETITIONS` as elsewhere in this pipeline) and reporting the `n_finite_per_study` counts (which cohorts, if any, failed to produce a finite calibration fit in some replicates, and how often — likely `StudyS1` again, given its known separation issue, but confirm against the real output rather than assuming).
- A new small table (numbered following whatever the current last table number is — check the file's actual current highest `Table S` number before assigning; do not assume it is still S9, since Task 1 and Task 2 may have added rows to existing tables but should not have added new table NUMBERS) reporting the strongest 5-10 off-diagonal correlations from `joint_bootstrap_correlation.csv` (which pairs of held-out cohorts are most correlated, and roughly why — e.g. two small cohorts whose removal from each other's development set moves the fit the most).

- [ ] **Step 4: Re-render and re-scan**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"` and the supplement equivalent.
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript` then `--only supplement`.

- [ ] **Step 5: Commit**

```bash
git add manuscript/manuscript_expanded.md supplementary/supplement_expanded.md build_expanded/
git commit -m "docs: report the joint-bootstrap covariance findings in the Discussion, Limitations, and supplement"
```

---

### Task 5: Log-scale MAE labeling — geometric mean, SD of log(MAE), natural-log definition

**Files:**
- Modify: `manuscript/manuscript_expanded.md:162` (and its Methods section defining the log transform — check `### Statistical Analysis`, line 89 onward, for the right place to add a defining sentence)
- Modify: `supplementary/supplement_expanded.md:61,65,126,130,133,136,192,194,196,211`
- Modify: `src/bigp3_als/render_expanded.py` (Figure 3 legend — the function producing `figure_transportability.png`, likely the one at `render_expanded.py:85` given its `ax.axvline(summary["mean"], ...)` call — read the surrounding code first to confirm the legend text source)

**Interfaces:** none — this is a labeling-only fix; no function signatures change.

The reviewer's point: `random_effects_pooling(..., transform="log")` (added in the prior revision round, `src/bigp3_als/expanded.py`) correctly back-transforms the MAE mean via `exp(mean(log(x)))`, which is the geometric mean, but every citation of it in the manuscript and supplement calls it simply "the mean," and the between-cohort SD is left on the log scale but labeled just "SD," neither qualified as "geometric" or "on the log scale" in the surrounding prose (only in a general footnote). Fix every citation, not just one.

- [ ] **Step 1: Add an explicit Methods definition**

In `manuscript/manuscript_expanded.md`, under `### Statistical Analysis` (starting line 89 — read the current text first to place this naturally, likely near wherever the MAE prediction-interval fix from the prior revision round already lives), add one sentence: "Cohort-level mean absolute error was pooled after natural-log transformation, because the quantity cannot be negative; the reported mean is the back-transformed geometric mean, and its between-cohort standard deviation is reported on the log scale, not back-transformed." (Matches the reviewer's exact suggested Methods wording.)

- [ ] **Step 2: Fix every manuscript and supplement citation**

In `manuscript/manuscript_expanded.md:162`, change "averaged 0.090 with a between-cohort standard deviation of 0.477 on the log scale" to "averaged 0.090 (the geometric mean; the arithmetic mean of the 18 cohort-level errors was 0.101) with a between-cohort standard deviation of 0.477 on the log scale" — this both adds the "geometric" qualifier and reports the arithmetic mean descriptively, per the reviewer's explicit suggestion ("I would also report the arithmetic mean of 0.101 descriptively so readers can reconcile the revised analysis with ordinary averaging"). Confirm 0.101 against the real `output/expanded/random_effects_pooling.csv`/protocol output before using it verbatim — it is quoted from the reviewer's own review, not independently re-derived in this plan, so check it.

In `supplementary/supplement_expanded.md`:
- Line 61 (Table S2 caption): after "...but its between-cohort SD is reported on the log scale, consistent with the main text." add "The reported mean for that row is the geometric mean; the arithmetic mean of the 18 cohort-level errors was 0.101."
- Line 63-69 (Table S2 itself): change the row label "Mean absolute error" to "Mean absolute error (geometric mean)" so the qualifier travels with the number even if a reader skips the caption prose.
- Lines 126, 130, 133, 136 (Table S4 caption and prose, "Sensitivity Analyses"): wherever "mean absolute error" is used to describe the cohort-level pooled quantity (not the pooled-over-records one), add "(geometric mean)" on first use in that paragraph.
- Line 192, 194 (Table S6 caption and header): the column currently headed "Mean across cohorts" → "Geometric mean across cohorts"; the column currently headed "Between-cohort MAE SD" → "Between-cohort SD of log(MAE)" (the reviewer's exact suggested wording for this specific column, matching the fact this table's whole column is log-scale, unlike Table S2's shared column).
- Line 196 (Table S6 caption prose, "the mean across cohorts is the quantity Table S4 reports as mean absolute error"): update to say "the geometric mean across cohorts."
- Line 211 ("the between-cohort MAE SD, which is computed on the log scale and reads 0.459 against 0.477, a gap of 0.018"): no change needed here — already correctly describes it as log-scale; leave as-is.

- [ ] **Step 3: Fix Figure 3's legend**

Read `src/bigp3_als/render_expanded.py` around the function producing `figure_transportability.png` (the one with `ax.axvline(summary["mean"], ...)`, likely near line 85-116) to find where the legend label text for that vertical line is set (e.g. a `label="mean"` kwarg passed to `axvline` or a separate `ax.legend()` call). Change whatever string currently reads "mean" (or similar, e.g. "mean across withheld cohorts") to "geometric mean across withheld cohorts" — read the actual current label text first; do not guess its exact current wording.

Also update `manuscript/manuscript_expanded.md`'s Figure 3 caption (line 192) if it uses the word "mean" unqualified to describe this same line — check and fix if so.

- [ ] **Step 4: Re-render and re-scan**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"` and the supplement equivalent.
Regenerate the figure if Step 3 changed `render_expanded.py`: rerun whichever script calls `render_transportability` (`scripts/13_render_figures.py`), then rebuild: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript` then `--only supplement`.

- [ ] **Step 5: Commit**

```bash
git add manuscript/manuscript_expanded.md supplementary/supplement_expanded.md \
  src/bigp3_als/render_expanded.py output/expanded/figures/ build_expanded/
git commit -m "fix: label log-scale MAE pooling as a geometric mean throughout, define natural-log transform in Methods"
```

---

### Task 6: "Independent cohorts" wording and cross-study participant-overlap transparency

**Files:**
- Modify: `manuscript/manuscript_expanded.md:57-64` (`### Data Source and Cohort`), `manuscript/manuscript_expanded.md:277,315` (Discussion opener, Conclusion), `manuscript/manuscript_expanded.md:295` onward (Study Limitations)
- Modify: `supplementary/supplement_expanded.md:321` onward (`## S12. Transparency statement` — read its current content first)

**Interfaces:** none — text-only.

- [ ] **Step 1: Read the current text of the relevant sections before editing**

Read `manuscript/manuscript_expanded.md:277-315` (Discussion opener through Conclusion) and `supplementary/supplement_expanded.md:321` to the end of the file (S12), to see the exact current wording rather than assuming.

- [ ] **Step 2: Fix "independent" where it overstates**

In `manuscript/manuscript_expanded.md:277`, change "Across 18 independent P300-speller cohorts" to "Across 18 source-study cohorts" (or "18 distinct study cohorts" — pick whichever reads more naturally in context once the actual sentence is in front of the implementer).

In `manuscript/manuscript_expanded.md:315`, change "In 18 independent P300-speller cohorts" to the same replacement phrase chosen in the previous step, for consistency.

Do NOT touch `manuscript/manuscript_expanded.md:309`'s use of "not fully independent" (describing the held-out estimates' shared development data) — that is a correct, opposite-direction use of the word and is not what the reviewer flagged.

- [ ] **Step 3: Add the participant-overlap caveat to the manuscript**

`supplementary/supplement_expanded.md:7` already states: "Study-scoped participant identifiers were retained to prevent accidental cross-study linkage; they do not identify unique people across studies." The manuscript itself does not yet carry this caveat. Add one sentence to `### Data Source and Cohort` (`manuscript/manuscript_expanded.md`, around line 57-64): "Participant identifiers are study-scoped; because the source studies draw from a limited number of contributing laboratories, participant overlap across studies cannot be ruled out from the archive's documentation (supplement, S1)." (Cross-reference whatever the actual supplement section number is for S1/Data provenance — confirm against the file rather than assuming S1 is still correct after Tasks 1-5's edits.)

Add a second, shorter version to `### Study Limitations` (line 295 onward): "Because participant identifiers are study-scoped, we could not determine whether any individuals participated in more than one source study." (The reviewer's exact suggested wording.)

- [ ] **Step 4: Add the same caveat to the supplement's Transparency statement**

In `## S12. Transparency statement`, add one sentence stating the same participant-overlap caveat, cross-referencing the existing S1 sentence rather than duplicating its exact wording verbatim.

- [ ] **Step 5: Re-render and re-scan**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"` and the supplement equivalent.
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript` then `--only supplement`.

- [ ] **Step 6: Commit**

```bash
git add manuscript/manuscript_expanded.md supplementary/supplement_expanded.md build_expanded/
git commit -m "fix: replace overreaching 'independent cohorts' wording, add cross-study participant-overlap caveat"
```

---

### Task 7: Soften practical-use claims

**Files:**
- Modify: `manuscript/manuscript_expanded.md:291,315`

**Interfaces:** none — text-only.

- [ ] **Step 1: Read the current exact text**

Read `manuscript/manuscript_expanded.md:288-296` (Discussion, the "concrete step" paragraph) and `:313-316` (Conclusion) in full before editing.

- [ ] **Step 2: Soften the Conclusion**

Change "A calibration score may support ranking sessions within a setting and may support a data-quality screen, and it should not be used to report an expected accuracy in a cohort where the mapping was not developed without local recalibration." to something matching the reviewer's suggested direction: "The score may be useful for within-setting ranking after local validation, and the artifact-rejection fraction is a candidate data-quality screen that warrants prospective evaluation; neither use has been prospectively validated here, and the score should not be used to report an expected accuracy in a cohort where the mapping was not developed without local recalibration." (Keep the existing final clause about not reporting expected accuracy without recalibration — that part is not in dispute; only the two forward-looking claims need the "warrants validation"/"after local validation" qualifiers.)

- [ ] **Step 3: Soften the Discussion's "concrete step"**

Change "Screening calibration data quality before relying on a calibration-derived estimate is therefore a concrete step, and it is available at no cost because the rejection fraction is computed while the score is computed." to: "Screening calibration data quality before relying on a calibration-derived estimate is therefore a candidate step that warrants prospective evaluation, and it is available at no cost because the rejection fraction is computed while the score is computed."

- [ ] **Step 4: Re-render and re-scan**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"`.
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`.

- [ ] **Step 5: Commit**

```bash
git add manuscript/manuscript_expanded.md build_expanded/
git commit -m "fix: soften practical-use claims for session ranking and artifact-fraction screening"
```

---

### Task 8: Keep the protocol-descriptor section secondary after Task 1's additions

**Files:**
- Modify: `manuscript/manuscript_expanded.md:261-266` (`### Protocol Descriptors as Moderators`)

**Interfaces:** none — condensation only, no new content.

Task 1 added two new descriptors and their results to this section. The reviewer's concern (separate from Major Comment 1's factual fix) is that this section should not grow to rival the transportability finding in prominence. This task is a check-and-trim, done only after Task 1 has landed.

- [ ] **Step 1: Measure the section's current length**

After Task 1 is complete, count the words in `### Protocol Descriptors as Moderators` (`manuscript/manuscript_expanded.md:261-266`) with `wc -w` on just that section's text.

- [ ] **Step 2: Trim if it has grown substantially**

If the section has grown by more than roughly 40-50 words from Task 1's additions (i.e., the two new descriptor results were reported at the same density as everything else rather than concisely), condense: report the two new descriptors' results in the same single-clause style already used for `n_conditions` ("The number of stimulus conditions was likewise flat (p = 0.84)" is the existing density target), rather than a full sentence each. Do not remove any number, only tighten phrasing. If Task 1's addition was already concise (a strong possibility, since Task 1's own Step 7 instructions already asked for single-clause density), this step may require no changes — state so in the task report rather than trimming content that doesn't need it.

- [ ] **Step 3: Confirm no decoder-model additions are needed**

This is a documentation-only check, not a code change: confirm the manuscript does not commit to adding a CNN, transformer, or other new decoder model in response to this review (the reviewer explicitly says none is needed, and the existing regularized-linear-discriminant comparator in Table S6/S8 already demonstrates the primary conclusion is not specific to logistic regression). No file changes are expected from this step; if any earlier task's edits accidentally implied a new model was forthcoming, remove that implication.

- [ ] **Step 4: Re-render and re-scan if Step 2 made changes**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"`.
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`.

- [ ] **Step 5: Commit (only if Step 2 changed anything)**

```bash
git add manuscript/manuscript_expanded.md build_expanded/
git commit -m "docs: keep the protocol-descriptor section concise and secondary to the transportability finding"
```

---

### Task 9: Figure legibility — Figure 1 text/legend size, Figure 2 main-text panel size, Figure 4 grayscale-safe encoding

**Files:**
- Modify: `src/bigp3_als/render_expanded.py`
- Modify: `scripts/13_render_figures.py`

**Interfaces:**
- Consumes/modifies: `render_calibration_forest` (Figure 1), `render_calibration_curves` (Figure 2), `render_skill_by_cohort` (Figure 4) — read each function's current body before editing, since exact line numbers may have shifted after Tasks 1-8.

- [ ] **Step 1: Enlarge Figure 1's text and legend**

In `render_calibration_forest` (`render_expanded.py`, currently `figsize=(9.8, 6.2)` at line 268, legend `fontsize=8.5` at line 282): increase the figure size modestly, e.g. to `figsize=(11.0, 7.0)`, and increase the legend fontsize from 8.5 to 10. Check `_forest_panel`'s own body (called at lines 269-272) for any additional small-fontsize text (axis labels, tick labels) and bump anything below 9pt to at least 9-9.5pt, keeping the panel-letter label (`fontsize=14`) as-is since that one is already legible.

- [ ] **Step 2: Enlarge Figure 2's main-text (6-panel) version without changing the 18-panel supplement version**

In `render_calibration_curves` (`render_expanded.py:313-352`), the panel grid is `columns = min(6, len(cohort_list))`, `rows = math.ceil(len(cohort_list) / columns)`, `figsize=(1.62 * columns, 1.78 * rows + 0.5)`. For exactly 6 cohorts (the main-text call), this always produces a single row of 6 (`columns=6, rows=1`, figsize approximately `(9.72, 2.28)`) — a wide, short strip that leaves most of a portrait page's height empty, which is the reviewer's exact complaint.

Add two new keyword-only parameters with defaults that preserve current behavior for every existing call site: `max_columns: int | None = None` and a size multiplier pair `panel_width: float = 1.62, panel_height: float = 1.78`. Change the grid-shape line to `columns = min(max_columns or 6, len(cohort_list))` and the figsize line to `figsize=(panel_width * columns, panel_height * rows + 0.5)`.

In `scripts/13_render_figures.py`, the main-text call (`render_calibration_curves(predictions, ALS_STUDIES, figures, cohorts=MAIN_TEXT_COHORTS, filename="figure_calibration_curves_main")`) gets three new keyword arguments: `max_columns=3, panel_width=2.3, panel_height=2.5` — producing a 2-row-by-3-column grid with meaningfully larger individual panels, filling the page better. Leave the un-cohorted supplement call (`render_calibration_curves(predictions, ALS_STUDIES, figures)`, no `cohorts=` argument, producing the 18-panel `figure_calibration_curves.png`/Figure S2) with no new keyword arguments, so its size is unchanged.

- [ ] **Step 3: Add a grayscale-safe encoding to Figure 4 (optional — descope if it proves fiddly)**

The reviewer calls this "not essential." In `render_skill_by_cohort` (`render_expanded.py`, the `barh` function around line 153), cohort type (ALS vs. other) is already encoded by color (`colours` at line 155). Add a `hatch` parameter to the `barh` call, differing by cohort type (e.g. `hatch="//"` for ALS bars, `None` for others), matching the existing `ALS_MARKER`/`OTHER_MARKER` shape-distinction precedent from the prior revision round's Figure 1/Figure 4 scatter fixes. If this turns out to visually clutter the chart or fight with the existing color legend, skip it and note in the task report why — this step is explicitly non-essential per the reviewer's own framing.

- [ ] **Step 4: Regenerate the figures**

Run whichever script calls these render functions (`scripts/13_render_figures.py` — check `--help` for its actual arguments) to regenerate `figure_calibration_forest.png/pdf`, `figure_calibration_curves_main.png/pdf`, and `figure_skill_by_cohort.png/pdf`.

Visually inspect the regenerated Figure 1 and Figure 2 (main-text version) — open the PNG or the rendered page (after Step 5) and confirm text is legibly larger, not just that the code ran without error.

- [ ] **Step 5: Rebuild and re-verify page layout**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`.
Confirm, in the rendered PDF, that Figure 2's now-larger main-text panel grid still fits within its existing `{=latex}` minipage block without overflowing the page margin (a 2-row-by-3-column grid at `panel_width=2.3` gives a total width around 6.9 inches — check this is within the manuscript's text width; if it overflows, reduce `panel_width` slightly rather than leaving an overflowing figure).

- [ ] **Step 6: Commit**

```bash
git add src/bigp3_als/render_expanded.py scripts/13_render_figures.py output/expanded/figures/ build_expanded/
git commit -m "fix: enlarge Figure 1 legend/text and Figure 2 main-text panel grid, optional grayscale encoding for Figure 4"
```

---

### Task 10: Restructure Table 2 — move the full per-cohort table to the supplement, keep a short main-text summary

**Files:**
- Modify: `manuscript/manuscript_expanded.md:204-225` (Table 2)
- Modify: `supplementary/supplement_expanded.md` (new table, after Task 1's new grid-size/paradigm columns are available)

**Interfaces:**
- Consumes: Task 1's `documented_protocol_metadata()` output (grid size, checkerboard indicator) and the existing `cohort_calibration.csv`/per-cohort metrics already feeding the current Table 2.

The reviewer's explicitly stated preference: "I would favor moving the full table to the supplement. Figure 1 already communicates the intercept and slope results much better." This task follows that stated preference directly, and additionally folds in the grid-size/paradigm columns Task 1 produced, since the reviewer separately asked for a table carrying "cohort; ALS documentation; participants; grid size; paradigm; equipment; median selection interval" — equipment is omitted from that list per the Global Constraints (it is documented but constant across the whole archive, so a column of 18 identical values adds nothing).

- [ ] **Step 1: Read the current Table 2 exactly**

Read `manuscript/manuscript_expanded.md:204-225` in full (header, all 18 rows, caption) before editing anything — do not work from the earlier research summary, which may be stale after Tasks 1-9's edits.

- [ ] **Step 2: Move the full table to the supplement, with two new columns**

In `supplementary/supplement_expanded.md`, add a new table (after the current last-numbered table — check the file's actual current highest `Table S` number first, do not assume) titled "Per-cohort composition, documented protocol metadata, and withheld-cohort performance," with the same rows and columns as the current manuscript Table 2, PLUS two new columns: "Grid size" and "Checkerboard paradigm" (yes/no), sourced from Task 1's `documented_protocol_metadata()` output (the exact per-cohort values are in the Global Constraints table above — use those, or re-derive from the regenerated `output/expanded/` data if Task 1 wrote a CSV containing them).

- [ ] **Step 3: Replace the main-text Table 2 with a short summary**

In `manuscript/manuscript_expanded.md`, replace the current 9-column Table 2 with a shorter table keeping only: Cohort, Participants, Records, Selections, Observed accuracy, MAE, AUC — dropping the "Calib. intercept" and "Calib. slope (95% CI)" columns (Figure 1 already shows these per cohort, with confidence intervals, more legibly than a table can). Update the table's caption to note the full per-cohort table including documented grid size and paradigm is in the supplement (cite its real table number from Step 2), and that calibration intercept/slope per cohort are shown in Figure 1.

- [ ] **Step 4: Fix the CI-column split in whichever table still carries it**

If any of the remaining per-cohort tables (the new supplement table, or any other) still carries a combined "estimate (low to high)" column in one cell (e.g. "1.578 (0.691 to 2.464)"), split it into three columns (estimate, lower CI, upper CI) as the reviewer suggested, to avoid the multi-line cell-wrapping problem the review found in the current PDF. Apply this to the new supplement table if it inherits the combined-column format from the current manuscript Table 2.

- [ ] **Step 5: Re-render and check both tables' PDF legibility**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"` and the supplement equivalent.
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript` then `--only supplement`.
Visually inspect the rendered PDF pages containing both tables (extract the relevant pages and read them, or use a PDF-to-text/image tool already used elsewhere in this repo's build) — confirm no cell wraps across more than 2 lines and the supplement table (now 11 columns: the original 9 plus 2 new, minus any combined-CI column split into 2 more) fits legibly, using `\small` and landscape wrapping (the existing pattern from Table S6) if needed.

- [ ] **Step 6: Commit**

```bash
git add manuscript/manuscript_expanded.md supplementary/supplement_expanded.md build_expanded/
git commit -m "refactor: move the full per-cohort table to the supplement with documented grid-size/paradigm columns, shorten the main-text table"
```

---

### Task 11: Data and Code Availability — cite the exact commit hash; document the Zenodo/OSF archival step as a human action

**Files:**
- Modify: `manuscript/manuscript_expanded.md:327-329`
- Modify: `submission/AUTHOR_ACTIONS.md`

**Interfaces:** none — text-only.

No GitHub release, tag, or Zenodo/OSF DOI exists for this repository yet (confirmed: no remote is configured, `git remote -v` is empty). Minting a DOI requires creating external accounts this plan cannot do — that part is a human action. Citing the exact commit hash of the submitted analysis is mechanical and can be done now.

- [ ] **Step 1: Get the current commit hash**

Run: `git rev-parse HEAD` — this is the current HEAD at the time this task runs, not the eventual final commit: Tasks 12, 13, and 14 all commit after this one, and the final whole-branch review (Task 15) may add its own fix-wave commit on top of those. The hash cited here will necessarily be superseded before this plan finishes. That is expected, not an error — cite the real current hash now (never a placeholder string), and rely on Task 15's own checklist, which already includes "give the commit-hash citation one final one-line update to the true final commit" as one of its review-scope items.

- [ ] **Step 2: Update the manuscript's Data and Code Availability section**

In `manuscript/manuscript_expanded.md:327-329`, change:
```
Analysis code and frozen outputs are available at https://github.com/Alon-Gorenshtein/study_bigp3_als_calibration.
```
to:
```
Analysis code and frozen outputs are available at https://github.com/Alon-Gorenshtein/study_bigp3_als_calibration (commit {HASH}).
```
using the real hash from Step 1.

- [ ] **Step 3: Document the remaining human action**

In `submission/AUTHOR_ACTIONS.md`, add (or update, if a similar item already exists from the prior revision round) an item: "Before submission: push this repository to the cited GitHub URL if not already done, create a tagged release matching the cited commit, archive that release and the frozen `output/expanded/` outputs on Zenodo or OSF, obtain a DOI, and replace the commit-hash citation in `manuscript/manuscript_expanded.md`'s Data and Code Availability section with the archived-release DOI once minted." This is not required for the scientific conclusion (the reviewer says so explicitly) but strengthens a paper whose selling point includes reproducibility.

- [ ] **Step 4: Re-render**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`.

- [ ] **Step 5: Commit**

```bash
git add manuscript/manuscript_expanded.md submission/AUTHOR_ACTIONS.md build_expanded/
git commit -m "docs: cite the exact commit hash in Data and Code Availability, document Zenodo/OSF archival as a remaining human action"
```

---

### Task 12: Minor textual bundle — phrasing, I-squared symbol, cohort-label spacing

**Files:**
- Modify: `manuscript/manuscript_expanded.md:95,231,277,315`
- Modify: `supplementary/supplement_expanded.md:57` (and lines 95,99,168,200,202,250,256,266,311 for the I-squared symbol — confirm exact current line numbers after Tasks 1-11's edits before touching)

**Interfaces:** none — text-only, except the I-squared symbol needs a PDF-rendering check.

- [ ] **Step 1: "the slope agreed" and "cannot be promised"**

In `manuscript/manuscript_expanded.md:277`, change "the slope agreed, at tau = 0.43" to "slope heterogeneity led to the same conclusion, at tau = 0.43" (matching the reviewer's suggested consistent phrasing, and matching how the abstract already frames this per the reviewer's own observation).

In `manuscript/manuscript_expanded.md:315`, change "a cohort outside the archive cannot be promised discrimination above chance or skill above zero" to "the prediction interval for a cohort outside the archive does not exclude discrimination at chance or skill at or below zero" (the reviewer's suggested more conventional phrasing).

- [ ] **Step 2: I-squared → I² — verify actual PDF rendering before committing to one form**

The manuscript and supplement currently spell out "I-squared" consistently (6 instances in the manuscript, 3 in the supplement — confirm the current count with `grep -c "I-squared"` on both files first, since Tasks 1-11 may have added or removed instances). The reviewer wants "I²" in the final typeset version.

Before doing a global replace: this repository has direct precedent (the prior revision round's Greek-rho fix) that a raw Unicode superscript character can silently fail to render in the xelatex PDF pipeline even though it displays fine in the markdown source or DOCX. Test both approaches on one instance first:
1. Replace one "I-squared" with the raw Unicode "I²" (U+00B2 SUPERSCRIPT TWO after a literal "I").
2. Rebuild just the manuscript (`UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`) and extract the PDF's text layer (e.g. `pdftotext` or however the prior round verified the rho fix — check `docs/editorial_revision_log.md` for the exact command used) to confirm the glyph survived.
3. If it did not render correctly, use inline LaTeX math instead: `$I^2$` (matching the `$\rho$` precedent), and re-verify.

Once the working form is confirmed on one instance, apply it to every remaining "I-squared" occurrence in both `manuscript/manuscript_expanded.md` and `supplementary/supplement_expanded.md`. Confirm the DOCX rendering is unaffected (the DOCX writer may need the plain Unicode form even if the PDF path needs LaTeX math — check both output formats, not just the PDF, matching how the rho fix was verified for both formats last time).

- [ ] **Step 3: Cohort-label spacing — "StudyH" → "Study H"**

Fix every instance where the internal no-space code label leaked into prose (confirm the exact current locations with `grep -n "Study[A-Z][0-9]*'s\|Study[A-Z][0-9]* \|In Study[A-Z]\|StudyS1\|StudyH\|StudyE\|StudyR\|StudyS2\|StudyJ" manuscript/manuscript_expanded.md supplementary/supplement_expanded.md` before editing, since Tasks 1-11 may have touched these same paragraphs and shifted line numbers — do not rely on the line numbers below without reconfirming):
- `manuscript/manuscript_expanded.md:95`: "StudyS1's cluster resamples" → "Study S1's cluster resamples" (note: Task 2 also edits this exact area — if Task 2 already fixed the spacing incidentally while rewriting the sentence, this step becomes a no-op; check before editing).
- `manuscript/manuscript_expanded.md:231`: six occurrences ("In StudyH", "in StudyE, StudyR, StudyS2 and StudyS1", "StudyS1 is the limiting case", "In the sixth, StudyJ") — add the space in every one: "Study H", "Study E, Study R, Study S2 and Study S1", "Study S1", "Study J".
- `supplementary/supplement_expanded.md:57`: "StudyS1's resamples" → "Study S1's resamples" (same overlap note as above — Task 2 touches this exact sentence too; check first).

- [ ] **Step 4: Re-render and re-scan**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"` and the supplement equivalent.
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript` then `--only supplement`.
Run the full test suite: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest -v 2>&1 | tail -10`.

- [ ] **Step 5: Commit**

```bash
git add manuscript/manuscript_expanded.md supplementary/supplement_expanded.md build_expanded/
git commit -m "fix: phrasing tightening, I-squared symbol (PDF-verified), cohort-label spacing"
```

---

### Task 13: Novelty citations — Colwell 2014, Won 2019, Song 2024, and an explicit priority claim

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (Introduction, lines 35-46; Discussion, line 281 area; References, after the current entry 36)

**Interfaces:** none — text and reference-list additions only.

A separate novelty/prior-art check (run independently of the peer review, and already reconciled with this manuscript's existing framing) confirms the paper's central claim is not previously published, but flagged three related papers not yet cited: a "projected accuracy" performance-prediction measure (Colwell et al. 2014), an RSVP-based performance predictor (Won et al. 2019), and a 2024 cross-dataset P300 signal-alignment study (Song et al. 2024) that evaluates a different question (ERP-classification transfer, not calibration-to-accuracy transportability) and should be distinguished from this study rather than treated as a duplicate. All three citations below have been independently verified against PubMed/PMC and Crossref (DOI and full author list cross-checked against the primary record, not a title-only match) — use them exactly as given; do not re-derive or alter them.

- [ ] **Step 1: Add the three references to the References section**

The current reference list runs 1-36 (confirm this is still true after Tasks 1-12's edits — another task may have added a reference for a new statistical method; if so, these become the next three numbers after whatever the list actually ends at, not necessarily 37-39). Append, in the exact existing AMA format:

```
37. Colwell KA, Throckmorton CS, Collins LM, Morton KD. Projected accuracy metric for the P300 Speller. *IEEE Trans Neural Syst Rehabil Eng*. 2014;22(5):921-925. doi:10.1109/TNSRE.2014.2324892
38. Won K, Kwon M, Jang S, Ahn M, Jun SC. P300 speller performance predictor based on RSVP multi-feature. *Front Hum Neurosci*. 2019;13:261. doi:10.3389/fnhum.2019.00261
39. Song M, Gwon D, Jun SC, Ahn M. Signal alignment for cross-datasets in P300 brain-computer interfaces. *J Neural Eng*. 2024;21(3):036007. doi:10.1088/1741-2552/ad430d
```

(renumber if the list does not actually end at 36 — keep the three references and their content identical, only the leading numbers change).

- [ ] **Step 2: Cite Colwell 2014 and Won 2019 in the Introduction, alongside the existing within-cohort-limitation discussion**

Read `manuscript/manuscript_expanded.md:35-46` in full first. In the paragraph beginning "Two features of that literature limit what it can support," which currently discusses the within-cohort limitation of prior performance-prediction work (citing Mainsah, ref [15]) — add Colwell (projected accuracy from flash-level data) and Won (RSVP multi-feature performance prediction) as further instances of the same limitation, in the same sentence or an adjacent one, e.g. inserting after the existing Mainsah sentence in the first Introduction paragraph: "A projected-accuracy measure built from flash-level data and a multi-feature predictor built from a separate rapid-serial-visual-presentation task have made related predictions from within-session or within-study data.[37,38]" (adapt the exact wording to fit smoothly with what is actually there once Tasks 1-12 have possibly touched nearby lines — do not disrupt the existing citation flow for refs [9]-[15]).

- [ ] **Step 3: Distinguish Song 2024 from this study's question**

In the paragraph beginning "Evaluating transportability also imposes a requirement that has not previously been met in this setting" (`manuscript/manuscript_expanded.md`, same Introduction section), add one sentence distinguishing recent cross-dataset P300 work from this study's specific question: "A recent cross-dataset evaluation aligned P300 event-related-potential signals across independent archives to improve classification transfer, a different question from whether a fitted calibration-to-accuracy mapping itself transports numerically.[39]" Place this where it reads naturally — likely right before or after the existing archive-availability sentence citing ref [18].

- [ ] **Step 4: Add an explicit priority statement**

Somewhere in the same two Introduction paragraphs (not the Abstract — the abstract is at its word limit per Global Constraints), add one sentence stating the paper's priority claim explicitly, in the manuscript's own dry, precise register rather than a promotional one: "To our knowledge, no published study has evaluated whether a calibration-derived score's fitted mapping to online accuracy transports to a source study withheld from its development, as distinct from evaluating the score's within-cohort association or its within-study discrimination." Place it as the closing sentence of whichever of the two paragraphs (limitation-of-prior-work, or transportability-requirement) it reads more naturally after, once both are in front of the implementer with Steps 2-3's edits already applied.

- [ ] **Step 5: Re-render and re-scan**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"` — pay particular attention to whether the new "to our knowledge" sentence or the Colwell/Won/Song additions introduce any promotional-register tells (the de-AI scan's Tier 1/Tier 2 vocabulary list flags exactly this kind of overclaiming phrasing).
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`.
Confirm the three new DOIs render correctly and are clickable/well-formed in the PDF and DOCX.

- [ ] **Step 6: Commit**

```bash
git add manuscript/manuscript_expanded.md build_expanded/
git commit -m "docs: cite Colwell 2014, Won 2019, and Song 2024, add an explicit priority statement to the Introduction"
```

---

### Task 14: Full rebuild, word-count check, de-AI scan, test suite, revision log

**Files:**
- Modify: `docs/editorial_revision_log.md`
- Rebuild: `build_expanded/*.pdf`, `build_expanded/*.docx`

**Interfaces:** none — verification and housekeeping only.

This task runs last, after Task 13's novelty citations, so its word-count and rebuild checks cover every change this plan makes, not just Tasks 1-12's.

- [ ] **Step 1: Full rebuild of all three documents**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py` (no `--only` flag — rebuild manuscript, cover letter, and supplement together, to catch any cross-document inconsistency the per-document `--only` runs in earlier tasks might have missed).

- [ ] **Step 2: Word-count check against the 12,000-word ceiling**

Count the manuscript's main text (excluding front matter, references, and section headers — matching the method the prior revision round used, documented in `docs/editorial_revision_log.md`). Confirm it remains under JNE's 12,000-word ceiling. If Tasks 1-13 pushed it close to or over that limit, this is a real problem requiring a targeted condensation pass — do not silently let it slide; report the actual count.

Also re-confirm the abstract word count is still ≤300 (Global Constraints noted it was 289/300 before this round; Task 12's phrasing changes and Task 13's Introduction additions are the only tasks touching the abstract's immediate vicinity, and none of this plan's tasks target the abstract directly, so it should be unchanged — verify rather than assume).

- [ ] **Step 3: Full test suite**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest -v 2>&1 | tail -20`.
Expected: all tests pass (count will be higher than the prior round's 169, given Tasks 1-3 added new tests).

- [ ] **Step 4: De-AI-writing scan on all three rendered documents**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"`, the same for `supplementary/supplement_expanded.md` and `manuscript/cover_letter_expanded.md`. Confirm zero em dashes in all three (the hard constraint); note any new Tier 1/Tier 2 vocabulary hits and judge each on its merits (legitimate technical terminology vs. a real tell), matching the standard established in the prior revision round.

- [ ] **Step 5: Append to the editorial revision log**

In `docs/editorial_revision_log.md`, add a new dated section summarizing this second pre-submission review pass: the major comments addressed (protocol-descriptor metadata, matched-cohort bootstrap comparison, joint-bootstrap covariance, log-scale MAE labeling, independence wording, practical-use softening, figure/table legibility, commit-hash citation, novelty citations, minor textual fixes), and explicitly note the one consciously deferred item (Firth/penalized regression for the bootstrap, per Task 2).

- [ ] **Step 6: Commit**

```bash
git add build_expanded/ docs/editorial_revision_log.md
git commit -m "docs: full rebuild, word-count and test verification, revision log entry for the second pre-submission review pass"
```

---

### Task 15: Final whole-branch review

Follow the subagent-driven-development skill's final-review process exactly as used in the prior revision round: dispatch the final code reviewer (adapted `code-reviewer.md` template for this manuscript-revision domain) on the most capable available model, covering the FULL diff from this plan's base commit to the tip of Task 14. Apply at most one fix wave for whatever it finds, dispatch one scoped re-review of that fix wave, and adjudicate any residual finding with the human partner rather than looping further — matching the "no second fix wave" rule from the prior round.

Pay particular attention, in the review brief's Global Constraints, to:
- Every numeric claim in Tasks 1-4 traces to a real, regenerated output file (not a hand-typed number).
- No task reintroduced "prespecified" language (the exact regression the prior round's residual fix corrected).
- The joint-bootstrap covariance matrix (Task 3) is genuinely symmetric and its diagonal matches the per-cohort variances a reader would expect from the existing per-cohort bootstrap.
- Table 2's move to the supplement (Task 10) did not leave a dangling main-text cross-reference to a table number or column that no longer exists in the main text.
- The commit-hash citation (Task 11) reflects the ACTUAL final commit, not an intermediate one from partway through this plan's execution — this may require a final one-line update after the whole-branch review's own fix commits land, since those commits change the hash again.
