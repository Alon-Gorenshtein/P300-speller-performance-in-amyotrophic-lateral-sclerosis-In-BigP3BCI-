# Deployed-decoder documentation check

## Question

The Methods asserted that the classifier used online during each session's Test phase was fitted
on that same session's Train-phase files, and that the predictor evaluated in this study is therefore
the fit quality of the decoder that was actually deployed. This document records what the bigP3BCI
v1.0.0 archive documents about the online decoder, source study by source study, what the
publications the archive cites add, and why the original assertion does not survive either route.

Archive documentation was the primary evidence. Where the archive is silent the entry is "not
documented", not an inference from how P300 copy-spelling protocols usually work. The source-study
publications are reported separately and are labelled as such, because they are external literature
that the archive points to rather than documentation the archive provides.

## Summary of the three findings

1. **The archive names no online classifier for any of the 20 source studies.** The only relevant
   archive text is one collection-level description of the paradigm. The BCI2000 parameter files that
   would carry a decoder specification were deliberately withheld from the release.
2. **The primary source-study publications do document the practice, where they are retrievable.**
   Three were retrieved and their statements verified verbatim, from two different laboratories and
   three different source studies. All three describe a stepwise linear discriminant analysis
   classifier fitted on a session's calibration data and applied in that session's test runs. Two
   source studies have no related publication at all, and three cite items that are not reliably
   retrievable.
3. **The original assertion was false regardless of which route is taken.** The predictor evaluated
   in this study is not the deployed decoder under any reading. `manuscript_expanded.md` line 60
   defines it as the out-of-fold area under the curve of *this study's own* L2-regularised logistic
   classifier with file-grouped cross-validation. That is a different classifier, a different fitting
   procedure and a different scoring rule from the historical SWLDA decoder. Finding 3, not finding 1,
   is the decisive one, and the manuscript now rests the withdrawal on it.

## What the archive contains

The published archive holds 6,983 checksummed files: 6,980 EDF+ recordings across 20 source studies
plus `README.md`, `LICENSE.txt` and `bigP3BCI_v1_0_0.pdf`, together with the `SHA256SUMS.txt`
manifest that lists them. Its 6,983 lines name exactly those three non-EDF members and nothing else.
There is no per-study README, no BCI2000 parameter (`.prm`) file, and no configuration, JSON, CSV,
MAT or XML file of any kind. The `README.md` states the reason the parameters are absent:

> Per institutional restrictions, source data files (in BCI2000 .dat format) cannot be publicly
> distributed as they potentially contain identifiable information.

The BCI2000 `.dat` files are where a deployed classifier's specification and weight matrix would
normally live. They were withheld from the release.

## What the archive documents

**The online classifier is not documented for any of the 20 source studies.** No study-level
statement about the online decoder exists anywhere in the archive. The only relevant documentation
is a single collection-level description of the paradigm in `README.md`, reproduced verbatim below,
which names no classifier and makes no per-study or per-session claim:

> A P300 speller experiment session consists of a calibration phase and a test phase. During the
> calibration phase, participants perform copy-spelling with no classifier use and no BCI feedback
> presented to collect labeled EEG data to train a P300 classifier. During the test phase, the
> trained P300 classifier is applied and participants perform copy-spelling with the BCI prediction
> of the target character presented as feedback after data collection for a character trial.

