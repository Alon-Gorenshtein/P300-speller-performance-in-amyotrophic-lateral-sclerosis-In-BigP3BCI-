# Response to Reviewers

**The calibration-to-accuracy mapping in P300 spellers does not transport across cohorts, and neither alignment nor local recalibration repairs it**

Manuscript JNE-111284 | *Journal of Neural Engineering* | September 2026

Warren M. Grill, PhD, Editor-in-Chief

---

Dear Professor Grill and Reviewers,

We thank you and the two reviewers for the careful and constructive assessment of our manuscript and for the opportunity to submit a revised version. We are grateful for the reviewers' recognition that the distinction between a within-cohort association and a transportable fitted mapping is the substantive question, and for a set of comments that identified precisely the analyses the original submission was missing.

This revision is substantive rather than editorial. In response to the Editor-in-Chief and to Reviewer 2 we have added a full data re-alignment analysis: four alignment arms, two operating on the calibration signal itself by Euclidean Alignment with two different reference choices, and two operating on the score by within-cohort standardisation and by within-cohort rank transformation. In response to Reviewer 2 we have added a nonlinear decoder arm, in fact two of them, a radial-basis kernel approximation and a gradient-boosted tree ensemble, so that the failure to transport can be separated from the choice of a linear decision boundary. In response to Reviewer 1 and Reviewer 2 together we have added a resampling study that quantifies what local recalibration actually costs, in local participants and in character selections, and reports the minimum improvement the study had power to detect. All six new predictor arms were put through the identical leave-one-study-out procedure and the identical random-effects summary as the primary analysis, so every reported tau is directly comparable to the published values. We have also surfaced the reconstructed-decoder caveat into the Abstract and the opening of the Discussion, reasoned explicitly about the direction of the archive-homogenisation bias, expanded the amyotrophic lateral sclerosis characterisation limitation, added a paragraph on cumulative researcher degrees of freedom, added recent literature and the historical context Reviewer 2 asked for, and reduced the manuscript's redundancy, though its net length increased once the requested new analyses were added.

The new analyses did not confirm what we expected, and we report them as they came out. No alignment method restores transportability. No nonlinear decision boundary restores it. Local recalibration does not reliably improve on simply transporting the fitted mapping at any local sample size we could evaluate, and at the smallest sample sizes the two-parameter refit is significantly worse. These are negative results, and two of them qualify recommendations the original manuscript made. We have changed the Conclusion accordingly rather than preserve the original advice.

Throughout this document the reviewers' words are reproduced verbatim, our response follows, and the revised manuscript text is quoted so that the revision can be read without opening the manuscript. New tables are embedded inline. Section references are to the clean revised manuscript; the same changes are marked in yellow in the highlighted manuscript file.

We thank you again for your consideration and for the reviewers' insightful input, which has materially improved the rigour of this work and, in two places, corrected it.

Sincerely,

Alon Gorenshtein, MD, on behalf of all authors

---

## Overview of Revisions

- **Data re-alignment (new).** Four alignment arms were added and evaluated: Euclidean Alignment with a session-level reference, Euclidean Alignment with a cohort-level reference, within-cohort standardisation of the score, and within-cohort rank transformation of the score. None restores transportability; the two score-space arms make it substantially worse. New Methods subsection, new Results subsection, new Figure, new supplementary tables.
- **Nonlinear decision boundaries (new).** Two nonlinear calibration decoders were added, a radial-basis kernel approximation and a gradient-boosted tree ensemble on a principal-component reduction. Both discriminate less well than the regularised linear decoder and neither improves transport. New Methods and Results text.
- **Cost of local recalibration (new).** A participant-resampling study inside each withheld cohort, at nine local sample sizes from 1 to 16 participants, with both an intercept-only and an intercept-and-slope refit, evaluated on the held-out participants of the same cohort against the transported mapping on the identical participants. Reported with minimum detectable effects at 80% power. New Methods and Results text, new Figure, new supplementary tables.
- **Reconstructed decoder.** The caveat that the predictor is not the deployed online decoder now appears in the Abstract and in the first paragraph of the Discussion, not only in the Methods.
- **Archive homogenisation.** The Discussion now reasons about the direction of the bias introduced by the archive's shared montage, sampling rate and amplifier, and states that the reported heterogeneity likely understates what an independent deployment would show.
- **ALS characterisation.** The relevant limitation now states explicitly which clinical variables are absent for every cohort.
- **Researcher degrees of freedom.** A new Discussion paragraph addresses cumulative multiplicity beyond what formal correction captures.
- **Literature and historical context.** The Introduction cites recent work on calibration-based performance prediction and reports what the prior literature does and does not say about why cross-cohort evaluation was not attempted.
- **Conclusion.** Revised. The original recommendation to recalibrate locally is now qualified by the evidence in this revision.
- **Length.** Redundant statistics were removed from the Discussion and the clustered-sandwich-versus-bootstrap estimator comparison was moved to the Supplement, as Reviewer 1 suggested; the three new analyses the reviewers requested increased the net main-text length from approximately 6,600 to 8,900 words.

## Response to Editorial and Production Requirements

- **Author Response.** This document, uploaded at Step 1 of the online submission form.
- **Highlighted PDF.** A copy of the revised manuscript with every change marked in yellow highlight, in PDF, with figures and tables included, uploaded with the file designation "Complete Document for Review (PDF Only)".
- **Source File.** A clean revised manuscript in Microsoft Word format, with no tracked changes, coloured text or comments, carrying the full author list and affiliations, the corresponding author and email, funding and acknowledgements, and the ethics statement. Tables, figure captions and equations are editable and no colour or grey-scale shading appears in any table.
- **Clean PDF version.** An unmarked PDF generated from the clean source file, with the file designation "Source Files".
- **Supplementary material.** The revised Supplement, clean, with a title and description, with the file designation "Supplementary Data Files".
- **Data availability.** All analysis code, including every script that produced the new analyses in this revision, and the frozen intermediate files on which the new tables depend, are provided in the repository named in the Data availability statement.

