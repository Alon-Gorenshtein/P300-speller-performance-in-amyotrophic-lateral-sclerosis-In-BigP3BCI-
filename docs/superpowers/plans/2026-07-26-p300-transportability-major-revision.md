# P300 Transportability Major Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct an aliasing error in the feature pipeline, replace the paper's headline heterogeneity argument with a hierarchical estimate that separates true between-cohort variation from sampling error, and repair the unit-of-analysis, benchmark, and overclaim problems a reviewer identified, so the manuscript states only what the evidence supports.

**Architecture:** The existing pipeline stays. Feature extraction gains a correct antialiasing decimator; a new `heterogeneity.py` module estimates per-cohort calibration slopes and intercepts with their standard errors and fits a random-effects model for tau-squared; a new `protocol.py` module recovers per-cohort protocol covariates and tests whether they explain residual heterogeneity; the analysis frame moves from character-expanded rows to grouped binomial rows so the estimand is explicit. Every downstream number, figure, table and manuscript claim is regenerated from the corrected pipeline.

**Tech Stack:** Python 3.11 via `uv`, NumPy 2.3, SciPy 1.16, scikit-learn 1.7, statsmodels 0.14, pandas 2.3, matplotlib, MNE, pytest.

## Global Constraints

- Run everything through `uv run` with `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv` and `COPYFILE_DISABLE=1`. The project venv cannot be created on the external volume because AppleDouble files break wheel installation.
- Python is pinned `>=3.11,<3.13`. The system `python3` is 3.9 and will fail on `zip(strict=)`.
- `scipy.stats.linregress` is broken against this NumPy build. Use `bigp3_als.expanded._simple_regression`.
- `scipy.stats.pearsonr` rejects object-dtype input. Coerce with `pd.to_numeric` first.
- Never edit `output/final/`. That directory holds the frozen four-cohort analysis and is the regression baseline.
- After any change to shared code, re-run the four-cohort regression check in Task 1 and confirm the six headline metrics still reproduce to `0.00e+00`.
- No em dashes anywhere in prose. Run `python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py <file>` before every manuscript commit.
- Journal of Neural Engineering caps the abstract at 300 words and states it may rescind over-length manuscripts.
- Descriptive language only. No causal claims. Do not write "mechanism" unless a mediation or covariate-adjustment analysis supports it.

---

## Reviewer findings and where each is addressed

| # | Finding | Task |
|---|---|---|
| 1 | Decimation aliases 10.67 to 30 Hz | 2, 3 |
| 2 | Raw slope SD conflates heterogeneity with sampling error | 4, 5 |
| 3 | Predictor is decoder-calibration quality, not a biomarker | 9, 11 |
| 4 | Predictor precision varies by cohort | 6 |
| 5 | Unit of analysis and character weighting | 7 |
| 6 | Benchmark terminology inconsistent and one claim wrong | 8 |
| 7 | ALS interaction not credible at record level | 10 |
| 8 | "Associated in every cohort" overclaims | 5, 11 |
| 9 | Omitted protocol covariates | 12 |
| 10 | Promised analyses missing | 13 |
| 11 | No calibration figure | 14 |
| 12 | Terminology, ordering provenance, counts, placeholders | 15 |
| 13 | Cover letter overclaims | 16 |

---

### Task 1: Lock the regression baseline before touching shared code

**Files:**
- Create: `tests/test_regression_baseline.py`
- Read: `output/final/external_validation_metrics.csv`

**Interfaces:**
- Consumes: nothing.
- Produces: `test_four_cohort_primary_is_unchanged`, a guard every later task must keep green.

- [ ] **Step 1: Write the failing test**

```python
"""The four-cohort result is frozen. Any change to shared code must not move it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

BASELINE = {
    "session_mean_absolute_error": 0.095282,
    "character_brier_score": 0.110083,
    "character_brier_skill_score": 0.287339,
    "predicted_probability_character_auc": 0.827604,
    "calibration_intercept": 0.021516,
    "calibration_slope": 0.991029,
}


@pytest.mark.slow
def test_four_cohort_primary_is_unchanged(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, "scripts/05_run_validation.py",
         "--trials", "output/intermediate/online_trials_with_b.csv",
         "--features", "output/intermediate/calibration_features_with_b.csv",
         "--metadata", "output/intermediate/file_metadata_with_b.csv",
         "--output-directory", str(tmp_path)],
        check=True,
    )
    metrics = pd.read_csv(tmp_path / "external_validation_metrics.csv")
    pooled = metrics.loc[metrics["held_out_study"].str.startswith("Pooled")].iloc[0]
    for name, expected in BASELINE.items():
        assert pooled[name] == pytest.approx(expected, abs=1e-6), name
```

- [ ] **Step 2: Run it and confirm it passes now**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_regression_baseline.py -v -m slow`
Expected: PASS. If it fails now, stop and investigate before any other task.

- [ ] **Step 3: Register the marker**

Add to `pyproject.toml` under `[tool.pytest.ini_options]`:

```toml
markers = ["slow: reruns a full validation pass"]
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_regression_baseline.py pyproject.toml
git commit -m "test: freeze the four-cohort primary result as a regression guard"
```

---

### Task 2: Replace the aliasing decimator

**Files:**
- Modify: `src/bigp3_als/features.py:52-55`
- Test: `tests/test_features_decimation.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `_downsampled_epoch_features(epochs, decimation_factor=4)` returning shape `(n_epochs, n_channels * ceil(n_samples / factor))`, and module constant `DECIMATION_FACTOR = 4`.

**Why 4.** The bandpass edge is 30 Hz. After decimating by `d` the Nyquist frequency is `256 / d / 2`. Only `d <= 4` keeps Nyquist at or above 30 Hz (`d=4` gives 32 Hz). The current `d=12` gives 10.67 Hz, so everything from 10.67 to 30 Hz folds back onto lower frequencies. Feature count rises from 352 to 16 x 64 = 1024, which the L2-regularised classifier handles because each session supplies thousands of epochs.

- [ ] **Step 1: Write the failing test**

```python
"""Decimation must not alias the retained passband."""

from __future__ import annotations

import numpy as np

from bigp3_als.features import DECIMATION_FACTOR, _downsampled_epoch_features

SAMPLING_HZ = 256.0
BANDPASS_EDGE_HZ = 30.0


def test_decimation_factor_keeps_nyquist_above_the_passband() -> None:
    nyquist = SAMPLING_HZ / DECIMATION_FACTOR / 2.0
    assert nyquist >= BANDPASS_EDGE_HZ


def test_feature_width_matches_the_decimation_factor() -> None:
    epochs = np.zeros((5, 16, 256))
    features = _downsampled_epoch_features(epochs)
    expected_samples = int(np.ceil(256 / DECIMATION_FACTOR))
    assert features.shape == (5, 16 * expected_samples)


def test_a_25_hz_tone_is_not_folded_to_a_lower_frequency() -> None:
    """At the old factor a 25 Hz tone aliased to 3.7 Hz. It must survive as itself."""
    time = np.arange(256) / SAMPLING_HZ
    tone = np.sin(2 * np.pi * 25.0 * time)
    epochs = np.tile(tone, (1, 1, 1))

    features = _downsampled_epoch_features(epochs).reshape(1, 1, -1)[0, 0]

    decimated_rate = SAMPLING_HZ / DECIMATION_FACTOR
    spectrum = np.abs(np.fft.rfft(features - features.mean()))
    peak_hz = np.fft.rfftfreq(len(features), 1.0 / decimated_rate)[spectrum.argmax()]
    assert abs(peak_hz - 25.0) < 2.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_features_decimation.py -v`
Expected: FAIL, `ImportError: cannot import name 'DECIMATION_FACTOR'`.

- [ ] **Step 3: Implement**

Replace `src/bigp3_als/features.py:52-55` with:

```python
DECIMATION_FACTOR = 4


def _downsampled_epoch_features(epochs: np.ndarray, decimation_factor: int = DECIMATION_FACTOR) -> np.ndarray:
    """Return a compact epoch representation without folding the retained passband.

    Taking every nth sample is only safe when the resulting Nyquist frequency stays above the
    filter passband. Epochs reach this function band-limited to 30 Hz, so a factor of four leaves
    Nyquist at 32 Hz. Larger factors were used previously and folded 10.7 to 30 Hz onto lower
    frequencies.
    """
    if decimation_factor < 1:
        raise ValueError("decimation factor must be at least 1")
    return epochs[:, :, ::decimation_factor].reshape(len(epochs), -1)
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_features_decimation.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add src/bigp3_als/features.py tests/test_features_decimation.py
git commit -m "fix: decimate at a factor that keeps Nyquist above the 30 Hz passband

Taking every twelfth sample of a 256 Hz signal band-limited to 30 Hz left an
effective Nyquist of 10.67 Hz, folding 10.67 to 30 Hz onto lower frequencies.
A factor of four leaves Nyquist at 32 Hz."
```

