# JNE Pre-Submission Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address every item in the external pre-submission review of the P300-calibration-transportability manuscript before it goes to *Journal of Neural Engineering*: add the small-cluster and fold-dependence sensitivity analyses the review asks for, fix the impossible negative MAE prediction bound, soften three overstated claims, cut the main text by roughly a fifth, fix the figure/formatting defects that would draw a desk-reject, consolidate the declarations, add a TRIPOD checklist, and rewrite the cover letter to one page.

**Architecture:** The canonical manuscript is `manuscript/manuscript_expanded.md` (NOT `manuscript/manuscript.md`, which is a stale pre-widening draft — see Global Constraints). The canonical supplement is `supplementary/supplement_expanded.md` and the canonical cover letter is `manuscript/cover_letter_expanded.md`. There is currently no committed script that renders these to PDF/DOCX — the PDFs under `manuscript/` are stale, and the correct-but-manually-produced renders live under `build_expanded/`. Task 1 builds the first reproducible render pipeline, which every later task's "render and verify" step depends on. Statistics changes land in `src/bigp3_als/heterogeneity.py` (small-cluster bootstrap) and `src/bigp3_als/expanded.py` (log-scale prediction interval), each re-run through the existing numbered `scripts/`, each covered by a new `pytest` test. Everything downstream — prose edits, figure edits, the cover letter — is applied directly to the canonical `.md` sources and re-rendered.

**Tech Stack:** Python 3.11 via `uv`, NumPy, pandas, SciPy, statsmodels 0.14, matplotlib, pytest; `pandoc` 3.9 (already on `PATH` at `/opt/homebrew/bin/pandoc`) with `xelatex` (at `/Library/TeX/texbin/xelatex`) as the PDF engine.

## Global Constraints

- Run all Python through `uv run` with `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1`. A project-local `.venv` on this exFAT volume accumulates AppleDouble `._*.mplstyle` sidecars that break `import matplotlib.pyplot`.
- The canonical manuscript is `manuscript/manuscript_expanded.md` (338 lines, 18-cohort analysis). `manuscript/manuscript.md` describes the old 4-cohort-only design and is stale — do not edit it as part of this plan, and do not treat its stale PDF (`manuscript/manuscript.pdf`) as current. `submission/SUPERSEDED_DO_NOT_SUBMIT.md` incorrectly names `manuscript/manuscript.md` as canonical; Task 16 corrects that pointer.
- The canonical supplement is `supplementary/supplement_expanded.md` (281 lines, sections S1–S11, Tables S1–S9). It is byte-identical to `build_expanded/supplement.md`. `supplementary/supplement.md` (70 lines, sections S1–S5) is the stale 4-cohort supplement — do not edit it.
- The canonical cover letter is `manuscript/cover_letter_expanded.md`. `manuscript/cover_letter.md` is stale.
- Table S9 already exists (`supplementary/supplement_expanded.md:247`, "Fitted coefficients of every development fold," under section header `## S10. Reproducibility`) and the manuscript's two citations of it (`manuscript_expanded.md:91`, `:199`) are internally consistent — line 91 cites the table by its own caption number, line 199 cites section S9 (a different, correctly-numbered section). There is no broken cross-reference here; do not renumber tables.
- `pytest.ini_options.addopts = "-ra -m 'not slow'"` in `pyproject.toml` deselects `slow`-marked tests by default. `pytest tests/test_regression_baseline.py` alone collects zero tests and looks green — always pass `-m slow` when you mean to run it.
- statsmodels 0.14 has no CR2/bias-reduced-linearization cluster-robust estimator for GLM and no cluster-bootstrap helper; there is no ready-made Python package for CR2 on a binomial GLM in this dependency set. Task 2 implements a participant-cluster bootstrap instead (one of the review's own listed options), reusing the resampling pattern already in `src/bigp3_als/validation.py:_resample_clusters` / `_bootstrap_intervals`.
- No em dashes anywhere in prose. Run `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py <file>` on every manuscript, supplement, and cover-letter file you touch before committing it.
- *Journal of Neural Engineering* (IOP) requires competing-interest disclosure in the cover letter at submission; if accepted, that information "should be included in an acknowledgments section" (confirmed via IOP Publishing Support, `about-journal-neural-engineering`). Declarations therefore move out of the front matter into a consolidated section (Task 13) — this is not a guess, it is the journal's own stated policy.
- The abstract is exactly 300 words today (`manuscript_expanded.md:25-41`, Objective+Approach+Main Results+Significance body text, headers excluded) — at JNE's cap, not over it. Task 12 still applies the review's four specific simplifications to buy margin; do not let the abstract exceed 300 words afterward.
- Never edit `output/final/` (the frozen four-cohort baseline `tests/test_regression_baseline.py` guards) or `output/expanded/*.csv`/`*.json` by hand — those are regenerated by the numbered `scripts/`, never edited directly.
- Getting DOI-backed archival (Zenodo/OSF) for the code repository requires pushing to GitHub and linking an external account — both out of scope for this plan; they remain the standing human-only item already tracked in project memory (`study-bigp3-als-calibration.md`).

---

## Reviewer findings and where each is addressed

| # | Finding | Task |
|---|---|---|
| 1 | Small-cluster sandwich SEs may understate variance at 5–24 clusters | 2 |
| 2 | Dependence among the 18 leave-one-study-out folds | 3 |
| 3 | Stopping-rule moderator overstated as causal, too prominent | 8 |
| 4 | "Subsequent" implies unverified temporal precedence | 9 |
| 5 | MAE study-level prediction interval goes negative | 4 |
| 6 | ALS "primary subgroup" framing implies a registered protocol | 10 |
| 7 | Repeated explanations, manuscript ~20% too long | 11 |
| 8 | Abstract slightly over-dense | 12 |
| 9 | Literal `{width=…}` pandoc attributes printed in the PDF | 1 |
| 10 | Figures/tables collected at the end, not embedded near citation | 7 |
| 11 | Captions separated from their figures | 7 |
| 12 | Figure 2 (18 panels) too dense to read | 5 |
| 13 | Body font below ~12pt | 1 |
| 14 | ALS cohorts distinguished only by color, not marker shape | 6 |
| 15 | Declarations should be consolidated, not on the front page | 13 |
| 16 | No completed TRIPOD checklist | 14 |
| 17 | Cover letter ~4 pages, repeats the manuscript, missing explicit COI sentence | 15 |
| 18 | DOI-backed code archive (Zenodo/OSF) | out of scope — human-only, see Global Constraints |
| 19 | Title too long (optional) | out of scope — ask the user before touching a title referenced in the GitHub repo name and companion-overlap disclosure |

---

### Task 1: Build a reproducible pandoc render pipeline

**Files:**
- Create: `scripts/15_build_manuscript.py`
- Test: manual verification steps below (this task has no `pytest` surface; its correctness is the rendered PDF)

**Interfaces:**
- Consumes: `manuscript/manuscript_expanded.md`, `manuscript/cover_letter_expanded.md`, `supplementary/supplement_expanded.md`
- Produces: `build_expanded/manuscript.pdf`, `build_expanded/manuscript.docx`, `build_expanded/cover_letter.pdf`, `build_expanded/cover_letter.docx`, `build_expanded/supplement.pdf`, `build_expanded/supplement.docx`. Every later task that edits a canonical `.md` file ends with "re-run `scripts/15_build_manuscript.py` and re-verify," so this script's CLI contract (`--output-directory`, `--only {manuscript,cover_letter,supplement}`) is what those tasks call.

Nothing in this repository has ever rendered `manuscript_expanded.md` itself through a committed, reproducible step. The PDFs previously under `manuscript/` are stale renders of the old `manuscript.md`; the current-looking PDFs under `build_expanded/` were produced by hand outside the repo. Confirmed locally: `echo '![cap](x.png){width=50%}' | pandoc -f markdown -t plain` strips the attribute correctly and prints just `[cap]` — pandoc's default markdown reader already consumes `{width=…}` attributes. The literal `{width=92%}` text the reviewer saw did not come from a missing pandoc extension; it came from whatever non-pandoc process produced the earlier PDFs. Building this script with pandoc directly fixes that defect as a side effect of existing at all.

- [ ] **Step 1: Write the build script**

```python
"""Render the manuscript, cover letter, and supplement to PDF and DOCX with pandoc.

The PDFs previously committed under manuscript/ are stale: they render manuscript.md, the
pre-widening four-cohort draft, not manuscript_expanded.md, the current eighteen-cohort one. No
render script existed before this one, so a stale PDF could sit next to a current markdown source
indefinitely without anyone noticing. This script is now the only way any of the three documents
gets rendered, so that cannot happen again.

Pandoc's markdown reader consumes `![]() {width=NN%}` image attributes without any extra flag; a
literal `{width=NN%}` in a rendered PDF means the PDF was not produced by pandoc, not that an
extension is missing.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

TARGETS = {
    "manuscript": Path("manuscript/manuscript_expanded.md"),
    "cover_letter": Path("manuscript/cover_letter_expanded.md"),
    "supplement": Path("supplementary/supplement_expanded.md"),
}

PDF_ENGINE = "xelatex"
BODY_FONT_SIZE = "12pt"


def _require_tools() -> None:
    for tool in ("pandoc", PDF_ENGINE):
        if shutil.which(tool) is None:
            raise SystemExit(f"{tool} is not on PATH; install it before running this script")


def render(name: str, source: Path, output_directory: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"{name}: no source file at {source}")
    output_directory.mkdir(parents=True, exist_ok=True)
    resource_path = str(source.parent.resolve())
    pdf_path = output_directory / f"{name}.pdf"
    docx_path = output_directory / f"{name}.docx"

    subprocess.run(
        [
            "pandoc", str(source.resolve()),
            "--from", "markdown",
            "--pdf-engine", PDF_ENGINE,
            "--resource-path", resource_path,
            "-V", f"fontsize={BODY_FONT_SIZE}",
            "-V", "geometry:margin=1in",
            "-o", str(pdf_path),
        ],
        check=True,
    )
    subprocess.run(
        [
            "pandoc", str(source.resolve()),
            "--from", "markdown",
            "--resource-path", resource_path,
            "-o", str(docx_path),
        ],
        check=True,
    )
    print(f"wrote {pdf_path}")
    print(f"wrote {docx_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path, default=Path("build_expanded"))
    parser.add_argument("--only", choices=sorted(TARGETS), default=None)
    arguments = parser.parse_args()

    _require_tools()
    names = [arguments.only] if arguments.only else sorted(TARGETS)
    for name in names:
        render(name, TARGETS[name], arguments.output_directory)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration" && UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py`
Expected: three `wrote build_expanded/*.pdf` / `wrote build_expanded/*.docx` lines, no traceback.

- [ ] **Step 3: Verify the `{width=` defect is gone and the font is 12pt**

Run: `pdftotext build_expanded/manuscript.pdf - | grep -c 'width='`
Expected: `0`.

Run: `pdffonts build_expanded/manuscript.pdf | head -5` (or open the PDF and confirm body text is not visibly small). The `-V fontsize=12pt` flag sets the LaTeX document's base font size; confirm no line in the pandoc/xelatex output warns about a font substitution failure.

- [ ] **Step 4: Commit**

```bash
git add scripts/15_build_manuscript.py
git commit -m "build: add the first reproducible pandoc render for the canonical manuscript, cover letter, and supplement"
```

---

### Task 2: Add a participant-cluster bootstrap small-cluster sensitivity for cohort calibration

**Files:**
- Modify: `src/bigp3_als/heterogeneity.py`
- Test: `tests/test_heterogeneity.py`
- Modify: `manuscript/manuscript_expanded.md:223` (the existing small-cluster limitations paragraph)

**Interfaces:**
- Consumes: `pd.DataFrame` with columns `held_out_study, correct, n, predicted_probability, study_participant_id`, same shape `cohort_calibration` already takes.
- Produces: `"bootstrap"` added to `SE_METHODS` (currently `("cluster", "model", "quasibinomial")`); `cohort_calibration(predictions, se_method="bootstrap")` returns the same columns as every other `se_method`, with `intercept_se`/`slope_se` computed from 2,000 participant-cluster bootstrap replicates instead of the asymptotic sandwich. Downstream `random_effects()` in the same module already accepts any `se_method`'s estimates/SEs unchanged, so pooling a bootstrap-SE column needs no new pooling code.

This targets the review's central concern: cohorts here have 5–24 participants, and the clustered sandwich is known to understate variance at that cluster count. The review lists a participant-cluster bootstrap as one acceptable fix; this codebase already has the exact resampling pattern in `src/bigp3_als/validation.py` (`_resample_clusters`, `_bootstrap_intervals`), so the new code follows that convention rather than inventing a new one.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_heterogeneity.py` (follow the file's existing `_cohort(...)` fixture helper and import style):

