---
doc_id: "DOC-MARKDOWN-27618503595CF3BB"
revision: "0.1"
status: "controlled_evidence"
applicable_version: "0.2.9"
reviewer: ""
approver: ""
---
# WP08 area-supported contact — prospective R1.7 diagnostic

## Purpose and status

R1.7 is a new, prospective, serial diagnostic campaign for the experimental
area-supported frictional-contact benchmark. It follows the fail-closed R1.6
campaign and does not rewrite or supersede any R1.6 result. The campaign may
run M1, then M2, then M3 only while each preceding case gate passes. A failure
is preserved and stops dependent cases; there are no retries or post-result
parameter changes.

This is not formal WP08 qualification, an independent global FEM reference, a
formal replay, or a mesh-convergence qualification. No WP08 points are awarded
by this run. Any eventual Owner review must assess the complete evidence and
limitations separately.

## Frozen numerical problem

- Body: straight TET4 prism, `Lx=2.0 m`, `Ly=1.0 m`, `Lz=0.5 m`.
- Material: isotropic 3-D linear elasticity, `E=1.0e6 Pa`, `nu=0.30`.
- Boundary conditions: all translations fixed on the body face at `x=0`;
  the four rigid-master metadata nodes are fixed in all translations. No slave
  node on the body face at `x=2` is fixed.
- Contact: existing fixed-initial-search node-to-triangle route; initial gap
  `5.0e-4 m`; master plane at `x=2.0005 m`, normal `[-1,0,0]`; friction
  coefficient `mu=0.30`.
- Tangential support law: reference T3 tributary area, `K_i=kappa*A_i`, with
  no redistribution and frozen `kappa=2,666,700 N/m^3`. This is the already
  selected benchmark calibration, not a measured material property.
- Loads: normal resultant `1000 N` in `+x`; tangential resultant in `+y`,
  `150 N` for `stick_target` and `450 N` for `slip_target`. Normal load ramps
  first; tangential load ramps second, over the same eight declared increments.
- Mesh hierarchy: M1=`2x1x1`, M2=`4x2x2`, M3=`8x4x4` parent cells, each
  converted by the frozen benchmark generator to TET4 elements. Geometry,
  element construction, contact patch, loads, and area weights are unchanged.
- Solver settings: direct linear solver route; initial contact search;
  `contact_max_iterations=25`; `contact_friction_tolerance=1e-9`; gap
  tolerance `1e-10 m`; eight predeclared load increments per case.

The exact executable inputs and their hashes are recorded in the generated
contract and source manifest. The policy digest in that record is contextual
provenance only; this benchmark does not claim enforcement of the governing
nonlinear policy.

## R1.7 implementation change

R1.6 M3/slip failed closed. Its immutable evidence records an active-set/root
failure; the concrete runner guard rejected a large deterministic seed before
trying that single seed candidate. R1.7 changes only that algorithmic path:
the coupled projection may attempt the deterministic seed once, then applies
the unchanged cap before any exponential normal-set enumeration. It does not
raise the cap. Sparse support-local stick assembly and the existing bounded
root/reclassification behavior are also included in the frozen R1.7 source
snapshot.

This revision changes production contact implementation. It does not change
the geometry, mesh hierarchy, material, boundary conditions, loads, friction
coefficient, surface stiffness density, tolerances, iteration limits,
diagnostic gates, solver backend, or fallback policy. The source manifest
binds the exact code and targeted tests used by each execution.

## Predeclared gates and sequence

For both load cases at each mesh level, require successful process termination,
solver convergence, all eight load increments accepted, finite required
observables, all four slave nodes active at the terminal state, rank-2 active
support, full active tributary area, and the requested terminal tangential
state (`stick` for `stick_target`; `slip` for `slip_target`). The runners
record equilibrium, contact state, residuals, telemetry, raw arrays, process
identity, and hashes. A missing field is not a pass.

Execution order is strictly serial:

1. M1 stick, then M1 slip. Proceed only if both pass all declared M1 gates.
2. M2 stick, then M2 slip. Proceed only if both pass all declared M2 gates.
3. M3 stick, then M3 slip. Stop on the first failed process or gate.

Refinement deltas are descriptive only. No numerical mesh-convergence
threshold is frozen in this diagnostic campaign, so no convergence PASS or
FAIL may be inferred from those deltas.

## Evidence, preservation, and limitations

Each case is executed in its own recorded child process. Frozen contracts,
source manifests, process logs, progress, JSON results, telemetry, and raw
arrays are written without overwriting an existing campaign directory. R1.6
and earlier evidence remain separate and immutable. The R1.7 M2/M3 amendment
may be frozen only after both M1 cases pass and the exact M1 evidence hashes
are bound.

No independent nonlinear/global FEM reference or formal replay is included.
The campaign does not establish general contact robustness, finite sliding,
frictional updated search, mesh convergence, performance, or formal WP08
qualification. Results are diagnostic evidence for Owner review only.
