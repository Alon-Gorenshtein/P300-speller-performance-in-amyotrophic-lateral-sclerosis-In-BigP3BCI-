# ALS Calibration-to-Online Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a provenance-checked, testable analysis that evaluates calibration-only prediction of online P300-speller performance in the ALS cohorts of bigP3BCI.

**Architecture:** The package will selectively materialize only EDF files for Studies F, L, and N from the source ZIP, parse EDF headers/events into normalized tables, construct calibration and online test outcomes independently, and perform leave-one-study-out validation. Scripts will produce immutable intermediate tables, final estimates, figures, and manuscript inputs; no manuscript number will be typed manually.

**Tech Stack:** Python 3.11; MNE; NumPy; pandas; SciPy; scikit-learn; statsmodels; Matplotlib; pytest; uv.

---

## File structure

- `pyproject.toml`: locked project dependencies and test commands.
- `src/bigp3_als/provenance.py`: validate the archive, choose eligible source members, and selectively extract them to the ignored cache.
- `src/bigp3_als/edf.py`: parse headers and harmonized EDF signal/event streams.
- `src/bigp3_als/trials.py`: reconstruct calibration epochs and valid online character selections.
- `src/bigp3_als/features.py`: calculate leakage-free calibration P300 discriminability and Pz amplitude.
- `src/bigp3_als/validation.py`: run leave-one-study-out models, participant-cluster bootstrap, and sensitivity analyses.
- `src/bigp3_als/render.py`: make publication tables and figures strictly from analysis tables.
- `scripts/01_validate_archive.py` through `scripts/06_render_outputs.py`: reproducible entry points.
- `tests/`: synthetic EDF-independent unit tests and regression tests for every event-reconstruction rule.
- `docs/`: protocol, data dictionary, statistical analysis plan, computational environment, and decision log.
- `manuscript/` and `supplement/`: manuscript source and derived outputs after the analysis is frozen.