---

### Task 3: Regenerate every feature and every downstream output

**Files:**
- Regenerate: `output/intermediate/calibration_features_all20.csv`
- Regenerate: `output/expanded/*`
- Create: `docs/pipeline_rerun_2026-07-26.md`

**Interfaces:**
- Consumes: `DECIMATION_FACTOR` from Task 2.
- Produces: the corrected `output/expanded/` tree that every later task reads.

- [ ] **Step 1: Rebuild calibration features**

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration"
export UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1
cp output/intermediate/calibration_features_all20.csv /tmp/features_aliased_backup.csv
uv run python scripts/04_extract_features.py \
  --cache data/source_cache_full \
  --output output/intermediate/calibration_features_all20.csv
```

Expect roughly 20 minutes and 521 session rows.

- [ ] **Step 2: Record how much the predictor moved**

```bash
uv run python -c "
import pandas as pd
old=pd.read_csv('/tmp/features_aliased_backup.csv'); new=pd.read_csv('output/intermediate/calibration_features_all20.csv')
k=['study','study_participant_id','session_id']
m=old.merge(new,on=k,suffixes=('_old','_new'))
d=(m['calibration_auc_new']-m['calibration_auc_old'])
print(f'sessions {len(m)} | mean change {d.mean():+.4f} | sd {d.std():.4f} | max |change| {d.abs().max():.4f}')
print(f'rank correlation old vs new: {m[[\"calibration_auc_old\",\"calibration_auc_new\"]].corr(method=\"spearman\").iloc[0,1]:.4f}')
"
```

Write the output into `docs/pipeline_rerun_2026-07-26.md` under a heading "Effect of the decimation correction on the predictor". If the rank correlation is above 0.98 the corrected pipeline tells a similar story and the revision is mostly about inference; if it is below 0.9 the primary results may change materially and every number in the manuscript must be re-read, not just re-run.

- [ ] **Step 3: Re-run the four-cohort regression guard**

Run: `uv run python -m pytest tests/test_regression_baseline.py -v -m slow`
Expected: **FAIL.** The frozen baseline used the aliased features, so it must move. Record the new six values in `docs/pipeline_rerun_2026-07-26.md`, then update `BASELINE` in `tests/test_regression_baseline.py` to the corrected values and add a comment naming this task as the reason the baseline was re-cut.

- [ ] **Step 4: Re-run the expanded analysis and the sensitivities**

```bash
uv run python scripts/06_run_expanded.py --bootstrap-repetitions 2000 --output-directory output/expanded
uv run python scripts/07_run_sensitivity.py
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_regression_baseline.py docs/pipeline_rerun_2026-07-26.md
git commit -m "chore: regenerate all features and outputs after the decimation fix"
```

---

### Task 4: Per-cohort calibration estimates with standard errors

**Files:**
- Create: `src/bigp3_als/heterogeneity.py`
- Test: `tests/test_heterogeneity.py`

**Interfaces:**
- Consumes: `output/expanded/external_validation_predictions.csv`, which carries `held_out_study`, `correct`, `n`, `predicted_probability`, and a `model_role` column that today holds only `primary` but must be filtered anyway so a later comparator run cannot silently pollute the fit.
- Produces:
  - `cohort_calibration(predictions: pd.DataFrame) -> pd.DataFrame` with columns `held_out_study`, `intercept`, `intercept_se`, `slope`, `slope_se`, `n_records`, `n_selections`.
  - `random_effects(estimates: pd.Series, standard_errors: pd.Series) -> dict` with keys `pooled`, `pooled_se`, `tau_squared`, `tau`, `i_squared`, `q_statistic`, `q_p_value`, `n_studies`, `prediction_interval_low`, `prediction_interval_high`.

- [ ] **Step 1: Write the failing test**

```python
"""Cohort calibration must carry its own uncertainty, and pooling must separate
true between-cohort variation from sampling error."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bigp3_als.heterogeneity import cohort_calibration, random_effects


def _predictions(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for study, slope in (("StudyA", 1.0), ("StudyB", 1.0)):
        for index in range(40):
            p = float(np.clip(rng.uniform(0.3, 0.95), 0.01, 0.99))
            n = 20
            rows.append({"held_out_study": study, "n": n,
                         "correct": rng.binomial(n, p), "predicted_probability": p})
    return pd.DataFrame(rows)


def test_cohort_calibration_returns_one_row_per_cohort_with_standard_errors() -> None:
    result = cohort_calibration(_predictions())

    assert list(result["held_out_study"]) == ["StudyA", "StudyB"]
    assert (result["slope_se"] > 0).all()
    assert (result["intercept_se"] > 0).all()


def test_calibration_slope_is_near_one_when_predictions_are_correct() -> None:
    result = cohort_calibration(_predictions())

    for _, row in result.iterrows():
        assert row["slope"] == pytest.approx(1.0, abs=0.45)


def test_random_effects_reports_no_heterogeneity_for_identical_estimates() -> None:
    summary = random_effects(pd.Series([1.0, 1.0, 1.0, 1.0]), pd.Series([0.1, 0.1, 0.1, 0.1]))

    assert summary["tau_squared"] == pytest.approx(0.0, abs=1e-9)
    assert summary["i_squared"] == pytest.approx(0.0, abs=1e-6)
    assert summary["pooled"] == pytest.approx(1.0, abs=1e-9)


def test_random_effects_attributes_small_spread_to_sampling_error() -> None:
    """Spread the same size as the standard errors is not evidence of heterogeneity."""
    summary = random_effects(pd.Series([0.9, 1.0, 1.1]), pd.Series([0.3, 0.3, 0.3]))

    assert summary["tau_squared"] == pytest.approx(0.0, abs=1e-6)
    assert summary["i_squared"] < 10.0


def test_random_effects_detects_spread_far_larger_than_the_standard_errors() -> None:
    summary = random_effects(pd.Series([0.1, 1.0, 2.2]), pd.Series([0.05, 0.05, 0.05]))

    assert summary["tau_squared"] > 0.3
    assert summary["i_squared"] > 90.0
    assert summary["q_p_value"] < 0.01


def test_prediction_interval_is_wider_than_the_confidence_interval() -> None:
    summary = random_effects(pd.Series([0.1, 1.0, 2.2]), pd.Series([0.05, 0.05, 0.05]))
    width = summary["prediction_interval_high"] - summary["prediction_interval_low"]
    assert width > 2 * 1.96 * summary["pooled_se"]


def test_random_effects_refuses_a_single_study() -> None:
    with pytest.raises(ValueError, match="at least two"):
        random_effects(pd.Series([1.0]), pd.Series([0.1]))
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_heterogeneity.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'bigp3_als.heterogeneity'`.

- [ ] **Step 3: Implement**

```python
"""Separate genuine between-cohort variation from sampling error.

Reporting the spread of cohort-specific calibration slopes as evidence of heterogeneity assumes
each slope is measured precisely. Cohorts here differ several-fold in participants and selections,
and some sit near ceiling, so part of the observed spread is sampling error. A random-effects
summary estimates the between-cohort variance after the within-cohort variance is accounted for,
which is the quantity the transportability claim actually needs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

PROBABILITY_FLOOR = 1e-6


def cohort_calibration(predictions: pd.DataFrame) -> pd.DataFrame:
    """Fit calibration intercept and slope, with standard errors, inside each withheld cohort."""
    required = {"held_out_study", "correct", "n", "predicted_probability"}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"predictions missing columns: {missing}")

    if "model_role" in predictions.columns:
        predictions = predictions.loc[predictions["model_role"] == "primary"]
        if predictions.empty:
            raise ValueError("no primary-model predictions found")

    rows: list[dict[str, object]] = []
    for study, group in predictions.groupby("held_out_study", sort=True):
        if str(study).startswith("Pooled"):
            continue
        probability = np.clip(
            group["predicted_probability"].to_numpy(dtype=float), PROBABILITY_FLOOR, 1 - PROBABILITY_FLOOR
        )
        design = sm.add_constant(np.log(probability / (1 - probability)), has_constant="add")
        successes = group["correct"].to_numpy(dtype=float)
        trials = group["n"].to_numpy(dtype=float)
        entry: dict[str, object] = {
            "held_out_study": study,
            "n_records": int(len(group)),
            "n_selections": int(trials.sum()),
            "intercept": np.nan, "intercept_se": np.nan,
            "slope": np.nan, "slope_se": np.nan,
        }
        try:
            model = sm.GLM(
                np.column_stack([successes, trials - successes]), design, family=sm.families.Binomial()
            ).fit()
            entry.update(
                intercept=float(model.params[0]), intercept_se=float(model.bse[0]),
                slope=float(model.params[1]), slope_se=float(model.bse[1]),
            )
        except (ValueError, IndexError, np.linalg.LinAlgError,
                sm.tools.sm_exceptions.PerfectSeparationError):
            pass
        rows.append(entry)
    return pd.DataFrame(rows)


