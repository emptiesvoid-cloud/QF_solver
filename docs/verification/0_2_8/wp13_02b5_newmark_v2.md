---
doc_id: DOC-028-WP13-02B5-NEWMARK-V2-001
revision: 0.1
status: owner_review_required
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP13-02B5 — Newmark V2 campaign

WP13-02B5 executes the pre-declared contract
[`WP13-02B4-NEWMARK-MIXED-V2-001`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02b4_newmark_v2_contract.json)
from commit `ccab01854f42d56aa6dc7202d9c5dd76dd9b2dde`. The contract, gates,
benchmark, formulation and prior WP13-02B/02B2/02B3 records are unchanged.

## Scope and archive

The run uses a connected 48-DOF model with 3 TET4, 2 WEDGE6 and 1 HEX8, one
connected component, consistent mass, zero Rayleigh damping and a first-mode
initial condition. The full machine-readable result is recorded in
[`manifest.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02b5_v2/manifest.json)
and the float64 archive in
[`wp13_02b5_arrays.npz`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02b5_v2/wp13_02b5_arrays.npz).
The archive contains all four time-step histories, oracle controls, interface
records and two complete T1/160 replays; the manifest records shapes and
SHA-256 digests for all 166 arrays.

The independent dense K/M reference gives a first frequency of
`97.80394654204198 Hz`; the production modal cross-check is
`97.80394654200138 Hz`, with relative error `4.151203847779255e-13`.

## Results

T1/20 and T1/40 are retained as `CHARACTERIZATION_ONLY`; T1/80 and T1/160
are the declared `ACCEPTANCE` levels. All five convergence sequences are
strictly decreasing and have observed orders within the frozen `1.5 <= p <=
2.5` gate. The acceptance gates pass at both fine levels, including full
displacement/velocity/acceleration controls, residual, energy, continuity,
force transfer and interface-energy metrics. The two T1/160 replays pass
numerical determinism with identical status/iterations and zero recorded
relative differences across the archived fields.

## Failure-contract blocker

The numerical campaign and its acceptance gates pass, but the required
failure contract does not. The malformed `initial_conditions` non-list case
was **not rejected** by the runtime path. The other invalid-dt, missing-mass,
damping, time-load, unknown-DOF, mixed-interface and unsupported-family cases
are recorded with explicit rejection or route refusal, and no silent fallback
was observed.

Therefore:

`WP13-02B5 = FAIL_FAILURE_CONTRACT`

There is no claim candidate and no automatic promotion. A separate scoped
remediation and rerun under this unchanged contract are required before an
Owner Gate can review a candidate. No 0.2.7 evidence was modified.