### Task 1: Initialize an isolated research package

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/bigp3_als/__init__.py`
- Create: `tests/__init__.py`

- [ ] Write a failing import smoke test for `bigp3_als` and run `uv run pytest tests/test_smoke.py -q`; expect collection failure.
- [ ] Add the minimal package metadata, Python version, analysis dependencies, and a pytest configuration; rerun the smoke test and expect one pass.
- [ ] Add ignore rules for `data/source_cache/`, `output/`, `.venv/`, and macOS `._*` sidecars while keeping source, tests, documentation, and checksums tracked.
- [ ] Commit with `chore: initialize BigP3 ALS validation package`.

### Task 2: Implement provenance-checked selective ingestion

**Files:**
- Create: `src/bigp3_als/provenance.py`
- Create: `tests/test_provenance.py`
- Create: `scripts/01_validate_archive.py`
- Create: `docs/data_provenance.md`

- [ ] Write tests with a synthetic ZIP that assert: only Studies F/L/N EDF members are selected; AppleDouble sidecars are rejected; a wrong archive hash aborts; manifest checksum mismatch aborts; and selected cache content exactly equals the manifest.
- [ ] Run `uv run pytest tests/test_provenance.py -q`; expect failure because the module is absent.
- [ ] Implement `build_manifest`, `validate_archive_sha256`, `validate_member_sha256`, and `activate_cache` with atomic staging. Pin the verified SHA256 of the local BigP3 ZIP in a constant and record all selected member hashes in `output/intermediate/manifest_validation.json`.
- [ ] Run `uv run pytest tests/test_provenance.py -q`; expect all ingestion tests to pass.
- [ ] Run `uv run python scripts/01_validate_archive.py --archive '/Volumes/Extreme SSD/Mimic-IV/bigp3bci-an-open-diverse-and-machine-learning-ready-p300-based-brain-computer-interface-dataset-1.0.0.zip'`; inspect that the manifest contains F/L/N only and commit provenance code and documentation.

### Task 3: Parse clinical metadata and event channels

**Files:**
- Create: `src/bigp3_als/edf.py`
- Create: `tests/test_edf.py`
- Create: `scripts/02_build_metadata.py`
- Create: `docs/data_dictionary.md`

- [ ] Write tests using synthetic fixed-width EDF header bytes to verify ALSFRS-R parsing, adult age-year calculation, missing-value handling, and study-scoped participant/session IDs.
- [ ] Run `uv run pytest tests/test_edf.py -q`; expect missing-module failure.
- [ ] Implement header parsing without treating a 2020 placeholder birth year as a measured age. Implement deterministic channel selection requiring the shared 16 clinical EEG channels and the required event streams.
- [ ] Run tests; expect pass. Then generate `clinical_metadata.parquet` and a missingness table from the selected cache.
- [ ] Commit with `feat: parse BigP3 clinical metadata and EDF schema`.

### Task 4: Reconstruct valid online character outcomes

**Files:**
- Create: `src/bigp3_als/trials.py`
- Create: `tests/test_trials.py`
- Create: `scripts/03_build_trials.py`
- Create: `docs/outcome_definition.md`

- [ ] Write synthetic state-stream tests for a correct selection, incorrect selection, missing selected target, multiple phase-3 samples, and a `FakeFeedback` override. Assert that only non-overridden feedback trials are eligible for the primary outcome.
- [ ] Run `uv run pytest tests/test_trials.py -q`; expect failure because the functions are absent.
- [ ] Implement `reconstruct_online_trials` so target identity comes from the preceding phase-2 trial and predicted identity comes from phase 3. Persist trial-level correctness plus precise exclusion reasons.
- [ ] Run tests; expect pass. Execute the script and manually verify the known probe files: `F_03_SE001_Dyn_Test01.edf` has six reconstructed correct selections, `L_01_SE001_CB_Test06.edf` has four correct of six, and `N_01_SE001_Dry_Test01.edf` has one correct of six.
- [ ] Commit with `feat: reconstruct feedback-phase spelling outcomes`.

### Task 5: Construct leakage-free calibration predictors

**Files:**
- Create: `src/bigp3_als/features.py`
- Create: `tests/test_features.py`
- Create: `scripts/04_extract_features.py`
- Create: `docs/feature_specification.md`

- [ ] Write tests with synthetic labelled epochs asserting that target labels come only from `StimulusType` at stimulus-onset transitions; all epochs are restricted to calibration files; and changing Test data cannot alter the calibration AUC.
- [ ] Run `uv run pytest tests/test_features.py -q`; expect missing-module failure.
- [ ] Implement filtering, -200 to 800 ms epoching, baseline correction, inner grouped cross-validation, regularized logistic AUC, and 250-500 ms Pz amplitude. Require a prespecified minimum number of target and non-target epochs; record exclusions.
- [ ] Run tests; expect pass. Build a session-condition predictor table keyed only to calibration metadata.
- [ ] Commit with `feat: derive calibration-only P300 predictors`.

### Task 6: Validate the clinical deployment question

**Files:**
- Create: `src/bigp3_als/validation.py`
- Create: `tests/test_validation.py`
- Create: `scripts/05_run_validation.py`
- Create: `docs/statistical_analysis_plan.md`

- [ ] Write tests for leave-one-study-out partitioning, zero overlap of held-out study IDs with development data, deterministic bootstrap seeds, and preservation of all sessions/conditions when resampling a participant cluster.
- [ ] Run `uv run pytest tests/test_validation.py -q`; expect missing-module failure.
- [ ] Implement binomial calibration-only models, study-held-out predictions, validation discrimination/calibration/MAE metrics, and participant-cluster bootstrap confidence intervals. Create predeclared secondary Pz-amplitude and ALSFRS-R-enhanced models using identical splits.
- [ ] Run tests; expect pass. Execute the validation script and write immutable estimates, all validation predictions, and study-specific tables.
- [ ] Commit with `feat: add external-study ALS validation analysis`.

### Task 7: Add robustness checks and adversarial audit

**Files:**
- Create: `scripts/05b_run_sensitivity.py`
- Create: `tests/test_sensitivity.py`
- Create: `docs/robustness_matrix.md`

- [ ] Write tests that assert leave-one-participant-out calculations never use the held-out participant, artificial feedback never enters the primary result, and unknown cross-study identity is reported rather than algorithmically inferred.
- [ ] Run `uv run pytest tests/test_sensitivity.py -q`; expect failure.
- [ ] Implement study-specific analyses, leave-one-participant-out sensitivity, a complete-case ALSFRS-R sensitivity, and a table that labels each analysis as primary, secondary, or exploratory.
- [ ] Run the complete test suite with `uv run pytest -q`; expect all tests to pass. Review all output files for participant counts, outcome denominators, and impossible performance values.
- [ ] Commit with `feat: add prespecified robustness analyses`.

### Task 8: Render frozen analysis outputs

**Files:**
- Create: `src/bigp3_als/render.py`
- Create: `scripts/06_render_outputs.py`
- Create: `tests/test_render.py`
- Create: `docs/output_inventory.md`

- [ ] Write tests ensuring figure/table functions reject missing required columns and write files beneath `output/` only.
- [ ] Run `uv run pytest tests/test_render.py -q`; expect failure.
- [ ] Implement a study-flow diagram, calibration-versus-online plot with held-out-study facets, external-validation calibration plot, participant-level spaghetti/forest sensitivity figure, and journal-ready tables.
- [ ] Run the renderer and visually inspect every raster/vector output at publication size. Run `uv run pytest -q` again; expect all tests to pass.
- [ ] Commit with `feat: render frozen clinical validation outputs`.

### Task 9: Produce the clinical manuscript and submission artifacts

**Files:**
- Create: `manuscript/main.md`
- Create: `manuscript/references.bib`
- Create: `supplement/appendix.md`
- Create: `submission/README.md`

- [ ] Draft all manuscript sections only after Task 8 outputs are frozen; source every numerical claim from a table under `output/final/`.
- [ ] Independently verify all references and DOIs with the AMA citation workflow; record unverifiable items rather than inventing citations.
- [ ] Render the manuscript and supplement, check figure/table citations, use journal-neutral language, and run an adversarial clinical-methods review.
- [ ] Create a clean submission folder containing the manuscript, figures, tables, supplement, cover letter, transparency statement, reproducibility instructions, and citation audit; commit with `docs: add submission-ready clinical manuscript package`.

## Self-review

- Spec coverage: Tasks 2-8 implement all analytic components in the design; Task 9 converts only frozen outputs into the manuscript package.
- Placeholder scan: the plan specifies every function boundary, outcome rule, test category, and validation boundary; no unspecified data source or outcome is permitted.
- Consistency: all primary models use Study F/L/N, calibration-only features, feedback-phase character correctness, and leave-one-study-out validation. Study B is not used for ALSFRS-R models.