def random_effects(estimates: pd.Series, standard_errors: pd.Series) -> dict[str, float]:
    """Summarise cohort estimates by DerSimonian and Laird random-effects pooling."""
    frame = pd.DataFrame({"y": pd.to_numeric(estimates, errors="coerce"),
                          "se": pd.to_numeric(standard_errors, errors="coerce")}).dropna()
    frame = frame.loc[frame["se"] > 0]
    k = len(frame)
    if k < 2:
        raise ValueError("random-effects pooling needs at least two studies")

    y = frame["y"].to_numpy(dtype=float)
    variance = frame["se"].to_numpy(dtype=float) ** 2
    fixed_weight = 1.0 / variance
    fixed_mean = float((fixed_weight * y).sum() / fixed_weight.sum())

    q = float((fixed_weight * (y - fixed_mean) ** 2).sum())
    c = float(fixed_weight.sum() - (fixed_weight**2).sum() / fixed_weight.sum())
    tau_squared = max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0

    weight = 1.0 / (variance + tau_squared)
    pooled = float((weight * y).sum() / weight.sum())
    pooled_se = float(np.sqrt(1.0 / weight.sum()))
    critical = float(stats.t.ppf(0.975, df=k - 1))
    spread = float(np.sqrt(tau_squared + pooled_se**2))

    return {
        "n_studies": float(k),
        "pooled": pooled,
        "pooled_se": pooled_se,
        "tau_squared": tau_squared,
        "tau": float(np.sqrt(tau_squared)),
        "i_squared": float(max(0.0, 100.0 * (q - (k - 1)) / q)) if q > 0 else 0.0,
        "q_statistic": q,
        "q_p_value": float(stats.chi2.sf(q, df=k - 1)),
        "prediction_interval_low": pooled - critical * spread,
        "prediction_interval_high": pooled + critical * spread,
    }
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_heterogeneity.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 5: Commit**

```bash
git add src/bigp3_als/heterogeneity.py tests/test_heterogeneity.py
git commit -m "feat: estimate between-cohort calibration heterogeneity with sampling error removed"
```

---

### Task 5: Run heterogeneity on real data and decide whether the headline survives

**Files:**
- Create: `scripts/08_run_heterogeneity.py`
- Create: `output/expanded/cohort_calibration.csv`, `output/expanded/heterogeneity_summary.json`
- Create: `docs/heterogeneity_verdict.md`

**Interfaces:**
- Consumes: `cohort_calibration`, `random_effects` from Task 4.
- Produces: `output/expanded/cohort_calibration.csv` read by Tasks 11 and 14.

- [ ] **Step 1: Write the runner**

```python
"""Report calibration heterogeneity across withheld cohorts with sampling error removed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from scipy import stats

from bigp3_als.heterogeneity import cohort_calibration, random_effects


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path,
                        default=Path("output/expanded/external_validation_predictions.csv"))
    parser.add_argument("--output-directory", type=Path, default=Path("output/expanded"))
    arguments = parser.parse_args()

    calibration = cohort_calibration(pd.read_csv(arguments.predictions))
    for column, estimate, error in (("slope", "slope", "slope_se"), ("intercept", "intercept", "intercept_se")):
        critical = stats.norm.ppf(0.975)
        calibration[f"{column}_ci_low"] = calibration[estimate] - critical * calibration[error]
        calibration[f"{column}_ci_high"] = calibration[estimate] + critical * calibration[error]
    calibration.to_csv(arguments.output_directory / "cohort_calibration.csv", index=False)

    summary = {
        "slope": random_effects(calibration["slope"], calibration["slope_se"]),
        "intercept": random_effects(calibration["intercept"], calibration["intercept_se"]),
        "naive_slope_sd": float(calibration["slope"].std(ddof=1)),
        "naive_intercept_sd": float(calibration["intercept"].std(ddof=1)),
    }
    (arguments.output_directory / "heterogeneity_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )

    for name in ("slope", "intercept"):
        s = summary[name]
        print(f"{name}: pooled {s['pooled']:.3f}, tau {s['tau']:.3f}, I2 {s['i_squared']:.1f}%, "
              f"Q p {s['q_p_value']:.2e}, PI [{s['prediction_interval_low']:.3f}, "
              f"{s['prediction_interval_high']:.3f}]")
    print(f"naive slope SD {summary['naive_slope_sd']:.3f} vs tau {summary['slope']['tau']:.3f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/08_run_heterogeneity.py`

- [ ] **Step 3: Write the verdict document**

Create `docs/heterogeneity_verdict.md` recording tau, I-squared, the Q test, the prediction interval, and the naive standard deviation, then state which of these three the data support. **This decides the paper's headline. Do not write the Results until it is written down.**

- **Heterogeneity confirmed** (`I2 > 75%`, `Q p < 0.01`, slope prediction interval excluding a useful range): the current claim stands. Report tau and I-squared instead of the naive standard deviation everywhere.
- **Heterogeneity moderate** (`I2` 40 to 75%): soften to "calibration varied across cohorts beyond what sampling error explains, though the between-cohort variance is imprecisely estimated". Title becomes the reviewer's suggested wording.
- **Heterogeneity not established** (`I2 < 40%` or `Q p > 0.05`): **the paper's headline is wrong.** Retitle to the association finding, move calibration variability to a limitation, and state plainly that the observed spread of cohort slopes is compatible with sampling error. Flag this to the author before writing further.

- [ ] **Step 4: Commit**

```bash
git add scripts/08_run_heterogeneity.py docs/heterogeneity_verdict.md
git commit -m "feat: report calibration heterogeneity as tau and I-squared rather than a raw spread"
```

---

### Task 6: Quantify predictor precision per cohort

**Files:**
- Create: `src/bigp3_als/predictor_precision.py`
- Test: `tests/test_predictor_precision.py`
- Create: `output/expanded/predictor_precision.csv`

**Interfaces:**
- Consumes: `output/intermediate/calibration_features_all20.csv`, `output/expanded/cohort_calibration.csv`.
- Produces: `precision_table(features, records) -> pd.DataFrame` with `study`, `median_train_files`, `median_folds`, `median_calibration_epochs`, `median_target_epochs`, `auc_standard_error`; and `precision_versus_slope(precision, calibration) -> dict` with `spearman_rho`, `p_value`, `n_studies`.

**Why.** A noisier predictor attenuates a fitted slope. If cohorts with fewer calibration files show systematically flatter slopes, part of the heterogeneity is measurement error rather than true cohort difference, and the paper must say so.

- [ ] **Step 1: Write the failing test**