---

## Editor-in-Chief

**Comment E.1.**

> We received the comments from two exceedingly well-qualified Reviewers, and while they agree that this may be an important contribution, substantial revisions are required before we can reconsider this manuscript for publication. Additional analyses to consider data re-alignment would substantially increase the impact of the contribution.

**Response.** We thank the Editor-in-Chief for identifying data re-alignment as the analysis that would most strengthen the contribution. We agree, and it is the centrepiece of this revision. We want to be explicit that this was the right thing to ask for: it is the standard remedy in the brain-computer interface transfer literature for exactly the kind of between-cohort variation this paper reports, and a paper claiming a mapping does not transport is incomplete if it has not tested whether the field's usual correction repairs it.

We approached the question from two directions, because "alignment" can mean two different things for a study of this shape.

First, alignment of the *signal*. Euclidean Alignment whitens each recording by the inverse square root of its own mean epoch covariance, placing recordings made through different amplifiers, caps and impedances on a common scale [He and Wu 2020]. We implemented it with two reference choices. A **session-level** reference uses that session's own calibration epochs, which is the canonical form and is deployable at a new site on the first user. A **cohort-level** reference pools every session in the cohort, weighted by epoch count, which removes what a cohort's recording chain shares while leaving between-session variation inside the cohort intact. The cohort-level arm is the one aimed most directly at a claim about cohorts, and we report it as such.

Second, alignment of the *score*. Standardising a cohort's calibration scores within that cohort, or replacing them by within-cohort normal quantiles, requires the target cohort's calibration recordings, using only their usual target/non-target labels, but never its online accuracy. This is transductive unsupervised domain adaptation, and it is the only family that could in principle repair the mapping without any labelled outcome from the new site.

Every arm was put through the identical leave-one-study-out procedure and the identical random-effects summary as the primary analysis, so the tau it returns is directly comparable to the published tau of 0.432 for the slope and 0.873 for the intercept. As a check on the pipeline, the primary arm was re-run through the same code and reproduced the published values to thirteen significant digits, with per-cohort fits matching the published file to within 5.3e-15.

The result is negative, and uniformly so (PI denotes the 95% prediction interval in the table below):

| Arm | Pooled MAE | Slope tau | Slope 95% PI | Intercept tau | Intercept 95% PI |
| --- | --- | --- | --- | --- | --- |
| Calibration score (primary) | 0.098 | 0.432 | 0.111 to 2.005 | 0.873 | -1.97 to 1.85 |
| Euclidean Alignment, session reference | 0.095 | 0.419 | 0.136 to 1.975 | 0.922 | -2.06 to 1.98 |
| Euclidean Alignment, cohort reference | 0.097 | 0.461 | 0.074 to 2.095 | 0.941 | -2.12 to 1.99 |
| Within-cohort standardisation | 0.129 | 0.653 | -0.230 to 2.621 | 1.675 | -3.59 to 3.69 |
| Within-cohort rank transformation | 0.131 | 0.686 | -0.196 to 2.802 | 1.562 | -3.58 to 3.22 |

Three things in that table are worth the Editor's attention.

The two Euclidean Alignment arms barely move the score at all. Their Spearman correlation with the unaligned score is 0.986 for the session reference and 0.990 for the cohort reference, and their mean discriminability is 0.800 and 0.802 against the unaligned 0.805. This is mechanistically coherent rather than a sign that the method was misapplied: the calibration classifier is fitted within a single session on features that are already standardised, so whitening by a covariance reference has little left to remove. One candidate explanation this rules out is that the transportability failure is a simple consequence of the signal's scale or channel geometry, since Euclidean Alignment targets exactly that class of covariance difference and removing it left the score, and the transportability result, essentially unchanged. That is a mechanistic answer to the Editor's question rather than a bare null, and the agreement between two different reference choices strengthens it.

The two score-space arms make transportability substantially worse, and this is the most informative single result in the revision. Standardising within cohort forces every cohort's score to mean zero and unit variance before the model is fitted, which destroys the between-cohort information about absolute score level. The calibration intercept must then absorb each cohort's accuracy level on its own, and its tau nearly doubles. The slope prediction interval for both score-space arms extends below zero, meaning that for a cohort outside this archive these mappings do not exclude an inverted relationship. The practical reading is that the *absolute level* of the calibration score carries genuinely transportable information, and that normalising it away is actively harmful. Something about the score does transport; it is simply not enough to make the fitted mapping hold.

We also checked whether the conclusion depends on the standard-error convention, since the primary analysis reports four, and here we must state a qualification rather than suppress it. Both Euclidean Alignment arms yielded a marginally higher downstream character-level AUC than the unaligned one, 0.756 and 0.753 against 0.748, despite calibration-block discriminability that was essentially unchanged (0.800 and 0.802 against 0.805; supplement, Table S15), and a higher downstream AUC produces a lower pooled error more or less mechanically. Both accordingly have a lower pooled mean absolute error than the primary, 0.095 and 0.097 against 0.098, and a higher Brier skill score. Session-level alignment also has a lower slope tau than the primary under all four conventions, and a lower intercept tau under three of them, the exception being the paper's own participant-clustered convention. We therefore do not claim that no arm improves anything, and we apply to the alignment arms the same discipline we apply to the nonlinear ones: an arm whose predictions rank withheld sessions better will estimate their accuracy better, and that is not evidence that transport was repaired.

