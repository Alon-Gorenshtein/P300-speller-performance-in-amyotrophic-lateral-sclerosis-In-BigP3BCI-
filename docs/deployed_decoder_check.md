# Deployed-decoder documentation check

## Question

The Methods asserted that the classifier used online during each session's Test phase was fitted
on that same session's Train-phase files. This document records what the bigP3BCI v1.0.0 archive
actually documents about the online decoder, source study by source study. Only archive
documentation was accepted as evidence. Where the archive is silent, the entry is "not documented",
not an inference from how P300 copy-spelling protocols usually work.

## What the archive contains

The published archive holds 6,983 checksummed files: 6,980 EDF+ recordings across 20 source studies
plus `README.md`, `LICENSE.txt` and `bigP3BCI_v1_0_0.pdf`, together with the `SHA256SUMS.txt`
manifest that lists them. Its 6,983 lines name exactly those three non-EDF members and nothing
else. There is no per-study README, no
BCI2000 parameter (`.prm`) file, and no configuration, JSON, CSV, MAT or XML file of any kind. The
`README.md` states the reason the parameters are absent:

> Per institutional restrictions, source data files (in BCI2000 .dat format) cannot be publicly
> distributed as they potentially contain identifiable information.

The BCI2000 `.dat` files are where a deployed classifier's specification and weight matrix would
normally live. They were withheld from the release.

## Verdict

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

This supports the general structure of the protocol. It does not support the manuscript's stronger
claim, for three reasons:

1. No classifier family, algorithm or implementation is named for any study, so "the decoder that
   was actually deployed" cannot be characterised from the archive at all.
2. The statement never says that the online classifier's training set was the distributed Train
   files of that same session. It says labeled data are collected during a calibration phase. It
   does not state which files, whether all of them were used, or whether the classifier was refitted
   for each session in the eight studies that recorded more than one session per participant.
3. The archive's own Usage Notes warn that there are "missing files for some participants", so the
   distributed Train files are not guaranteed to be the complete calibration set for a session.

## Per-study record

"Family documented" asks whether the archive names the online classifier's algorithm or family.
"Trained on that session's Train files documented" asks whether the archive states, for that study,
that the classifier applied during the Test phase was fitted on that session's Train-phase files.
Session counts are from the file hierarchy of the verified cache, not from the archive's summary
table, and are reported as structural context rather than as documentation.

| Study | ALS cohort per archive | EDF files | Sessions | Sessions with both phases | Family documented | Trained on that session's Train files documented | Evidence |
|---|---|---:|---:|---:|---|---|---|
| A | No | 390 | 13 | 13 | Not documented | Not documented | Archive Table 1 gives publication, subjects, sessions, paradigm and grid only. No classifier text in README, descriptor PDF, EDF headers or annotations. |
| B | Yes | 544 | 60 | 56 | Not documented | Not documented | As above. Two sessions carry Test files with no Train files in the same session (B_01 SE002, B_01 SE003), so for those sessions the archive does not even contain the calibration data the claim refers to. |
| C | No | 341 | 19 | 15 | Not documented | Not documented | As above. Four sessions carry Test files with no Train files (C_18, C_20, C_21, C_22, all SE001). Every Train file is labelled CB and every Test file CBERN, with no documented mapping between them. |
| D | No | 307 | 17 | 17 | Not documented | Not documented | As above. Train files sit under one condition folder (RC) while Test files sit under several (Dyn, DynBigram), and the archive does not document how calibration files map onto test conditions. |
| E | No | 88 | 8 | 8 | Not documented | Not documented | As above. The archive states only that study E's protocol "is similar to that of study D". |
| F | Yes | 270 | 30 | 30 | Not documented | Not documented | As above. One Train condition (CBCol) against three Test conditions (Dyn, DynBigram, Static), with no documented mapping. |
| G | No | 320 | 20 | 20 | Not documented | Not documented | As above. One Train condition (CB) against two Test conditions (DynBigram, DynNgram), with no documented mapping. |
| H | No | 372 | 16 | 16 | Not documented | Not documented | As above. One Train condition (CB) against four Test conditions (CBGaze01, CBGaze10, CBGazeNo, CBGazeReal) with no documented mapping. |
| I | No | 265 | 13 | 13 | Not documented | Not documented | As above. The archive states only that study I's protocol "is similar to that of study J". |
| J | No | 502 | 20 | 20 | Not documented | Not documented | As above. |
| K | No | 128 | 8 | 8 | Not documented | Not documented | As above. |
| L | Yes | 330 | 11 | 11 | Not documented | Not documented | As above. |
| M | No | 420 | 21 | 21 | Not documented | Not documented | As above. The archive states only that study M's protocol "is similar to that of study K". |
| N | Yes | 160 | 16 | 16 | Not documented | Not documented | As above. Sessions were recorded with both dry and wet electrodes, and the archive does not document whether a separate online classifier was fitted per electrode condition. |
| O | No | 347 | 36 | 34 | Not documented | Not documented | As above. Two sessions carry Train files with no Test files (O_14 SE001, O_14 SE002). |
| P | No | 228 | 38 | 38 | Not documented | Not documented | As above. |
| Q | No | 1,080 | 107 | 107 | Not documented | Not documented | As above. |
| R | No | 480 | 40 | 40 | Not documented | Not documented | As above. |
| S1 | No | 120 | 10 | 10 | Not documented | Not documented | As above. |
| S2 | No | 288 | 24 | 24 | Not documented | Not documented | As above. |

