---
doc_id: "DOC-MARKDOWN-050C5A69D3C2E886"
revision: "0.1"
status: "controlled_evidence"
applicable_version: "0.2.9"
reviewer: ""
approver: ""
---
# WP08 area-supported contact — prospective R1.8 diagnostic

## Status and purpose

R1.8 is a new, prospective diagnostic revision following the preserved R1.7
campaign. It addresses the R1.7 M3/slip failure in which the coupled
normal–tangential projection produced a negative gap at a contact omitted from
the normal active set. After each coupled projection, R1.8 recomputes the
normal complementarity proposal and deterministically resolves a changed
normal set before accepting the candidate. Repeated sets/cycles and failure to
stabilize remain fail-closed.

This is experimental evidence only. It is not formal WP08 qualification, an
independent global FEM reference, a formal replay, or a mesh-convergence
qualification. No WP08 points are awarded.

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
  no redistribution and frozen `kappa=2,666,700 N/m^3`. This is the selected
  benchmark calibration, not a measured material property.
- Loads: normal resultant `1000 N` in `+x`; tangential resultant in `+y`,
  `150 N` for `stick_target` and `450 N` for `slip_target`. Normal load ramps
  first; tangential load ramps second, over the same eight declared increments.
- Mesh hierarchy: M1=`2x1x1`, M2=`4x2x2`, M3=`8x4x4` parent cells, each
  converted by the frozen benchmark generator to TET4 elements. Geometry,
  element construction, contact patch, loads, and area weights are unchanged.
- Solver settings: direct linear solver route; initial contact search;
  `contact_max_iterations=25`; `contact_friction_tolerance=1e-9`; gap
  tolerance `1e-10 m`; eight predeclared load increments per case.

## R1.8 mechanics change

R1.7 attempted one deterministic coupled seed, but rejected it when the
post-coupling normal complementarity proposal differed from the seed. R1.8
reuses the existing deterministic active-set transition policy to resolve the
proposed normal set and repeats the coupled solve until the set is stable. A
visited-set cycle or exhaustion of the existing 25-iteration limit fails
closed. The exhaustive enumeration cap remains unchanged at eight contacts;
R1.8 does not broaden that exponential search.

No geometry, mesh, material, boundary condition, load, friction coefficient,
surface stiffness density, tolerance, threshold, iteration limit, solver
backend, or fallback policy is changed. The source manifest and execution
bindings identify the exact implementation and targeted tests used.

## Predeclared gates and sequence

For both load cases at each mesh level, require successful process termination,
solver convergence, all eight load increments accepted, finite required
observables, all four slave nodes active at the terminal state, rank-2 active
support, full active tributary area, and the requested terminal tangential
state (`stick` for `stick_target`; `slip` for `slip_target`). A missing field is
not a pass.

Execution is strictly serial:

1. M1 stick, then M1 slip. Proceed only if both pass all M1 gates.
2. M2 stick, then M2 slip. Proceed only if both pass all M2 gates.
3. M3 stick, then M3 slip. Stop on the first failed process or gate.

Refinement deltas are descriptive only. No numerical mesh-convergence
threshold is frozen, so no convergence PASS or FAIL may be inferred from
those deltas. There is one authorized campaign attempt and no rerun or
post-result parameter/threshold adjustment.

## Evidence and limitations

Each case runs in its own recorded child process. Contracts, source manifests,
process logs, progress, JSON results, telemetry, and raw arrays are written
without overwriting an existing campaign directory. R1.6 and R1.7 evidence are
preserved and hash-bound; neither is rewritten or reclassified.

No independent nonlinear/global FEM reference or formal replay is included.
The campaign does not establish general contact robustness, finite sliding,
frictional updated search, mesh convergence, performance, or formal WP08
qualification. Results are diagnostic evidence for Owner review only.