What the numbers support is the narrower claim that no arm *restores transportability*. Under no arm and no convention did the intercept tau fall below 0.75; the best value observed anywhere was 0.754, and for the two Euclidean Alignment arms under the paper's own clustered convention it was higher than the primary's, at 0.922 and 0.941. The prediction interval for an unrepresented cohort spans roughly -2.0 to +2.0 on the log-odds scale throughout, which is far too wide for a mapping to be carried to a new site. We note also that the four conventions are four re-weightings of the same fitted per-cohort estimates from the same eighteen cohorts, sharing every prediction and differing only in the within-cohort standard errors, which is why the pooled error is numerically identical across all four. The stability we report is therefore robustness to the standard-error convention, not four independent confirmations, and the differences between arms carry no interval separating them from zero.

The revised manuscript states this as follows.

> No re-alignment specification restored transportability (Figure 5; supplement, S12; Tables S13 and S14). Aligning the calibration epochs by Euclidean Alignment left the score almost unchanged, whether the reference covariance was estimated from the session itself (Spearman 0.986 against the unaligned score) or pooled across the cohort (0.990). Both Euclidean Alignment arms yielded marginally higher downstream character-level AUC (0.756 and 0.753 against 0.748) and, since a higher downstream AUC produces a lower pooled error more or less mechanically, a marginally lower pooled estimation error (0.095 and 0.097 against 0.098), despite calibration-block discriminability that was essentially unchanged (0.800 and 0.802 against 0.805; supplement, Table S15); a downstream improvement of this kind is not evidence that the mapping was repaired. Overall calibration heterogeneity was not meaningfully repaired, even though session-level alignment's slope tau moved slightly in the favourable direction: slope tau was 0.419 and 0.461 against 0.432, and intercept tau 0.922 and 0.941 against 0.873. Session-level alignment lowered slope tau under all four standard-error specifications and intercept tau under three, the exception being the participant-clustered specification used throughout (supplement, Table S16); that direction is robust to the choice of specification rather than independently replicated by it, since the four re-weight the same fitted per-cohort estimates and share every prediction.
>
> Aligning the score instead of the signal was worse. Standardising each cohort's scores within that cohort raised intercept tau to 1.675 and pooled estimation error to 0.129, and a within-cohort rank transformation gave 1.562 and 0.131; for both, the prediction interval for the calibration slope in an unrepresented cohort extends below zero. Because within-cohort standardisation removes the between-cohort information about absolute score level, the calibration intercept must absorb each cohort's accuracy level unaided, which is what inflates its heterogeneity. The absolute level of the calibration score therefore carries information that does transport, and removing it makes the estimate worse rather than better. Under no specification and no alignment arm did the intercept tau fall below 0.75, and the prediction interval for an unrepresented cohort spanned roughly -2.0 to +2.0 on the log-odds scale throughout, far too wide for a site to act on a transported calibration.

We are grateful for the suggestion. The paper is stronger for having tested the obvious remedy and reported that it does not work.

---

## Reviewer 1

We thank Reviewer 1 for a careful and generous reading, and in particular for stating the distinction on which the paper turns, that a fitted mapping transporting to withheld cohorts is a different claim from a within-cohort association. We are grateful for the recognition that the sensitivity and robustness analyses are extensive. The five major comments and the minor comment each identified a real gap, and three of them required new analysis rather than new text. They are addressed in order below.

**Comment 1.1.**

> Archive homogenization vs. true external validation. The BigP3BCI dataset already imposes a shared montage and sampling rate across studies. Please discuss more prominently in the main text (rather than just the Methods) whether this curation likely under- or overstates the heterogeneity a reader would encounter across genuinely independent clinical deployments (e.g., different amplifiers, sites, and electrode caps). The manuscript currently acknowledges this limitation ("not external validation in the strict sense") but does not reason about the directional impact of this bias.

**Response.** We agree, and we accept the criticism as stated: the original text named the limitation and then declined to reason about it, which leaves the reader unable to judge which way it cuts. We have added a paragraph to the Discussion, not only to the Methods, that reasons about the direction explicitly and commits to an answer.

The reasoning is asymmetric, and we say so. BigP3BCI imposes a shared sixteen-channel montage, a common sampling rate, and a single amplifier model (gUSBAmp) across every source study. Each of those is a source of between-cohort variation that a reader's own deployment would have and this archive does not. We were unable to identify any plausible mechanism by which curation of this kind would *inflate* the observed heterogeneity. The reported tau therefore likely understates what a site meeting a genuinely independent cohort should expect, and the transportability failure is, if anything, understated rather than overstated.

The new alignment analyses bear on this directly and we have cross-referenced them. Cohort-level Euclidean Alignment removes what a cohort's recording chain shares, which is the class of difference the archive has already suppressed. It did not reduce heterogeneity; it slightly increased it. That is evidence that, within this harmonised archive, covariance differences addressable by alignment do not explain the residual spread; what an independent site's amplifier or montage would additionally contribute is not something this archive can quantify.

The revised Discussion reads:

> This archive is not external validation in the strict sense, and the direction of that limitation is worth stating rather than merely noting. BigP3BCI imposes a shared sixteen-channel montage, a common sampling rate and a single amplifier model across every source study, and each of those is a source of between-cohort variation that a reader's own deployment would carry and this archive does not. We identified no plausible mechanism by which curation of this kind would inflate the heterogeneity observed here. Because BigP3BCI suppresses several technical sources of between-site variation, the heterogeneity reported here likely understates what a site encountering a genuinely independent cohort should expect; the mapping's failure to transport is if anything understated rather than overstated. What this archive can quantify is narrower: cohort-level Euclidean Alignment removes what a cohort's recording chain shares, which is the class of covariance difference the archive's shared hardware could still leave behind within its own harmonisation, and it did not reduce between-cohort heterogeneity (Results, Alignment Did Not Restore Transportability). Within the harmonised archive, that class of covariance difference does not explain the residual spread; what an independent site's amplifier or montage would additionally contribute is a source of variation this archive does not contain and cannot quantify.

**Comment 1.2.**

> Predictor vs. deployed decoder. The calibration score is based on a reconstructed classifier, rather than the actual decoder used online in the source studies. This caveat is vital to the paper's practical recommendations. Currently, it appears only deep in the Methods section. I believe it should be surfaced near the Abstract or Discussion framing so readers do not over-trust the clinical implications of using this score.

**Response.** We agree this is vital and that burying it in a Methods subsection was the wrong placement. The caveat now appears in three places: the Abstract, the first paragraph of the Discussion, and the Methods subsection where it already lived.

The Abstract's Significance section now reads, with the new clause underlined here for the reviewer's convenience only:

> **Original:** "The score carries a reproducible signal about accuracy in the corresponding session, but the mapping between them is cohort-specific: usable for ranking sessions within a setting, not for reporting expected accuracy elsewhere without local recalibration."
>
> **Revised:** "The evaluated score is the cross-validated discriminability of a classifier fitted here on each session's calibration data, not the decoder the source studies used online, which the archive does not document. That score carries a reproducible signal about accuracy in the corresponding session, but the mapping between them is cohort-specific: usable for ranking sessions within a setting, not for reporting expected accuracy elsewhere."

The first paragraph of the Discussion now opens with the same statement, so a reader who skips the Methods still meets it before any implication is drawn:

> Across 18 source-study cohorts, the discriminability of a classifier fitted to a session's calibration block was related to that same session's online spelling accuracy, with a positive point estimate in every cohort, at the participant level, and when the calibration recording came from an earlier session. It is important to be clear at the outset about what that classifier is. It is not the decoder that produced the online accuracy being estimated: the archive names no online classifier for any source study, and the BCI2000 parameter files that would carry its specification were withheld from the release, so the deployed decoder cannot be reconstructed. The predictor evaluated here is a separate classifier fitted by us to the same calibration recordings, and every result below concerns the cross-validated learnability of a session's calibration data rather than a property of any deployed system. A fitted mapping from that score to expected accuracy did not transport, with substantial between-cohort variation in both the calibration intercept and the slope (Results, Transportability). One cohort was estimated less accurately than the development-mean benchmark, six less accurately than their own mean.

**Comment 1.3.**

> Practical path to local recalibration. The Conclusion recommends "local recalibration" but provides no operational sense of what that requires (e.g., how many subjects or calibration trials are needed to learn a usable local mapping?). Including even a brief simulation or a dedicated discussion of operational feasibility would substantially strengthen the clinical translatability of the paper's main recommendation.

**Response.** We thank the reviewer for this comment, which identified the weakest sentence in the original manuscript. The Conclusion told readers to recalibrate locally without any statement of what that costs, and the reviewer is right that a recommendation of that form is not usable. We ran the simulation. It did not support the recommendation, and we have changed the recommendation rather than the simulation.

The design is as follows, and we note that it answers the reviewer's question in the sharper of the two units they offered. Within each withheld cohort we drew *n* participants at random without replacement as a local calibration set, refitted the mapping on those participants alone, and evaluated the refit on the participants who were not drawn. The transported mapping was scored on the identical held-out participants within the same draw, so every comparison is paired and the two cannot differ by which sessions happened to be easy. We repeated this 200 times per cohort and size, at nine sizes from 1 to 16 local participants, requiring at least three participants to remain for evaluation. Two refits were compared: an intercept-only refit, which shifts the whole mapping and is identified from a single participant, and an intercept-and-slope refit, which also changes how steeply estimated accuracy tracks the score. Inference treats the cohort as the unit of replication, as elsewhere in the paper.

Because the number of contributing cohorts falls as the local draw grows, we report the ladder twice: once using every cohort available at each size, and once restricted to the six cohorts present at every size, so that the shape of the curve is not confounded by a changing and progressively easier cohort mix. The composition-balanced ladder is the one we quote.

| Refit | Local n | Median local sel. | MAE, transported | MAE, recalibrated | Improvement (95% CI) | MDE 80% |
| --- | --- | --- | --- | --- | --- | --- |
| Intercept only | 1 | 60 | 0.097 | 0.112 | -0.012 (-0.032 to +0.008) | 0.027 |
| Intercept only | 2 | 120 | 0.093 | 0.097 | -0.004 (-0.020 to +0.013) | 0.022 |
| Intercept only | 4 | 246 | 0.090 | 0.091 | -0.000 (-0.014 to +0.014) | 0.019 |
| Intercept only | 8 | 528 | 0.090 | 0.087 | +0.003 (-0.010 to +0.016) | 0.018 |
| Intercept only | 16 | 1,056 | 0.089 | 0.084 | +0.005 (-0.007 to +0.016) | 0.016 |
| Intercept and slope | 2 | 120 | 0.099 | 0.173 | **-0.073 (-0.111 to -0.035)** | 0.051 |
| Intercept and slope | 3 | 180 | 0.095 | 0.125 | **-0.029 (-0.053 to -0.006)** | 0.031 |
| Intercept and slope | 8 | 528 | 0.090 | 0.094 | -0.003 (-0.013 to +0.007) | 0.014 |
| Intercept and slope | 16 | 1,056 | 0.089 | 0.086 | +0.003 (-0.005 to +0.010) | 0.011 |