```python
"""Predictor precision differs between cohorts and must be measured, because
measurement error in a predictor flattens a fitted slope."""

from __future__ import annotations

import pandas as pd
import pytest

from bigp3_als.predictor_precision import precision_table, precision_versus_slope


def _features() -> pd.DataFrame:
    return pd.DataFrame({
        "study": ["StudyA"] * 3 + ["StudyB"] * 3,
        "study_participant_id": [f"P{i}" for i in range(6)],
        "session_id": ["SE001"] * 6,
        "train_file_count": [10, 10, 10, 2, 2, 2],
        "n_calibration_epochs": [4000, 4000, 4000, 400, 400, 400],
        "n_target_epochs": [600, 600, 600, 60, 60, 60],
        "calibration_auc": [0.80, 0.82, 0.78, 0.70, 0.60, 0.85],
    })


def test_precision_table_reports_one_row_per_study() -> None:
    table = precision_table(_features())

    assert list(table["study"]) == ["StudyA", "StudyB"]
    assert table.loc[table["study"] == "StudyA", "median_train_files"].iloc[0] == 10


def test_fold_count_is_capped_at_five_by_the_pipeline() -> None:
    table = precision_table(_features())

    assert table.loc[table["study"] == "StudyA", "median_folds"].iloc[0] == 5
    assert table.loc[table["study"] == "StudyB", "median_folds"].iloc[0] == 2


def test_cohort_with_fewer_epochs_has_the_larger_auc_standard_error() -> None:
    table = precision_table(_features()).set_index("study")

    assert table.loc["StudyB", "auc_standard_error"] > table.loc["StudyA", "auc_standard_error"]


def test_precision_versus_slope_returns_a_rank_correlation() -> None:
    precision = pd.DataFrame({"study": ["StudyA", "StudyB", "StudyC"],
                              "auc_standard_error": [0.01, 0.05, 0.10]})
    calibration = pd.DataFrame({"held_out_study": ["StudyA", "StudyB", "StudyC"],
                                "slope": [1.5, 1.0, 0.5]})

    result = precision_versus_slope(precision, calibration)

    assert result["n_studies"] == 3
    assert result["spearman_rho"] == pytest.approx(-1.0, abs=1e-9)
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_predictor_precision.py -v`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
"""Measure how precisely the calibration score itself was estimated in each cohort.

The score is a cross-validated area under the curve computed from that session's calibration files.
Sessions differ several-fold in files, folds and surviving epochs, so the score is not measured
equally well everywhere. Measurement error in a predictor attenuates a fitted slope, which is an
alternative explanation for between-cohort differences in calibration.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

MAX_FOLDS = 5


def _auc_standard_error(auc: float, n_target: float, n_nontarget: float) -> float:
    """Hanley and McNeil approximate standard error of an area under the curve."""
    if n_target < 1 or n_nontarget < 1:
        return float("nan")
    q1 = auc / (2 - auc)
    q2 = 2 * auc**2 / (1 + auc)
    variance = (
        auc * (1 - auc) + (n_target - 1) * (q1 - auc**2) + (n_nontarget - 1) * (q2 - auc**2)
    ) / (n_target * n_nontarget)
    return float(np.sqrt(max(variance, 0.0)))


def precision_table(features: pd.DataFrame) -> pd.DataFrame:
    """Summarise, per study, how much data supported each session's calibration score."""
    frame = features.dropna(subset=["calibration_auc"]).copy()
    frame["folds"] = frame["train_file_count"].clip(upper=MAX_FOLDS)
    frame["n_nontarget_epochs"] = frame["n_calibration_epochs"] - frame["n_target_epochs"]
    frame["auc_se"] = [
        _auc_standard_error(a, t, nt)
        for a, t, nt in zip(frame["calibration_auc"], frame["n_target_epochs"], frame["n_nontarget_epochs"])
    ]
    return (
        frame.groupby("study", sort=True)
        .agg(
            median_train_files=("train_file_count", "median"),
            median_folds=("folds", "median"),
            median_calibration_epochs=("n_calibration_epochs", "median"),
            median_target_epochs=("n_target_epochs", "median"),
            auc_standard_error=("auc_se", "median"),
        )
        .reset_index()
    )


def precision_versus_slope(precision: pd.DataFrame, calibration: pd.DataFrame) -> dict[str, float]:
    """Test whether cohorts with a noisier predictor show flatter calibration slopes."""
    merged = precision.merge(
        calibration.rename(columns={"held_out_study": "study"})[["study", "slope"]], on="study"
    ).dropna(subset=["auc_standard_error", "slope"])
    if len(merged) < 3:
        return {"n_studies": float(len(merged)), "spearman_rho": float("nan"), "p_value": float("nan")}
    rho, p_value = stats.spearmanr(merged["auc_standard_error"], merged["slope"])
    return {"n_studies": float(len(merged)), "spearman_rho": float(rho), "p_value": float(p_value)}
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_predictor_precision.py -v`
Expected: PASS, 4 tests.

- [ ] **Step 5: Produce the real table and commit**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -c "
import pandas as pd, json
from bigp3_als.predictor_precision import precision_table, precision_versus_slope
p = precision_table(pd.read_csv('output/intermediate/calibration_features_all20.csv'))
p.to_csv('output/expanded/predictor_precision.csv', index=False)
c = pd.read_csv('output/expanded/cohort_calibration.csv')
print(json.dumps(precision_versus_slope(p, c), indent=2))
print(p.to_string(index=False))
"
git add src/bigp3_als/predictor_precision.py tests/test_predictor_precision.py
git commit -m "feat: measure per-cohort predictor precision as an alternative explanation for slope heterogeneity"
```

---

### Task 7: Make the estimand explicit with grouped binomial fitting

**Files:**
- Create: `src/bigp3_als/estimand.py`
- Test: `tests/test_estimand.py`
- Create: `output/expanded/estimand_comparison.csv`

**Interfaces:**
- Consumes: `output/expanded/analysis_records.csv`.
- Produces: `fit_grouped_binomial(development, validation, feature, weighting) -> np.ndarray` where `weighting` is one of `"character"`, `"session"`, `"participant"`; and `compare_estimands(records, feature) -> pd.DataFrame` with one row per weighting and columns `weighting`, `mean_absolute_error`, `calibration_slope`, `n_units`.

**Why.** The current model is fitted on character-expanded rows, so a session contributing 30 characters influences the fit thirty times as much as one contributing 4, even though the predictor is identical within a session. That silently chooses the per-character estimand. The paper should state which estimand it means and show that the choice does not drive the conclusion.

- [ ] **Step 1: Write the failing test**

