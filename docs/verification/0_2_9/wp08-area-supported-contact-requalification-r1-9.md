# WP08 area-supported contact — prospective R1.9 diagnostic

## Purpose and status

R1.9 is a new prospective diagnostic revision following R1.8. It addresses
the R1.8 M3/slip failure without changing the benchmark or its acceptance
thresholds. The campaign is experimental evidence only: it does not establish
formal WP08 qualification, award points, claim an independent global FEM
reference, or classify mesh convergence.

The Owner authorized freezing the R1.9 runner and executing one serial M1/M2/M3
campaign. The authorization does not permit retries, parameter changes,
threshold changes, or downstream execution after a failed gate.

## R1.8 failure and R1.9 correction

R1.8 passed M1 and M2 for both `stick_target` and `slip_target`, and M3 for
`stick_target`. M3 `slip_target` failed closed at load step 8 after seven
accepted steps. The direct active-slip root had already exceeded the frozen
`1e-9` scaled residual criterion. The coupled projection then proposed and
correctly added five omitted normal contacts, but its aggregate root stopping
measure hid a local slip-cone alignment residual at contact 1:

- observed local force residual: `2.0834372780912926e-8 N`;
- admissibility limit: `1.1809752086004155e-8 N`;
- normalized local residual: approximately `1.764e-9`, above the unchanged
  `1e-9` limit.

The coupled solver accepted the aggregate root result, while the final
per-contact physical validator correctly rejected it. R1.9 changes that
internal inconsistency: convergence and fallback refinement are governed by
the maximum per-contact normalized residual, and the existing semismooth then
globalized refinement paths continue from the latest candidate until that
same frozen local criterion passes or the solver fails closed. The physical
zero set, admissibility test, `1e-9` tolerance, iteration limit, backend, and
fallback policy are not weakened or enlarged.

## Frozen benchmark — unchanged from R1.8

- Straight TET4 prism: `Lx=2.0 m`, `Ly=1.0 m`, `Lz=0.5 m`.
- Isotropic 3-D linear elasticity: `E=1.0e6 Pa`, `nu=0.30`.
- All translations fixed on the body face at `x=0`; four rigid-master metadata
  nodes fixed in all translations; no body slave node fixed at `x=2`.
- Fixed-initial-search node-to-triangle contact; initial gap `5.0e-4 m`,
  master plane `x=2.0005 m`, normal `[-1,0,0]`, friction `mu=0.30`.
- Tangential support is reference T3 tributary area with `K_i=kappa*A_i`, no
  redistribution, and frozen `kappa=2,666,700 N/m^3`. This is a benchmark
  calibration, not a measured material property.
- Normal resultant `1000 N` in `+x`; separate tangential resultants in `+y`
  for stick-target and slip-target cases. The eight frozen load steps and
  M1/M2/M3 mesh definitions are inherited unchanged from the R1.8 benchmark
  contract and are hash-bound in the R1.9 contract.
- One process at a time. Run order is M1 stick, M1 slip, M2 stick, M2 slip,
  M3 stick, M3 slip. M2 requires both M1 gates; M3 requires both M2 gates.
  Stop downstream cases after any failure; never rerun a started solve.

## Unchanged controls

Geometry, mesh hierarchy, material, boundary conditions, loads and load steps,
contact area weights, `kappa`, friction coefficient, linear solver backend,
fallback policy, contact-count guard, 25-iteration active-set bound,
convergence tolerances, diagnostic gates, and mesh-refinement thresholds are
unchanged. The only intended R1.9 production-mechanics change is the
per-contact normalized residual criterion and residual-driven refinement in
the coupled contact projection/root path.

## Evidence and interpretation

The run produces separate per-case process manifests, logs, telemetry, JSON
results, and raw arrays, all bound to the frozen source inventory and contract.
M1/M2/M3 results and any failure are retained exactly as observed. Refinement
metrics are descriptive because no mesh-convergence threshold is frozen.
Independent observable recomputation, if performed, is not an independent
global FEM/Newton solve. Replay, if performed, is not implied by completing
this diagnostic campaign.

Expected terminal classifications are technical diagnostic outcomes only:
`EXPERIMENTAL_EXECUTION_PASS` if every predeclared case gate passes,
`REFINEMENT_DIAGNOSTIC_FAIL` if the descriptive mesh comparison is concerning,
and `NOT_FORMALLY_QUALIFIED` in either case. A numerical or provenance failure
must remain `FAIL_CLOSED`; no Owner score is assigned by the runner.