The archive's published description on PhysioNet carries the same statement in its Experiment Setup
section ("An experiment session consists of a calibration phase and a test phase... During the test
phase, the trained BCI classifier is applied") and likewise names no classifier family and gives no
study-level detail.

One further sentence in the data descriptor touches the online machinery and is quoted here so that
it is not mistaken for an omission:

> Most labels for the EDF+ data records are derived from parameter definitions in the P3SpellerTask
> and EyeTrackerLogger modules in BCI2000.

That sentence explains the provenance of the data-record *labels*. It names two BCI2000 modules, not
a classifier, and it carries no information about what was fitted on what.

The archive also records the online decoder's output, not its specification. The EDF+ data dictionary
defines `SelectedTarget`, `SelectedRow` and `SelectedColumn` as the predicted target character, row
and column during the feedback phase, and `FakeFeedback` as an index that overrides the prediction
actually displayed. This study reconstructs its outcome from those traces. Recording a decoder's
selections is not documentation of what the decoder was or what it was fitted on.

## What the source-study publications document

The archive's Table 1 gives a Related Publication for 18 of the 20 studies. These are external
literature, not archive documentation, but a P300 reviewer will have them in mind, so they were
consulted rather than left as a gap. Three were retrieved in full and their statements confirmed
verbatim against the Europe PMC full-text index, which returns the source article for each phrase.

| Source study | Publication | Verified statement |
|---|---|---|
| F (ALS) | Mainsah BO, Collins LM, Colwell KA, et al. *J Neural Eng*. 2015;12(1):016013. doi:10.1088/1741-2560/12/1/016013 | "The training dataset was used to train a stepwise linear discriminant analysis (SWLDA) classifier"; "Features extracted from the training data were used to develop a P300 classifier that was used in all the test runs for each session." Dynamic stopping was layered on top: data collection halts when a character probability reaches a threshold of 0.9. |
| O | Frye GE, Hauser CK, Townsend G, Sellers EW. *J Neural Eng*. 2011;8(2):025024. doi:10.1088/1741-2560/8/2/025024 | "The SWLDA algorithm was then used for online classification"; "Classification coefficients were generated with data collected during a calibration phase and subsequently applied during an online test phase." Separate classifiers were derived for the SUP and CBP conditions, which matches this study's two condition folders. |
| D | Mainsah BO, Colwell KA, Collins LM, Throckmorton CS. *IEEE Trans Neural Syst Rehabil Eng*. 2014;22(4):837-846. doi:10.1109/TNSRE.2014.2321290 | "Features extracted from the EEG data from the training session were used to train a Stepwise Linear Discriminant Analysis (SWLDA) classifier to obtain feature weights that were used in the dynamic stopping and dynamic stopping with language model algorithms"; "Features extracted from the training EEG data were used to train a single classifier that was used in all six testing runs." |

Two of the three come from one of the contributing author groups (Mainsah, Colwell, Collins,
Throckmorton) and one from the other (Frye, Hauser, Townsend, Sellers), so the practice is attested
on both sides of the collection rather than in one laboratory's habits.

Three limits bound how far this route can be taken, and none of them is closed by the archive.

1. **Two studies have no related publication at all.** Studies E and I are given no citation in
   Table 1, only a footnote that the protocol "is similar to that of" study D and study J
   respectively. Both contribute outcomes to this analysis, so the primary-literature route does not
   cover the whole analytic set. A third, study M, cites "Bayesian Adaptive Stimulus Optimization in
   Stimulus-driven Brain Computer Interfaces, 2024" with no venue.
2. **Two citations are conference items that are not reliably retrievable.** Study A cites a 2010
   presentation at the 4th International BCI Meeting in Asilomar and study G a paper from the 6th
   International BCI Conference in Graz. Study B cites a 2011 Foundations of Augmented Cognition
   proceedings chapter, which was not retrieved here.
3. **In several cohorts the deployed decoder is a classifier plus an online decision rule, which no
   one-line claim describes.** Studies D, F and G deploy dynamic stopping, in D and G with a language
   model; studies K and M deploy adaptive stimulus selection; study C deploys a spelling-correction
   layer, its Test condition being labelled CBERN. In those cohorts the quantity that produced the
   online selections is a
   classifier, a stopping or selection rule, and in two cases a language prior, and the archive
   documents none of the three. Study C contributes no outcomes to this analysis; the other five do.

## Per-study record

"Family documented" asks whether the archive names the online classifier's algorithm or family.
"Trained on that session's Train files documented" asks whether the archive states, for that study,
that the classifier applied during the Test phase was fitted on that session's Train-phase files.
Both questions concern the archive only. The last column records the citation the archive gives and
whether it was retrieved. Session counts are from the file hierarchy of the verified cache, not from
the archive's summary table, and are reported as structural context rather than as documentation.

| Study | ALS cohort per archive | EDF files | Sessions | Sessions with both phases | Family documented in archive | Trained on that session's Train files documented in archive | Archive-cited publication | Evidence and structural notes |
|---|---|---:|---:|---:|---|---|---|---|
| A | No | 390 | 13 | 13 | Not documented | Not documented | Asilomar 2010 presentation, not retrievable | Archive Table 1 gives publication, subjects, sessions, paradigm and grid only. No classifier text in README, descriptor PDF, EDF headers or annotations. |
| B | Yes | 544 | 60 | 56 | Not documented | Not documented | Augmented Cognition 2011 proceedings, not retrieved | As above. Two sessions carry Test files with no Train files (B_01 SE002, B_01 SE003), so for those the archive does not contain the calibration data the claim refers to, and two carry Train with no Test (B_04 SE010, B_16 SE001). |
| C | No | 341 | 19 | 15 | Not documented | Not documented | IEEE TNSRE 2015;23(5):737-743, not retrieved | As above. Four sessions carry Test files with no Train files (C_18, C_20, C_21, C_22, all SE001). Every Train file is labelled CB and every Test file CBERN, with no documented mapping. Deploys a spelling-correction layer. Contributes no outcomes. |
| D | No | 307 | 17 | 17 | Not documented | Not documented | IEEE TNSRE 2014;22(4):837-846, retrieved and verified | As above. One Train condition (RC) against two Test conditions (Dyn, DynBigram) with no documented mapping. Deploys dynamic stopping with a language model. |
| E | No | 88 | 8 | 8 | Not documented | Not documented | None; footnote says protocol similar to study D | As above. Contributes outcomes, and no primary publication covers it. |
| F | Yes | 270 | 30 | 30 | Not documented | Not documented | J Neural Eng 2015;12(1):016013, retrieved and verified | As above. One Train condition (CBCol) against three Test conditions (Dyn, DynBigram, Static) with no documented mapping. Deploys dynamic stopping. |
| G | No | 320 | 20 | 20 | Not documented | Not documented | Graz 2014 conference paper, not retrievable | As above. One Train condition (CB) against two Test conditions (DynBigram, DynNgram) with no documented mapping. Deploys dynamic stopping with a language model. |
| H | No | 372 | 16 | 16 | Not documented | Not documented | J Neural Eng 2017;14(5):056010, not retrieved | As above. One Train condition (CB) against four Test conditions (CBGaze01, CBGaze10, CBGazeNo, CBGazeReal) with no documented mapping. |
| I | No | 265 | 13 | 13 | Not documented | Not documented | None; footnote says protocol similar to study J | As above. Contributes outcomes, and no primary publication covers it. |
| J | No | 502 | 20 | 20 | Not documented | Not documented | J Neural Eng 2017;14(4):046025, not retrieved | As above. |
| K | No | 128 | 8 | 8 | Not documented | Not documented | NeurIPS 2018;31, not retrieved | As above. Deploys adaptive stimulus selection. |
| L | Yes | 330 | 11 | 11 | Not documented | Not documented | Clin EEG Neurosci 2018;49(2):114-121, not retrieved | As above. |
| M | No | 420 | 21 | 21 | Not documented | Not documented | Cited as "2024" with no venue | As above. Deploys adaptive stimulus selection. |
| N | Yes | 160 | 16 | 16 | Not documented | Not documented | J Neural Eng 2016;13(6):066018, not retrieved | As above. Sessions were recorded with both dry and wet electrodes, and the archive does not document whether a separate online classifier was fitted per electrode condition. |
| O | No | 347 | 36 | 34 | Not documented | Not documented | J Neural Eng 2011;8(2):025024, retrieved and verified | As above. Two sessions carry Train files with no Test files (O_14 SE001, O_14 SE002). |
| P | No | 228 | 38 | 38 | Not documented | Not documented | Int J Hum Comput Interact 2010;27(1):69-84, not retrieved | As above. Contributes no outcomes. |
| Q | No | 1,080 | 107 | 107 | Not documented | Not documented | Clin Neurophysiol 2017;128(10):2050-2057, not retrieved | As above. |
| R | No | 480 | 40 | 40 | Not documented | Not documented | Brain Comput Interfaces 2018;5(1):30-39, not retrieved | As above. |
| S1 | No | 120 | 10 | 10 | Not documented | Not documented | J Neural Eng 2019;16(3):036026, not retrieved | As above. |
| S2 | No | 288 | 24 | 24 | Not documented | Not documented | J Neural Eng 2019;16(3):036026, not retrieved | As above. |

Six sessions carry Test files with no Train files and four carry Train files with no Test files. The
six Test-only sessions are outside the analytic set, because a session with no calibration files
yields no calibration score. They are recorded here because they show that the archive's file
organisation does not by itself guarantee that a session's online decoder could have been fitted on
that session's distributed Train files. The archive's own Usage Notes acknowledge "missing files for
some participants".

In five studies the Train condition labels are disjoint from the Test condition labels: C calibrates
under CB and tests under CBERN, D calibrates under RC and tests under Dyn and DynBigram, F calibrates
under CBCol and tests under Dyn, DynBigram and Static, G calibrates under CB and tests under
DynBigram and DynNgram, and H calibrates under CB and tests under four gaze conditions. One
calibration condition therefore precedes several test conditions, and the archive documents no
mapping from calibration files to test runs. Mainsah 2015 and Mainsah 2014 both state that one
classifier served all test runs of a session, which is consistent with that layout, but that is the
publications speaking and not the archive. In the other 15 studies the two sets of labels coincide.
That coincidence is a property of how the files are named. It is not a statement by the distributor
about which data trained the online decoder, and it is not treated as one here.

## Why the claim was withdrawn even though the practice is attested

The original sentence made two claims at once: that the online classifier was fitted on that
session's Train files, and that the predictor evaluated here is therefore the fit quality of the
decoder that was deployed. The publications support a version of the first claim for the studies
they cover. Nothing supports the second. From `manuscript_expanded.md` line 60:

> The primary score was the out-of-fold area under the receiver operating characteristic curve of an
> L2-regularised logistic classifier (C = 1.0, lbfgs solver) trained on standardised features, with
> stratified grouped cross-validation grouping by European Data Format file so that no epoch was
> scored by a model fitted on the same recording file.

That is a classifier fitted in this study, with a different algorithm, a different regularisation, a
different feature pipeline and a cross-validated scoring rule that the online system never used. It
shares only its input recordings with the historical SWLDA decoder. The predictor is therefore the
learnability of a session's calibration data, and the withdrawal stands on that, not on what the
archive happens to document.

## Searches performed

Every search below excluded macOS AppleDouble sidecar files, whose names begin with `._`.

1. Extension census of the verified cache, `data/source_cache_full`: 6,980 files, all `.edf`. No
   other file type is present.
2. Sweep of the cache for `.prm`, `.ini`, `.cfg`, `.json`, `.csv`, `.mat`, `.dat`, `.xml` and
   `.yaml` files: none found.
3. Case-insensitive grep of the cache for `classifier`, `stepwise`, `SWLDA` and `calibration` in
   `.txt` and `.md` files: no matches, because no such files exist in the cache.
4. Listing of every non-EDF member of the distributed ZIP: `LICENSE.txt`, `README.md`,
   `SHA256SUMS.txt`, `bigP3BCI_v1_0_0.pdf`. Cross-checked against `SHA256SUMS.txt`, which lists the
   same three non-EDF members.
5. Full read of `README.md`. It contains the collection-level protocol statement quoted above and
   the statement that BCI2000 `.dat` source files are not distributed. It names no classifier.
6. Full text extraction of the data descriptor `bigP3BCI_v1_0_0.pdf` and a case-insensitive grep for
   `classifi`, `SWLDA`, `stepwise`, `LDA`, `discrimin`, `weight`, `coeffici`, `train`, `calibrat`
   and `online`. The only hits are inside cited publication titles and in the phrase "BCI Training"
   used as an IEEE P2731 data-level label. The descriptor documents, per study, only the related
   publication, subject count, ALS status, session count, stimulus paradigms and grid size, plus the
   EDF+ header dictionary and the EDF+ data-label dictionary. It documents nothing about the online
   classifier.
7. Header scan of all 6,980 EDF files. Patient identification, recording identification, the fixed
   reserved field, every signal label, transducer type, prefiltering string and per-signal reserved
   field were extracted and matched against `classif|swlda|stepwise|lda|discrim|weight|coeff|regress|train|model|filter`.
   Zero matches. The free-text fields carry only the dataset name and version, the study label, the
   session number, the amplifier model, the transducer type and the amplifier-stage filter settings.
8. EDF+ annotation scan across Train and Test files from every one of the 20 studies. The only
   annotation string present anywhere is "Begin recording".
9. Structural scan of the Train and Test phase directories for all 20 studies, giving the session
   counts in the table above, and a listing of the Train and Test condition labels per study.
10. Grep of the repository's own documentation (`docs/*.md`, including `data_provenance.md`,
    `reference_library.md` and `source_study_screening.md`) for `classifier`, `SWLDA`, `stepwise`,
    `online decod` and `deployed`. The only hits describe this study's own offline analysis
    classifier. No repository document records anything about the historical online decoders.