```python
"""The fitted mapping depends on what is being weighted. Make that explicit."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bigp3_als.estimand import compare_estimands, fit_grouped_binomial


def _records() -> pd.DataFrame:
    rows = []
    for study in ("StudyA", "StudyB", "StudyC"):
        for participant in range(6):
            score = 0.55 + 0.06 * participant
            n = 4 if participant < 3 else 30
            rows.append({
                "study": study,
                "study_participant_id": f"{study}:P{participant}",
                "session_id": "SE001",
                "condition": "CB",
                "n": n,
                "correct": int(round(n * min(0.99, 0.4 + 0.09 * participant))),
                "calibration_auc": score,
            })
    return pd.DataFrame(rows)


def test_grouped_binomial_returns_one_probability_per_validation_record() -> None:
    records = _records()
    development = records.loc[records["study"] != "StudyC"]
    validation = records.loc[records["study"] == "StudyC"]

    predictions = fit_grouped_binomial(development, validation, "calibration_auc", "character")

    assert predictions.shape == (len(validation),)
    assert ((predictions > 0) & (predictions < 1)).all()


def test_session_weighting_differs_from_character_weighting_when_denominators_differ() -> None:
    records = _records()
    development = records.loc[records["study"] != "StudyC"]
    validation = records.loc[records["study"] == "StudyC"]

    by_character = fit_grouped_binomial(development, validation, "calibration_auc", "character")
    by_session = fit_grouped_binomial(development, validation, "calibration_auc", "session")

    assert not np.allclose(by_character, by_session)


def test_unknown_weighting_is_rejected() -> None:
    records = _records()
    with pytest.raises(ValueError, match="weighting"):
        fit_grouped_binomial(records, records, "calibration_auc", "per-hour")


def test_compare_estimands_reports_every_weighting() -> None:
    result = compare_estimands(_records(), "calibration_auc")

    assert set(result["weighting"]) == {"character", "session", "participant"}
    assert (result["mean_absolute_error"] > 0).all()
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_estimand.py -v`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
"""Fit the calibration-to-accuracy mapping under an explicit choice of estimand.

Expanding each record into one row per character weights the fit by how many characters a session
contributed. That answers a question about a randomly chosen character. Weighting sessions or
participants equally answers different questions. The three are reported together so the reader can
see the mapping does not rest on an unstated choice.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

WEIGHTINGS = ("character", "session", "participant")


def _unit_weights(records: pd.DataFrame, weighting: str) -> np.ndarray:
    if weighting == "character":
        return records["n"].to_numpy(dtype=float)
    if weighting == "session":
        return np.ones(len(records), dtype=float)
    if weighting == "participant":
        counts = records.groupby("study_participant_id")["n"].transform("size")
        return (1.0 / counts).to_numpy(dtype=float)
    raise ValueError(f"unknown weighting: {weighting}; expected one of {WEIGHTINGS}")


def fit_grouped_binomial(
    development: pd.DataFrame, validation: pd.DataFrame, feature: str, weighting: str
) -> np.ndarray:
    """Fit on grouped successes and trials, then estimate accuracy for the validation records."""
    if weighting not in WEIGHTINGS:
        raise ValueError(f"unknown weighting: {weighting}; expected one of {WEIGHTINGS}")

    development = development.dropna(subset=[feature])
    mean = float(development[feature].mean())
    deviation = float(development[feature].std(ddof=0)) or 1.0

    x_dev = sm.add_constant(
        ((development[feature].to_numpy(dtype=float) - mean) / deviation), has_constant="add"
    )
    successes = development["correct"].to_numpy(dtype=float)
    trials = development["n"].to_numpy(dtype=float)
    weights = _unit_weights(development, weighting)
    scale = weights / trials

    model = sm.GLM(
        np.column_stack([successes, trials - successes]),
        x_dev,
        family=sm.families.Binomial(),
        freq_weights=scale,
    ).fit()

    x_val = sm.add_constant(
        ((validation[feature].to_numpy(dtype=float) - mean) / deviation), has_constant="add"
    )
    return np.asarray(model.predict(x_val), dtype=float)


def compare_estimands(records: pd.DataFrame, feature: str = "calibration_auc") -> pd.DataFrame:
    """Repeat the withheld-cohort evaluation under each weighting."""
    records = records.dropna(subset=[feature]).copy()
    observed = records["correct"] / records["n"]

    rows: list[dict[str, object]] = []
    for weighting in WEIGHTINGS:
        errors: list[float] = []
        for study in sorted(records["study"].unique()):
            development = records.loc[records["study"] != study]
            validation = records.loc[records["study"] == study]
            if development.empty or validation.empty:
                continue
            predicted = fit_grouped_binomial(development, validation, feature, weighting)
            errors.extend(np.abs(observed.loc[validation.index].to_numpy(dtype=float) - predicted))
        units = {
            "character": int(records["n"].sum()),
            "session": records.groupby(["study", "study_participant_id", "session_id"]).ngroups,
            "participant": records["study_participant_id"].nunique(),
        }[weighting]
        rows.append({
            "weighting": weighting,
            "mean_absolute_error": float(np.mean(errors)) if errors else float("nan"),
            "n_units": units,
        })
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_estimand.py -v`
Expected: PASS, 4 tests.

- [ ] **Step 5: Produce the comparison and commit**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -c "
import pandas as pd
from bigp3_als.estimand import compare_estimands
r = pd.read_csv('output/expanded/analysis_records.csv')
t = compare_estimands(r)
t.to_csv('output/expanded/estimand_comparison.csv', index=False)
print(t.to_string(index=False))
"
git add src/bigp3_als/estimand.py tests/test_estimand.py
git commit -m "feat: fit the mapping as grouped binomial under three explicit estimands"
```

---

### Task 8: Fix the benchmark naming and the incorrect claim

**Files:**
- Modify: `src/bigp3_als/strengthening.py` (rename columns in `null_benchmark`)
- Modify: `tests/test_strengthening.py`
- Modify: `src/bigp3_als/render_expanded.py` (`render_skill_by_cohort`)
- Modify: `manuscript/manuscript_expanded.md` lines 120 and 144

**Interfaces:**
- Consumes: nothing new.
- Produces: `null_benchmark` returns `development_mean_benchmark_mae` and `held_out_cohort_mean_benchmark_mae` in place of `null_mean_absolute_error` and `same_study_oracle_mean_absolute_error`.

**The error being fixed.** `skill` is computed against the development-set mean. The manuscript says in two places that two cohorts did worse than *their own* mean, which is the other benchmark. That is false as written.

- [ ] **Step 1: Write the failing test**

```python
def test_benchmark_columns_are_named_for_the_comparison_they_make() -> None:
    result = null_benchmark(_records())

    assert "development_mean_benchmark_mae" in result.columns
    assert "held_out_cohort_mean_benchmark_mae" in result.columns
    assert "null_mean_absolute_error" not in result.columns
    assert not any("oracle" in c for c in result.columns)
```

Add it to `tests/test_strengthening.py`.

- [ ] **Step 2: Run to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_strengthening.py -v`
Expected: FAIL on the new test.

- [ ] **Step 3: Rename in `strengthening.py`**

In `null_benchmark`, change the two dictionary keys in both the per-study rows and the pooled row:
- `"null_mean_absolute_error"` becomes `"development_mean_benchmark_mae"`
- `"same_study_oracle_mean_absolute_error"` becomes `"held_out_cohort_mean_benchmark_mae"`

Update the module docstring to drop the word "oracle" and to name the two benchmarks explicitly. Update `render_skill_by_cohort` in `render_expanded.py` to read `development_mean_benchmark_mae`, and change its x-axis label to `"Error reduction against the development-mean benchmark"`.

- [ ] **Step 4: Run the full suite**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/ -v`
Expected: PASS.

- [ ] **Step 5: Fix the two false sentences**

In `manuscript/manuscript_expanded.md`, replace the Results mini-headline at line 120:

> **In two cohorts the calibration score estimated accuracy less well than the development-mean benchmark.** Skill against that benchmark was negative in two of 18 cohorts and positive in the remainder (Figure 2). Skill against each cohort's own mean is reported for every cohort in Table 2.

and in the Discussion at line 144 replace "in two cohorts the score estimated accuracy less well than that cohort's own mean" with "in two cohorts the score estimated accuracy less well than the development-mean benchmark".

- [ ] **Step 6: Regenerate outputs and commit**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/06_run_expanded.py --bootstrap-repetitions 2000 --output-directory output/expanded
git add -A
git commit -m "fix: name each benchmark for the comparison it makes and correct two false claims

Skill was computed against the development-set mean, but the manuscript stated
in two places that two cohorts did worse than their own cohort mean. Those are
different benchmarks."
```

---

### Task 9: Verify the deployed-decoder claim, or withdraw it

**Files:**
- Create: `docs/deployed_decoder_check.md`
- Modify: `manuscript/manuscript_expanded.md`, the subsection "Relationship Between the Predictor and the Deployed Decoder"

**Interfaces:**
- Consumes: the archive documentation under `data/source_cache_full/`.
- Produces: a documented verdict that Task 11 cites.

**Why.** The Methods assert the online classifier was fitted on the same Train files. If the historical online decoders differed by study, that sentence is wrong for some cohorts.

- [ ] **Step 1: Search the archive documentation for the online decoding procedure**

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration/data/source_cache_full"
find . -maxdepth 2 -iname "*.txt" -o -maxdepth 2 -iname "*.md" -o -maxdepth 2 -iname "*.pdf" | grep -v '/\._' | head -20
grep -ril "classifier\|stepwise\|SWLDA\|calibration" --include="*.txt" --include="*.md" . 2>/dev/null | grep -v '/\._' | head
```

- [ ] **Step 2: Record what was and was not established**

Write `docs/deployed_decoder_check.md` with one row per source study: whether the archive documents the online classifier family, whether it documents that the online classifier was trained on that session's Train files, and the evidence. Where the documentation is silent, write "not documented" rather than inferring.

- [ ] **Step 3: Rewrite the manuscript subsection to match**

If the claim is documented for all cohorts, keep it and cite the documentation. If it is documented for some, restrict it to those and say so. If it is not documented anywhere, replace the subsection with:

> In these copy-spelling protocols the Train phase supplies the data from which an online classifier is derived before the Test phase begins. The archive does not document the online classifier for every source study, so the score is described here as the cross-validated learnability of that session's calibration data rather than as a property of the specific decoder deployed. This is why the quantity is reported as decoder-calibration quality and not as a physiological marker of user aptitude.

- [ ] **Step 4: Commit**

```bash
git add docs/deployed_decoder_check.md manuscript/manuscript_expanded.md
git commit -m "docs: check the deployed-decoder claim against the archive documentation"
```

---

### Task 10: Demote the ALS interaction to study-level meta-regression

**Files:**
- Modify: `src/bigp3_als/expanded.py`, replace `als_moderation`
- Modify: `tests/test_expanded.py`
- Modify: `manuscript/manuscript_expanded.md`, the "Cohort Type as a Moderator" subsection

**Interfaces:**
- Consumes: `output/expanded/cohort_calibration.csv` from Task 5.
- Produces: `als_meta_regression(cohort_calibration, als_studies) -> dict` with `n_als_studies`, `n_other_studies`, `mean_slope_als`, `mean_slope_other`, `difference`, `difference_se`, `p_value`.

**Why.** ALS status varies at the study level, not the record level. Testing it with 739 records treats 18 study-level observations as 739 and massively overstates precision. With four ALS studies the honest test is a two-sample comparison of study-level slopes.

- [ ] **Step 1: Write the failing test**

```python
def test_als_meta_regression_uses_studies_not_records_as_the_unit() -> None:
    calibration = pd.DataFrame({
        "held_out_study": ["StudyB", "StudyF", "StudyL", "StudyN", "StudyA", "StudyG", "StudyM"],
        "slope": [1.6, 1.5, 1.7, 1.2, 1.0, 0.9, 1.1],
        "slope_se": [0.2] * 7,
    })

    result = als_meta_regression(calibration, ALS_STUDIES)

    assert result["n_als_studies"] == 4
    assert result["n_other_studies"] == 3
    assert result["difference"] == pytest.approx(1.5 - 1.0, abs=0.01)
    assert result["p_value"] > 0.001  # seven studies cannot support a tiny p value


def test_als_meta_regression_refuses_fewer_than_three_studies_per_group() -> None:
    calibration = pd.DataFrame({
        "held_out_study": ["StudyB", "StudyA"], "slope": [1.6, 1.0], "slope_se": [0.2, 0.2]
    })
    with pytest.raises(ValueError, match="at least three"):
        als_meta_regression(calibration, ALS_STUDIES)
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_expanded.py -v`
Expected: FAIL, `als_meta_regression` undefined.

- [ ] **Step 3: Implement, and delete `als_moderation`**

```python
def als_meta_regression(cohort_calibration: pd.DataFrame, als_studies: tuple[str, ...]) -> dict[str, float]:
    """Compare calibration slopes between cohort types with the study as the unit of analysis.

    Cohort type varies between studies, not between records, so a record-level interaction test
    would treat a study-level exposure as if it had been measured hundreds of times. With a small
    number of studies per group this comparison is exploratory.
    """
    frame = cohort_calibration.dropna(subset=["slope"]).copy()
    frame["is_als"] = frame["held_out_study"].isin(als_studies)
    als = frame.loc[frame["is_als"], "slope"].to_numpy(dtype=float)
    other = frame.loc[~frame["is_als"], "slope"].to_numpy(dtype=float)
    if len(als) < 3 or len(other) < 3:
        raise ValueError("meta-regression needs at least three studies in each group")

    statistic, p_value = stats.ttest_ind(als, other, equal_var=False)
    pooled_se = float(np.sqrt(als.var(ddof=1) / len(als) + other.var(ddof=1) / len(other)))
    return {
        "n_als_studies": float(len(als)),
        "n_other_studies": float(len(other)),
        "mean_slope_als": float(als.mean()),
        "mean_slope_other": float(other.mean()),
        "difference": float(als.mean() - other.mean()),
        "difference_se": pooled_se,
        "t_statistic": float(statistic),
        "p_value": float(p_value),
    }
```

Remove `als_moderation` and its tests, and drop its call from `scripts/06_run_expanded.py`, writing `als_meta_regression` output to `output/expanded/als_meta_regression.json` instead.

- [ ] **Step 4: Run the suite**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/ -v`
Expected: PASS.

- [ ] **Step 5: Rewrite the manuscript subsection**

Replace the "Cohort Type as a Moderator" subsection with an exploratory paragraph reporting the study-level means, the difference with its standard error, the p value, and this sentence:

> Cohort type is a study-level attribute that is entangled with paradigm, hardware and stopping rule, only four studies carry a documented ALS population, and the remaining cohorts are not documented as healthy controls. This comparison is exploratory and cannot separate population from protocol.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "fix: test cohort type at the study level rather than the record level

Cohort type varies between studies. A record-level interaction treated 18
study-level observations as 739 and overstated precision by an order of
magnitude."
```

---

### Task 11: Rewrite every overclaiming sentence

**Files:**
- Modify: `manuscript/manuscript_expanded.md` (Abstract, Results, Discussion, Conclusion, title)

**Interfaces:**
- Consumes: `docs/heterogeneity_verdict.md` from Task 5, `docs/deployed_decoder_check.md` from Task 9, `output/expanded/predictor_precision.csv` from Task 6.

- [ ] **Step 1: Add cohort-level confidence intervals to the association claim**

Extend `within_study_association` in `strengthening.py` to return `pearson_ci_low` and `pearson_ci_high` via the Fisher z transformation, add a test asserting the interval contains the point estimate and narrows as n grows, then replace:

> The association was present in every contributing cohort

with:

> The point estimate was positive in all 18 contributing cohorts, but its magnitude varied widely and several cohort-specific estimates were imprecise, with confidence intervals including values close to zero (Table S3).

- [ ] **Step 2: Retitle**

Set the title to:

> Calibration-derived decoder discriminability is associated with online P300-speller accuracy, but numerical calibration varies across cohorts

unless Task 5 found heterogeneity not established, in which case use the title recorded in `docs/heterogeneity_verdict.md`.

- [ ] **Step 3: Replace the naive spread everywhere with tau and I-squared**

Every place reporting "between-cohort standard deviation" for slope or intercept must report tau, I-squared, and the Q test from `output/expanded/heterogeneity_summary.json`, and must state the naive standard deviation separately as the uncorrected spread.

- [ ] **Step 4: Rename the predictor throughout**

Replace "calibration discriminability" with "calibration-derived decoder discriminability" on first use in the Abstract, Introduction, Methods and Results, and add to the Methods: "The quantity is a measure of how well that session's calibration data support a decoder, not an independent physiological marker of user aptitude."

- [ ] **Step 5: Soften "stable property"**

Replace "The association is a stable property of these recordings; the calibrated mapping is not." with "The association appeared in every cohort examined, though with widely varying magnitude; the numerical mapping between the score and expected accuracy did not."

- [ ] **Step 6: Add measurement error as a competing explanation**

Add to the Discussion, using the Task 6 numbers:

> Predictor precision differs between cohorts, because the number of calibration files, surviving epochs and cross-validation folds differ. Measurement error in a predictor attenuates a fitted slope, so some of the between-cohort variation in calibration is attributable to how precisely the score itself was estimated rather than to a difference in the underlying relationship.

- [ ] **Step 7: Scan and commit**

```bash
python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py manuscript/manuscript_expanded.md
git add manuscript/manuscript_expanded.md src/bigp3_als/strengthening.py tests/test_strengthening.py
git commit -m "docs: bring every claim back to what the evidence supports"
```

---

### Task 12: Test whether protocol covariates explain the heterogeneity

**Files:**
- Create: `src/bigp3_als/protocol.py`
- Test: `tests/test_protocol.py`
- Create: `output/expanded/protocol_covariates.csv`, `output/expanded/protocol_meta_regression.json`

**Interfaces:**
- Consumes: `output/intermediate/online_trials_all20.csv`, `output/expanded/analysis_records.csv`, `output/expanded/cohort_calibration.csv`.
- Produces: `protocol_covariates(trials, records) -> pd.DataFrame` with `study`, `n_conditions`, `condition_list`, `median_selections_per_record`, `mean_accuracy`, `accuracy_sd`, `fraction_at_ceiling`; and `explains_heterogeneity(covariates, calibration) -> dict` with `covariate`, `spearman_rho`, `p_value` per covariate.

**Why.** Cohorts differ in matrix size, paradigm, electrode type and stopping rule. A reviewer will say that a single scalar mapping ignoring all of this demonstrates omitted-variable bias rather than a transportability limit. Either the recoverable covariates explain some heterogeneity, which is a finding, or they do not, which strengthens the claim.

- [ ] **Step 1: Write the failing test**

```python
"""Recoverable protocol differences are candidate explanations for heterogeneity."""

from __future__ import annotations

import pandas as pd
import pytest

from bigp3_als.protocol import explains_heterogeneity, protocol_covariates


def _trials() -> pd.DataFrame:
    return pd.DataFrame({
        "study": ["StudyA"] * 4 + ["StudyB"] * 4,
        "condition": ["CB", "CB", "RC", "RC", "Dry", "Dry", "Dry", "Wet"],
        "eligible": [True] * 8,
    })


def _records() -> pd.DataFrame:
    return pd.DataFrame({
        "study": ["StudyA"] * 3 + ["StudyB"] * 3,
        "n": [20, 20, 20, 10, 10, 10],
        "correct": [20, 18, 16, 5, 7, 9],
    })


def test_protocol_covariates_counts_conditions_per_study() -> None:
    table = protocol_covariates(_trials(), _records()).set_index("study")

    assert table.loc["StudyA", "n_conditions"] == 2
    assert table.loc["StudyB", "n_conditions"] == 2


def test_ceiling_fraction_is_reported() -> None:
    table = protocol_covariates(_trials(), _records()).set_index("study")

    assert table.loc["StudyA", "fraction_at_ceiling"] == pytest.approx(1 / 3)
    assert table.loc["StudyB", "fraction_at_ceiling"] == pytest.approx(0.0)


def test_explains_heterogeneity_returns_one_row_per_covariate() -> None:
    covariates = pd.DataFrame({
        "study": ["A", "B", "C", "D"],
        "mean_accuracy": [0.6, 0.7, 0.8, 0.9],
        "accuracy_sd": [0.3, 0.2, 0.1, 0.05],
        "fraction_at_ceiling": [0.0, 0.1, 0.4, 0.8],
        "median_selections_per_record": [10, 12, 14, 16],
        "n_conditions": [1, 2, 2, 3],
    })
    calibration = pd.DataFrame({
        "held_out_study": ["A", "B", "C", "D"], "slope": [0.5, 0.9, 1.4, 2.0]
    })

    result = explains_heterogeneity(covariates, calibration)

    assert set(result["covariate"]) >= {"mean_accuracy", "accuracy_sd", "fraction_at_ceiling"}
    assert result["spearman_rho"].abs().max() <= 1.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_protocol.py -v`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
"""Recover the protocol descriptors the archive supports, and test them against heterogeneity.

