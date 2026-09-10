---
doc_id: DOC-028-WP13-02B2-EVIDENCE-CLOSURE-001
revision: 0.1
status: owner_review_required
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP13-02B2 — Newmark evidence closure

This record closes the missing machine-readable evidence for the frozen
WP13-02B Newmark campaign. It does not promote the candidate claim and does
not modify the original contract, the WP13-02B result, the formulation, or
any 0.2.7 evidence.

## Frozen contract and interpretation

The source contract is
[`WP13-02A-NEWMARK-MIXED-CONTRACT-001`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02a_newmark_contract.json)
with Git blob SHA
`7e5af8374e33e8d45a61d4a60b01127802bfca64`. The closure runner verified that
the blob is unchanged.

The original contract declares `T1/20`, `T1/40`, `T1/80` and `T1/160`, but it
does not explicitly state whether the displacement RMS, phase, refinement and
replay gates apply at every level or only at the fine levels. It also does not
name a replay level. Therefore this record marks the interpretation as
`CONTRACT_AMBIGUITY`; it records, but does not insert, the fine-level
interpretation used by the earlier WP13-02B evidence.

| Evidence or gate | Recorded interpretation |
| --- | --- |
| All four time-step runs | Executed and archived |
| Frequency, dynamic residual, energy, continuity and force transfer | Measured at every declared level where the metric is defined |
| Displacement RMS, phase and refinement | Fine-level result is recorded; coarse applicability remains Owner-reviewable |
| Modal `q`, velocity and acceleration controls | Full arrays and errors archived; `v/a` are characterization because no separate contract gates exist |
| Replay | Two complete `T1/160` replays are archived; the original contract does not name the level |
| Interface energy | Explicit diagnostic measurement; no separate numeric threshold is added retroactively |

The coarse levels are not relabeled as passing oracle-gate levels. The
T1/20 and T1/40 data remain characterization data, while the fine-level
results are reported without changing their predeclared numeric values.

## Raw archive

The machine-readable manifest is
[`manifest.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02b2_raw/manifest.json),
and the complete float64 archive is
[`wp13_02b2_raw_arrays.npz`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02b2_raw/wp13_02b2_raw_arrays.npz).
The NPZ contains the time vector, displacement, velocity, acceleration,
reaction and residual histories for every declared level, plus modal
coordinates and analytical controls, probe records, interface power records,
and both complete replay records. The manifest contains the array shapes and
SHA-256 digest for every archived array and the archive itself.

The monitored probe is node 13, `UZ`; the modal controls are
`q = phi_unit.T @ M @ u`, `qv = phi_unit.T @ M @ v` and
`qa = phi_unit.T @ M @ a`, using the generalized-mass-normalized independent
reference mode.

The relative modal errors are:

| Level | q error | v error | a error |
| --- | ---: | ---: | ---: |
| T1/20 | 1.1660793079e-1 | 1.1910981196e-1 | 1.1660793079e-1 |
| T1/40 | 2.9549933179e-2 | 2.9991747120e-2 | 2.9549933179e-2 |
| T1/80 | 7.4228755026e-3 | 7.4928691458e-3 | 7.4228755027e-3 |
| T1/160 | 1.8593674730e-3 | 1.8707012222e-3 | 1.8593674730e-3 |

The q control follows the declared displacement-scale gate at the fine
levels; the velocity and acceleration columns are retained as explicit
controls, not silently assigned a new gate.

## Interface-energy diagnostic

For each interface, the archived power traces are formed from the local
element `K*u + M*a` contributions on the shared interface DOFs and integrated
with the recorded time vector. This is a diagnostic energy-transfer
decomposition, distinct from shared-DOF identity and from the original force
transfer gate.

At T1/160:

- TET4/WEDGE6 transfer: `+4.8023619574e-7 J` and
  `-4.8023619338e-7 J`; absolute closure error
  `2.3816808870e-15 J`, relative closure `2.4796974009e-9`.
- WEDGE6/HEX8 transfer: `+4.2232423892e-7 J` and
  `-4.2232424016e-7 J`; absolute closure error
  `1.2318987313e-15 J`, relative closure `1.4584750483e-9`.

These values are archived as `PASS_WITH_LIMITATIONS` diagnostics: the
original contract has no separately predeclared interface-energy threshold,
so no new threshold is applied after observation.

## Replay and failure contract

Two complete T1/160 replays have identical convergence status and iterations.
The archived displacement, velocity, acceleration, reaction, residual and
energy arrays have zero relative differences and identical SHA-256 digests.

The targeted failure cases reject invalid time step, missing/invalid mass,
unsupported damping, unsupported time load, invalid initial conditions,
invalid mixed connectivity and unsupported dynamic family. No silent family
fallback was observed.

## Status

`WP13-02B2 = CONTRACT_AMBIGUITY_BLOCKING`.

The raw evidence closure is complete, but a new Owner Gate must decide the
applicability of the frozen contract's coarse/fine gates and the replay-level
interpretation. This note is reviewable metadata only; the original contract
and the historical WP13-02B rejection remain unchanged.
