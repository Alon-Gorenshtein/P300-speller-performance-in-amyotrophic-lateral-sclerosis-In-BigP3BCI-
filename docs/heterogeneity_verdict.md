# Does the calibration mapping transport? Verdict on the heterogeneity of cohort calibration

Written before any Results text, from `scripts/08_run_heterogeneity.py` on
`output/expanded/external_validation_predictions.csv` (739 leave-one-study-out predictions,
19,611 selections, 271 participants, 18 withheld cohorts). Outputs:
`output/expanded/cohort_calibration.csv` and `output/expanded/heterogeneity_summary.json`.

## Verdict

**The fitted mapping does not transport. That conclusion holds, and it should be argued from the
intercept and from tau, not from the slope I-squared the manuscript currently leans on.**

The claim has two halves, and they are not equally delicate.

**The intercept settles it outright.** Under the primary cluster-robust specification the calibration
intercept has tau = 0.87 (95% CI 0.60 to 1.51) against a pooled intercept of -0.06, I-squared 86.1
with a **lower confidence limit of 79.5**, and a 95 percent prediction interval of -1.97 to 1.85. The
I-squared lower limit clears the conventional 75 threshold, so there is no boundary problem here at
all. A new cohort's calibration intercept can be anywhere from about -2 to about +2 on the log-odds
scale, which is the difference between a mapping that badly understates accuracy and one that badly
overstates it. Since "the fitted mapping" is the intercept and slope jointly, the intercept alone is
sufficient for the headline.

**The slope agrees but is the more delicate case.** tau = 0.43 (95% CI 0.30 to 0.77) against a pooled
slope of 1.06, with a 95 percent prediction interval of 0.11 to 2.00. The between-cohort variance is
significantly non-zero under every specification: the least extreme of the three Q tests is the
primary one, Q = 81.3 on 17 degrees of freedom, p = 2.3e-10. But the slope I-squared point estimate
is 79.1 with a confidence interval of 67.6 to 86.5, which spans the 75 threshold, so the slope cannot
carry a threshold claim.

**What must change in the manuscript.** Report tau with its confidence interval as the headline
statistic, lead with the intercept, and demote I-squared to a descriptive companion reported with its
own interval. Do not write "I-squared of 79 percent indicates substantial heterogeneity" for the
slope, and do not write any sentence about the slope whose truth depends on I-squared exceeding 75.
The Methods must state that the primary I-squared is an upper estimate, for the reason in the
few-clusters section below. Under the plan's labels the intercept is "heterogeneity confirmed" and
the slope sits between "confirmed" and "moderate"; the honest wording for the slope is the
reviewer's, that calibration varied across cohorts beyond what sampling error explains and that the
between-cohort variance is itself imprecisely estimated.

## The three specifications

Slope, DerSimonian and Laird pooling of 18 cohorts. All 18 fitted under every specification, none
dropped. tau intervals are Q-profile (Viechtbauer); PM is the Paule and Mandel point estimate of the
same quantity, reported so that the estimator choice is visible.

| specification | pooled slope (SE) | tau (95% CI) | tau, PM | I-squared (95% CI) | Q (17 df) | Q p | 95% prediction interval | PI includes 0 |
|---|---|---|---|---|---|---|---|---|
| cluster-robust, primary | 1.058 (0.122) | 0.4319 (0.296 to 0.772) | 0.4634 | 79.1 (67.6 to 86.5) | 81.29 | 2.3e-10 | 0.111 to 2.005 | no |
| quasi-binomial | 1.058 (0.125) | 0.4427 (0.299 to 0.774) | 0.4663 | 79.4 (68.1 to 86.7) | 82.50 | 1.4e-10 | 0.087 to 2.028 | no |
| model-based, sensitivity | 1.067 (0.139) | 0.5462 (0.368 to 0.805) | 0.5151 | 95.0 (93.3 to 96.2) | 338.21 | 1.4e-61 | -0.122 to 2.256 | yes |

Intercept, same pooling. **This is the stronger case and belongs first in the Results.**

| specification | pooled intercept (SE) | tau (95% CI) | tau, PM | I-squared (95% CI) | Q (17 df) | Q p | 95% prediction interval |
|---|---|---|---|---|---|---|---|
| cluster-robust, primary | -0.057 (0.241) | 0.8734 (0.599 to 1.510) | 0.9057 | 86.1 (79.5 to 90.6) | 122.56 | 5.0e-18 | -1.968 to 1.854 |
| quasi-binomial | -0.087 (0.222) | 0.7936 (0.586 to 1.496) | 0.8967 | 83.5 (75.2 to 89.1) | 103.12 | 2.3e-14 | -1.826 to 1.651 |
| model-based, sensitivity | -0.093 (0.224) | 0.8657 (0.690 to 1.539) | 0.9712 | 95.6 (94.1 to 96.6) | 383.43 | 5.4e-71 | -1.979 to 1.794 |