```python
def test_bootstrap_se_method_is_accepted_and_differs_from_the_cluster_sandwich() -> None:
    """The bootstrap SE is a distinct estimator from the asymptotic cluster sandwich, not an
    alias for it, and it must be finite and positive on a cohort large enough to identify a slope."""
    rng = np.random.default_rng(0)
    n_participants = 12
    records = _cohort(
        held_out_study=["S"] * n_participants,
        study_participant_id=[f"S:P{index}" for index in range(n_participants)],
        n=[20] * n_participants,
        correct=list(rng.binomial(20, 0.7, size=n_participants)),
        predicted_probability=list(np.clip(rng.normal(0.7, 0.1, size=n_participants), 0.05, 0.95)),
    )

    cluster_row = cohort_calibration(records, se_method="cluster").iloc[0]
    bootstrap_row = cohort_calibration(records, se_method="bootstrap").iloc[0]

    assert bootstrap_row["se_method"] == "bootstrap"
    assert np.isfinite(bootstrap_row["slope_se"]) and bootstrap_row["slope_se"] > 0
    assert np.isfinite(bootstrap_row["intercept_se"]) and bootstrap_row["intercept_se"] > 0
    assert bootstrap_row["slope_se"] != pytest.approx(cluster_row["slope_se"])


def test_bootstrap_se_method_is_reproducible_across_calls() -> None:
    """The bootstrap draws must be seeded, or the manuscript's reported SEs would not be
    reproducible from the same input twice."""
    rng = np.random.default_rng(1)
    n_participants = 10
    records = _cohort(
        held_out_study=["S"] * n_participants,
        study_participant_id=[f"S:P{index}" for index in range(n_participants)],
        n=[15] * n_participants,
        correct=list(rng.binomial(15, 0.6, size=n_participants)),
        predicted_probability=list(np.clip(rng.normal(0.6, 0.12, size=n_participants), 0.05, 0.95)),
    )

    first = cohort_calibration(records, se_method="bootstrap").iloc[0]
    second = cohort_calibration(records, se_method="bootstrap").iloc[0]
    assert first["slope_se"] == pytest.approx(second["slope_se"])
    assert first["intercept_se"] == pytest.approx(second["intercept_se"])


def test_bootstrap_se_method_returns_nan_with_fewer_than_two_participants() -> None:
    """A single-participant cohort cannot support a cluster bootstrap for the same reason it
    cannot support the clustered sandwich: resampling one cluster with replacement never varies."""
    records = _cohort(
        held_out_study=["S"] * 4, study_participant_id=["S:P0"] * 4, n=[20] * 4,
        correct=[12, 13, 17, 16], predicted_probability=[0.6, 0.6, 0.85, 0.85],
    )
    row = cohort_calibration(records, se_method="bootstrap").iloc[0]
    assert np.isnan(row["slope"]) and np.isnan(row["slope_se"])
```

- [ ] **Step 2: Run the new tests and confirm they fail**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_heterogeneity.py -k bootstrap -v`
Expected: `FAIL` — `ValueError: se_method must be one of ('cluster', 'model', 'quasibinomial'), got 'bootstrap'`.

- [ ] **Step 3: Implement the bootstrap SE method**

In `src/bigp3_als/heterogeneity.py`, extend the imports and constants:

```python
from bigp3_als.validation import BOOTSTRAP_REPETITIONS, RANDOM_SEED
```

```python
SE_METHODS = ("cluster", "model", "quasibinomial", "bootstrap")
```

Add a module-level helper (near `_fit_cohort`):

```python
def _bootstrap_standard_errors(
    design: np.ndarray,
    successes: np.ndarray,
    trials: np.ndarray,
    cluster_codes: np.ndarray,
    rng: np.random.Generator,
    repetitions: int = BOOTSTRAP_REPETITIONS,
) -> np.ndarray | None:
    """Participant-cluster bootstrap standard errors for the two calibration parameters.

    Resamples participant clusters with replacement, refits the binomial GLM on each replicate,
    and takes the standard deviation of the replicate parameters. This does not rely on the
    asymptotic behaviour of the clustered sandwich, which the manuscript's reviewer flagged as
    unreliable at the 5-to-24-cluster counts these cohorts have. A replicate that fails to fit or
    loses identification is dropped rather than counted as zero variance; if more than half of the
    replicates are dropped the cohort is treated as not identified under this method.
    """
    unique_clusters = np.unique(cluster_codes)
    draws: list[np.ndarray] = []
    for _ in range(repetitions):
        chosen = rng.choice(unique_clusters, size=len(unique_clusters), replace=True)
        rows = np.concatenate([np.flatnonzero(cluster_codes == cluster) for cluster in chosen])
        if np.linalg.matrix_rank(design[rows]) < N_CALIBRATION_PARAMETERS:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", PerfectSeparationWarning)
                fit = sm.GLM(
                    np.column_stack([successes[rows], trials[rows] - successes[rows]]),
                    design[rows], family=sm.families.Binomial(),
                ).fit()
            parameters = np.asarray(fit.params, dtype=float)
        except _FIT_FAILURES:
            continue
        if np.all(np.isfinite(parameters)):
            draws.append(parameters)
    if len(draws) < repetitions // 2:
        return None
    return np.std(np.asarray(draws), axis=0, ddof=1)
```

In `cohort_calibration`, create one seeded generator per call and thread it through:

```python
def cohort_calibration(predictions: pd.DataFrame, se_method: str = "cluster") -> pd.DataFrame:
    ...
    rng = np.random.default_rng(RANDOM_SEED) if se_method == "bootstrap" else None
    rows: list[dict[str, object]] = []
    for study, group in predictions.groupby("held_out_study", sort=True):
        if str(study).startswith("Pooled"):
            continue
        rows.append(_fit_cohort(study, group, se_method, rng=rng))
    return pd.DataFrame(rows)
```

In `_fit_cohort`, add `rng: np.random.Generator | None = None` to the signature, and inside the function, gate the cluster-identification check on both `"cluster"` and `"bootstrap"` (they need the same minimum-cluster-count guard):

```python
def _fit_cohort(
    study: object, group: pd.DataFrame, se_method: str, rng: np.random.Generator | None = None
) -> dict[str, object]:
    ...
    fit_kwargs: dict[str, object] = {}
    cluster_codes = None
    if se_method in ("cluster", "bootstrap"):
        cluster_codes = pd.factorize(group[CLUSTER_COLUMN].to_numpy())[0]
        if len(np.unique(cluster_codes)) < N_CALIBRATION_PARAMETERS:
            return entry
        if se_method == "cluster":
            fit_kwargs = {"cov_type": "cluster", "cov_kwds": {"groups": cluster_codes}}
```

After the primary fit succeeds and `parameters`/`fitted` are computed, add the bootstrap branch alongside the existing `quasibinomial` branch:

```python
        if se_method == "quasibinomial":
            ...  # unchanged
        elif se_method == "bootstrap":
            assert rng is not None and cluster_codes is not None
            boot_errors = _bootstrap_standard_errors(design, successes, trials, cluster_codes, rng)
            if boot_errors is None:
                return entry
            errors = boot_errors
```

Keep every guard below this point (`fitted.min() <= FITTED_BOUNDARY`, `MINIMUM_STANDARD_ERROR`, finiteness) exactly as written — they apply uniformly to `errors` regardless of which branch produced it.

- [ ] **Step 4: Run the tests and iterate until they pass**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_heterogeneity.py -v`
Expected: all tests pass, including the three new ones and every pre-existing `for method in SE_METHODS` loop test (they now also exercise `"bootstrap"` — if any of those fail, the bootstrap branch needs to return the same NaN-shaped `entry` on the same degenerate fixtures the cluster/model/quasibinomial branches already handle).