The six sessions that carry Test files without Train files are outside the analytic set, because a
session with no calibration files yields no calibration score. They are recorded here because they
show that the archive's file organisation does not by itself guarantee that a session's online
decoder could have been fitted on that session's distributed Train files.

In five studies the Train condition labels are disjoint from the Test condition labels: C calibrates
under CB and tests under CBERN, D calibrates under RC and tests under Dyn and DynBigram, F calibrates
under CBCol and tests under Dyn, DynBigram and Static, G calibrates under CB and tests under
DynBigram and DynNgram, and H calibrates under CB and tests under four gaze conditions. One
calibration condition therefore precedes several test conditions, and the archive documents no
mapping from calibration files to test runs. In the other 15 studies the two sets of labels coincide.
That coincidence is a property of how the files are named. It is not a statement by the distributor
about which data trained the online decoder, and it is not treated as one here.

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
8. EDF+ annotation scan, sampling Train and Test files from every one of the 20 studies. The only
   annotation string present anywhere is "Begin recording".
9. Structural scan of the Train and Test phase directories for all 20 studies, giving the session
   counts in the table above.
10. Grep of the repository's own documentation (`docs/*.md`, including `data_provenance.md`,
    `reference_library.md` and `source_study_screening.md`) for `classifier`, `SWLDA`, `stepwise`,
    `online decod` and `deployed`. The only hits describe this study's own offline analysis
    classifier. No repository document records anything about the historical online decoders.
11. Retrieval of the archive's published description at `physionet.org/content/bigp3bci/1.0.0/`.
    Its Experiment Setup section repeats the collection-level statement and names no classifier;
    its Usage Notes warn of missing files for some participants.

## What the archive does record about online decoding

The archive records the online decoder's output, not its specification. The EDF+ data dictionary
defines `SelectedTarget`, `SelectedRow` and `SelectedColumn` as the predicted target character,
row and column during the feedback phase, and `FakeFeedback` as an index that overrides the
prediction actually displayed. This study reconstructs its outcome from those traces. Recording a
decoder's selections is not documentation of what the decoder was or what it was fitted on.

## Consequence for the manuscript

The subsection "Relationship Between the Predictor and the Deployed Decoder" and the corresponding
limitation were rewritten to state that the Train phase supplies the data from which an online
classifier is derived before the Test phase begins, that the archive does not document the online
classifier for every source study, and that the score is therefore described as the cross-validated
learnability of that session's calibration data rather than as a property of the specific decoder
deployed.
