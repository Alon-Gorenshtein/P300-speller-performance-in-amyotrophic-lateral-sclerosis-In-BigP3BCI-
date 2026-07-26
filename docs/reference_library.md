# Reference library

Candidate references for the expanded manuscript, each located through a Crossref bibliographic
query on 2026-07-26. Every DOI below resolved to a Crossref record whose first author, journal and
year are reproduced here. Full author lists, volumes, issues and pages are re-verified by
`scripts/verify_refs.py` at the citation stage before anything ships.

The previous version of the manuscript carried four references. A reviewer of a Journal of Neural
Engineering submission would expect engagement with the P300 performance-prediction literature this
study extends, and with the prediction-model reporting literature its design belongs to.

## Direct antecedents, must be cited and benchmarked

| DOI | First author | Journal | Year | Why |
|---|---|---|---|---|
| 10.1088/1741-2560/13/6/066007 | Mainsah | J Neural Eng | 2016 | The closest prior work: derives P300-speller accuracy as a function of a calibration-derived detectability index, in this study's target journal, by the first author of this study's dataset. Must be cited, and d-prime must enter the comparator set. |
| 10.1371/journal.pone.0076148 | Halder | PLoS ONE | 2013 | Predicts P300 BCI aptitude in severe motor impairment. |
| 10.1088/1741-2560/9/2/026014 | Mak | J Neural Eng | 2012 | EEG correlates of P300-BCI performance in ALS; the premise this study evaluates out of sample. |
| 10.1016/j.neuroimage.2010.03.022 | Blankertz | NeuroImage | 2010 | The canonical neurophysiological performance predictor, for the sensorimotor-rhythm case. |
| 10.1016/j.neulet.2009.06.045 | Guger | Neurosci Lett | 2009 | Establishes the performance-variability problem the prediction literature responds to. |

## P300 speller method and paradigm

| DOI | First author | Journal | Year |
|---|---|---|---|
| 10.1016/0013-4694(88)90149-6 | Farwell | Electroencephalogr Clin Neurophysiol | 1988 |
| 10.1088/1741-2560/3/4/007 | Krusienski | J Neural Eng | 2006 |
| 10.1016/j.jneumeth.2007.07.017 | Krusienski | J Neurosci Methods | 2008 |
| 10.1016/j.clinph.2010.01.030 | Townsend | Clin Neurophysiol | 2010 |
| 10.1088/1741-2560/11/5/056004 | Kaufmann | J Neural Eng | 2014 |
| 10.1088/1741-2560/12/1/016013 | Mainsah | J Neural Eng | 2015 |
| 10.1371/journal.pone.0078432 | Speier | PLoS ONE | 2013 |

## Decoding methods, for the comparator discussion

| DOI | First author | Journal | Year |
|---|---|---|---|
| 10.1109/tbme.2009.2012869 | Rivet | IEEE Trans Biomed Eng | 2009 |
| 10.1109/tbme.2011.2172210 | Barachant | IEEE Trans Biomed Eng | 2012 |
| 10.1080/2326263x.2017.1297192 | Congedo | Brain-Computer Interfaces | 2017 |
| 10.1088/1741-2552/aab2f2 | Lotte | J Neural Eng | 2018 |

## Brain-computer interfaces in amyotrophic lateral sclerosis

| DOI | First author | Journal | Year |
|---|---|---|---|
| 10.1016/j.clinph.2005.06.027 | Sellers | Clin Neurophysiol | 2006 |
| 10.1016/j.clinph.2008.03.034 | Nijboer | Clin Neurophysiol | 2008 |
| 10.3109/17482961003777470 | Sellers | Amyotroph Lateral Scler | 2010 |
| 10.1177/155005941104200410 | Silvoni | Clin EEG Neurosci | 2011 |
| 10.3389/fnhum.2013.00732 | Riccio | Front Hum Neurosci | 2013 |
| 10.1038/nrneurol.2016.113 | Chaudhary | Nat Rev Neurol | 2016 |
| 10.1056/nejmoa1608085 | Vansteensel | N Engl J Med | 2016 |
| 10.1212/wnl.0000000000005812 | Wolpaw | Neurology | 2018 |
| 10.1016/j.clinph.2010.01.034 | Kleih | Clin Neurophysiol | 2010 |
| 10.1016/S1388-2457(02)00057-3 | Wolpaw | Clin Neurophysiol | 2002 |

## Prediction-model development, validation and reporting

The design of this study is an external-validation study of a one-predictor model, so it belongs to
this literature and should report against its conventions.

| DOI | First author | Journal | Year | Why |
|---|---|---|---|---|
| 10.1136/bmj.g7594 | Collins | BMJ | 2015 | TRIPOD; the reporting standard this manuscript should follow. |
| 10.1016/j.jclinepi.2014.06.018 | Debray | J Clin Epidemiol | 2015 | Framework for interpreting external validation, including between-study heterogeneity. |
| 10.1136/bmj.i3140 | Riley | BMJ | 2016 | External validation across clustered data; the source of the random-effects and prediction-interval treatment. |
| 10.1016/j.jclinepi.2015.12.005 | Van Calster | J Clin Epidemiol | 2016 | Calibration hierarchy; supports reporting calibration-in-the-large and slope per study rather than pooled. |
| 10.1097/ede.0b013e3181c30fb2 | Steyerberg | Epidemiology | 2010 | Performance measures for prediction models. |
| 10.1016/s0895-4356(03)00047-7 | Steyerberg | J Clin Epidemiol | 2003 | Internal versus external validation, bias and precision. |

## Data source

| DOI | First author | Repository | Year |
|---|---|---|---|
| 10.13026/0byy-ry86 | Mainsah | PhysioNet | 2025 |

## Rejected candidates and why

- Riley, minimum sample size, `10.1002/sim.8409`: the Crossref query returned the correction notice
  rather than the article. Retrieve the original before use.
- Jeunet, predicting mental-imagery BCI performance, `10.1371/journal.pone.0282281`: also a
  correction notice. The topic is motor imagery rather than P300 and is not required.
- Kubler, clinical applications, `10.1109/iww-bci.2015.7073033`: a two-page conference abstract, not
  a citable review.
- Lopez-Gordo auditory BCI, Fazel-Rezai paradigm chapter, Breiman random forests: retrieved during
  searching but not relevant to this manuscript.