Source studies differ in stimulus paradigm, matrix design, electrode type and stopping rule. Most
of these are not recorded as fields, but several are recoverable from the reconstructed trials and
the analysis records. If they track the cohort-specific calibration slope, then some of the apparent
transportability failure is an omitted-variable problem rather than an irreducible one.
"""

from __future__ import annotations

import pandas as pd
from scipy import stats

COVARIATES = (
    "mean_accuracy",
    "accuracy_sd",
    "fraction_at_ceiling",
    "median_selections_per_record",
    "n_conditions",
)


def protocol_covariates(trials: pd.DataFrame, records: pd.DataFrame) -> pd.DataFrame:
    """Summarise per study the protocol descriptors the archive supports."""
    eligible = trials.loc[trials["eligible"]] if "eligible" in trials else trials
    conditions = (
        eligible.groupby("study")["condition"]
        .agg(n_conditions="nunique", condition_list=lambda values: ",".join(sorted(set(values))))
        .reset_index()
    )
    frame = records.copy()
    frame["accuracy"] = frame["correct"] / frame["n"]
    outcome = (
        frame.groupby("study")
        .agg(
            mean_accuracy=("accuracy", "mean"),
            accuracy_sd=("accuracy", "std"),
            fraction_at_ceiling=("accuracy", lambda s: float((s >= 1.0).mean())),
            median_selections_per_record=("n", "median"),
        )
        .reset_index()
    )
    return conditions.merge(outcome, on="study", how="outer")


def explains_heterogeneity(covariates: pd.DataFrame, calibration: pd.DataFrame) -> pd.DataFrame:
    """Rank-correlate each protocol descriptor with the cohort-specific calibration slope."""
    merged = covariates.merge(
        calibration.rename(columns={"held_out_study": "study"})[["study", "slope"]], on="study"
    )
    rows: list[dict[str, object]] = []
    for name in COVARIATES:
        if name not in merged:
            continue
        pair = merged[[name, "slope"]].dropna()
        if len(pair) < 3:
            rows.append({"covariate": name, "n_studies": len(pair),
                         "spearman_rho": float("nan"), "p_value": float("nan")})
            continue
        rho, p_value = stats.spearmanr(pair[name], pair["slope"])
        rows.append({"covariate": name, "n_studies": len(pair),
                     "spearman_rho": float(rho), "p_value": float(p_value)})
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_protocol.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 5: Run on real data, add a Results paragraph, commit**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -c "
import pandas as pd, json
from bigp3_als.protocol import protocol_covariates, explains_heterogeneity
t=pd.read_csv('output/intermediate/online_trials_all20.csv'); r=pd.read_csv('output/expanded/analysis_records.csv')
c=protocol_covariates(t,r); c.to_csv('output/expanded/protocol_covariates.csv',index=False)
e=explains_heterogeneity(c, pd.read_csv('output/expanded/cohort_calibration.csv'))
e.to_json('output/expanded/protocol_meta_regression.json', orient='records', indent=2)
print(e.to_string(index=False))
"
git add src/bigp3_als/protocol.py tests/test_protocol.py
git commit -m "feat: test whether recoverable protocol descriptors explain calibration heterogeneity"
```

Add a Results paragraph reporting the correlations, and a Limitations sentence naming matrix size, stopping rule and online decision procedure as descriptors the archive does not expose.

---

### Task 13: Deliver the analyses the Methods promised

**Files:**
- Modify: `scripts/07_run_sensitivity.py`
- Modify: `manuscript/manuscript_expanded.md`, Methods and Results
- Modify: `supplementary/supplement_expanded.md`, add comparator results

**Interfaces:**
- Consumes: existing sensitivity machinery.
- Produces: rows `leave-two-studies-out development` in `output/expanded/sensitivity_analyses.csv`, plus `output/expanded/comparator_metrics.csv`.

**Two promises are currently unmet:** leave-two-studies-out development, and the calibration-slope power statement. The supplement also names the comparator predictors without reporting their performance.

- [ ] **Step 1: Add leave-two-studies-out**

Append to `scripts/07_run_sensitivity.py` before the table is written:

```python
    import itertools

    primary_spec = next(spec for spec in MODEL_SPECS if spec.role == "primary")
    studies = sorted(records["study"].unique())
    errors: list[float] = []
    for held_out in itertools.combinations(studies, 2):
        development = records.loc[~records["study"].isin(held_out)]
        validation = records.loc[records["study"].isin(held_out)]
        if development["study"].nunique() < 3 or validation.empty:
            continue
        predicted = _fit_probability_model(development, validation, primary_spec.features)
        observed = validation["correct"] / validation["n"]
        errors.append(float((observed - predicted).abs().mean()))
    rows.append({
        "analysis": f"leave-two-studies-out development ({len(errors)} splits)",
        "n_studies": len(studies),
        "n_records": int(len(records)),
        "n_selections": int(records["n"].sum()),
        "mae_mean": float(np.mean(errors)),
        "mae_between_study_sd": float(np.std(errors, ddof=1)),
        "mae_prediction_low": float(np.percentile(errors, 2.5)),
        "mae_prediction_high": float(np.percentile(errors, 97.5)),
        "slope_mean": float("nan"), "slope_between_study_sd": float("nan"),
        "slope_prediction_low": float("nan"), "slope_prediction_high": float("nan"),
    })
```

Add `import numpy as np` and `from bigp3_als.validation import _fit_probability_model` at the top.

- [ ] **Step 2: Report calibration-slope power**

Add to Results, computing from `heterogeneity_summary.json`:

> With the pooled calibration-slope standard error of SE, a departure from unity of at least 2.8 x SE would have been detectable at 80% power and a two-sided 5% threshold. Departures smaller than that cannot be excluded.

- [ ] **Step 3: Build the comparator table**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -c "
import pandas as pd
from bigp3_als.validation import MODEL_SPECS, run_source_study_held_out_validation
r=pd.read_csv('output/expanded/analysis_records.csv')
out=[]
for spec in MODEL_SPECS:
    try:
        _, m = run_source_study_held_out_validation(r.dropna(subset=list(spec.features)), spec, bootstrap_repetitions=50)
    except Exception as exc:
        print('skip', spec.name, exc); continue
    p=m[m['held_out_study'].astype(str).str.startswith('Pooled')].iloc[0]
    out.append({'predictor':spec.name,'role':spec.role,
                'mae':p['session_mean_absolute_error'],'brier':p['character_brier_score'],
                'auc':p['predicted_probability_character_auc'],
                'intercept':p['calibration_intercept'],'slope':p['calibration_slope']})
pd.DataFrame(out).to_csv('output/expanded/comparator_metrics.csv',index=False)
print(pd.DataFrame(out).round(3).to_string(index=False))
"
```

Add the result as Table S5 in the supplement.

- [ ] **Step 4: Run and commit**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python scripts/07_run_sensitivity.py
git add -A
git commit -m "feat: deliver the leave-two-studies-out, slope-power and comparator analyses the Methods promised"
```

---

### Task 14: Show the calibration failure

**Files:**
- Modify: `src/bigp3_als/render_expanded.py`
- Test: `tests/test_render_expanded.py`
- Create: `output/expanded/figures/figure_calibration_forest.pdf`, `figure_calibration_curves.pdf`

**Interfaces:**
- Consumes: `output/expanded/cohort_calibration.csv`, `output/expanded/external_validation_predictions.csv`.
- Produces: `render_calibration_forest(cohort_calibration, summary, als_studies, directory)` and `render_calibration_curves(predictions, als_studies, directory)`.

**Why.** The paper's central claim is miscalibration and no figure shows a calibration curve. These become Figures 1 and 2; the existing transportability and skill figures move to 3 and 4, and the cohort-type scatter moves to the supplement because its straight-line fits are inconsistent with the logistic mapping used in the analysis.

- [ ] **Step 1: Write the failing test**

```python
"""The calibration figures must exist and must draw intervals, not bare points."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bigp3_als.expanded import ALS_STUDIES
from bigp3_als.render_expanded import render_calibration_curves, render_calibration_forest