Naive standard deviations of the 18 cohort estimates, the statistics being replaced: **0.5596** for
the slope and **1.1749** for the intercept. They are the same under all three specifications, because
they ignore the standard errors entirely. The slope figure overstates the primary tau by 30 percent.

The Paule and Mandel column matters in one direction only. Under the primary specification it gives a
**larger** tau than DerSimonian and Laird for both the slope (0.4634 against 0.4319) and the intercept
(0.9057 against 0.8734), so the estimator this analysis chose is the conservative one and the
headline does not depend on that choice.

### Why cluster-robust is primary and model-based is the favourable one

The 739 records come from 271 participants, and the conditions recorded within one session share an
identical predicted probability by construction, so the records are not independent draws. A binomial
likelihood that treats each as its own draw understates the within-cohort variance. Because tau
squared is (Q - (k-1)) / C, an understated within-cohort variance inflates Q and therefore inflates
the estimated between-cohort variance. The model-based row is the specification most favourable to
the manuscript's existing claim, which is why it is the sensitivity and not the primary: it gives
I-squared 95.0, the largest slope tau, and it is the only one of the three whose slope prediction
interval includes zero. Its I-squared is inflated by a dependence structure known to be present in
this data, not hypothesised.

### The quasi-binomial row, and the level at which the specifications agree

Cluster-robust and quasi-binomial corrections fail differently. The clustered variance assumes the
participant is the right clustering unit and needs many clusters to behave. The quasi-binomial scale
needs neither: it multiplies the model-based standard errors by the square root of the Pearson
dispersion, estimated from 6 to 87 residual degrees of freedom rather than from 5 to 24 clusters.
Their pooled results agree closely, slope tau 0.4319 against 0.4427 and I-squared 79.1 against 79.4,
and that agreement localises the disagreement with the model-based row: essentially all of the gap
between 79 and 95 is extra-binomial variance that both corrections absorb and the model-based
specification does not.

**State this as a pooled-level agreement, because that is the only level at which it holds.** Cohort
by cohort the two sets of standard errors differ substantially: the ratio of the cluster-robust slope
standard error to the quasi-binomial one runs from 0.599 (StudyS1) to 1.208 (StudyB), and it falls
below 1 in 6 of 18 cohorts. Clustering does not even reliably widen the standard error relative to
the model-based fit: it shrinks it in 3 of 18 cohorts (StudyE, StudyR, StudyS1). The corrections
converge on the pooled between-cohort variance while disagreeing about individual cohorts, and a
Methods sentence claiming per-cohort agreement would be false.

Two further cautions against reading the agreement as more than it is. The two corrections are not
independent, they are two ways of widening the same standard errors, so they can agree and both still
be too small. And quasi-binomial scaling absorbs marginal overdispersion but not correlation among
records within a participant, so it is not a strict upper bound either. Both residual biases point
the same way, toward a within-cohort variance that is still too small and an I-squared still too
large. Nothing available argues 79.1 is an underestimate.

Per-cohort dispersions run from 0.74 (StudyS1) to 8.79 (StudyJ), and 17 of 18 exceed 1, so
extra-binomial variance is present in almost every cohort.

## The few-clusters problem, and what the conclusion actually survives

Each cohort has between 5 and 24 participants: StudyK 5, StudyE and StudyN 8, StudyF and StudyS1 10,
StudyL 11, StudyA and StudyI 13, StudyH 16, StudyD and StudyO 17, StudyB 18, StudyG, StudyJ, StudyQ
and StudyR 20, StudyM 21, StudyS2 24. A cluster-robust variance is downward-biased and noisy below
roughly 30 clusters even with the CR1 finite-sample correction statsmodels applies, and every cohort
here is below that. The bias direction is unfavourable in exactly the way that matters: a
downward-biased within-cohort variance inflates tau squared and I-squared, the same direction as the
defect the cluster-robust specification was introduced to remove. **79.1 is therefore an upper
estimate of the slope I-squared, and the true value may lie below 75.**

