# WP11 bounded multi-family extension plan

## Purpose

WP11-R2 extends the existing bounded PETSc/MPI static smoke qualification from
the historical TET4 route to the standard solid families already implemented
by the solver: HEX8, TET10 and HEX20. The historical TET4 R1 evidence remains
immutable and is not overwritten.

This is a backend and element-kernel compatibility qualification. It is not a
mesh-convergence study, a scalability benchmark, or a claim that the four
families produce equivalent results. TET4/TET10 use the canonical unit
tetrahedron and HEX8/HEX20 use the canonical unit cube, so cross-family
observable comparison is explicitly out of scope.

## Family-by-family plan

| Family | Role | Canonical case | Target DOFs | Qualification gates |
|---|---|---|---:|---|
| TET4 | historical control and R2 adapter check | one unit tetrahedron, static UZ load | 12 | M1/M2/M3, without rewriting R1 |
| HEX8 | additive family extension | one unit cube, static UZ load | 24 | M1/M2/M3 |
| TET10 | additive high-order tetrahedron extension | one unit tetrahedron with quadratic edge nodes | 30 | M1/M2/M3 |
| HEX20 | additive high-order hexahedron extension | one unit cube with quadratic edge nodes | 60 | M1/M2/M3 |

For every family:

1. M1 runs the standard element kernels with the serial SciPy reference path.
2. M2 runs the same frozen case through PETSc/MPI with two ranks in the
   pinned container. The implementation uses root-side bounded assembly and
   replicated input; it makes no distributed-scaling claim.
3. M3 is a fresh-process replay with the same source, contract, container and
   rank count. It must reproduce the recorded fingerprints and observables.
4. The independent check is a file-backed NumPy recomputation of observables
   from the saved displacement and result files. It is not an independent
   global FEM/Newton solve and must not import production contact or solver
   routines.

## Gates and limitations

- all stored values must be finite;
- free residual relative L2 must be at most `1e-10`;
- M1/M2 displacement L2 and infinity-norm relative differences must be at
  most `1e-10`;
- M3 fingerprints and declared observables must match exactly at the stored
  float64 representation;
- no fallback is permitted;
- the contract, source SHA, runner SHA, container digest, MPI rank count and
  artifact hashes must be recorded for every case.

The extension remains bounded to linear static, homogeneous one-element
cases, serial/direct standard assembly, the pinned PETSc/MPI image, and four
element families. It does not qualify dynamics, contact/friction, finite
sliding, large-scale partitioned input, strong/weak scaling, or correlation
against Code_Aster or another external FEM solver.

## Owner review package

The final package must contain one raw result set and one independent check for
each family and gate, a consolidated manifest, a fail-closed checker report,
targeted test results, and a per-family limitation table. The package may be a
candidate for the existing WP11 score only after explicit Owner review; no
official points are awarded automatically by this extension.