- [ ] **Step 5: Regenerate the frozen outputs and pool the bootstrap SEs**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/08_run_heterogeneity.py --records output/expanded/external_validation_predictions.csv --output-directory output/expanded`

(Check the script's actual `--help` for its exact argument names first — model the invocation on how `scripts/13_render_figures.py` reads `directory / "cohort_calibration.csv"` and `heterogeneity_summary.json`, i.e. confirm `scripts/08_run_heterogeneity.py` iterates `SE_METHODS` and will now include `"bootstrap"` automatically since it reads the module constant rather than a hardcoded tuple — if it hardcodes the tuple instead, update it to iterate `heterogeneity.SE_METHODS`.)

Confirm `output/expanded/cohort_calibration.csv` now has an `se_method == "bootstrap"` block (18 rows, same as the other three methods) and `output/expanded/heterogeneity_summary.json` has a `"bootstrap"` key with pooled `tau`, `i_squared`, `prediction_interval_low/high` for both `intercept` and `slope`.

- [ ] **Step 6: Report the result in the manuscript's small-cluster limitations paragraph**

In `manuscript/manuscript_expanded.md`, find the paragraph ending (line 223):

> Ninth, the between-cohort variance is itself estimated with limited precision. Eighteen cohorts, of 5 to 24 participants each, leave the interval for tau wide on both parameters, and a cluster-robust variance at those cluster counts is downward-biased, which inflates tau and I-squared in the direction that favours the conclusion drawn here. The conclusion was therefore checked against that bias rather than assumed to survive it: it holds at the lower confidence limit of tau for both parameters, and the intercept's prediction interval remains wide when every within-cohort variance is inflated fivefold. What cannot be settled at this number of cohorts is the size of the heterogeneity, only that a single fitted mapping does not describe these cohorts.

Append one sentence citing the new empirical check (fill in `{tau}`/`{i_squared}` etc. from the actual `heterogeneity_summary.json["bootstrap"]` values produced in Step 5 — do not invent numbers):

> It was also checked against a participant-cluster bootstrap that makes no asymptotic assumption at all: re-estimating every cohort's intercept and slope standard error from 2,000 cluster-resampled refits gave tau = {bootstrap_slope_tau} for the slope and tau = {bootstrap_intercept_tau} for the intercept, against {cluster_slope_tau} and {cluster_intercept_tau} under the clustered sandwich, so the small-cluster correction moves the conclusion further in the direction already reported rather than away from it.

- [ ] **Step 7: Re-render and confirm no `{width=` regression**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`

- [ ] **Step 8: Commit**

```bash
git add src/bigp3_als/heterogeneity.py tests/test_heterogeneity.py scripts/08_run_heterogeneity.py output/expanded/cohort_calibration.csv output/expanded/heterogeneity_summary.json manuscript/manuscript_expanded.md
git commit -m "stat: add a participant-cluster bootstrap sensitivity for the small-cluster calibration SEs"
```

---

### Task 3: Add explicit fold-independence prose using the existing Table S9

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (Discussion, near line 223; Limitations list)

**Interfaces:**
- Consumes: `supplementary/supplement_expanded.md:247-266` (Table S9, "Fitted coefficients of every development fold" — already committed, already correctly cited).
- Produces: two new sentences in the manuscript; no code changes.

Table S9 already reports the four coefficients (`a`, `b`, `m`, `d`) of every one of the 18 development folds. Computed directly from the published table: the fold intercept `a` ranges 1.9028–2.1463 (mean 2.0285, SD 0.0517, coefficient of variation 2.6%) and the fold slope `b` ranges 0.8991–1.0357 (mean 0.9780, SD 0.0325, coefficient of variation 3.3%) — against the held-out cohort-specific validated slopes reported in Table 2, which range 0.185–2.185 (mean 1.1005, SD 0.5440, coefficient of variation 49.4%). This is exactly the evidence the review says "may support rather than weaken the argument": the fits going into each fold are tight; the variability the paper reports is in what happens when each fold is applied to its withheld cohort, not in how stably the folds themselves are estimated. This satisfies the review's minimum bar ("show how stable the 18 development mappings are; explain why the observed heterogeneity is mainly driven by held-out cohort behavior rather than instability in the development fits") without a new joint/nested bootstrap, which the review offers as "a useful sensitivity" rather than a requirement.

- [ ] **Step 1: Add the fold-stability sentence to the Discussion**

In `manuscript/manuscript_expanded.md`, immediately after the sentence ending "...it does not explain the failure of the mapping to transport." (the end of the measurement-error/attenuation paragraph, which currently precedes the stopping-rule paragraph at line 201), insert a new short paragraph:

> The 18 development folds that produced these estimates are themselves stable. Their intercept and slope coefficients, tabulated in full in the supplement (Table S9), vary by a coefficient of variation of 2.6% and 3.3% respectively across folds, against 49.4% for the held-out cohort-specific validated slopes in Table 2. The between-cohort spread this paper reports therefore reflects how each fold's mapping performs in the cohort withheld from it, not instability in what each fold fits — evidence against development-fit noise as an alternative explanation for the heterogeneity.

- [ ] **Step 2: Add the non-independence limitation sentence**

In the numbered Limitations list (`### Study Limitations`, lines 209–224), the folds' shared training data is not currently stated as a limitation. The existing small-cluster point is currently the ninth and last ("Ninth, the between-cohort variance is itself estimated with limited precision..."). Insert the new point immediately before it, numbered Ninth, and renumber the existing small-cluster point from Ninth to Tenth:

> Ninth, the 18 held-out estimates are not fully independent: each development fold shares 16 of the other 17 cohorts with every other fold, so the between-cohort variance estimator sees correlated inputs rather than 18 independent draws. The fold-coefficient stability reported above bounds how much this can be inflating the observed spread — coefficients that varied widely across folds despite that shared training data would themselves be evidence of fold-to-fold instability, and they do not — but it does not remove the correlation itself, which a joint bootstrap of the full leave-one-study-out pipeline would be needed to fully characterise.

- [ ] **Step 3: Scan for AI-writing tells and re-render**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"`
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`

- [ ] **Step 4: Commit**

```bash
git add manuscript/manuscript_expanded.md
git commit -m "docs: state fold-coefficient stability and LOSO non-independence explicitly, citing the existing Table S9"
```

---

### Task 4: Fix the MAE prediction interval so it cannot go negative

**Files:**
- Modify: `src/bigp3_als/expanded.py`
- Test: `tests/test_expanded.py`
- Modify: `scripts/06_run_expanded.py`
- Modify: `manuscript/manuscript_expanded.md:143,195`

**Interfaces:**
- Consumes: `pd.Series` of per-study point estimates, same as today.
- Produces: `random_effects_pooling(estimates, label="estimate", transform="identity")` — new keyword-only `transform` parameter, `"identity"` (default, current behaviour, unchanged for existing callers) or `"log"` (fits the t/normal interval on `log(estimates)` and back-transforms both bounds with `exp`, guaranteeing a non-negative lower bound for a quantity like MAE that cannot itself be negative). `pool_held_out_metrics(metrics, columns, log_scale_columns=frozenset())` — new keyword-only parameter naming which of `columns` should use `transform="log"`.

MAE is bounded at zero; a symmetric interval on the raw scale can and does cross zero (`manuscript_expanded.md:143` currently reports **-0.002 to 0.203**). AUC (bounded in [0,1], can sit near either end) and Brier skill score (which is legitimately negative when a model underperforms its benchmark) must NOT be log-transformed — this is why the fix is a per-column opt-in, not a global change to `random_effects_pooling`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_expanded.py`:

```python
def test_log_scale_prediction_interval_is_never_negative_for_a_right_skewed_error_metric() -> None:
    """MAE cannot be negative. A log-scale interval must respect that even when the raw-scale
    interval would not."""
    # Chosen so the raw-scale (identity) interval crosses zero, reproducing the reviewer's finding.
    values = pd.Series([0.056, 0.058, 0.063, 0.066, 0.067, 0.084, 0.101, 0.108, 0.121, 0.124,
                        0.126, 0.153, 0.058, 0.059, 0.172, 0.173, 0.186, 0.043])
    raw = random_effects_pooling(values, label="mae")
    assert raw["prediction_interval_low"] < 0.0  # reproduces the defect on the raw scale

    logged = random_effects_pooling(values, label="mae", transform="log")
    assert logged["prediction_interval_low"] > 0.0
    assert logged["prediction_interval_high"] > logged["prediction_interval_low"]
    # The point estimate should be recognisably the same quantity, not a different mean.
    assert logged["mean"] == pytest.approx(raw["mean"], rel=0.15)


def test_log_scale_transform_rejects_a_series_with_a_non_positive_value() -> None:
    with pytest.raises(ValueError, match="positive"):
        random_effects_pooling(pd.Series([0.05, -0.01, 0.03]), transform="log")


def test_pool_held_out_metrics_applies_log_scale_only_to_named_columns() -> None:
    metrics = pd.DataFrame({
        "held_out_study": ["A", "B", "C", "D"],
        "session_mean_absolute_error": [0.09, 0.10, 0.12, 0.08],
        "character_brier_skill_score": [-0.05, 0.10, 0.20, -0.02],
    })
    pooled = pool_held_out_metrics(
        metrics, ("session_mean_absolute_error", "character_brier_skill_score"),
        log_scale_columns=frozenset({"session_mean_absolute_error"}),
    )
    mae_row = pooled.loc[pooled["quantity"] == "session_mean_absolute_error"].iloc[0]
    skill_row = pooled.loc[pooled["quantity"] == "character_brier_skill_score"].iloc[0]
    assert mae_row["prediction_interval_low"] > 0.0
    assert skill_row["prediction_interval_low"] < 0.0  # skill is legitimately negative; must be untouched
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_expanded.py -k "log_scale or applies_log_scale" -v`
Expected: `FAIL` — `TypeError: random_effects_pooling() got an unexpected keyword argument 'transform'`.

- [ ] **Step 3: Implement the log-scale transform**

In `src/bigp3_als/expanded.py`, replace `random_effects_pooling`:

```python
def random_effects_pooling(
    estimates: pd.Series, label: str = "estimate", transform: str = "identity"
) -> dict[str, float]:
    """Summarise per-study estimates with a mean interval and a new-study prediction interval.

    The confidence interval describes the average across the source studies that were observed. The
    prediction interval describes the value a single new source study would be expected to produce,
    and is the quantity a reader should use. With few studies the two differ substantially, and
    reporting only the first overstates precision.

    ``transform="log"`` fits the interval on the log scale and reports it back on the original
    scale. Use it for a quantity that is bounded at zero, such as a mean absolute error: the
    identity-scale interval is symmetric around the mean and can cross zero when the between-study
    spread is large relative to the mean, which is not a value the quantity can actually take. It is
    not appropriate for a quantity that is legitimately signed, such as a skill score.
    """
    if transform not in ("identity", "log"):
        raise ValueError(f"transform must be 'identity' or 'log', got {transform!r}")

    values = pd.Series(estimates).dropna().to_numpy(dtype=float)
    n_studies = len(values)
    if n_studies < 2:
        raise ValueError("random-effects pooling needs at least two studies")
    if transform == "log" and np.any(values <= 0.0):
        raise ValueError("transform='log' needs every value to be strictly positive")

    scale_values = np.log(values) if transform == "log" else values
    mean = float(scale_values.mean())
    between_sd = float(scale_values.std(ddof=1))
    standard_error = between_sd / np.sqrt(n_studies)
    critical = float(stats.t.ppf(0.975, df=n_studies - 1))

    ci_low, ci_high = mean - critical * standard_error, mean + critical * standard_error
    pi_low = mean - critical * between_sd * np.sqrt(1.0 + 1.0 / n_studies)
    pi_high = mean + critical * between_sd * np.sqrt(1.0 + 1.0 / n_studies)

    if transform == "log":
        reported_mean = float(np.exp(mean))
        ci_low, ci_high, pi_low, pi_high = (float(np.exp(x)) for x in (ci_low, ci_high, pi_low, pi_high))
        reported_between_sd = float(values.std(ddof=1))  # reported on the original scale for readability
    else:
        reported_mean = mean
        reported_between_sd = between_sd

    return {
        "quantity": label,
        "n_studies": float(n_studies),
        "mean": reported_mean,
        "between_study_sd": reported_between_sd,
        "confidence_interval_low": ci_low,
        "confidence_interval_high": ci_high,
        "prediction_interval_low": pi_low,
        "prediction_interval_high": pi_high,
    }
```

Update `pool_held_out_metrics` to accept and thread the per-column flag:

```python
def pool_held_out_metrics(
    metrics: pd.DataFrame, columns: tuple[str, ...], log_scale_columns: frozenset[str] = frozenset()
) -> pd.DataFrame:
    """Apply :func:`random_effects_pooling` to each held-out-study metric column.

    ``log_scale_columns`` names columns to pool on the log scale, for quantities bounded at zero.
    """
    per_study = metrics.loc[~metrics["held_out_study"].str.startswith("Pooled")]
    rows = [
        random_effects_pooling(
            per_study[column], label=column,
            transform="log" if column in log_scale_columns else "identity",
        )
        for column in columns if column in per_study
    ]
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_expanded.py -v`
Expected: all pass, including the three new tests and every pre-existing `random_effects_pooling` test (they call it positionally/by keyword without `transform`, which defaults to `"identity"` and reproduces today's numbers exactly).

- [ ] **Step 5: Wire the log scale into the script that produces the manuscript's numbers**

In `scripts/06_run_expanded.py`, change:

```python
    pooled = pool_held_out_metrics(metrics, POOLED_COLUMNS)
```

to:

```python
    pooled = pool_held_out_metrics(
        metrics, POOLED_COLUMNS, log_scale_columns=frozenset({"session_mean_absolute_error"})
    )
```

- [ ] **Step 6: Re-run the script and read off the corrected interval**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/06_run_expanded.py --output-directory output/expanded` (check `--help` for the script's actual required arguments first; it already writes `random_effects_pooling.csv` and prints the MAE PI block — that printed block is the corrected number).

Confirm `output/expanded/random_effects_pooling.csv`'s `session_mean_absolute_error` row now has `prediction_interval_low > 0`.

- [ ] **Step 7: Update the two manuscript citations with the corrected numbers**

In `manuscript/manuscript_expanded.md:143`, replace `-0.002 to 0.203` with the new `prediction_interval_low`–`prediction_interval_high` values from Step 6 (do not hand-type placeholder numbers — copy them from the regenerated CSV), and add one clause noting the interval is now computed on the log scale:

> ...giving a 95% interval for the mean of 0.077 to 0.124 and a 95% interval for a cohort not represented in the archive, computed on the log scale because the quantity cannot be negative, of {new_low} to {new_high} (Figure 3).

In `manuscript/manuscript_expanded.md:195`, replace `-0.002 to 0.203` with the same corrected values.

- [ ] **Step 8: Re-render and re-scan**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"`
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`

- [ ] **Step 9: Commit**

```bash
git add src/bigp3_als/expanded.py tests/test_expanded.py scripts/06_run_expanded.py output/expanded/random_effects_pooling.csv manuscript/manuscript_expanded.md
git commit -m "fix: compute the MAE prediction interval on the log scale so it cannot cross zero"
```

---

### Task 5: Split Figure 2 into a readable main-text subset and a full supplementary figure

**Files:**
- Modify: `src/bigp3_als/render_expanded.py`
- Modify: `scripts/13_render_figures.py`
- Modify: `manuscript/manuscript_expanded.md` (Figure 2 caption + image block, ~lines 259/275)
- Modify: `supplementary/supplement_expanded.md` (new supplementary figure entry)

**Interfaces:**
- Consumes: `predictions: pd.DataFrame`, `als_studies: tuple[str, ...]`, same as today.
- Produces: `render_calibration_curves(predictions, als_studies, directory, bins=10, cohorts=None)` — new optional `cohorts` parameter; when `None` (default), behaves exactly as today (all cohorts, used for the full supplementary version); when given an explicit tuple of study names, restricts the panel grid to those cohorts (used for the main-text 6-panel version). Writes to `figure_calibration_curves.png`/`.pdf` when `cohorts=None` and `figure_calibration_curves_main.png`/`.pdf` when a subset is given, so both artifacts can exist side by side without one overwriting the other.

The review's complaint is that 18 tiny panels are unreadable in the main text. Rather than enlarging them (which would need a full landscape page and still be dense), keep the full 18-panel figure — it is a real, useful figure — but move it to the supplement, and show a representative 6-cohort subset in the main text: the four ALS cohorts (StudyB, StudyF, StudyL, StudyN) plus the two non-ALS cohorts at the extremes of Table 2's slope range (Study H, slope 0.185, the flattest; Study S2, slope 2.185, the steepest), so the main-text figure still shows the full spread of behaviour, not just a arbitrary sample.

- [ ] **Step 1: Add the `cohorts` parameter to `render_calibration_curves`**

In `src/bigp3_als/render_expanded.py`, change the signature and the cohort-selection line, and parameterise the output filename:

```python
def render_calibration_curves(
    predictions: pd.DataFrame,
    als_studies: tuple[str, ...],
    directory: Path,
    bins: int = 10,
    cohorts: tuple[str, ...] | None = None,
    filename: str = "figure_calibration_curves",
) -> None:
    """Plot observed against estimated accuracy, one panel per withheld cohort.

    ``cohorts``, when given, restricts the panel grid to that subset (used for a readable
    main-text figure); the default ``None`` draws every cohort (used for the full supplementary
    figure). ``filename`` lets the two versions be written without one overwriting the other.
    """
    require_columns(predictions, {"held_out_study", "predicted_probability", "correct", "n"})
    frame = predictions
    if "model_role" in frame.columns:
        frame = frame.loc[frame["model_role"] == "primary"]
    if frame.empty:
        raise ValueError("no primary predictions available to draw calibration curves")

    available = sorted(frame["held_out_study"].unique())
    if cohorts is not None:
        missing = sorted(set(cohorts) - set(available))
        if missing:
            raise ValueError(f"cohorts not present in predictions: {missing}")
        cohort_list = list(cohorts)
    else:
        cohort_list = available
    ...
```

Replace every later reference to `cohorts` (the loop variable) inside the function body with `cohort_list`, and change the final save call from `_save(fig, directory, "figure_calibration_curves")` to `_save(fig, directory, filename)`.

- [ ] **Step 2: Update the render entry point to produce both versions**

In `scripts/13_render_figures.py`, add the constant and a second call:

```python
from bigp3_als.expanded import ALS_STUDIES

MAIN_TEXT_COHORTS = ALS_STUDIES + ("StudyH", "StudyS2")
```

and after the existing `render_calibration_curves(predictions, ALS_STUDIES, figures)` call, add:

```python
    render_calibration_curves(
        predictions, ALS_STUDIES, figures, cohorts=MAIN_TEXT_COHORTS, filename="figure_calibration_curves_main"
    )
```

Update the `print` block underneath to list both:

```python
    print("  figure_calibration_curves        Figure S2 (all 18 cohorts)")
    print("  figure_calibration_curves_main   Figure 2 (6-cohort subset)")
```

- [ ] **Step 3: Run the figure script and confirm both files exist**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/13_render_figures.py --directory output/expanded`
Expected: `output/expanded/figures/figure_calibration_curves_main.png` (6 panels) and `figure_calibration_curves.png` (18 panels, unchanged) both exist.

- [ ] **Step 4: Point the manuscript's Figure 2 at the subset image, and move the full figure to the supplement**

In `manuscript/manuscript_expanded.md`, the current Figure 2 caption (originally: *"Figure 2. Observed against estimated session accuracy, one panel per withheld cohort."*) becomes:

> **Figure 2. Observed against estimated session accuracy, in the four ALS cohorts and the two non-ALS cohorts at either end of the calibration-slope range (Table 2).** Each point is one of up to ten equal-count bins of the estimate within that cohort, placed at the selection-weighted mean estimate and the observed accuracy of the records in it, with point area increasing with the selections it rests on. The dashed line is equality. Points above it are bins whose accuracy the mapping understated and points below are bins whose accuracy it overstated. The number in each panel is observed minus estimated accuracy across that whole cohort. The full 18-cohort version of this figure is Figure S2.

and its image line changes from `figure_calibration_curves.png` to `figure_calibration_curves_main.png`.

- [ ] **Step 5: Register Figure S2 in the supplement**

In `supplementary/supplement_expanded.md`, add a new subsection after `## S9. Predictor reliability and disattenuated heterogeneity` (renumber `S10`/`S11` to `S11`/`S12` if you insert it as a numbered section, or append it at the end before `## S11. Transparency statement` and title it descriptively without a number collision — check the current highest figure number used anywhere in the supplement first with `grep -n "Figure S" supplementary/supplement_expanded.md` and use the next free one):

> **Figure S2. Observed against estimated session accuracy, one panel per withheld cohort, all 18 cohorts.** The main-text Figure 2 shows six representative cohorts (the four ALS cohorts and the two non-ALS extremes of the calibration-slope range); this figure shows every cohort. Each point is one of up to ten equal-count bins of the estimate within that cohort, placed at the selection-weighted mean estimate and the observed accuracy of the records in it, with point area increasing with the selections it rests on. A cohort supports at most as many bins as it has distinct estimates, and the estimate is a property of the session rather than of the record, so two of the 18 cohorts draw eight bins rather than ten. The dashed line is equality. Points above it are bins whose accuracy the mapping understated and points below are bins whose accuracy it overstated, so the panels carry the direction of the miscalibration that Figure 1 summarises as a spread. The number in each panel is observed minus estimated accuracy across that whole cohort.

with the image line `![](../output/expanded/figures/figure_calibration_curves.png){width=100%}`.

- [ ] **Step 6: Re-render everything and spot-check**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py`
Open `build_expanded/manuscript.pdf` and `build_expanded/supplement.pdf` and confirm Figure 2 is now the 6-panel version and is legible at the rendered size.

- [ ] **Step 7: Commit**

```bash
git add src/bigp3_als/render_expanded.py scripts/13_render_figures.py manuscript/manuscript_expanded.md supplementary/supplement_expanded.md output/expanded/figures
git commit -m "fig: split the 18-panel calibration-curve figure into a 6-cohort main figure and a full supplementary figure"
```

---

### Task 6: Distinguish ALS cohorts by marker shape as well as color

**Files:**
- Modify: `src/bigp3_als/render_expanded.py`
- Modify: `src/bigp3_als/render.py` (if it defines any of the shared marker/color constants used across figures — check `ALS_COLOR`/`OTHER_COLOR` definitions with `grep -n "ALS_COLOR\s*=" src/bigp3_als/*.py` first)

**Interfaces:**
- Consumes: nothing new.
- Produces: a new module constant `ALS_MARKER = "D"` (diamond) and `OTHER_MARKER = "o"` (circle) alongside the existing `ALS_COLOR`/`OTHER_COLOR`, applied everywhere those colors currently distinguish cohort type in a scatter or legend.

The review's ask is specifically for grayscale/color-vision accessibility: color alone should not be the only channel encoding ALS-vs-other.

- [ ] **Step 1: Locate every plotting call that currently uses `ALS_COLOR`/`OTHER_COLOR` to distinguish cohort type**

Run: `grep -n "ALS_COLOR\|OTHER_COLOR" src/bigp3_als/render_expanded.py src/bigp3_als/render.py`

For each `ax.scatter(...)` call that colors by `ALS_COLOR`/`OTHER_COLOR` (the forest-plot legend handles at the top of `render_calibration_forest`, the calibration-curves panels in `render_calibration_curves`, `_build_cohort_type_relationship`, and any skill-by-cohort bar/scatter in `render_skill_by_cohort`), add a matching `marker=` argument: `marker=ALS_MARKER if <is_als_condition> else OTHER_MARKER`. Bar charts (which already use `marker="s"` per the earlier exploration note) do not need this — marker shape only matters for point/scatter encodings; leave bars as bars.

- [ ] **Step 2: Add the constants**

Wherever `ALS_COLOR`/`OTHER_COLOR` are currently defined (likely `src/bigp3_als/render.py`, shared by both render modules — confirm with the grep from Step 1), add immediately below them:

```python
ALS_MARKER = "D"
OTHER_MARKER = "o"
```

- [ ] **Step 3: Update each scatter call and the legend handles**

In `render_calibration_forest`, the legend handle block currently reads:

```python
    handles += [
        plt.Line2D([], [], marker="o", linestyle="none", color=ALS_COLOR, label="ALS cohort"),
        plt.Line2D([], [], marker="o", linestyle="none", color=OTHER_COLOR, label="Other cohort"),
    ]
```

change to:

```python
    handles += [
        plt.Line2D([], [], marker=ALS_MARKER, linestyle="none", color=ALS_COLOR, label="ALS cohort"),
        plt.Line2D([], [], marker=OTHER_MARKER, linestyle="none", color=OTHER_COLOR, label="Other cohort"),
    ]
```

Apply the equivalent `marker=` change to every other `ax.scatter(...)` call identified in Step 1 that plots ALS vs. other-cohort points (`_build_cohort_type_relationship` is the clearest additional case — its two `ax.scatter(...)` calls, one per `is_als` branch, each get the matching marker).

- [ ] **Step 4: Re-render figures and inspect**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/13_render_figures.py --directory output/expanded`
Open the regenerated PNGs (`output/expanded/figures/figure_calibration_forest.png`, `figure_cohort_type_relationship.png`) and confirm ALS points are visibly diamonds and other-cohort points are visibly circles, independent of color.

- [ ] **Step 5: Run the full test suite to confirm no rendering test asserts marker style**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_render_expanded.py tests/test_render.py -v`
Expected: pass unchanged (these tests check that files are written and basic shape/data properties, not marker glyphs — if any test does assert on marker style, update its expected value rather than removing the assertion).

- [ ] **Step 6: Re-render the manuscript and commit**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py
git add src/bigp3_als/render_expanded.py src/bigp3_als/render.py output/expanded/figures
git commit -m "fig: distinguish ALS cohorts by marker shape as well as color, for grayscale and color-vision accessibility"
```

---

### Task 7: Embed tables and figures near their first citation, and pair every caption with its image

**Files:**
- Modify: `manuscript/manuscript_expanded.md`

**Interfaces:** None — pure document restructuring, verified by rendering and reading, not by `pytest`.

Currently every table and figure lives in one trailing `## Tables and Figure Legends` section (lines 229–297), with all four figure captions written consecutively (lines ~257–269) followed by all four image lines consecutively (lines ~271–277) — captions and images are not even adjacent to each other, let alone near the text that first cites them. IOP's initial-submission guidance asks for a single PDF with figures and tables embedded at the appropriate points in the text. This task does the mechanical cut-and-paste to satisfy that.

- [ ] **Step 1: Identify each table/figure's first in-text citation**

Run: `grep -n "Table 1\|Table 2\|Figure 1\|Figure 2\|Figure 3\|Figure 4" manuscript/manuscript_expanded.md | grep -v "^229\|^231\|^25[0-9]\|^26[0-9]\|^27[0-9]"` (excludes the Tables-and-Figures section itself) to find where each is first named in running prose. Confirm against the section structure already mapped: Table 1 is first relevant to `### Cohort` (line 125); Table 2 and Figure 1 are first relevant to `### Transportability` (line 141, which reports the intercept/slope tau values Figure 1 visualises); Figure 2 is first relevant to the same `### Transportability` subsection, immediately after Figure 1's citation; Figure 3 is first relevant to the MAE/estimation-error paragraph inside `### Transportability` (the paragraph containing "Figures 1 and 2" / "(Figure 3)" reference already present per Task 4 Step 7); Figure 4 (skill-by-cohort) is first relevant wherever the manuscript first discusses skill against the development-mean benchmark inside `### Estimation Error and Its Reference Points` (line 137).

- [ ] **Step 2: Cut each table/figure block (caption + image, as one unit) and paste it after its first-citation paragraph**

For each of Table 1, Table 2, Figure 1, Figure 2, Figure 3, Figure 4: remove its caption paragraph and its `![]()` image line together as one contiguous block from the `## Tables and Figure Legends` section, and paste that same block (caption immediately followed by its image, with no blank paragraph or other content between them) immediately after the paragraph identified in Step 1. Preserve each caption's exact text — this step moves text, it does not rewrite it (any rewriting from Tasks 4/5/8/9/10 happens as those tasks touch these same captions; do this step either before or after those, but not concurrently with the same file section to avoid merge conflicts if working with a subagent per task).

- [ ] **Step 3: Delete the now-empty `## Tables and Figure Legends` header**

Once every table and figure has been moved out, delete the section header itself (leaving `## Data and Code Availability` to directly follow whatever the last Results/Discussion content is). Confirm nothing else was orphaned: `grep -n "^## Tables and Figure Legends"` should return nothing.

- [ ] **Step 4: Verify every image path still resolves and every caption survived intact**

Run: `grep -c '^!\[\]' manuscript/manuscript_expanded.md` — expect `4` (unchanged count, just relocated).
Run: `grep -c '^\*\*Table\|^\*\*Figure' manuscript/manuscript_expanded.md` — expect `6` (2 tables + 4 figures, unchanged count).

- [ ] **Step 5: Re-render and visually confirm embedding**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`
Open `build_expanded/manuscript.pdf` and confirm each table/figure now appears on or near the page where it is first discussed, with its caption on the same page as its image (not separated by several pages as before).

- [ ] **Step 6: Scan for AI-writing tells (the move should not have introduced any new prose) and commit**

```bash
python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"
git add manuscript/manuscript_expanded.md
git commit -m "docs: embed each table and figure near its first citation, with captions adjacent to their images"
```

---

### Task 8: Soften and de-duplicate the stopping-rule moderator language

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (lines 37, 173, 175, 201, 215)
- Modify: `manuscript/cover_letter_expanded.md` (line 15, or its relocated line after Task 15 restructures the letter — do this task before Task 15)

**Interfaces:** None — prose edit.

The phrase "accounted for two thirds of the between-cohort variance" appears six times across the abstract, two Results subsections, Discussion, and Limitations, and the review specifically asks that the causal-sounding "accounted for" be replaced with the statistically accurate "was associated with a ... reduction in estimated residual between-cohort variance," and that its prominence in the abstract and cover letter be reduced (the paper's principal finding is the lack of transportability; the moderator is a secondary, exploratory explanation).

- [ ] **Step 1: Abstract (line 37) — cut the mention, don't just soften it**

Replace:

> The slope agreed and was itself imprecisely estimated: tau 0.43 (0.30 to 0.77), unrepresented-cohort interval 0.111 to 2.005; the median time per selection, the archive's only trace of the stopping rule, accounted for two thirds of that between-cohort variance (Holm-corrected p = 0.012). Skill was negative in one of 18 cohorts.

with:

> The slope agreed and was itself imprecisely estimated: tau 0.43 (0.30 to 0.77), unrepresented-cohort interval 0.111 to 2.005. Skill was negative in one of 18 cohorts.

(the moderator result belongs in Results/Discussion, where it is now stated once with full statistical care — not in a 300-word abstract, where it cannot carry its own caveats).

- [ ] **Step 2: Results, "Protocol Descriptors as Moderators" (line 173) — this is the one place the full result is stated; reword "accounted for" but keep it here**

Replace:

> **The time a cohort took over each selection accounted for two thirds of the between-cohort variance in calibration slope.**

with:

> **The time a cohort took over each selection was associated with a two-thirds reduction in estimated residual between-cohort variance in calibration slope.**

and later in the same paragraph, replace:

> reducing the between-cohort variance of the slope from tau squared = 0.187 to 0.063, a share of 66%, equivalently a residual between-cohort standard deviation of 0.25 against 0.43.

with:

> associated with a reduction in the between-cohort variance of the slope from tau squared = 0.187 to 0.063, a share of 66%, equivalently a residual between-cohort standard deviation of 0.25 against 0.43.

Leave the rest of this paragraph and its immediate follow-on paragraph (the null-descriptor and correction-family-robustness content) as the single full statement of this result — Task 11 will move most of its dense stress-test detail to the supplement, but the headline sentence stays here in its corrected wording.

- [ ] **Step 3: Discussion (line 201) — condense to a cross-reference instead of restating the full explanation**

Replace the full paragraph:

> Part of that variation is now attributable to a protocol difference rather than to the cohorts themselves. The time each cohort took over a selection, which is the archive's only trace of the stopping rule, accounted for two thirds of the between-cohort variance in the calibration slope, leaving a residual between-cohort standard deviation of 0.25 against 0.43 unmoderated. That does not restore transportability, for two reasons. A mapping whose slope depends on the stopping rule is still not one that can be carried to a site whose stopping rule is unknown, and knowing it is not the same as being able to correct for it, since the correction estimated here rests on 18 cohorts and on a descriptor that is itself partly determined by the recording wherever stopping was data-dependent. What the result does change is the interpretation of the residual spread: it is not an irreducible property of the population, and a site that reports its stopping rule alongside a calibration score would remove a substantial share of the uncertainty in a transported estimate.

with:

> Part of that variation is attributable to a protocol difference rather than to the cohorts themselves: the time each cohort took over a selection, the archive's only trace of the stopping rule, was associated with the two-thirds reduction in residual between-cohort variance reported above (Results, Protocol Descriptors as Moderators). That association does not restore transportability — a mapping whose slope depends on the stopping rule still cannot be carried to a site whose stopping rule is unknown — but it does change how the residual spread should be read: it is not an irreducible property of the population, and a site that reports its stopping rule alongside a calibration score would remove a substantial share of the uncertainty in a transported estimate.

- [ ] **Step 4: Discussion (line 215) — condense similarly**

Replace:

> The archive records none of these rules as fields, but two of them leave a recoverable trace that was tested here: the time taken per selection, which is the signature of the stopping rule and accounted for two thirds of the between-cohort variance in calibration slope, and the range of target indices, which bounds the speller alphabet from below and accounted for no share distinguishable from zero.

with:

> The archive records none of these rules as fields, but two of them leave a recoverable trace that was tested here: the time taken per selection, the signature of the stopping rule (Results, Protocol Descriptors as Moderators), and the range of target indices, which bounds the speller alphabet from below and was not associated with a share distinguishable from zero.

- [ ] **Step 5: Cover letter (line 15) — cut to one sentence, remove the standalone paragraph's prominence**

This is addressed together with the full cover-letter rewrite in Task 15; do not edit `cover_letter_expanded.md` here if Task 15 is scheduled after this task — instead leave a one-line note for that task: the current paragraph 4 (starting "One cohort-level feature accounts for much of that spread...") should shrink to one sentence using the same "was associated with" phrasing, positioned as a secondary point, not its own paragraph.

- [ ] **Step 6: Verify count and re-render**

Run: `grep -c "accounted for.*between-cohort variance" manuscript/manuscript_expanded.md` — expect `0` (all instances reworded to "was associated with").
Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"`
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`

- [ ] **Step 7: Commit**

```bash
git add manuscript/manuscript_expanded.md
git commit -m "docs: reword the stopping-rule moderator as associational, not causal, and de-duplicate its repetition"
```

---

### Task 9: Soften "subsequent" temporal-precedence language

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (lines 29, 41, 53, 193, 227)

**Interfaces:** None — prose edit.

The archive's timestamps are de-identified (already stated in Methods, `manuscript_expanded.md:57`: "Every timestamp in the archive is de-identified, so recording order cannot be established from file headers"), so "subsequent online accuracy" claims a chronology the data cannot verify for the primary analysis. The one analysis that IS genuinely temporally separated — the preceding-session secondary analysis (`### Predictor From a Preceding Session`) — should keep language that reflects real precedence; every other use of "subsequent" describing the primary same-session analysis should not.

- [ ] **Step 1: Abstract Objective (line 29)**

Replace:

> A calibration-derived score has been related to subsequent online P300-speller accuracy, always within the cohort measured.

with:

> A calibration-derived score has been related to online P300-speller accuracy in the same session, always within the cohort measured.

- [ ] **Step 2: Abstract Significance (line 41)**

Replace:

> The score carries a reproducible signal about subsequent accuracy, but the mapping between them is cohort-specific...

with:

> The score carries a reproducible signal about accuracy in the corresponding session, but the mapping between them is cohort-specific...

- [ ] **Step 3: Introduction/Objective (line 53)**

Replace:

> We evaluated whether a calibration-derived score estimates subsequent online session accuracy in cohorts withheld from model development...

with:

> We evaluated whether a calibration-derived score estimates online session accuracy in the corresponding P300-speller session, in cohorts withheld from model development...

- [ ] **Step 4: Results summary (line 193)**

Replace:

> ...the discriminability of a classifier fitted to a session's calibration block was related to that session's subsequent online spelling accuracy...

with:

> ...the discriminability of a classifier fitted to a session's calibration block was related to that same session's online spelling accuracy...

- [ ] **Step 5: Conclusion (line 227)**

Replace:

> ...calibration-derived decoder discriminability was related to subsequent online spelling accuracy...

with:

> ...calibration-derived decoder discriminability was related to online spelling accuracy in the corresponding session...

- [ ] **Step 6: Confirm the preceding-session analysis is untouched and still correctly distinguished**

Run: `sed -n '179,182p' manuscript/manuscript_expanded.md` and confirm the `### Predictor From a Preceding Session` subsection still reads "Using a calibration recording from a preceding session, rather than from the session being estimated..." — this is the one place "preceding"/genuinely-separated language belongs, and it should not have been touched by Steps 1–5.

- [ ] **Step 7: Verify and re-render**

Run: `grep -n "subsequent" manuscript/manuscript_expanded.md` — expect no matches.
Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"`
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`

- [ ] **Step 8: Commit**

```bash
git add manuscript/manuscript_expanded.md
git commit -m "docs: replace unverifiable 'subsequent' timing language with same-session phrasing, per the de-identified timestamp limitation already stated in Methods"
```

---

### Task 10: Reframe the ALS "primary subgroup" language

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (lines 33, 53, 61, 71, 157)

**Interfaces:** None — prose edit.

`docs/statistical_analysis_plan.md` already establishes (and the manuscript already states) that no analysis plan was registered and that the ALS-only design was the project's own working note before later widening — the review's ask is to stop calling it "primary" repeatedly, which implies more protocol status than a repeatedly-stated disclaimer can undo, and to state the chronology once rather than as a running refrain.

- [ ] **Step 1: Methods, Study Design and Reporting (line 61) — this is the correct single place to state it; tighten the wording but keep it here**

Replace:

> No analysis plan was registered. The four documented ALS cohorts were fixed as the primary subgroup in the project documentation before the design was widened beyond them.

with:

> No analysis plan was registered. The four documented ALS cohorts were fixed as the originally planned subgroup in the project documentation before the design was widened beyond them.

- [ ] **Step 2: Methods, Data Source and Cohort (line 71) — remove the repeat, replace with a cross-reference**

Replace:

> The archive documentation identifies an ALS study population for four source studies. These were the originally targeted primary subgroup, fixed before the design was widened beyond them.

with:

> The archive documentation identifies an ALS study population for four source studies (Study Design and Reporting, above).

- [ ] **Step 3: Introduction/Objective (line 53) — remove "primary," keep the fact**

Replace:

> The documented ALS cohorts were the originally targeted primary subgroup.

with:

> The documented ALS cohorts were the originally planned subgroup, before the design widened to every source study with an eligible online outcome.

- [ ] **Step 4: Results, Amyotrophic Lateral Sclerosis Subgroup (line 157) — remove "primary"**

Replace:

> Within the originally targeted primary subgroup the mean absolute error was 0.091...

with:

> Within the originally planned subgroup the mean absolute error was 0.091...

- [ ] **Step 5: Abstract Approach (line 33) — de-emphasize; state it plainly without "primary"**

Replace:

> The four documented amyotrophic lateral sclerosis (ALS) cohorts were the originally targeted primary subgroup.

with:

> The four documented amyotrophic lateral sclerosis (ALS) cohorts were the originally planned subgroup, before widening to every source study with an eligible online outcome.

- [ ] **Step 6: Verify and re-render**

Run: `grep -n "primary subgroup\|targeted primary" manuscript/manuscript_expanded.md` — expect no matches.
Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"`
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`

- [ ] **Step 7: Commit**

```bash
git add manuscript/manuscript_expanded.md
git commit -m "docs: describe the ALS cohorts as the originally planned subgroup, stated once, not repeated as 'primary'"
```

---

### Task 11: Cut main-text length by moving dense methodological detail to the supplement

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (`### Protocol Descriptors as Moderators`, `### Sensitivity Analyses`)
- Modify: `supplementary/supplement_expanded.md` (new subsection under `## S6. Sensitivity analyses`, or a new `S12`)

**Interfaces:** None — prose edit, verified by word count.

The manuscript body (Introduction through Conclusion, excluding Tables/Figures/Data-Availability/References) is currently roughly 8,900–9,000 words. Do this task after Tasks 3, 4, 8, 9, 10 (their edits change the exact wording of the paragraphs being cut here) and after Task 7 (so line numbers for "near its first citation" placement are stable before this task moves prose out of the body entirely). Target: body word count at or below 7,300 words, verified in Step 4 below — not a percentage, a number you can check.

- [ ] **Step 1: Condense the "Protocol Descriptors as Moderators" stress-test paragraphs**

The current second paragraph of this subsection (starting "No other descriptor accounted for a share distinguishable from zero...") and third paragraph (starting "The interval is not a fully exogenous descriptor...") together run to roughly 470 words of rank-correlation, log-scale, fixed-vs-variable-interval-split, and correction-family-robustness detail. Replace both paragraphs in the main text with:

> No other descriptor was associated with a share of the between-cohort variance distinguishable from zero, including both available proxies for matrix size (Supplementary Methods, S6). The result was also checked for robustness to how the stopping rule's descriptor was defined, to whether it is partly a consequence of the recording rather than a fixed protocol setting, and to how the multiple-comparison correction was applied across the eight descriptors tested; all three checks left the result materially unchanged (Supplementary Methods, S6).

and move the full original text of both paragraphs, verbatim, into `supplementary/supplement_expanded.md` under `## S6. Sensitivity analyses` as a new subsection titled "Protocol-descriptor moderator robustness," preceded by one sentence of context: "The main-text Results (Protocol Descriptors as Moderators) reports the headline association and points here for the full robustness detail."

- [ ] **Step 2: Condense the "Sensitivity Analyses" subsection**

The current subsection runs four analyses plus the 153-split double-holdout check plus the comparator-predictor sweep in dense prose (roughly 350 words). Replace with a shorter version that states each result once, in one clause, pointing to the supplement tables that already carry the numbers (Tables S4 and S6 already exist per the supplement's section list):

> Results were consistent under four further checks: excluding low-count records, restricting to cohorts with meaningful accuracy variation, excluding records with heavy calibration-epoch rejection, and analysing only the non-ALS cohorts (Supplementary Table S3). Withholding two cohorts at a time, so development ran on 16 rather than 17 cohorts, reproduced the primary result across all 153 splits (Supplementary Table S4). Every comparator predictor named in the Methods was run through the same procedure and is reported in full in Supplementary Table S6; the regularised linear discriminant computed from the identical features agreed with the primary score to within 0.007 on every summary column, so the transportability result reflects how separable the calibration data are rather than the classifier family used to measure it.

Move the full original paragraph text (the specific per-analysis numbers currently in the main text: 0.100/0.047 for the low-count exclusion, 0.124/0.601 for the ceiling-variation restriction, 0.087/0.465 for the rejection-fraction exclusion, -0.015 to 0.216 for the non-ALS-only analysis, and the 0.1007/0.1006 etc. double-holdout figures) into the supplement's existing Table S3/S4/S6 if those numbers are not already there (`grep -n "0.1007\|0.601\|Table S3\|Table S4\|Table S6" supplementary/supplement_expanded.md` first to check whether they are already duplicated in the supplement — if so, this step is only a main-text cut with no new supplement content needed; if not, add a short paragraph carrying the exact numbers next to whichever table is closest in topic).

- [ ] **Step 3: Confirm the supplement's de-AI scan and pandoc render still work**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "supplementary/supplement_expanded.md"`
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only supplement`

- [ ] **Step 4: Measure the new body word count**

Run:
```bash
python3 -c "
import re
text = open('manuscript/manuscript_expanded.md').read()
start = text.index('## Introduction')
end = text.index('## Tables and Figure Legends') if '## Tables and Figure Legends' in text else text.index('## Data and Code Availability')
body = text[start:end]
body = re.sub(r'^#+.*$', '', body, flags=re.MULTILINE)  # drop headers
words = len(body.split())
print(f'body word count: {words}')
"
```
Expected: at or below 7,300. If still above, the next-largest cut candidates are the ALS-vs-full-archive Discussion paragraph (currently restates numbers already in Results, `manuscript_expanded.md` Discussion, the paragraph beginning "The comparison between the four ALS cohorts and the full archive...") and the Limitations list's most detailed individual points — condense any Limitations point that restates a number already given in Results/Discussion to a one-clause cross-reference, following the same pattern as Steps 1–2, until the count clears 7,300.

- [ ] **Step 5: Re-render both documents fully and read them once**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py`
Open `build_expanded/manuscript.pdf` and confirm the Results still read coherently with the condensed moderator/sensitivity paragraphs — the goal is a shorter paper that still argues its own case, not a paper with holes where evidence used to be.

- [ ] **Step 6: Commit**

```bash
git add manuscript/manuscript_expanded.md supplementary/supplement_expanded.md
git commit -m "docs: move dense moderator-robustness and sensitivity-analysis detail to the supplement, cutting main-text length"
```

---

### Task 12: Trim the abstract per the review's four specific edits

**Files:**
- Modify: `manuscript/manuscript_expanded.md:25-41`

**Interfaces:** None — prose edit, verified by word count.

Do this task after Tasks 8, 9, 10 (it edits sentences those tasks already reworded — Task 8 Step 1 already removed the moderator clause from the abstract; Task 9 Step 2 and Task 10 Step 5 already touched the Significance/Approach sentences). This task applies the review's remaining three suggestions: shorten the predictor definition, report fewer separate interval bounds, and rephrase "the slope agreed" more directly.

- [ ] **Step 1: Shorten the predictor definition in Approach**

Replace:

> The predictor was calibration-derived decoder discriminability, the cross-validated discriminability of a classifier fitted to calibration epochs only.

with:

> The predictor was calibration-derived decoder discriminability: cross-validated discriminability of a classifier fitted only to calibration epochs.

(marginal, but removes one redundant "discriminability" repetition — combine with Step 2 for the real savings).

- [ ] **Step 2: Reduce the number of separate interval bounds in Main Results**

Replace (this sentence was already shortened by Task 8 Step 1, which removed the trailing moderator clause and "Skill was negative..." sentence stays):

> Calibration did not transport: the intercept had tau 0.87 (95% CI 0.60 to 1.51) and a 95% interval for an unrepresented cohort of -1.97 to 1.85, spanning mappings that badly understate and badly overstate accuracy. The slope agreed and was itself imprecisely estimated: tau 0.43 (0.30 to 0.77), unrepresented-cohort interval 0.111 to 2.005.

with:

> Calibration did not transport: the intercept had tau 0.87, with a 95% interval for an unrepresented cohort of -1.97 to 1.85 on the log-odds scale, spanning mappings that badly understate and badly overstate accuracy. Slope heterogeneity led to the same conclusion, at tau 0.43 and an unrepresented-cohort interval of 0.111 to 2.005.

(drops the two parenthetical tau confidence intervals — the prediction intervals are the numbers that carry the transportability claim, per the manuscript's own emphasis elsewhere; "slope heterogeneity led to the same conclusion" replaces "the slope agreed and was itself imprecisely estimated," which is the exact rewording the review suggests).

- [ ] **Step 3: Count the abstract and confirm it is still ≤300 words**

Run:
```bash
python3 -c "
import re
text = open('manuscript/manuscript_expanded.md').read()
start = text.index('### Objective')
end = text.index('## Introduction')
body = text[start:end]
body = re.sub(r'^#+.*$', '', body, flags=re.MULTILINE)
print(len(body.split()))
"
```
Expected: a number below 300 (this frees margin, since the abstract started exactly at the cap and Steps 1–2 plus Task 8/9/10's abstract edits all cut words without adding any).

- [ ] **Step 4: Re-render, scan, commit**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md"`
Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`

```bash
git add manuscript/manuscript_expanded.md
git commit -m "docs: tighten the abstract per the reviewer's specific edits, buying margin under the 300-word cap"
```

---

### Task 13: Consolidate declarations into an Acknowledgements section before References

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (front matter lines ~17-23; new section before `## Data and Code Availability`)

**Interfaces:** None — document restructuring.

Confirmed via IOP Publishing Support (`publishingsupport.iopscience.iop.org`, "About Journal of Neural Engineering"): competing-interest disclosure belongs in the cover letter at submission, and "if the article is subsequently accepted for publication, this information should be included in an acknowledgments section" — not scattered across the front page. This is the journal's own stated policy, not a stylistic guess.

- [ ] **Step 1: Remove Funding, Competing interests, Ethics approval, and Author contributions from the front matter**

In `manuscript/manuscript_expanded.md`, delete these four lines (currently immediately after "Address correspondence to:"):

> **Funding:** None.
>
> **Competing interests:** None declared.
>
> **Ethics approval:** Institutional review board approval was not required; the determination is stated in full in the Methods, under Ethics.
>
> **Author contributions:** Contributions are described using the CRediT taxonomy. A.G.: conceptualization, methodology, software, formal analysis, data curation, validation, visualization, and writing of the original draft. Y.A.: software, data curation, formal analysis, validation, and review and editing of the manuscript. M.O.: methodology, software, validation, and review and editing of the manuscript. Y.B.: methodology, validation, and review and editing of the manuscript. E.K.: conceptualization, methodology, supervision, resources, and review and editing of the manuscript. O.D.: conceptualization, methodology, investigation, formal analysis, clinical interpretation, supervision, writing of the original draft, and review and editing of the manuscript. All authors critically reviewed the manuscript and approved the final version submitted for publication. A.G. (corresponding author) had full access to all data in the study and takes responsibility for the integrity of the data and the accuracy of the analysis.

Keep the Address correspondence line — that stays in the front matter.

- [ ] **Step 2: Add a new `## Acknowledgements` section immediately before `## Data and Code Availability`**

Insert the same four declarations, verbatim, as a new section:

```markdown
## Acknowledgements

**Funding:** None.

**Competing interests:** None declared.

**Ethics approval:** Institutional review board approval was not required; the determination is stated in full in the Methods, under Ethics.

**Author contributions:** Contributions are described using the CRediT taxonomy. A.G.: conceptualization, methodology, software, formal analysis, data curation, validation, visualization, and writing of the original draft. Y.A.: software, data curation, formal analysis, validation, and review and editing of the manuscript. M.O.: methodology, software, validation, and review and editing of the manuscript. Y.B.: methodology, validation, and review and editing of the manuscript. E.K.: conceptualization, methodology, supervision, resources, and review and editing of the manuscript. O.D.: conceptualization, methodology, investigation, formal analysis, clinical interpretation, supervision, writing of the original draft, and review and editing of the manuscript. All authors critically reviewed the manuscript and approved the final version submitted for publication. A.G. (corresponding author) had full access to all data in the study and takes responsibility for the integrity of the data and the accuracy of the analysis.
```

- [ ] **Step 3: Confirm submission-system compatibility before finalizing**

This move follows IOP's own stated post-acceptance convention. Before the actual submission (not part of this plan's automatable steps), check the live JNE submission system's initial-submission requirements — some journals still want a separate "Conflict of interest" field entered directly into the submission portal regardless of manuscript body placement. If the portal has such a field, this manuscript section and that field should say the same thing, not conflict.

- [ ] **Step 4: Re-render and commit**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only manuscript`

```bash
git add manuscript/manuscript_expanded.md
git commit -m "docs: move funding, competing-interests, ethics, and author-contribution declarations into a consolidated Acknowledgements section, per IOP's stated policy"
```

---

### Task 14: Create a completed TRIPOD checklist

**Files:**
- Create: `supplementary/tripod_checklist.md`

**Interfaces:** None — new document.

The manuscript already cites the TRIPOD statement as reference [19] and states "Reporting follows the TRIPOD statement for prediction-model studies" (`manuscript_expanded.md:57`), but no completed checklist artifact exists. This is a real gap, not a formatting nit — reviewers and editors check this against the manuscript directly.

- [ ] **Step 1: Build the checklist table, one row per TRIPOD (2015) item, citing the exact manuscript location**

Create `supplementary/tripod_checklist.md`:

```markdown
# TRIPOD checklist for prediction model development and validation

Completed against `manuscript/manuscript_expanded.md` (this study is a validation of a previously
proposed calibration-to-accuracy relationship, not a development of a new model; items specific to
model development are marked not applicable and the reason is given).

| Section | Item | # | Checklist item | Reported on page/section |
|---|---|---|---|---|
| Title and abstract | Title | 1 | Identify as a validation study; specify the target population and outcome | Title; Abstract, Objective |
| | Abstract | 2 | Structured summary of objectives, design, setting, participants, predictor, outcome, statistical analysis, results, conclusions | Abstract |
| Introduction | Background | 3a | Explain the medical context and rationale | Introduction, paragraphs 1-2 |
| | Objectives | 3b | State study objectives, including whether developing or validating | Introduction, final paragraph; Methods, Study Design and Reporting |
| Methods | Source of data | 4a | Study design, data source | Methods, Data Source and Cohort |
| | | 4b | Study dates | Methods, Data Source and Cohort (archive version, no recruitment dates because this is a legacy public archive) |
| | Participants | 5a | Eligibility criteria | Methods, Data Source and Cohort |
| | | 5b | Setting and locations | Methods, Data Source and Cohort |
| | | 5c | Dates of recruitment | Not applicable; legacy public archive with de-identified timestamps (Methods, Study Design and Reporting) |
| | Outcome | 6a | Outcome definition and how/when assessed | Methods, Outcome |
| | | 6b | Blinding of outcome assessment | Not applicable; outcome is a deterministic reconstruction from archived event logs, not an assessor judgement |
| | Predictors | 7a | Definition and measurement of predictors | Methods, Calibration Predictor |
| | | 7b | Blinding of predictor assessment | Methods, Study Design and Reporting (calibration and outcome data are from separate protocol phases) |
| | Sample size | 8 | Explain how sample size was arrived at | Methods, Data Source and Cohort (all eligible archive studies used, not a powered sample) |
| | Missing data | 9 | Handling of missing predictor/outcome data | Methods, Outcome; Results, Cohort (excluded phases documented in Table 1) |
| | Statistical analysis methods | 10a | Development: relationship modelling | Methods, Model Specification |
| | | 10b | Internal validation | Not applicable to this design; see 10c |
| | | 10c | External validation methods | Methods, Validation Design (leave-one-source-study-out) |
| | | 10d | Any model updating | Not applicable; the fitted mapping is applied as-is to the withheld cohort, not updated |
| | Risk groups | 11 | How risk groups were created | Not applicable; outcome is a continuous accuracy proportion, not a risk category |
| | Development vs. validation | 12 | Differences between development and validation data | Methods, Validation Design; Discussion, Study Limitations |
| Results | Participants | 13a | Flow of participants, with reasons for exclusion | Results, Cohort; Table 1 |
| | | 13b | Characteristics of participants | Results, Cohort; Table 2 |
| | | 13c | Comparison of development vs. validation participants | Discussion, Study Limitations (cohort heterogeneity discussed; no separate person-level comparison table because cohorts, not held-out individuals, are the unit withheld) |
| | Model development | 14a | Unadjusted association between predictors and outcome | Results, Association Between Calibration-Derived Decoder Discriminability and Online Accuracy |
| | | 14b | Model specification | Methods, Model Specification |
| | Model specification | 15a | Full prediction model (all coefficients) | Supplementary Table S9 (fitted coefficients of every development fold) |
| | | 15b | Explanation of how to use the model | Supplementary Table S9, worked example |
| | Model performance | 16 | Performance measures with confidence intervals | Results, Estimation Error and Its Reference Points; Table 2; Figures 1-3 |
| | Model updating | 17 | Details of model updating | Not applicable; see item 10d |
| Discussion | Limitations | 18 | Study limitations, sources of bias | Discussion, Study Limitations |
| | Interpretation | 19a | Interpretation for validation studies, considering objectives, limitations, results from similar studies | Discussion, paragraphs 1-3 |
| | | 19b | Overall interpretation, implications for practice | Discussion, Conclusion |
| | Implications | 20 | Potential clinical use, implications for future research | Discussion, Conclusion; Abstract, Significance |
| Other information | Supplementary information | 21 | Availability of supplementary resources | Data and Code Availability |
| | Funding | 22 | Source of funding | Acknowledgements |
```

- [ ] **Step 2: Cross-check every row against the actual manuscript, after Tasks 1-13 have landed**

Do this step last, after every other manuscript-editing task in this plan is committed (section names and line numbers referenced above may shift — e.g., Task 7 relocates Table 1/Table 2/Figures 1-4, Task 13 adds the Acknowledgements section). Re-read the current `manuscript/manuscript_expanded.md` section headers with `grep -n "^##\|^###"` and correct any "Reported on" cell that no longer matches the current section name.

- [ ] **Step 3: Register the new file in the supplement's file inventory**

If `supplementary/supplement_expanded.md`'s `## S10. Reproducibility` / "Pipeline and outputs" subsection lists supplementary deliverables, add one sentence noting the TRIPOD checklist is a separate file (`supplementary/tripod_checklist.md`) submitted alongside the supplement, not a numbered section within it.

- [ ] **Step 4: Commit**

```bash
git add supplementary/tripod_checklist.md supplementary/supplement_expanded.md
git commit -m "docs: add a completed TRIPOD checklist mapping every item to its manuscript location"
```

---

### Task 15: Rewrite the cover letter to about one page

**Files:**
- Modify: `manuscript/cover_letter_expanded.md`

**Interfaces:** None — prose rewrite, verified by word count.

Do this task after Task 8 (stopping-rule wording) and Task 13 (declarations wording) so the cover letter's numbers and phrasing match the final manuscript rather than needing a second pass. Current letter is 1,143 words / 4 rendered pages. Target: 450-550 words / about 1 page, in the five-part structure the review specifies, with an explicit competing-interests sentence and the public-dataset-rule paragraph removed.

**Explicit decision, already made by the user: do not disclose any companion manuscript in this letter.** The current letter's final paragraph ("A companion manuscript from our group uses the same archive to ask a different question...") is cut entirely, not shortened or reworded. Do not name, describe, or allude to any other in-progress manuscript on this archive anywhere in the rewritten letter.

- [ ] **Step 1: Rewrite the letter in five parts**

Replace the full body of `manuscript/cover_letter_expanded.md` (keep the date, "Re:" line, salutation, and signature block) with:

```markdown
We submit "[exact current title]" for consideration as a Paper in *Journal of Neural Engineering*.

**Submission and journal fit.** A calibration-derived score has repeatedly been related to online P300-speller accuracy within the cohort where it was measured, most notably by Mainsah and colleagues in this journal (*J Neural Eng* 2016;13:066007), who derived speller accuracy analytically from a calibration-derived detectability index. Whether a mapping fitted in one set of cohorts transports to a cohort it has never seen is the question that decides whether such a score can be reported anywhere other than where it was developed, and it is the question this manuscript answers.

**What is new.** Using the public BigP3BCI archive, we evaluated a calibration-derived score across 18 source-study cohorts with a leave-one-study-out design (271 participants, 739 session-condition records, 19,611 selections), rather than the single-cohort evaluations the literature has reported to date.

**Principal results.** The association held in every withheld cohort (participant-level r = 0.714) but the fitted mapping from score to expected accuracy did not transport: the calibration intercept had a between-cohort standard deviation of tau = 0.87, spanning a 95% interval for an unrepresented cohort of -1.97 to 1.85 on the log-odds scale, and the slope agreed at tau = 0.43. Both conclusions hold at the lower confidence limit of tau, so the finding does not depend on the number of cohorts being read favourably. A four-cohort subgroup limited to the documented ALS cohorts alone, evaluated on its own, gave a materially tighter and more favourable picture (uncorrected between-cohort slope spread 0.223, against 0.560 across all 18) — a concrete demonstration of how few-cohort evaluation understates real-world variability.

**Why this matters to your readership.** The manuscript separates two claims the field has tended to report together: an association that appears in every cohort examined, and a calibrated mapping that transports between them. A calibration score can support ranking sessions within a setting and can support a data-quality screen; it should not be used to report an expected accuracy in a cohort where the mapping was not developed, without local recalibration. This is a transportability evaluation of a widely proposed relationship, not a classifier-improvement study.

**Declarations.** The authors declare no competing interests. This work has not been submitted elsewhere and is not under consideration by any other journal.

Sincerely,
```

Replace `"[exact current title]"` in the opening line with the manuscript's actual title (`manuscript/manuscript_expanded.md`'s title line) before this file is considered complete — do not leave it unresolved in the committed file.

- [ ] **Step 2: Count words and confirm the page target**

Run:
```bash
python3 -c "
import re
text = open('manuscript/cover_letter_expanded.md').read()
body = re.sub(r'^#.*$', '', text, flags=re.MULTILINE)
print(len(body.split()))
"
```
Expected: 450-550.

- [ ] **Step 3: Re-render and confirm page count**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py --only cover_letter`
Run: `pdfinfo build_expanded/cover_letter.pdf | grep Pages` (or open it) — expect 1, at most 2.

- [ ] **Step 4: Scan for AI-writing tells and commit**

Run: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/cover_letter_expanded.md"`

```bash
git add manuscript/cover_letter_expanded.md
git commit -m "docs: rewrite the cover letter to one page in five parts, with an explicit competing-interests sentence, no companion-manuscript disclosure per author decision"
```

---

### Task 16: Final integration — full rebuild, full test suite, correct the stale-canonical pointer, update the revision log

**Files:**
- Modify: `submission/SUPERSEDED_DO_NOT_SUBMIT.md`
- Modify: `docs/editorial_revision_log.md`
- Verify: everything touched by Tasks 1-15

**Interfaces:** None — integration and verification.

- [ ] **Step 1: Run the full test suite, including the slow regression guard**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest -v`
Expected: all non-slow tests pass (should now be 161 + however many new tests Tasks 2 and 4 added).

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_regression_baseline.py -v -m slow`
Expected: PASS — confirms none of the stats changes in Tasks 2/4 accidentally touched the frozen four-cohort baseline.

- [ ] **Step 2: Rebuild every document from scratch**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/15_build_manuscript.py`

- [ ] **Step 3: Run the full verification checklist against the rebuilt PDFs**

- [ ] No literal `{width=` anywhere: `pdftotext build_expanded/manuscript.pdf - | grep -c 'width=' && pdftotext build_expanded/supplement.pdf - | grep -c 'width='` — both `0`.
- [ ] Abstract ≤300 words (Task 12, Step 3 script, re-run).
- [ ] Body ≤7,300 words (Task 11, Step 4 script, re-run).
- [ ] Cover letter 450-550 words, ≤2 pages (Task 15, Steps 3-4, re-run).
- [ ] No `subsequent` describing the primary same-session analysis: `grep -n "subsequent" manuscript/manuscript_expanded.md` returns nothing.
- [ ] No `accounted for.*between-cohort variance`: `grep -c "accounted for.*between-cohort variance" manuscript/manuscript_expanded.md` returns `0`.
- [ ] No `primary subgroup`: `grep -n "primary subgroup" manuscript/manuscript_expanded.md` returns nothing.
- [ ] MAE prediction interval lower bound is positive in the rendered text (search the PDF text for the corrected numbers from Task 4).
- [ ] `## Acknowledgements` exists and precedes `## Data and Code Availability`; the front matter no longer has `**Funding:**`/`**Competing interests:**`/`**Ethics approval:**`/`**Author contributions:**` before the Abstract.
- [ ] Figure 2 in the rendered manuscript PDF is the 6-panel version; Figure S2 in the supplement PDF is the 18-panel version.
- [ ] `supplementary/tripod_checklist.md` exists and every row's "Reported on" cell matches a real, current section name (re-run Task 14 Step 2's cross-check if any earlier task moved a section).
- [ ] De-AI scan clean on every touched file: `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py "manuscript/manuscript_expanded.md" "manuscript/cover_letter_expanded.md" "supplementary/supplement_expanded.md" "supplementary/tripod_checklist.md"`.

- [ ] **Step 4: Correct the stale canonical-file pointer**

In `submission/SUPERSEDED_DO_NOT_SUBMIT.md`, find the line naming `manuscript/manuscript.md` as canonical (around line 29) and update it to name `manuscript/manuscript_expanded.md`, `manuscript/cover_letter_expanded.md`, and `supplementary/supplement_expanded.md` instead, with a one-line note that the render pipeline is now `scripts/15_build_manuscript.py` rather than a manual process.

- [ ] **Step 5: Update the editorial revision log**

Append a new dated entry to `docs/editorial_revision_log.md` following its existing format, summarizing this pass: the six numbered scientific/statistical fixes, the length cut with before/after word counts, the figure and formatting fixes, the declarations move, the new TRIPOD checklist, and the cover-letter rewrite — mirroring the level of detail the existing entries for the 2026-07-26 major revision already use.

- [ ] **Step 6: Final commit**

```bash
git add submission/SUPERSEDED_DO_NOT_SUBMIT.md docs/editorial_revision_log.md
git commit -m "docs: correct the canonical-file pointer to the expanded manuscript/supplement/cover-letter set, log the pre-submission review pass"
```

---

## Not in scope for this plan

- **DOI-backed archive (Zenodo/OSF).** Requires pushing this repository to GitHub and linking an external Zenodo/OSF account — both actions need the user's explicit authorization and login, and remain the standing human-only item already tracked in project memory.
- **Title shortening.** The review offers two tighter alternative titles. The current title is referenced by name in the GitHub repository description, the companion-overlap disclosure document (`docs/companion-overlap-bigp3bci.md`), and other in-flight manuscripts' cross-references. Changing it is a real option but should be a decision the user makes explicitly, not one folded into a mechanical revision pass — ask before touching it.
- **Confirming JNE's live submission-portal requirements** (separate COI field, specific reference style, current word limits beyond the abstract cap already verified) at the moment of actual submission — Task 13 Step 3 flags the one place this plan's output depends on it.
