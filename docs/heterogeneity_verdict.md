# Does the calibration mapping transport? Verdict on the heterogeneity of cohort calibration slopes

Written before any Results text, from `scripts/08_run_heterogeneity.py` on
`output/expanded/external_validation_predictions.csv` (739 leave-one-study-out predictions,
19,611 selections, 271 participants, 18 withheld cohorts). Outputs:
`output/expanded/cohort_calibration.csv` and `output/expanded/heterogeneity_summary.json`.

## Verdict

**Heterogeneity confirmed for the purpose the manuscript needs it, but not by the I-squared
threshold, and the manuscript must stop leaning on that threshold.**

The between-cohort variance in the calibration slope is not explicable by sampling error under any
specification: Q = 81.3 on 17 degrees of freedom, p = 2.3e-10 under the primary specification, and
the most conservative of the three still gives p = 1.4e-10. The magnitude is large in absolute
terms, tau = 0.43 on the log-odds slope scale against a pooled slope of 1.06, giving a 95 percent
prediction interval for the slope in a new cohort of 0.11 to 2.00. A slope of 0.11 and a slope of
2.00 describe opposite failures of the same fitted mapping, so no single fitted mapping serves a new
cohort. That is the claim the paper makes and it is supported.

What is **not** supported is the specific threshold statement "I-squared exceeds 75 percent". The
point estimate is 79.1, its test-based 95 percent confidence interval is 67.6 to 86.5, and the
residual bias in the primary specification runs downward on the within-cohort variance and therefore
upward on I-squared. Inflating every within-cohort variance by 20 percent, well inside the error of a
cluster-robust variance built on 5 to 24 clusters, puts I-squared at 74.9. The threshold call is a
coin flip. The substantive quantity is not: the same 20 percent inflation moves tau from 0.432 to
0.420 and the prediction interval from [0.111, 2.005] to [0.131, 1.978].

**Consequence for the manuscript.** Report tau and the prediction interval as the headline evidence
and I-squared with its confidence interval as a descriptive companion. Do not write "I-squared of
79 percent indicates substantial heterogeneity" as though 79 were known to three significant
figures, and do not write any sentence whose truth depends on I-squared being above 75. The Methods
must state that the primary specification is an upper estimate of I-squared for the reason given in
the section on few clusters below. Under the plan's own labels this sits between "confirmed" and
"moderate", and the honest wording is the reviewer's: calibration varied across cohorts beyond what
sampling error explains, and the between-cohort variance is itself imprecisely estimated.

## The three specifications

Slope, DerSimonian and Laird pooling of 18 cohorts. All 18 cohorts fitted under every
specification; none dropped.

| specification | pooled slope (SE) | tau | I-squared (95% CI) | Q (17 df) | Q p | 95% prediction interval | PI includes 0 |
|---|---|---|---|---|---|---|---|
| cluster-robust, primary | 1.058 (0.122) | 0.4319 | 79.1 (67.6 to 86.5) | 81.29 | 2.3e-10 | 0.111 to 2.005 | no |
| quasi-binomial | 1.058 (0.125) | 0.4427 | 79.4 (68.1 to 86.7) | 82.50 | 1.4e-10 | 0.087 to 2.028 | no |
| model-based, sensitivity | 1.067 (0.139) | 0.5462 | 95.0 (93.3 to 96.2) | 338.21 | 1.4e-61 | -0.122 to 2.256 | yes |

Naive standard deviation of the 18 cohort slopes, the statistic the manuscript currently reports:
**0.5596**. It is not a specification, it is the same number under all three, because it ignores the
standard errors entirely. It overstates the primary tau by 30 percent.

Intercept, for completeness:

| specification | pooled intercept (SE) | tau | I-squared (95% CI) | Q (17 df) | Q p | 95% prediction interval |
|---|---|---|---|---|---|---|
| cluster-robust, primary | -0.057 (0.241) | 0.8734 | 86.1 (79.5 to 90.6) | 122.56 | 5.0e-18 | -1.968 to 1.854 |
| quasi-binomial | -0.087 (0.222) | 0.7936 | 83.5 (75.2 to 89.1) | 103.12 | 2.3e-14 | -1.826 to 1.651 |
| model-based, sensitivity | -0.093 (0.224) | 0.8657 | 95.6 (94.1 to 96.6) | 383.43 | 5.4e-71 | -1.979 to 1.794 |