def test_calibration_forest_writes_both_formats(tmp_path: Path) -> None:
    calibration = pd.DataFrame({
        "held_out_study": ["StudyA", "StudyB", "StudyF"],
        "slope": [0.5, 1.0, 1.8], "slope_se": [0.2, 0.1, 0.3],
        "intercept": [0.4, 0.0, -0.6], "intercept_se": [0.3, 0.2, 0.4],
    })
    summary = {"slope": {"pooled": 1.1, "prediction_interval_low": 0.2,
                         "prediction_interval_high": 2.0, "tau": 0.5, "i_squared": 80.0}}

    render_calibration_forest(calibration, summary, ALS_STUDIES, tmp_path)

    assert (tmp_path / "figure_calibration_forest.pdf").exists()
    assert (tmp_path / "figure_calibration_forest.png").exists()


def test_calibration_curves_write_both_formats(tmp_path: Path) -> None:
    predictions = pd.DataFrame({
        "held_out_study": ["StudyA"] * 30 + ["StudyB"] * 30,
        "n": [20] * 60,
        "correct": list(range(10, 20)) * 6,
        "predicted_probability": [0.4 + 0.02 * i for i in range(30)] * 2,
    })

    render_calibration_curves(predictions, ALS_STUDIES, tmp_path)

    assert (tmp_path / "figure_calibration_curves.pdf").exists()
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_render_expanded.py -v`
Expected: FAIL, `ImportError`.

- [ ] **Step 3: Implement both figures**

`render_calibration_forest` draws, for each cohort, the slope with a 95% interval from `slope_se`, ordered by slope, coloured by cohort type, with a vertical reference at 1.0, a band for the random-effects prediction interval, and tau plus I-squared annotated in the axis label. A second panel does the same for the intercept with a reference at 0.

`render_calibration_curves` plots, per cohort, observed accuracy against predicted accuracy in deciles of prediction with the identity line, using a small-multiples grid, so a reader sees the direction of miscalibration in each cohort.

- [ ] **Step 4: Run to verify it passes, then render for real**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -m pytest tests/test_render_expanded.py -v
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -c "
import json, pandas as pd
from pathlib import Path
from bigp3_als.expanded import ALS_STUDIES
from bigp3_als.render_expanded import render_calibration_forest, render_calibration_curves
d=Path('output/expanded'); out=d/'figures'
render_calibration_forest(pd.read_csv(d/'cohort_calibration.csv'), json.load(open(d/'heterogeneity_summary.json')), ALS_STUDIES, out)
render_calibration_curves(pd.read_csv(d/'external_validation_predictions.csv'), ALS_STUDIES, out)
"
```