The strongest answer to that concern is not a hypothetical bias factor but a property of the data.
**The headline survives at the lower 95 percent confidence limit of tau.** Holding the within-cohort
variances at their estimates and setting tau to each Q-profile limit in turn:

| slope quantity | tau = 0.296, lower limit | tau = 0.432, point estimate | tau = 0.772, upper limit |
|---|---|---|---|
| pooled slope (SE) | 1.049 (0.094) | 1.058 (0.122) | 1.078 (0.196) |
| prediction interval | 0.394 to 1.704 | 0.111 to 2.005 | -0.603 to 2.759 |

At the lower confidence limit of tau the slope in a new cohort still ranges from 0.39 to 1.70, across
which no single fitted mapping is usable. The same holds for the intercept: at its lower limit of
tau = 0.599 the prediction interval is still -1.386 to 1.256.

A hypothetical bias ladder gives the same answer and is retained because it addresses the
few-clusters concern in its own terms. Repooling with every within-cohort variance multiplied by a
common factor:

| within-cohort variances inflated by | tau | I-squared | Q p | 95% prediction interval |
|---|---|---|---|---|
| x1.0 (as estimated) | 0.4319 | 79.1 | 2.3e-10 | 0.111 to 2.005 |
| x1.1 | 0.4262 | 77.0 | 4.5e-09 | 0.121 to 1.991 |
| x1.2 | 0.4203 | 74.9 | 5.3e-08 | 0.131 to 1.978 |
| x1.5 | 0.4024 | 68.6 | 9.2e-06 | 0.163 to 1.938 |
| x2.0 | 0.3704 | 58.2 | 1.1e-03 | 0.224 to 1.871 |
| x3.0 | 0.2965 | 37.3 | 5.7e-02 | 0.375 to 1.728 |
| x5.0 | 0.0000 | 0.0 | 5.1e-01 | 0.853 to 1.335 |

The x3.0 row lands at tau 0.2965, within 0.0004 of the Q-profile lower limit, which is why its
prediction interval of 0.375 to 1.728 is nearly the 0.394 to 1.704 above. Read the ladder as three
separate answers:

- **The slope I-squared threshold falls at a 20 percent understatement of the within-cohort
  variance**, which is small and entirely plausible at 5 to 24 clusters. That claim is not robust and
  must not be asserted.
- **That heterogeneity exists survives a doubling** (p = 1.1e-03) and only crosses 0.05 near a
  tripling, which is not a live possibility at these cluster counts.
- **That the fitted mapping does not transport survives everything short of x5.0**, and survives at
  the lower confidence limit of tau, which is the stronger form of the same statement.

The quasi-binomial ladder crosses 75 at the same place (x1.2 gives 75.3), as expected from two
specifications starting 0.3 points apart.

## The two items required on the record

### 1. Does the slope prediction interval include zero, and does the answer differ by specification?

**Yes, it differs, and the difference is decision-relevant.**

- Cluster-robust, primary: [0.111, 2.005]. **Excludes zero.**
- Quasi-binomial: [0.087, 2.028]. **Excludes zero.**
- Model-based, sensitivity: [-0.122, 2.256]. **Includes zero.**

Under the primary specification a sentence such as "we cannot exclude that the score carries no
calibration information in a new cohort" is **not** supported and must not be written. It is
supported only by the model-based specification, the one inflated by a dependence structure known to
be present, so it cannot carry that sentence alone.

Three qualifications belong with this, all against the manuscript's interest. The exclusion is
marginal, 0.111 against a pooled slope of 1.058. The interval undercovers by construction, because
tau squared enters as though known rather than estimated, and that understatement grows with
heterogeneity, so it bites hardest in this range; it would need to widen by 12 percent to reach zero,
which is inside the range by which methods accounting for the estimation of tau squared widen
prediction intervals at eighteen studies. And at the **upper** confidence limit of tau the interval
is -0.603 to 2.759, which does include zero. The exclusion of zero should therefore be reported as a
fact about this interval at the point estimate of tau, never relied on as a finding.

The cohort-level evidence points the same way: under the primary specification, 4 of the 18
cohort-specific slope confidence intervals include zero (StudyH 0.185 [-0.289, 0.659], StudyJ 0.326
[-0.063, 0.716], StudyK 0.480 [-0.193, 1.153], StudyS1 1.312 [-0.216, 2.840]). In roughly a fifth of
withheld cohorts the calibration slope is not individually distinguishable from zero. The association
is reliable on average, pooled slope 1.058 (95% CI 0.820 to 1.296, which excludes zero and includes
one), but it is not reliable cohort by cohort, and the manuscript should say so rather than
describing the association as transporting without qualification.