Naive standard deviation of the 18 intercepts: **1.1749**.

### Why cluster-robust is primary and model-based is the favourable one

The 739 records come from 271 participants, and the conditions recorded within one session share an
identical predicted probability by construction, so the records are not independent draws. A
binomial likelihood that treats each as its own draw understates the within-cohort variance. Because
tau squared is (Q - (k-1)) / C, an understated within-cohort variance inflates Q and therefore
inflates the estimated between-cohort variance. The model-based row is therefore the specification
most favourable to the manuscript's existing claim, which is why it is the sensitivity and not the
primary: it reports I-squared of 95.0 and the largest tau, and it is the only one of the three whose
prediction interval includes zero. Its I-squared is inflated by a dependence structure that is known
to be present in this data, not hypothesised.

### Why the quasi-binomial row is worth its space

Cluster-robust and quasi-binomial corrections fail differently. The clustered variance assumes the
participant is the right clustering unit and needs many clusters to be well behaved. The
quasi-binomial scale needs neither: it multiplies the model-based standard errors by the square root
of the Pearson dispersion, which is estimated from 6 to 87 residual degrees of freedom rather than
from 5 to 24 clusters. Their agreement, tau 0.4319 against 0.4427 and I-squared 79.1 against 79.4, a
gap of 0.3 points, is stronger evidence than either alone, and it localises the disagreement with the
model-based row precisely: essentially all of the gap between 79 and 95 is the extra-binomial
variance that both corrections absorb and the model-based specification does not.

Two cautions against reading the agreement as more than it is. First, the two corrections are not
independent of each other, they are two ways of widening the same standard errors, so they can agree
and both still be too small. Second, quasi-binomial scaling absorbs marginal overdispersion but not
correlation among records within a participant, so it is not a strict upper bound on the correction
either. Both remaining biases point the same way, toward a within-cohort variance that is still too
small and an I-squared that is still too large. Nothing here argues that 79.1 is an underestimate.

Per-cohort dispersions run from 0.74 (StudyS1) to 8.79 (StudyJ), and 17 of 18 exceed 1, so
extra-binomial variance is present in almost every cohort.

## The few-clusters problem, and how much it would have to matter

Each cohort has between 5 and 24 participants: StudyK 5, StudyE and StudyN 8, StudyF and StudyS1 10,
StudyL 11, StudyA and StudyI 13, StudyH 16, StudyD and StudyO 17, StudyB 18, StudyG, StudyJ, StudyQ
and StudyR 20, StudyM 21, StudyS2 24. A cluster-robust variance is downward-biased and noisy below
roughly 30 clusters even with the CR1 finite-sample correction statsmodels applies, and every cohort
here is below that. The bias direction is unfavourable in exactly the way that matters: a
downward-biased within-cohort variance inflates tau squared and I-squared, the same direction as the
defect the cluster-robust specification was introduced to remove. **79.1 is therefore an upper
estimate of I-squared, and the true value may lie below 75.**

The question is how much bias would be needed to change each conclusion. Repooling the same slopes
with every within-cohort variance multiplied by a common factor answers it directly:

| within-cohort variances inflated by | tau | I-squared | Q p | 95% prediction interval |
|---|---|---|---|---|
| x1.0 (as estimated) | 0.4319 | 79.1 | 2.3e-10 | 0.111 to 2.005 |
| x1.1 | 0.4262 | 77.0 | 4.5e-09 | 0.121 to 1.991 |
| x1.2 | 0.4203 | 74.9 | 5.3e-08 | 0.131 to 1.978 |
| x1.5 | 0.4024 | 68.6 | 9.2e-06 | 0.163 to 1.938 |
| x2.0 | 0.3704 | 58.2 | 1.1e-03 | 0.224 to 1.871 |
| x3.0 | 0.2965 | 37.3 | 5.7e-02 | 0.375 to 1.728 |
| x5.0 | 0.0000 | 0.0 | 5.1e-01 | 0.853 to 1.335 |

Read it as three separate answers.

- **The I-squared threshold falls at a 20 percent understatement of the within-cohort variance.**
  That is a small and entirely plausible bias at 5 to 24 clusters. The "I-squared above 75" claim is
  not robust and must not be asserted.
