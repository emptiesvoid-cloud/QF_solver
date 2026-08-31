---
doc_id: DOC-027-019
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 WEDGE6 Static Vertical Slice

WP08 validates the first user-facing static path around the WP07 WEDGE6
kernel. The gate is `PASS` for this bounded technical slice; WEDGE6 remains
`EXPERIMENTAL` and no public qualification is granted.

## Controlled scope

The tested route is six-node Gmsh Prism 6 import into the common sparse
linear-static solver, with homogeneous isotropic small-strain material. The
slice covers nodal loads, constant body/gravity loads, pressure on the two
TRI3/three QUAD4 boundary contracts, surface traction, existing constraints,
multi-prism assembly, reactions, force and moment equilibrium, and
displacement, Gauss-point strain/stress and integration-energy results.

The canonical face contract is preserved: two triangular faces and three
quadrilateral faces are mapped through `WEDGE6_FACES`. Invalid geometry is
rejected by the existing fail-closed Jacobian/quality path; no orientation is
repaired silently.

## Evidence

The declarative catalog is
`qualification/0_2_7/vnv_v2/wp08_cases.json`. The replay generated
`qualification/0_2_7/vnv_v2/wp08_evidence.json` from source SHA
`8040909d6d65f740e1daf858ce572d250a87b39a`: 15 cases, 14 `PASS`, one
`EXPECTED_FAILURE_PASS` for the inverted-prism rejection, and zero unexpected
failures. The evidence records source SHA, canonical input/result digests,
observables, predeclared oracle/tolerance, verdict and runtime metadata.

The maintained integration coverage is in
`tests/integration/test_wedge6_static_workflow.py`. It exercises native Gmsh
import, all declared load resultants, a two-prism static patch, prescribed
displacement, result serialization and equilibrium including the moment
closure.

Replay from the repository root with:

```text
PYTHONPATH=src python scripts/run_wp08_wedge6.py
```

## Boundary of the claim

This gate does not qualify WEDGE6 generally. Modal, Newmark, harmonic,
nonlinear, J2, Total-Lagrangian, contact, external-correlation and robustness
claims remain deferred or out of scope. The production route uses the
existing `TRI3_X_GAUSS2` integration defined by WP07; this gate does not add
reduced integration or alter TET/HEX formulations.
