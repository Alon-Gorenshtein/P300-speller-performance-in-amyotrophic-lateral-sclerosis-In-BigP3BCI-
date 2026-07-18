# Online spelling outcome definition

The primary outcome is feedback-phase character correctness. For each transition into `PhaseInSequence == 3`, the target is the final nonzero `CurrentTarget` value in the directly preceding contiguous phase-2 window. The selected character is the modal nonzero `SelectedTarget` value during that phase-3 window.

A trial is eligible only if feedback was displayed, target and selected character can both be recovered, and `FakeFeedback` did not override the selected character. Eligible trials are correct when target equals selected character. Every ineligible feedback phase is retained with one explicit exclusion reason.
