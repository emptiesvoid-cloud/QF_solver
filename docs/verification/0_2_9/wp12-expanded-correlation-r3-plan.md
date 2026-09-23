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
- Large per-case raw output stays in the ignored local directory for the
  active frozen revision. A versioned sibling
  SHA-256 manifest and concise reports remain in Git. R3.2 raw output remains
  separate in its original local archive.

## Preflight revision history

The first frozen R3 contract is preserved but was rejected by the execution
preflight because it omitted root-level Code_Aster image fields required by
the runner. No structural solve started. R3.1 passed preflight but its first
case exposed missing root-level timeout/memory aliases after 144 QF primary
linear solves and before any Code_Aster process started. Those cases are
preserved as `FAIL_CLOSED`; no correlation is claimed. R3.2 validates all
duplicated runtime fields in preflight and is frozen under new contract and
output paths. Neither earlier contract or evidence is overwritten.

## R3.2–R3.4 findings and R3.5 correction

The independent R3.2 audit found 132/144 candidate cases and failed closed on
12 HEX20 H3 cases. These were Code_Aster input/import failures, not numerical
solver divergences. The `.mail` serializer emitted an 81-character HEX20
connectivity record; Code_Aster's official mesh-file specification limits a
line to 80 characters and ignores content after column 80. The final node
identifier was therefore truncated. The R3.2 contract, raw results, manifest,
and audit remain preserved without reinterpretation.

R3.3 then attempted a full prospective run using numeric node identifiers.
Code_Aster rejected the first node token as an invalid identifier before
`MECA_STATIQUE`. Twenty cases recorded exit code 6, one case was interrupted
with the same parser diagnostic, and 123 cases were not started. The complete
partial raw tree is hash-manifested; no R3.3 correlation is claimed.

R3.4 used compact alphabetic names. Code_Aster accepted the mesh but rejected
those labels in `FORCE_NODALE/NOEUD`, where its parser expected the native
`N`-prefixed integer form. The first case stopped before `MECA_STATIQUE`; the
fail-fast runner left the other 143 cases unstarted. This is an input-format
failure, not a numerical disagreement.

R3.5 uses `N1`, `N2`, … for nodes and force-card references, and one-character
alphabetic element IDs (`A`…`Z`, then `AA`…) to preserve the 80-column limit.
Regression tests cover all four H3 element families and stop-on-execution-error
behavior. Before freezing, a four-family Code_Aster H3 diagnostic smoke checks
mesh import, force application, and solve completion; it is not formal
correlation evidence. R3.5 then uses a new contract, output root, and manifest
for a fresh 144-case run. The solver mechanics, mesh topology, loads, material,
boundary conditions, image, and numerical gates are unchanged. R2 and all
failed R3 revisions are preserved and never mixed into R3.5.

## Scope boundary

This is bounded same-mesh correlation for small-strain, homogeneous,
isotropic, linear-static elasticity and the four named element families. H1,
H2, and H3 are diversity labels in this matrix, not a mesh-convergence claim.
No stress-field equivalence, nonlinear material/geometric behavior, contact,
friction, dynamics, buckling, continuation, MPI/PETSc scaling, or experimental
validation is claimed. Agreement between two FEM implementations is not a
substitute for experimental data. Existing WP12 R2 status and the global
ledger remain unchanged pending any future Owner decision.