- [ ] **Step 5: Renumber every figure callout and commit**

Figure 1 forest, Figure 2 calibration curves, Figure 3 transportability, Figure 4 skill by cohort, eFigure 1 cohort-type scatter. Update the legends block and every inline callout, then:

```bash
grep -n "Figure [0-9]" manuscript/manuscript_expanded.md
git add -A
git commit -m "feat: show the calibration failure directly with a forest plot and per-cohort curves"
```

---

### Task 15: Terminology, provenance and remaining defects

**Files:**
- Modify: `manuscript/manuscript_expanded.md`, `supplementary/supplement_expanded.md`
- Modify: `src/bigp3_als/strengthening.py`, `across_session_association`

**Interfaces:**
- Consumes: nothing new.

- [ ] **Step 1: Rename the design**

Replace "external validation" with "internal-external cross-validation across source studies" throughout, citing Debray 2015 and Riley 2016, because every cohort comes from one harmonised archive.

- [ ] **Step 2: Fix the prespecification claim**

The analysis was not registered. Replace every "prespecified" with "originally targeted" for the ALS subgroup, and with "defined before the widened analysis was run" for the sensitivity analyses, or provide a dated protocol. Add to Methods: "No analysis plan was registered; the subgroup and sensitivity analyses were fixed in the project documentation before the widened cohort was assembled, and the commit history records their dates."

- [ ] **Step 3: Document the session-ordering assumption**

`across_session_association` orders sessions by `session_id`. Add to its docstring and to the Methods:

> Session order was taken from the lexical order of session identifiers, which the archive assigns sequentially within a participant. Recording timestamps are de-identified and cannot confirm this, so the preceding-session analysis rests on the assumption that identifier order matches recording order.

Add a test asserting the function raises if identifiers within a participant are not sortable into a strict order.

- [ ] **Step 4: Reconcile the two selection counts in Table 1**

Add a footnote row to Table 1 giving both totals, and change the final row label to "Total eligible feedback phases (19,688); analysed selections (19,611) after requiring a usable calibration feature set".

- [ ] **Step 5: Add a data and code availability statement**

Insert before References:

> **Data and code availability.** BigP3BCI version 1.0.0 is publicly available (doi:10.13026/0byy-ry86). Analysis code and frozen outputs are available at [repository URL to be inserted by the submitting authors]. The archive is not redistributed.

- [ ] **Step 6: Scan and commit**

```bash
python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py manuscript/manuscript_expanded.md
python3 ~/.claude/skills/de-ai-writing/scripts/scan_ai_writing.py supplementary/supplement_expanded.md
git add -A
git commit -m "docs: correct design terminology, prespecification language and ordering provenance"
```

---

### Task 16: Rewrite the cover letter and rebuild the packet

**Files:**
- Modify: `manuscript/cover_letter_expanded.md`
- Rebuild: `build_expanded/`, `_submission_ready/study_bigp3_als_calibration/`

- [ ] **Step 1: Remove the two overclaims**

Replace "after removing every between-cohort difference" with "after centring both variables within cohort, which removes cohort means though not differences in variance, protocol or measurement precision".

Replace "the cohort-level mechanism that produces it" with "an examination of which cohort-level features are and are not associated with it", because an association in one sensitivity analysis does not establish a mechanism.

- [ ] **Step 2: Restate the finding at its corrected strength**

Rewrite the second paragraph from `docs/heterogeneity_verdict.md`, reporting tau, I-squared and the Q test rather than the raw range, and stating the estimand explicitly.

- [ ] **Step 3: Rebuild**

```bash
cd "/Volumes/Extreme SSD/Mimic-IV/study_bigp3_als_calibration"
cp manuscript/manuscript_expanded.md build_expanded/manuscript.md
cp supplementary/supplement_expanded.md build_expanded/supplement.md
cp manuscript/cover_letter_expanded.md build_expanded/cover_letter.md
bash ../_pub_assets/build_pub.sh "$(pwd)/build_expanded"
```

- [ ] **Step 4: Verify the built files and the abstract cap**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/calib_venv COPYFILE_DISABLE=1 uv run python -c "
import re, zipfile, glob
for f in sorted(glob.glob('build_expanded/*.docx')):
    t=re.sub('<[^>]+>','',zipfile.ZipFile(f).read('word/document.xml').decode('utf8','ignore'))
    assert 'oracle' not in t.lower(), f
    assert chr(8212) not in t, f
    print(f, 'ok', len(t.split()), 'words')
"
python3 -c "
import re
t=open('manuscript/manuscript_expanded.md').read()
a=t.split('## Abstract',1)[1].split('## Introduction',1)[0]
n=sum(len(chr(10).join(s.split(chr(10))[1:]).split()) for s in re.split(r'### ',a) if s.strip())
assert n<=300, f'abstract {n} over the 300 word cap'
print('abstract', n, '/300')
"
```

- [ ] **Step 5: Archive the superseded packet and install the new one**

Move the current packet contents to `_submission_ready/study_bigp3_als_calibration/_superseded_2026-07-26_aliased/`, copy the rebuilt documents and figures in, and update `README.md` and `SUBMISSION_CHECKLIST.md` with the new key numbers and a version-check line naming the decimation correction.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: rebuild the packet after the decimation correction and the claim revisions"
```

---

## Self-Review

**Spec coverage.** All 13 reviewer findings map to a task in the table at the top. Findings 1 and 2 are the two that can change the paper's conclusion, and both have an explicit decision point: Task 3 Step 2 records how far the predictor moved, and Task 5 Step 3 records whether heterogeneity survives, with three named outcomes and instructions for each.

**Placeholders.** The only intentional placeholder is the repository URL in Task 15 Step 5, which is a human-supplied value and is marked as such. Task 9 Step 3 and Task 5 Step 3 are conditional rather than vague; each branch states the exact wording to use.

**Type consistency.** `cohort_calibration` produces `held_out_study`, `slope`, `slope_se`, `intercept`, `intercept_se`, consumed under those names by `random_effects` (Task 5), `precision_versus_slope` (Task 6), `als_meta_regression` (Task 10), `explains_heterogeneity` (Task 12) and `render_calibration_forest` (Task 14). `precision_versus_slope` and `explains_heterogeneity` both rename `held_out_study` to `study` before merging, which is stated in both implementations. `null_benchmark` column renames in Task 8 propagate to `render_skill_by_cohort`, which Task 8 Step 3 updates explicitly.

**Ordering constraint.** Tasks 4 through 14 all read `output/expanded/`, which Task 3 regenerates. Task 3 must complete before any of them, or every number will come from the aliased pipeline.