### 2. Cohorts that failed to fit

**None. Zero cohorts were dropped from the pooling under any of the three specifications.** All 18
withheld cohorts produced an identified calibration slope and intercept with a usable standard error,
and `random_effects` returned `n_dropped = 0` with empty `dropped_labels` in all six poolings (three
specifications, slope and intercept). Every k in this document is 18, and the manuscript may state 18
cohorts without qualification.

This was not guaranteed. The estimator refuses a cohort with no residual degrees of freedom, one
whose predicted probability never varies, one with fewer participants than parameters under
clustering, one whose fit is separated, one whose quasi-binomial dispersion is degenerate, and one
whose standard error collapses below 1e-8 because the model reproduces its data exactly. StudyE, at 8
records and 6 residual degrees of freedom, is closest to those limits and still fits. Anyone rerunning
this after a change to the predictions file must re-read `n_dropped` rather than assume it stays at
zero.

## What the manuscript should now say

The manuscript currently prints stale pre-regeneration numbers, so each item below gives the string
to search for and the value that replaces it. Current values come from
`output/expanded/cohort_calibration.csv` and `heterogeneity_summary.json`.

| what the manuscript prints now | where | what it must become |
|---|---|---|
| between-cohort SD **0.586** for the slope | `manuscript_expanded.md` lines 20, 118, 124, 150, 152; `cover_letter_expanded.md` lines 11, 13 | tau **0.43** (95% CI 0.30 to 0.77); the naive SD is 0.5596 if a raw spread is quoted at all |
| between-cohort SD **1.073** for the intercept | `manuscript_expanded.md` line 118 | tau **0.87** (95% CI 0.60 to 1.51); naive SD 1.1749 |
| slope ranged **0.075 to 2.233** | `manuscript_expanded.md` lines 20, 118, 144, 200, and the Table 2 rows for Study A and Study H; `cover_letter_expanded.md` line 11 | **0.185 to 2.185** (StudyH to StudyS2) |
| intercept ranged **-2.445 to 1.870** | `manuscript_expanded.md` lines 20, 118, 144, 200; `cover_letter_expanded.md` line 11 | **-2.169 to 1.995** (StudyA to StudyS1) |
| new-cohort slope interval **-0.104 to 2.437** | `manuscript_expanded.md` line 118 | **0.111 to 2.005** |
| new-cohort intercept interval **-2.405 to 2.249** | `manuscript_expanded.md` line 118 | **-1.968 to 1.854** |

The ALS-subgroup figure of **0.204** and the sensitivity-analysis slope spreads of **0.438**, **0.674**
and **0.716** are also stale, but they are outputs of the sensitivity scripts rather than of this
analysis, so this document does not supply replacements. Whoever owns those numbers must regenerate
them.

Beyond the numbers:

1. **Lead the transportability claim with the intercept**, which has tau 0.87, an I-squared lower
   confidence limit of 79.5, and no boundary problem. Present the slope as the secondary and more
   delicate case.
2. **Report tau with its Q-profile confidence interval** wherever the between-cohort spread appears,
   and say why the naive standard deviation was dropped: it counts sampling error as if it were
   between-cohort variation.
3. **State the primary specification and why it is primary**, in one sentence about repeated records
   within participants and sessions.
4. **Report I-squared with its interval and label it an upper estimate.** For the slope, 79.1 (95% CI
   67.6 to 86.5), with a Methods sentence that at 5 to 24 participants per cohort this is an upper
   estimate and that a 20 percent understatement of the within-cohort variance would put it below 75.
5. **Do not claim the slope prediction interval includes zero.** Do report that it reaches 0.11, that
   it includes zero at the upper confidence limit of tau, and that 4 of 18 cohorts have a slope not
   individually distinguishable from zero.
6. **Anchor the robustness claim on the confidence limit, not on a hypothetical.** The prediction
   interval at the lower 95 percent confidence limit of tau is 0.394 to 1.704 for the slope and
   -1.386 to 1.256 for the intercept, so the conclusion holds across the whole plausible range of the
   between-cohort variance.
7. **If the convergence of specifications is mentioned in the Methods, say it is a pooled-level
   agreement.** Per-cohort, the cluster-robust and quasi-binomial standard errors differ by up to 40
   percent, and clustering shrinks the standard error relative to the model-based fit in 3 of 18
   cohorts.
