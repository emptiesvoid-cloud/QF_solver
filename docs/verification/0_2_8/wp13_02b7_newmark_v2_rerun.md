---
doc_id: DOC-028-WP13-02B7-NEWMARK-V2-RERUN-001
revision: 0.1
status: owner_review_required
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP13-02B7 — Newmark V2 rerun

WP13-02B7 reruns the exact contract
[`WP13-02B4-NEWMARK-MIXED-V2-001`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02b4_newmark_v2_contract.json)
at `fc6b32c8ea1fff0a98390b7788018b14e2ac4891`, after the focused WP13-02B6
input-validation fix. The contract blob remains
`8b44792466eacaf1f341a7970502e9b48dbed4e1`; no gate, benchmark, oracle or
formulation was changed.

## Campaign evidence

The connected 48-DOF model contains 3 TET4, 2 WEDGE6 and 1 HEX8 with
consistent mass, zero damping and a valid first-mode initial condition. The
four declared levels were executed: T1/20 and T1/40 as characterization, and
T1/80 and T1/160 as acceptance levels. All convergence orders are within
`1.5 <= p <= 2.5`; fine-level accuracy, residual, energy and all interface
gates pass. Interface gates were checked at all four levels.

The independent dense K/M oracle gives `97.80394654204198 Hz`; runtime gives
`97.80394654200138 Hz`, with eigenfrequency error `4.151203847779255e-13`.
Two complete T1/160 replays pass numerical determinism with full archived
array comparisons within `1e-12`.

The complete machine-readable evidence is in
[`manifest.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02b7_v2/manifest.json) and
[`wp13_02b7_arrays.npz`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02b7_v2/wp13_02b7_arrays.npz),
including all 166 float64 arrays, inputs, oracle, interface records, replays
and SHA-256 digests.

## Failure contract and historical record

All seven failure-contract categories now pass. In particular,
non-list `initial_conditions` is rejected explicitly with
`InputValidationError`; no silent fallback is observed.

The prior B5 record remains unchanged and visible as
`FAIL_FAILURE_CONTRACT`. B7 is therefore `PASS_V2_CANDIDATE`, not an
automatic promotion. The bounded claim remains pending the separate Owner
Gate; no 0.2.7 evidence was modified.
