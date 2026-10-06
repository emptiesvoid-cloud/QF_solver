# WP06 — Campbell and modal tracking report

Source SHA: `bf59bac3d38f19139a401ec8665b326e05917629`

Overall GYRO-05: **PASS**; GYRO-06: **PASS**.
Maturity remains **EXPERIMENTAL**. GYRO-06 is internal mesh-convergence evidence, not independent physical validation.
GYRO-06 compares only common, explicitly retained tracked branches. Partial mode coverage is recorded as ambiguity; no branch is forced through an unresolved gap.

| Case | Metric | Observed | Frozen threshold | Status |
| --- | --- | ---: | ---: | --- |
| GYRO-05 | analytical_branch_frequency_hz | 6.592413594738119 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 38.42340221311719 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 9.836316430834657 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 25.751810740024194 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 12.426442452878927 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 20.384189607473697 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 15.139601543154876 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 16.731150974073774 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 15.915494309189533 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 15.915494309189533 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 15.139601543154876 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 16.731150974073774 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 12.426442452878927 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 20.384189607473697 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 9.836316430834657 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 25.751810740024194 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 6.592413594738119 | 1e-10 | PASS |
| GYRO-05 | analytical_branch_frequency_hz | 38.42340221311719 | 1e-10 | PASS |
| GYRO-05 | maximum_independent_qep_relative_residual | 2.9154413849188606e-15 | 1e-10 | PASS |
| GYRO-05 | complex_phase_invariance | True | exact branch/lineage/frequency/status signature equality | PASS |
| GYRO-05 | eigenpair_ordering_invariance | True | exact branch/lineage/frequency/status signature equality | PASS |
| GYRO-05 | combined_phase_and_eigenpair_ordering_invariance | True | exact branch/lineage/frequency/status signature equality | PASS |
| GYRO-05 | zero_speed_degenerate_cluster_identified | True | two coincident frequencies grouped as one degenerate cluster | PASS |
| GYRO-05 | degenerate_cluster_split_lineage_count | 2 | both child branches explicitly reference the parent cluster | PASS |
| GYRO-05 | controlled_ambiguity_detected_without_forced_continuity | True | DEGENERATE_CLUSTER plus MULTIPLE_CANDIDATES; no individual edge | PASS |
| GYRO-06 | maximum_qep_relative_residual_over_all_meshes_speeds_modes | 1.6173500115243727e-09 | 1e-08 | PASS |
| GYRO-06 | maximum_16_to_32_element_tracked_branch_frequency_delta | 0.00011432898981305986 | 0.005 | PASS |
| GYRO-06 | no_forced_continuity_for_reported_ambiguities | True | ambiguous/untracked edges remain absent from individual branch associations | PASS |

The contracts and complete metric/provenance rows are in `wp06_campbell_contract.json`, `gyro_05_campbell_analytical.json`, and `gyro_06_beam2_convergence.json`. The reproducible figure is `docs/assets/gyro06-campbell.png`.

Figure SHA-256: `bffc4c2f11e2598ec73f8365aff03c9727681a40d3c5f9ea1cb19c4006b4b445`; source execution key: `2158bfb994c674e0a2a7b44f617446ed7218768c18ab43b4ae72a40da3c87204`.

WP05 equations, QEP, `RotatingModalResult`, and maturity were not modified by this report generation.