We found no statistically supported crossing point. At no local sample size we could evaluate, up to 16 participants and 1,056 character selections, did either refit produce an improvement over the transported mapping whose confidence interval excluded zero. At the smallest sizes the two-parameter refit is significantly *worse* than transporting: at two local participants it increases mean absolute error by 0.073 (95% CI 0.035 to 0.111), and it remains significantly worse at three.

The mechanism is worth stating because it answers the reviewer's question about subjects versus trials. The calibration score is defined at the session level (Methods), and most participants in this archive contribute a single recorded session, so a local sample of two participants is typically, though not always, a refit on two distinct points. At two local participants, 24.1% of draws returned a *negative* recalibrated slope, that is, a mapping in which higher predicted accuracy implies lower observed accuracy. The binding constraint is the number of distinct session-level predictor values a local sample supplies, which tracks participant count far more than character-selection count: additional selections within an already-drawn session do not add a new predictor value, though drawing a participant with additional sessions would.

We also report what the study could have detected, so that this null is bounded rather than merely absent. With six cohorts contributing at each size, the analysis had 80% power to detect a mean improvement of 0.019, 0.018 and 0.016 in mean absolute error for the intercept-only refit at 4, 8 and 16 local participants, and 0.031, 0.014 and 0.011 for the intercept-and-slope refit, against a transported error of 0.089 to 0.093. Smaller improvements could have gone undetected.

We checked the obvious alternative explanation, that recalibration repairs the calibration parameters while mean absolute error is dominated by irreducible within-cohort variance. It does not. The intercept-only refit cannot change the calibration slope at all, since an additive shift on the log-odds scale preserves it exactly, and its effect on the intercept was never distinguishable from zero. The intercept-and-slope refit moved both parameters significantly *away* from ideal at small local sizes. Both outcomes point the same way.

The Conclusion has been revised accordingly:

> **Original:** "The score may be useful for within-setting ranking after local validation, and the artifact-rejection fraction is a candidate data-quality screen warranting prospective evaluation; neither use has been prospectively validated here, and the score should not be used to report expected accuracy in a cohort where the mapping was not developed without local recalibration."
>
> **Revised:** "The score may be useful for within-setting ranking after local validation, and the artifact-rejection fraction is a candidate data-quality screen warranting prospective evaluation. The score should not be used to report expected accuracy in a cohort where the mapping was not developed. We had expected local recalibration to be the remedy, and it is not one at any sample size this archive can evaluate: with up to 16 local participants and roughly 1,000 character selections, refitting the mapping locally did not reliably improve on transporting it, and refitting both intercept and slope on fewer than four local participants was significantly worse than transporting, inverting the mapping in a quarter of draws at two participants. A site that cannot assemble a local sample larger than this archive permits us to test should not assume that a small local recalibration will make a transported mapping usable."

We recognise that this is a less satisfying answer than a threshold would have been, and that it removes a recommendation the original manuscript made. We think it is the more useful finding.

**Comment 1.4.**

> Length. The main text (~30 pages) could be streamlined without losing content. Much of the Discussion recapitulates the Results using similar statistical framing. Additionally, some methodological comparisons could be polished in-text, such as the extended discussion regarding estimator agreement between the clustered sandwich estimator and the bootstrap tau. Consider moving more of this comparison to the supplement, where the corresponding tables already reside.

**Response.** We agree on both the diagnosis and the specific remedy. The estimator-agreement material has been moved to the Supplement, where its tables already were, and the Discussion passages that restated Results statistics have been cut.

Two blocks moved. The Discussion passage reporting the joint bootstrap's within-replicate between-cohort standard deviations, and the explanation that this quantity estimates something structurally larger than tau, now lives in Supplement S4; the Discussion retains one sentence stating that the folds are not independent, that a joint bootstrap measures the resulting correlation directly, and that it estimates a quantity structurally larger than tau, with a cross-reference. The Methods sentences comparing cluster-robust pooling on the bootstrap's seventeen identified cohorts against the all-eighteen values also moved to S4, with a cross-reference left in place.

We then worked through the Discussion paragraph by paragraph and removed statistics that the Results already state, keeping the interpretation and cross-referencing the number. The first paragraph no longer re-lists tau, its confidence interval and the slope range; the fold-stability paragraph no longer repeats coefficients of variation that Supplementary Table S12 carries; the predictor-precision paragraph no longer repeats the reliability range.

We should be transparent about the net effect, because it goes the other way and we would rather state it plainly than have the reviewer discover it. The trimming removed roughly 150 words of redundancy; the three new analyses the reviewers asked for added roughly 2,100 words of Methods and Results. The main text is therefore longer than the version the reviewers read, approximately 8,900 words against 6,600, and remains well inside this journal's 12,000-word limit for a Paper.

We could not find a way to add three analyses and shorten the paper at the same time without removing content the reviewers asked us to add. We took this comment to be about redundancy rather than a page target, and the redundancy the reviewer identified is gone: the estimator-agreement material now sits in the Supplement, where its tables already were, and the Discussion no longer restates statistics the Results give. If the editorial preference is for a shorter paper regardless, we would welcome direction on which of the new analyses should move to the Supplement in full, and we would suggest the nonlinear-boundary result as the least load-bearing of the three.

**Comment 1.5.**

> ALS clinical characterization. Only three studies include ALSFRS-R data, and there is no information regarding disease stage or duration. Given the ALS framing in the title, the authors should add a sentence to the Limitations section explicitly acknowledging this gap (beyond the current baseline description) to properly calibrate their clinical-population claims.