- **The finding that heterogeneity exists survives a doubling.** Q p is still 1.1e-03 at x2.0 and
  only crosses 0.05 near a tripling of every within-cohort variance. A threefold understatement of
  cluster-robust standard errors is not a live possibility at these cluster counts.
- **The finding that the fitted mapping does not transport survives everything short of x5.0.** Even
  at x3.0, tau is 0.30 and the prediction interval runs 0.375 to 1.728, a range across which no
  single fitted mapping is usable. The headline does not depend on the threshold call.

The same exercise on the quasi-binomial row crosses 75 at the same place, x1.2 giving 75.3, which is
the expected consequence of the two specifications starting 0.3 points apart.

## The two items required on the record

### 1. Does the slope prediction interval include zero, and does the answer differ by specification?

**Yes, it differs, and the difference is decision-relevant.**

- Cluster-robust, primary: [0.111, 2.005]. **Excludes zero.**
- Quasi-binomial: [0.087, 2.028]. **Excludes zero.**
- Model-based, sensitivity: [-0.122, 2.256]. **Includes zero.**

Under the primary specification a sentence such as "we cannot exclude that the score carries no
calibration information in a new cohort" is **not** supported and must not be written. It is
supported only by the model-based specification, which is the one inflated by a dependence structure
known to be present, so it cannot carry that sentence alone.

Two qualifications belong with this, both against the manuscript's interest. The exclusion is
marginal, 0.111 against a pooled slope of 1.058, so the correct reading is not that a new cohort's
slope is safely positive but that it is probably positive and could be close enough to zero to be
useless. And the prediction interval undercovers by construction, because tau squared enters as
though it were known rather than estimated, and that understatement grows with heterogeneity, so it
bites hardest in exactly this range. The interval would have to widen by 12 percent to reach zero,
which is inside the range by which methods that account for the estimation of tau squared widen
prediction intervals at eighteen studies. The exclusion of zero should therefore be reported as a
fact about this interval, not relied on as a finding.

The cohort-level evidence points the same way: under the primary specification, 4 of the 18
cohort-specific slope confidence intervals include zero (StudyH 0.185 [-0.289, 0.659], StudyJ 0.326
[-0.063, 0.716], StudyK 0.480 [-0.193, 1.153], StudyS1 1.312 [-0.216, 2.840]). In roughly a fifth of
withheld cohorts the score's calibration slope is not individually distinguishable from zero. The
association is reliable on average, pooled slope 1.058 (95 percent CI 0.820 to 1.296, which excludes
zero and includes one), but it is not reliable cohort by cohort, and the manuscript should say so
rather than describing the association as transporting without qualification.

### 2. Cohorts that failed to fit

**None. Zero cohorts were dropped from the pooling under any of the three specifications.** All 18
withheld cohorts produced an identified calibration slope and intercept with a positive standard
error, and `random_effects` returned `n_dropped = 0` and an empty `dropped_labels` in all six
poolings (three specifications, slope and intercept). Every k in this document is 18, and the
manuscript may state 18 cohorts without qualification.

This was not guaranteed. The estimator refuses a cohort with no residual degrees of freedom, one
whose predicted probability never varies, one with fewer participants than parameters under
clustering, and one whose fit is separated, and it refuses a quasi-binomial cohort whose dispersion
is degenerate. StudyE, at 8 records and 6 residual degrees of freedom, is the closest to those
limits and still fits. Anyone rerunning this after a change to the predictions file must re-read
`n_dropped` rather than assuming it stays at zero.

## What the manuscript should now say

1. Replace the naive standard deviation of 0.56 everywhere it appears with tau = 0.43 (95 percent
   prediction interval 0.11 to 2.00), and say why: 0.56 counts sampling error as if it were
   between-cohort variation, and it overstates the primary tau by 30 percent.
2. State the primary specification and why it is primary, in one sentence about repeated records
   within participants and sessions.
3. Report I-squared as 79.1 percent (95 percent CI 67.6 to 86.5) and state in the Methods that with
   5 to 24 participants per cohort this is an upper estimate, and that a 20 percent understatement of
   the within-cohort variance would put it below 75.
4. Do not claim the slope prediction interval includes zero. Do report that it reaches 0.11 and that
   4 of 18 cohorts have a slope not individually distinguishable from zero.
5. Keep the headline that the fitted mapping does not transport. It rests on tau and the prediction
   interval, both of which survive a threefold inflation of the within-cohort variance.
