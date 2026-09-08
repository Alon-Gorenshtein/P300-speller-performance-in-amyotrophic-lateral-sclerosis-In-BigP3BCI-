# The calibration-to-accuracy mapping in P300 spellers does not transport across cohorts

Analysis code and frozen outputs for the manuscript "The calibration-to-accuracy mapping in P300 spellers does not transport across cohorts, and neither alignment nor local recalibration repairs it," submitted to the *Journal of Neural Engineering*.

This repository contains **code and the frozen analysis outputs**, and no source data. The EEG archive (BigP3BCI 1.0.0) is obtained separately from its distributor; see [The archive](#the-archive) below.

## What the study does

A score computed from the calibration block that precedes a P300-speller session has repeatedly been related to that session's online spelling accuracy, always within the cohort in which it was measured. This study asks a different question: does a mapping *fitted* in one set of cohorts estimate accuracy in a cohort withheld from development?

Using 18 of 20 source studies in the public BigP3BCI archive (271 participants, 739 session-condition records, 19,611 character selections, four cohorts with an amyotrophic lateral sclerosis population), the calibration-to-accuracy mapping was fitted with one source study held out at a time and evaluated on the withheld study.

**Headline result.** The within-cohort association is positive in every cohort, but the fitted mapping does not transport: the calibration intercept has a between-cohort standard deviation (tau) of 0.87, and the slope varies more than tenfold across cohorts (tau 0.43). Four candidate repairs — two signal-alignment specifications, two score-alignment specifications, two nonlinear decision boundaries, and local recalibration using up to 16 participants — were each tested and none meaningfully restored transportability.

## Repository contents

- `src/` — the analysis package (feature extraction, validation, alignment, recalibration, heterogeneity estimation, figure rendering).
- `scripts/` — numbered pipeline scripts, run in order, that reproduce every reported number and figure from the extracted features.
- `output/` — frozen intermediate and final CSV/JSON outputs of the pipeline.
- `manuscript/`, `supplementary/` — the manuscript, supplement, and reviewer-response source files.
- `tests/` — the test suite that guards the frozen numeric outputs against regression.
- `docs/` — supporting analysis notes referenced from the manuscript and supplement.

## Reproducing the analysis

```
uv sync
uv run pytest tests/ -q
uv run python scripts/01_extract_features.py   # and so on, in numbered order
```

The raw EEG archive is required to regenerate features from scratch; the frozen `output/` files let the downstream statistical and figure-generating scripts (later-numbered scripts) run without it.

## The archive

BigP3BCI 1.0.0 (doi:10.13026/0byy-ry86) is distributed separately by PhysioNet and is not redistributed here.

## Citation

If you use this code, please cite the manuscript above (citation details to follow acceptance) and the BigP3BCI archive.