**Response.** We thank the reviewer for pressing on this, and we agree that the original wording understated the gap. The manuscript said only that no participant-level clinical characteristics were available. The revised limitation names the specific variables that are absent and states what the ALS framing can and cannot support.

> **Original:** "Seventh, the archive identifies an ALS population for four cohorts only, with no participant-level clinical characteristics available for any cohort."
>
> **Revised:** "Seventh, the clinical characterisation of the ALS cohorts is thin, and thinner than the framing of this study might suggest. The archive identifies an ALS population for four cohorts only. An ALSFRS-R score is recorded for three of the eighteen cohorts, and no cohort carries disease duration, time since diagnosis, bulbar versus limb onset, or respiratory status. The ALS cohorts therefore identify a population, not a disease stage, and no result reported here is conditional on severity. A calibration-to-accuracy mapping could be stage-dependent in a way this archive cannot show, and the subgroup analyses should be read as comparing cohorts that document an ALS population against cohorts that do not, rather than as characterising disease severity."

**Comment 1.6 (minor).**

> Researcher degrees of freedom: The extensive multiplicity of exploratory configurations (e.g., 2 paradigms, 7 comparator predictors, and an ALSFRS-R add-on) is handled transparently and is mostly Holm-corrected. However, a brief acknowledgment in the Discussion regarding cumulative researcher-degrees-of-freedom risk (beyond what formal corrections capture) would be appropriate, given that no analysis plan was preregistered.

**Response.** We appreciate this comment and agree that formal correction is not the same thing as protection from cumulative multiplicity. We have added a paragraph to the Discussion, placed near the existing non-registration disclosure rather than in the numbered Limitations list, because the point is about how the exploratory results should be read rather than a defect in the study.

We have also used it to disclose, proactively, a specification change made during this revision, which we describe under Additional Changes below and which we would rather the reviewer hear from us.

> No analysis plan was registered, and the configurations reported here were, with one exception disclosed below, fixed before they were run, but not before the data were seen. The moderator tests are Holm-corrected across the ten descriptors. The alignment specifications were fixed before being run. One nonlinear specification was not: the gradient-boosted arm's initial run lacked the class rebalancing its comparators use and retained fewer principal components than the measured-variance criterion specifies, and was corrected before any transportability analysis used the column, moving its mean discriminability from 0.655 to 0.714 (supplement, S12). Formal correction bounds the family it is applied to and nothing else. The number of specifications a study could have run, and the order in which analyses followed one another, are not captured by any correction procedure, and the exploratory results reported here should be read as hypothesis-generating for that reason. The primary result does not rest on a selected configuration: it is one comparison, reported identically in every sensitivity specification.

**Closing summary for Reviewer 1.**

Once again, we thank the reviewer for a review that identified three analyses the paper needed and two places where its framing misled. In response we have:

1. Added a Discussion paragraph reasoning explicitly about the direction of the archive-homogenisation bias, concluding that the reported heterogeneity likely understates what an independent deployment would show, and cross-referencing the new cohort-level alignment result as evidence for that direction.
2. Surfaced the reconstructed-decoder caveat into the Abstract and the opening paragraph of the Discussion.
3. Added a participant-resampling study quantifying the cost of local recalibration in both participants and character selections, with minimum detectable effects at 80% power, and revised the Conclusion to withdraw the unqualified recommendation to recalibrate locally.
4. Moved the estimator-agreement comparison to Supplement S4 and removed Discussion passages that restated Results statistics.
5. Expanded the ALS characterisation limitation to name the specific clinical variables that are absent and to state what the framing can support.
6. Added a Discussion paragraph on cumulative researcher degrees of freedom beyond formal correction, including proactive disclosure of a specification change made during this revision.

---

## Reviewer 2

We thank Reviewer 2 for a review that was unusually well aimed at the load-bearing assumptions of the study. Three of the five comments identified analyses whose absence a reader could reasonably have held against the paper, and we have run all three. We are grateful in particular for the question about whether linear decision boundaries were doing the work, which we had not asked ourselves and which turned out to have a clean answer.

**Comment 2.1.**

> First is about literature context. The intro leans pretty heavily on citations that are a decade or more old (like [15], [37], and [38]). It would be great to see some more recent work on calibration-based accuracy prediction mixed in. Also, since the paper highlights that past studies only kept things within single cohorts, I'm curious if earlier researchers ever explicitly flagged why they didn't cross cohorts—did they already suspect these mappings wouldn't generalize, or was it just a matter of convenience? Adding a bit more historical context here would make the motivation pop.

**Response.** We thank the reviewer for both halves of this comment, and we found the second half the more interesting question. We have added recent citations to the Introduction, and we have gone back to the prior literature to answer the historical question directly.

On the historical question we want to be careful to report what the sources actually say rather than what would be convenient for our motivation. We read the discussion and limitations sections of the principal prior reports of calibration-based performance prediction, and of the recent cross-dataset transfer work. We did not find an author who states that a fitted calibration-to-accuracy mapping was expected not to generalise, and we did not find one who states that cross-cohort evaluation was omitted for convenience. The question appears not to have been raised either way. That is itself informative, and it is what the revised Introduction says, rather than attributing a motive to prior authors that we cannot document.

