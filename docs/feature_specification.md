# Calibration feature specification

Only Train EDF files are eligible for this stage. A calibration event is a rising `StimulusBegin` transition during phase 2, labelled target or non-target by `StimulusType`. EEG uses the 16 channels shared by the ALS cohorts, 0.5-30 Hz zero-phase filtering, a -200 to 800 ms epoch, baseline correction using -200 to 0 ms, and exclusion of epochs exceeding 150 microvolts in absolute amplitude.

The primary score is grouped cross-validated AUC of a regularized logistic classifier. Its folds are grouped by EDF file, and its inputs are downsampled calibration EEG epochs only. The prespecified secondary score is target-minus-nontarget Pz amplitude averaged from 250 to 500 ms. Both scores are created once per participant-session from all that session's Train files; no Test sample, selection, or outcome is loaded by this script.
