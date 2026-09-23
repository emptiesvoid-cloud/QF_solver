# WP12 R3 — Expanded external-correlation campaign

## Purpose

The accepted WP12 R2 package correlates four one-element linear-static models
with Code_Aster. R3 prospectively broadens that evidence to 144 same-mesh
comparisons. R2 files and decisions remain unchanged. R3 is supplemental and
does not award or reallocate WP12 points.

## Frozen matrix

| Dimension | Cases |
|---|---:|
| Element families: TET4, HEX8, TET10, HEX20 | 4 |
| Geometries: slender beam, rectangular beam, short block | 3 |
| Meshes: H1 1×1×1, H2 2×1×1, H3 2×2×1 | 3 |
| Distal-face traction vectors: axial X, transverse Y, transverse Z, combined XYZ | 4 |
| **Total** | **144** |

Each case is generated once and supplied to both the QF Solver's existing
SciPy sparse direct linear-static path and a fresh serial Code_Aster 18.1
container. Each run is single-CPU; no cases run in parallel. Geometries are
homogeneous rectangular solids. Material is isotropic linear elastic, `E =
210 GPa`, `nu = 0.3`. All translational DOFs on the `x=0` face are fixed.

The resultant magnitude is 1000 N. It is applied as constant traction on the
complete `x=L` face, integrated to consistent equivalent nodal forces for the
element interpolation. The load vector and first moment are checked before
solving and are identical inputs to both solvers. TET4/TET10 use triangular
surface facets; HEX8/HEX20 use quadrilateral facets.

## Gates

The contract is frozen before any correlation solve. The retained relative
comparison gates are `1e-8` for displacement, reaction, external-work energy,
free residual, and force/moment balance; the absolute maximum fixed
displacement gate is `1e-12`. Any missing, non-finite, or hash-mismatched
evidence fails closed. Thresholds cannot be retuned after results.

## Evidence design

- `scripts/wp12_expanded_models.py` deterministically builds each input mesh
  and consistent traction vector without modifying production source.
- `scripts/run_wp12_expanded_code_aster.py` performs sequential QF and
  Code_Aster runs and records process, container, telemetry, and raw arrays.
- `scripts/audit_wp12_expanded_code_aster.py` independently checks the file
  manifest, parses the Code_Aster mesh and force cards, and recomputes
  comparison and equilibrium metrics using NumPy/SciPy only; it imports no QF
  solver code or campaign runner.
- Large per-case raw output stays in the ignored local directory
  `qualification/0_2_9/wp12_external_vv_r3_2_expanded_raw/`. A versioned sibling
  SHA-256 manifest and concise reports remain in Git.

## Preflight revision history

The first frozen R3 contract is preserved but was rejected by the execution
preflight because it omitted root-level Code_Aster image fields required by
the runner. No structural solve started. R3.1 passed preflight but its first
case exposed missing root-level timeout/memory aliases after 144 QF primary
linear solves and before any Code_Aster process started. Those cases are
preserved as `FAIL_CLOSED`; no correlation is claimed. R3.2 validates all
duplicated runtime fields in preflight and is frozen under new contract and
output paths. Neither earlier contract or evidence is overwritten.

## Scope boundary

This is bounded same-mesh correlation for small-strain, homogeneous,
isotropic, linear-static elasticity and the four named element families. H1,
H2, and H3 are diversity labels in this matrix, not a mesh-convergence claim.
No stress-field equivalence, nonlinear material/geometric behavior, contact,
friction, dynamics, buckling, continuation, MPI/PETSc scaling, or experimental
validation is claimed. Agreement between two FEM implementations is not a
substitute for experimental data. Existing WP12 R2 status and the global
ledger remain unchanged pending any future Owner decision.
