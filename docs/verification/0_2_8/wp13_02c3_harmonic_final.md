---
doc_id: DOC-028-WP13-02C3-HARMONIC-FINAL-001
revision: 0.1
status: owner_review_required
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP13-02C3 final mixed harmonic campaign

WP13-02C3 replays the complete frozen twelve-point harmonic campaign under
the unchanged contract
[WP13-02C-HARMONIC-MIXED-001](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02c_harmonic_contract.json).
The campaign was run after the C2 harness freeze and produced a separate
[manifest](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02c3_harmonic_final/manifest.json)
and NPZ archive.

All declared numerical gates pass. The dense complex K/M/C reference is the
acceptance oracle. The first-mode participation is only
4.470077849416487e-7, so the result does not support a first-mode-dominated
claim. The reported peak is therefore limited to the frozen frequency-grid
FRF peak.

Interface states are collected independently from family-local element
incidences for TET4/WEDGE6 and WEDGE6/HEX8. Replay comparisons cover complex
fields, modal coordinates, interface fields, work/energy and status. All nine
failure-contract cases pass strict type/message/path matching.

The original C campaign, its Owner rejection and the C2 remediation record
remain unchanged. No 0.2.7 evidence, formulation, numerical source, contract,
gate or maturity record was modified.