11. Retrieval of the archive's published description at `physionet.org/content/bigp3bci/1.0.0/`.
    Its Experiment Setup section repeats the collection-level statement and names no classifier;
    its Usage Notes warn of missing files for some participants.
12. Crossref lookup of the Frye 2011 DOI, `10.1088/1741-2560/8/2/025024`, confirming title, journal,
    year, volume, issue, article number and the four authors before citing it.
13. Retrieval of the Mainsah 2015, Frye 2011 and Mainsah 2014 full texts, followed by exact-phrase
    queries against the Europe PMC full-text index for each quoted sentence. Each phrase returned the
    expected article and no other, which confirms the quotations are verbatim rather than
    paraphrased.

## Consequence for the manuscript

The Methods subsection was retitled "What the Calibration Score Is, and What It Is Not", because the
old title named a relationship the paragraph concludes cannot be characterised. The subsection and
the corresponding limitation now state that the Train phase supplies the data from which the online
classifier is derived and that the source-study publications describe a linear classifier fitted on
each session's calibration data, that the archive itself names no online classifier and withholds the
parameter files so the deployed decoder cannot be reconstructed, and that the predictor is in any
case a separate classifier fitted here on the same recordings. Mainsah 2015 and Frye 2011 were cited
for the first point and the reference list renumbered to keep AMA order of first appearance.
