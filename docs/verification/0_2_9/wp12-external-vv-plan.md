# WP12 external V&V — prospective plan

## Bounded claim

This campaign proposes a scope-specific external correlation for the four
accepted WP11-R2 homogeneous, one-element, small-strain linear-static cases:
TET4, HEX8, TET10 and HEX20. It reuses the accepted WP11 M1 inputs read-only
and runs each case once in a fresh Code_Aster 18.1.0 container process. It
does not rerun QF M1/M2/M3.

The proposed candidate allocation is one WP12 point per element-family
correlation (maximum 4/4), subject to Owner review. It is not an official
sub-score frozen by the roadmap and does not imply whole-solver or whole-WP
external validation.

## Exact model transfer

- Geometry, node coordinates, element connectivity, material (`E=210e9`,
  `nu=0.30`), fixed DOFs, and nodal load vector are taken from the frozen WP11
  family model and its accepted M1 evidence.
- `TET4`/`TET10` retain the canonical unit tetrahedron. The `x=1` load set is
  the single corner node for these tetrahedral cases; it is not described as a
  face traction.
- `HEX8`/`HEX20` retain the canonical unit cube. The load is the exact frozen
  `FZ=-1000/n` nodal vector on all nodes with `x=1`.
- The `x=0` node set is fully fixed in `DX/DY/DZ` for all four families.
- Code_Aster uses `MODELISATION='3D'` with the same geometric order. HEX20
  nodes are explicitly reordered to the Code_Aster ASTER-mail convention.
- No stress-field or cross-family equivalence claim is included.

## Frozen comparison gates

The contract freezes before external execution:

- full displacement vector relative L2 and L-infinity differences;
- full support-reaction vector relative L2 and L-infinity differences;
- linear strain energy versus external work `0.5 * f dot u`;
- force and reference-configuration moment equilibrium in both solvers;
- maximum absolute displacement on fixed nodes;
- all-value finiteness, exact family/DOF/model fingerprint, zero fallback,
  immutable Code_Aster image digest, execution SHA and artifact hashes.

Proposed numeric limits are fixed in the contract before runs. A failed case
remains failed; no threshold or element/load definition is retuned afterward.
Families are independent: a failure in one does not cancel the other three.

## Execution order and controls

Sequential order is TET4, HEX8, TET10, HEX20, one CPU thread per fresh
container. No concurrent solve, retry, or solver fallback is allowed. Before
execution, the runner rehashes the accepted WP11 manifest and each M1 input,
reconstructs only the frozen model/linear-system inputs, and verifies exact
load/fixed/stiffness fingerprints. It then refuses any pre-existing output
directory.

For each family it preserves the generated ASTER mesh, `.comm` command file,
`.export` descriptor, QF M1 input snapshot, Code_Aster raw JSON, stdout/stderr,
process metadata, immediate-flush progress/telemetry and SHA-256 manifest. The
execution uses the image's official `run_aster` entrypoint, a fresh container,
`--no-mpi`, one Docker CPU and the frozen one-CPU export settings. A separate
fail-closed auditor does not import the WP12 runner or QF solver; it checks the
frozen deck against contract data and recomputes every metric from the raw
arrays.

The runner invocation was reviewed against the pinned image before freezing:
`run_aster --version` reports Code_Aster 18.1.0 and the image's `run_aster`
wrapper initializes the required profile. A plain system `python3` in this
image cannot import `code_aster`; therefore direct `python3 case.comm` is not
an acceptable solver invocation and is explicitly excluded.

## Plan audit / limitations

The plan is internally consistent with the WP12 gate-matrix wording “external
oracle/correlation records; scope-specific only” and directly addresses the
external-correlation limitation retained in WP11. The evidence can support
only this exact static elastic matrix. It does not discharge deferred external
correlation claims for WP04/WP05 geometric mechanics, WP06 arc length,
WP07/WP08 contact/friction, WP09/WP10 J2 or coupled nonlinear response, nor
does it establish mesh convergence, dynamics, MPI scalability, stress-field
equivalence, or general solver equivalence.

The independent solver is Code_Aster, not the WP11 NumPy observable
recomputation. The QF side remains the already accepted WP11 M1 result; no
new QF production solve is performed.

## Formal boundary

WP12 remains `0/4` official until the Owner reviews the frozen contract,
source provenance, raw external evidence, checker output and limitations.
No merge, governing push, ledger update or self-award of points is part of
this campaign.
