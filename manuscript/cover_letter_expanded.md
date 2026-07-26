---
title: "Cover letter"
---

Re: Submission of "Calibration discriminability tracks online P300-speller accuracy in eighteen cohorts, but the fitted mapping does not transport" as a Paper

Dear Editors of *Journal of Neural Engineering*,

We submit the manuscript above for consideration as a Paper. Calibration recordings are collected before a P300-speller session, and a score derived from them has repeatedly been related to that session's online spelling accuracy. Mainsah and colleagues took this furthest in this journal, deriving speller accuracy analytically from a calibration-derived detectability index so that performance could be estimated without extensive online testing (*J Neural Eng* 2016;13:066007). That relationship, and the earlier reports it builds on, were established within the cohort in which they were measured. Whether a mapping fitted in one set of cohorts estimates accuracy in a cohort it has never seen is a separate question, and it is the question that determines whether such a score can be used anywhere other than where it was developed.

We evaluated this using the public BigP3BCI archive. All 20 documented source studies supplied the shared 16-channel montage; 18 yielded eligible online outcomes, giving 271 participants, 410 sessions and 19,611 character selections, with the four documented ALS cohorts as the prespecified primary subgroup. Withholding one source study at a time, the association between calibration discriminability and subsequent accuracy appeared in every one of the 18 cohorts, at the level of individual participants (r = 0.701, n = 271), and after removing every between-cohort difference (r = 0.652). The fitted mapping, however, did not transport. Calibration slope ranged from 0.075 to 2.233 and intercept from -2.445 to 1.870 across withheld cohorts, and in two cohorts the score estimated accuracy less well than that cohort's own mean. For a cohort not represented in the archive, the interval on discrimination reaches down to chance. A single analysis improved transportability: excluding records in which more than 20% of calibration epochs were rejected reduced estimation error from 0.104 to 0.084 and slope variability from 0.586 to 0.438.

We believe this carries three implications for this journal's readership. First, it separates two claims that the field has tended to report together: an association that replicates across cohorts, and a calibrated mapping that does not. A calibration score can support ranking sessions within a setting, and can support a data-quality screen, but should not be used to report an expected accuracy elsewhere without local recalibration. Second, the four ALS cohorts analysed alone gave a calibration-slope standard deviation of 0.204, against 0.586 across all 18; those four cohorts were not merely too few to estimate the spread, they were homogeneous and favourable, so the resulting picture was optimistic in a measurable direction. Evaluations built on a small number of cohorts should be read accordingly. Third, the artifact-rejection result is actionable at no cost, because the rejection fraction is already computed whenever the score is computed.

We note that the journal's guidance asks that contributions using openly available data provide validation on additional data sets and insight into why performance differs. This study reports no performance improvement; it reports a negative transportability result across 18 independent cohorts, together with the cohort-level mechanism that produces it. All analysis code, frozen outputs, and the archive provenance record with checksum verification are available to support editorial assessment.

We thank the editors for their time and consideration. The work has not been submitted elsewhere and is not under consideration by any other journal. A companion manuscript from our group uses the same archive to ask a different question, namely how much of each emitted character selection is determined by a language-model prior rather than by the neural signal; it is being submitted to a different journal, reuses the calibration score reported here as a moderator, and a copy is provided with this submission in keeping with ICMJE guidance on overlapping publications.

Sincerely,

[Submitting author name, degree]

[Institution, department]

[Corresponding-author email]