> **Original:** "Two features of that literature limit what it can support. First, the relationships were established within the cohort measured; this does not establish that a mapping fitted in one set of cohorts will estimate accuracy in a cohort it has never seen, which is what matters if a score is to be used anywhere other than where it was developed."
>
> **Revised:** "Two features of that literature limit what it can support. First, the relationships were established within the cohort measured; this does not establish that a mapping fitted in one set of cohorts will estimate accuracy in a cohort it has never seen, which is what matters if a score is to be used anywhere other than where it was developed. We could find no statement in that literature either anticipating that such a mapping would fail to generalise or explaining why cross-cohort evaluation was not attempted; the question appears not to have been raised, which is consistent with the practical difficulty of assembling comparable cohorts before public multi-study archives existed."

**Comment 2.2.**

> Second is about model scope and limitations. The manuscript mentions that L2-regularized logistic and linear discriminant comparators are the go-to families for this. Were these chosen to look at the mapping strictly within cohorts, or specifically to test cross-cohort transfer? Since simple linear models can be notoriously fragile when facing domain shifts, I wonder if relying solely on them is enough to definitively claim the mapping cant transfer, or if it's partly just a limitation of linear boundaries. A brief discussion or extra justification on this front would be super helpful.

**Response.** We thank the reviewer for this question. It is a real gap: both scores in the original manuscript come from linear decoders, and the paper offered no evidence that the failure to transport is a property of the calibration-to-accuracy relationship rather than of the decision boundary. We tested it rather than argued it.

We added two nonlinear calibration decoders, computed on the identical epochs, fold assignments and evaluation metric, with each decoder's feature transformation fitted entirely within the training fold. The first is a radial-basis kernel boundary reached through a Nystroem approximation, with the same L2 logistic head and the same class rebalancing as the linear baseline. The second is a gradient-boosted tree ensemble on a principal-component reduction of the same features. An exact kernel machine was not affordable at roughly ten thousand calibration epochs per session, and we say so in the Methods.

The answer has two parts, and we report the first before the second because it constrains what the second can mean.

First, neither nonlinear boundary recovers the linear decoder's discriminability. Mean cross-validated AUC was 0.714 for the kernel arm and 0.714 for the tree ensemble, against 0.805 for the regularised linear decoder. We regard the agreement between the two as the informative feature: two structurally unrelated nonlinear families, one a kernel approximation with a linear head and the other a tree ensemble on a variance-preserving reduction, landing within 0.0001 of each other indicates that this result is not an artefact of either family's particular modelling choice, though it does not on its own establish that roughly 0.71 is a ceiling for nonlinear boundaries imposed by the data. This is the expected result for regularised linear methods on high-dimensional, low signal-to-noise single-trial P300 data, and it is consistent with the literature the reviewer refers to.

Second, neither improves transport. Slope tau was 0.461 and 0.514 against the primary's 0.432, and intercept tau 1.034 and 1.162 against 0.873.

We are careful in the manuscript not to overclaim from the second part. Because the nonlinear scores discriminate less well, a higher tau for them is not by itself decisive evidence about nonlinear boundaries: a noisier score could transport worse for that reason alone. The defensible claim, and the one we make, is narrower than the reviewer's question invites: a nonlinear decision boundary improves neither discrimination nor transport on these data, so the transportability failure was not rescued by either nonlinear alternative tested. We state the discrimination gap before the transport comparison so that a reader can apply the same caution. The revised Results state this as follows:

> Neither nonlinear decoder recovered the regularised linear decoder's discriminability. Mean cross-validated discriminability was 0.714 for the kernel approximation and 0.714 for the gradient-boosted ensemble, against 0.805 for the linear decoder, which discriminated better than both nonlinear arms in every one of the 18 cohorts (supplement, S12; Table S15). The close agreement between two structurally unrelated nonlinear families indicates that this result is not an artifact of either family's particular modelling choice, though it does not on its own establish a performance ceiling imposed by the data. Neither improved transport: slope tau was 0.461 and 0.514 and intercept tau 1.034 and 1.162, against 0.432 and 0.873. Because these scores discriminate less well than the linear one, their higher heterogeneity is not on its own evidence about nonlinear boundaries; what the comparison supports is the narrower statement that a nonlinear boundary improves neither discrimination nor transport here: the transportability failure was not rescued by either nonlinear alternative tested.

**Comment 2.3.**

> Third is the accounting for data alignment: In BCI research, alignment techniques are usually the go-to for ironing out inter-subject and inter-cohort differences. It'd strengthen the paper immensely to know whether the mapping still fails even if you throw data alignment into the mix. Is it worth discussing, or even testing, whether alignment bridges that cross-cohort gap?

**Response.** We thank the reviewer, and we agree that this was the most important omission in the original submission. The Editor-in-Chief independently identified the same gap, and we have answered it at length in the response to Comment E.1 above, which we ask the reviewer to read as the response to this comment as well rather than have us repeat it.

In brief: four alignment arms were tested, two on the signal by Euclidean Alignment with a session-level and a cohort-level reference, and two on the score by within-cohort standardisation and within-cohort rank transformation. None restores transportability. The two Euclidean Alignment arms leave the score almost unchanged (Spearman 0.986 and 0.990 against the unaligned score) and leave heterogeneity where it was, which is mechanistically coherent because the calibration classifier is already fitted within a single session on standardised features. The two score-space arms are substantially worse, nearly doubling intercept tau, because standardising within cohort destroys the between-cohort information about absolute score level that the calibration intercept needs.

