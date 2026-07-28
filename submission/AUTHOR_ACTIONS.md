# Author actions before submission

This package contains the complete reproducible analysis and a manuscript drafted from frozen outputs. `manuscript/manuscript.md` is the superseded pre-widening draft (see `submission/SUPERSEDED_DO_NOT_SUBMIT.md`) and must not be submitted; the canonical manuscript is `manuscript/manuscript_expanded.md`, alongside `supplementary/supplement_expanded.md` and `manuscript/cover_letter_expanded.md`. Author, affiliation, corresponding-author, funding, competing-interest, and CRediT information is already populated in the Acknowledgements section of `manuscript/manuscript_expanded.md` and in `manuscript/cover_letter_expanded.md`; none of it is placeholder text needing to be filled in. The following items still require the submitting team’s own review or a decision before any submission.

1. Verify the author, affiliation, corresponding-author, funding, competing-interest, and CRediT statements already populated in `manuscript/manuscript_expanded.md` and `manuscript/cover_letter_expanded.md` are current and correctly attributed for this submission round.
2. Confirm the local ethics or exemption determination for the secondary analysis of de-identified public data; do not state an exemption that has not been issued or confirmed by the submitting institution.
3. Confirm that the selected journal permits the intended public-data reuse and source-dataset citation.
4. Review the Zotero import, then select the journal’s citation style at submission.
5. Confirm that every author has reviewed the final rendered manuscript, supplement, and reproducibility materials.
6. Before submission: push this repository to the cited GitHub URL if not already done, create a tagged release matching the cited commit, archive that release and the frozen `output/expanded/` outputs on Zenodo or OSF, obtain a DOI, and replace the commit-hash citation in `manuscript/manuscript_expanded.md`’s Data and Code Availability section with the archived-release DOI once minted.
7. Decide whether to shorten the manuscript title. This was raised as an optional trim during the same revision pass and was deliberately left to the author’s own judgment rather than implemented.
