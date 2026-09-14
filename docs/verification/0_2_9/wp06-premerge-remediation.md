# WP06 pre-merge remediation preparation

Status: `PREPARED_FOR_OWNER_AUTHORIZED_REQUALIFICATION`

This record adds tooling after the immutable WP06-D Phase-1 failure and D1
forensic diagnosis. It does not alter either record:

- `qualification/0_2_9/wp06d_phase1_structural_raw.json`
- `qualification/0_2_9/wp06d1/wp06d1_m2_failure_diagnostic.json`

The original failure remains immutable: M1 passed, M2 failed the frozen
limit-point gate and moment-equilibrium gate, and M3 was not run.

## Monitor correction

The frozen R1 monitor is the downward mean crown displacement
`q = -mean(UZ at nodes 2, 3, 4)`. The new `mean_crown_uz` helper uses the
declared node tuple `(2, 3, 4)` in deterministic order and has no node-4-only
fallback. A future runner must provide the accepted displacement vector and
the model DOF map; missing or non-finite values fail closed.

The historical Phase-1 record still contains the former node-4 control value,
as reported by D1. It is not rewritten as corrected evidence.

## Checkpoint reader and accepted-state archive

`scripts/wp06_premerge_tools.py` provides a read-only adapter for the current
NPZ V2 reader and legacy V1-compatible stores. It passes model/DOF validation
when supported, retries only an explicitly detected legacy keyword mismatch,
then validates schema, finite displacement/load factor, metadata and digest.
Reading returns detached data and does not mutate a solver/model object.

Each future accepted state can be archived with step, lambda, lossless
displacement, corrected monitor, state digest and explicit fields for reaction,
moment, residual, arc-length constraint, Newton counts, retries and terminal
classification. Unavailable fields are represented as `null` with a reason;
they are never fabricated as zero.

## Independent equilibrium reconstruction

`reconstruct_balance` performs vector force and global-origin moment
accounting from internal and external nodal vectors. It independently forms
the constrained reaction contribution and reports residuals and frozen
threshold decisions. It does not consume the original summary equilibrium
fields and does not implement an arc-length algorithm.

## Future requalification guard

`scripts/prepare_wp06d_requalification.py` exposes a plan only. It requires
explicit Owner authorization before any future execution path and binds M3
behind successful M1 and M2 gates. No structural or extended-horizon run was
performed in this remediation.

## WP04 fingerprint drift

The inherited WP04 fingerprint test was coupled to current checkout bytes and
therefore failed after legitimate governing-branch integration changed files
and regenerated evidence. The test now validates the historical source blob
IDs and historical artifact presence at the recorded audit revision, while
the active current evidence assertions remain unchanged. This is
`INHERITED_TEST_EXPECTATION_DRIFT`, not a production mechanics correction.

## Governance

Physics, thresholds, solver mechanics, Newton policy, and the official WP06
status are unchanged. This preparation awards no points and still requires
CPU availability plus explicit Owner authorization for requalification.