We also confirmed the conclusion is not an artefact of the standard-error convention, and we report the qualification honestly rather than let a reader discover it. Both Euclidean Alignment arms yielded a marginally higher downstream character-level AUC than the unaligned one (0.756 and 0.753 against 0.748) and accordingly a lower pooled mean absolute error (0.095 and 0.097 against 0.098), despite calibration-block discriminability that was essentially unchanged (0.800 and 0.802 against 0.805; supplement, Table S15); a downstream improvement of this kind is not evidence that transport was repaired. Session-level alignment additionally has a lower slope tau under all four conventions and a lower intercept tau under three, the exception being the paper's own clustered convention. We therefore claim that no arm *restores* transportability, not that no arm improves anything: the intercept tau never fell below 0.75 under any arm or convention, and the prediction interval for an unrepresented cohort spans roughly -2.0 to +2.0 on the log-odds scale throughout.

**Comment 2.4.**

> Fourth is about quantifying recalibration: You note that local recalibration on a new cohort makes it feasible to predict online accuracy again. It would be awesome to get a sense of how much recalibration is actually needed to pull this off. Can the authors quantify the threshold (e.g., in terms of data volume or subjects) where it flips from non-transferable to workable? That would give us a much clearer picture of the distance between the two states.

**Response.** We thank the reviewer, and we note that Reviewer 1 asked the same question independently, which we took as a strong signal that the original Conclusion had promised something it did not deliver. The full analysis and its tables are given in the response to Comment 1.3 above.

The direct answer to the reviewer's question is that we could not find a threshold, and that we now doubt one exists within the range this archive can evaluate. Up to 16 local participants and roughly 1,000 character selections, neither an intercept-only nor an intercept-and-slope refit produced an improvement over the transported mapping whose confidence interval excluded zero. Below four local participants the two-parameter refit was significantly *worse* than transporting, and at two local participants it inverted the mapping, returning a negative slope, in 24.1% of draws.

We are aware that a null of this kind is only useful if it is bounded, so we report the minimum detectable effect at 80% power alongside it: improvements larger than 0.011 to 0.031 in mean absolute error, against a transported error of about 0.09, would have been detected with 80% probability at the sizes quoted, and none was. The phrase "flips from non-transferable to workable" in the reviewer's comment describes a transition we looked for and did not observe.

**Comment 2.5.**

> Finally, the title. The title could probably punch a bit harder. It might be worth tweaking it to immediately spotlight the paper's main takeaway regarding cross-cohort limits.

**Response.** We appreciate the suggestion and agree the original title buried its own finding in a subordinate clause. We have revised it, and the revision reflects not only the reviewer's point about emphasis but also the new evidence in this revision, which strengthens what the title can claim.

> **Original:** "Calibration-derived decoder discriminability is associated with online P300-speller accuracy, but the fitted mapping does not transport across cohorts"
>
> **Revised:** "The calibration-to-accuracy mapping in P300 spellers does not transport across cohorts, and neither alignment nor local recalibration repairs it"

The revised title leads with the finding, names the two remedies the revision tested, and states that neither works, which is the contribution this version makes over the original submission.

**Closing summary for Reviewer 2.**

Once again, we thank the reviewer for a review that turned three assumptions into tested claims. In response we have:

1. Added recent citations on calibration-based accuracy prediction to the Introduction, and reported directly what the prior literature does and does not say about why cross-cohort evaluation was not attempted, without attributing a motive we cannot document.
2. Added two nonlinear calibration decoders, a radial-basis kernel approximation and a gradient-boosted tree ensemble, computed on identical epochs through an identical cross-validation, and reported that neither recovers linear discriminability nor improves transport, while stating explicitly the limit on what that comparison can support.
3. Added four alignment arms, two on the signal and two on the score, with a full transportability evaluation of each, a mechanistic account of why the score-space arms are worse, and a standard-error-convention sensitivity analysis.
4. Added a participant-resampling study quantifying the cost of local recalibration, reported that no threshold was found within the evaluable range, bounded that null by reporting minimum detectable effects at 80% power, and revised the Conclusion accordingly.
5. Revised the title to lead with the finding and to name both remedies that were tested and failed.

---

## Additional Changes During Revision

We describe here three changes that no reviewer requested, so that the Editor and reviewers hear them from us.

**A specification was corrected after its first result was seen.** The gradient-boosted arm was initially run with a configuration that differed from the other arms in two ways: it did not receive the class rebalancing that both logistic-based arms use, against a median non-target to target imbalance of 10.98 to 1, and its principal-component reduction retained fewer components than the measured-variance criterion specifies (Supplement, S12). We corrected both and re-ran the extraction before any transportability analysis used the column. We report the change, and both the initial and corrected values, in the Supplement (S12) and in the manuscript's account of researcher degrees of freedom (Discussion). Our reason for correcting rather than reporting the original was that the arm exists specifically to answer whether a nonlinear boundary transports better, and an arm denied the class rebalancing its comparators received cannot answer that. We note that the correction moved the arm's mean AUC from 0.655 to 0.714, that is, it made the nonlinear arm *better* and the contrast with the linear decoder *smaller*, and that the corrected value is the one that agrees with the independent kernel arm.

**The between-cohort variance of one cohort reference is an outlier.** In the cohort-level alignment arm, StudyK's pooled reference has the most extreme condition number in the archive at 2.69e+03, three to twenty-two times every other cohort. It remains four orders of magnitude below the numerical floor used in the whitening step, and no cohort triggered the diagnostic threshold, so the alignment is unaffected. We considered several explanations for why StudyK differs, tested them against the archive, and could not support any of them; we state the observation and say that we did not identify its cause rather than offer a mechanism we cannot defend.

**Software versions.** The Methods reported software versions that did not match the environment in which the analyses were run. The revised Methods states the correct versions: Python 3.11.14 with NumPy 2.4.6, SciPy 1.17.1, scikit-learn 1.9.0, statsmodels 0.14.6, pandas 3.0.3 and MNE 1.12.1. We apologise for the error, which we found while preparing this revision.
