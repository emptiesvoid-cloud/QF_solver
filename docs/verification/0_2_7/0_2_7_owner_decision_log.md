---
doc_id: DOC-027-013
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Owner Decision Log

This log preserves the foundation decisions and records the Terra-authorized
WP07 technical implementation separately from public qualification.

| Decision ID | Topic | Proposed state | Decision | Evidence/SHA | Date |
| --- | --- | --- | --- | --- | --- |
| 027-OD-001 | WEDGE6 formulation and scope | `PROPOSED_OWNER_REVIEW` | pending | WP05/WP06/WP07 | - |
| 027-OD-002 | mesh-quality policies | `PROPOSED_OWNER_REVIEW` | pending | WP06 | - |
| 027-OD-003 | external C3D6/PENTA6 comparability | `PROPOSED_OWNER_REVIEW` | pending | WP05 | - |
| 027-OD-004 | J2 gap-closure policies | `PROPOSED_OWNER_REVIEW` | pending | WP11 | - |
| 027-OD-005 | 1M-DOF verdict and public boundary | `PROPOSED_OWNER_REVIEW` | pending | WP12 | - |
| 027-OD-006 | stretch/research selection | `PROPOSED_OWNER_REVIEW` | pending | WP13 | - |
| 027-OD-007 | final release scope | `PROPOSED_OWNER_REVIEW` | pending | WP14 | - |
| 027-OD-008 | WEDGE6 elemental kernel | `TERRA_GO` | `PASS_TECHNICAL_EXPERIMENTAL_ONLY` | T1-R4, WP07 evidence | 2026-08-31 |
| 027-OD-009 | WEDGE6 static vertical slice | `WP08_REVIEWED` | `PASS_TECHNICAL_EXPERIMENTAL_ONLY` | WP08 state/evidence, 8040909d6d65f740e1daf858ce572d250a87b39a | 2026-08-31 |

WP01 is a release-engineering foundation control rather than a numerical Owner
qualification decision. Its status is `PASS` because the SHA roles, actual
0.2.6 publication state, artifact classes and tag/version guard are recorded in
the WP01 machine-readable records. This does not approve any 0.2.7 capability.

WP02 is a registry-engineering foundation control rather than a new capability
qualification decision. Its status is `PASS` because the v2 source of truth
preserves all 33 public legacy identifiers, exposes 44 combination records,
keeps historical statuses out of the active vocabulary, and passes deterministic
schema, migration and generated-view checks. Inherited `QUALIFIED_BOUNDED`
states remain bounded 0.2.6 scope; this work package introduces no new evidence
or promotion.

WP03 is a compatibility-engineering foundation control rather than a new
capability qualification decision. Its descriptors describe technical routing
for existing element families, while the v2 registry remains the source of
maturity. The preflight is fail-closed and reports supported, experimental,
non-qualified and unsupported routes distinctly. Targeted descriptor, workflow
and analysis tests pass; no numerical source or Owner maturity decision was
changed.

WP05 is an external-oracle engineering control rather than a WEDGE6
qualification decision. The pinned Docker runs validated one minimal CalculiX
C3D6 deck and one Code_Aster PENTA6 deck locally. Both oracle routes are
`AVAILABLE_LOCAL_ONLY`; no QF WEDGE6 implementation, comparison verdict or
public capability was created. The eight future benchmarks remain `PLANNED`,
and the comparability tolerance remains `OWNER_REVIEW_REQUIRED`.

The WP05 preflight is `PASS` with the local-only limitation recorded in the
machine-readable contract and review pack. This does not authorize WP07 or
change any existing 0.2.6 decision.

WP04 is an additive V&V-engineering control rather than a capability
qualification decision. Its declarative case/oracle schema, runner verdicts,
canonical evidence serialization and replay mismatch checks pass on three
representative fixtures. Historical V&V runners remain supported; no numerical
source or maturity decision was changed.

WP06 is an additive mesh-quality control rather than a numerical capability
qualification. The common contract covers TET4, TET10, HEX8 and HEX20 with
deterministic `VALID`, `VALID_WITH_WARNING` and `INVALID` classifications,
and invalid geometry is surfaced by preflight as `MESH_GEOMETRY_INVALID`. No
universal aspect-ratio or conditioning threshold was approved; inherited
family diagnostics retain their legacy provenance. Rigid-transform,
dimensionless-scale, inversion, duplicate-node and serialization checks pass.
The WEDGE6 quality contract is prepared only as an inactive future schema and
`WEDGE6_IMPLEMENTED` remains `NO`. This status records engineering evidence
and does not promote any capability.

An entry may be changed to an approved state only with a decision owner, exact
evidence SHA, scope, limitations and date. No decision here reopens G07 or
changes any 0.2.6 maturity classification.

T1-R is a remediation checkpoint, not an Owner qualification decision. It
records the inactive WEDGE6 formulation, quadrature candidate and richer
verification reference, asymmetric node/face fixture, prism Jacobian validity
controls, stiffness/mass V&V obligations and external primary observables.
Its targeted tests pass and no WEDGE6 capability or kernel is exposed. The
checkpoint is ready for Terra/Owner re-review; WP07 remains `NOT_STARTED` and
kernel authorization remains `OWNER_REVIEW_REQUIRED`.

T1-R3 closes the two review findings that remained open. The inactive quality
contract now specifies a scale-aware certified minimum: at fixed triangular
coordinates `det(J)` is quadratic in `t`, so endpoints and every interior
stationary point are checked at each triangular vertex. Quadrature, face and
interior samples are diagnostics only. The Terra adversarial prism is rejected
by this certificate, with no automatic repair and no WEDGE6 kernel exposure.

The WEDGE6 external contract has one unique primary-observable declaration,
strict duplicate-key JSON loading, an affine same-mesh `1e-6` candidate marked
`OWNER_REVIEW_REQUIRED`, and mandatory case-specific Owner approval for
non-affine, distorted or refinement cases. Post-observation tolerance retuning
is forbidden. T1-R3 is ready for Terra re-review; WP07 remains `NOT_STARTED`
and kernel authorization remains `OWNER_REVIEW_REQUIRED`.

## WP07 technical implementation decision

Terra High's T1-R4 review authorized implementation after all six original
pre-WP07 blockers were closed. WP07 is `PASS` for the six-node, 18-DOF
small-strain homogeneous-isotropic elastic elemental kernel and its targeted
V&V. Evidence covers shape identities, affine constant strain, exact Jacobian
certificate, stiffness symmetry, rank 12 with six rigid-body modes, prescribed
load-state tests, distorted geometry, energy and production/reference
quadrature replay.

This is not a public qualification. The registry maturity for
`COMB-WEDGE6-linear_static` is `EXPERIMENTAL`, and preflight returns
`EXPERIMENTAL_ROUTE`. Gmsh import, face loads, user-level assembly and
reactions, modal/dynamic routes, nonlinear materials, contact and external
correlation were deferred to WP08 and later gates. Existing TET/HEX
formulations and their evidence are unchanged.

## WP08 static vertical-slice decision

WP08 is `PASS` for the bounded six-node Gmsh Prism 6 static workflow. The
15-case controlled evidence contains 14 `PASS` results and one
`EXPECTED_FAILURE_PASS` for fail-closed rejection of inverted geometry, with
no unexpected failures. It covers canonical TRI3/QUAD4 face mapping, nodal
and distributed loads, sparse static assembly, reactions, force and moment
equilibrium, constraints and displacement/strain/stress/energy recovery.

This decision does not promote WEDGE6: `COMB-WEDGE6-linear_static` remains
`EXPERIMENTAL` and public qualification is `DEFERRED`. Modal/Newmark/harmonic,
nonlinear, J2, TL, contact, robustness and external-correlation claims remain
outside this gate and require their own evidence.

## WP09 robustness and external V&V decision

WP09 is `PASS_WITH_LIMITATIONS` for the declared WEDGE6 static robustness
campaign. The controlled evidence contains 22 cases: 18 internal `PASS`
results and four `EXPECTED_FAILURE_PASS` results for inverted geometry, wrong
node ordering, malformed Gmsh input and singular boundary conditions. Aspect,
skew, near-degenerate, rigid-transform, scale-invariance, multi-element,
refinement and deterministic replay checks are recorded without changing the
kernel or existing element numerics.

The external results remain explicitly non-qualifying. CalculiX C3D6 completed
the affine deck locally, but its two-point integration route is not
formulation-compatible with QF WEDGE6 production `TRI3_X_GAUSS2` integration;
the displacement and energy differences are retained as diagnostics, not as a
failure or a pass. Code_Aster PENTA6 is now executed through the WP09-R
derived headless image: `mpi4py` was present in the pinned image's Spack view
but was not exposed by the stock profile, and `--no-mpi` does not bypass that
import. One affine same-mesh correlation passes for displacement, total
reaction and strain energy under the predeclared `1e-6` candidate, which remains
`OWNER_REVIEW_REQUIRED`. No pressure, refinement or distorted external
correlation is claimed. WEDGE6 remains
`EXPERIMENTAL` and public qualification remains `DEFERRED`; WP10 may proceed
under its separate modal contract.

## WP10 modal evidence decision

WP10 is `PASS_WITH_LIMITATIONS` for independent technical evidence of the
WEDGE6 modal route. The consistent translational mass satisfies symmetry,
positivity, total-mass conservation, density/geometry scaling and distorted-
prism checks. The common modal route records six finite positive modes with
residual and mass-orthogonality checks, deterministic replay, a diagnostic
four-level refinement series and one expected fail-closed zero-density case.
Code_Aster 18.1.0/PENTA6 provides a same-mesh frequency-only bounded
correlation under the predeclared `1e-2` candidate; its tolerance remains
`OWNER_REVIEW_REQUIRED` and no mode-shape MAC is claimed.

This is not a public qualification decision. `COMB-WEDGE6-modal` remains
`EXPERIMENTAL`, public qualification remains `DEFERRED`, static evidence is
not transferred automatically, and no lumped-mass, Newmark, harmonic,
nonlinear, J2, TL or contact WEDGE6 route is included. The decision is tied to
source SHA `7d494eaa638ffa88a04ed3e5c51f6036ad1804a1` and the controlled WP10
records.

## WP12 large-scale readiness checkpoint

WP12 is recorded as `PASS_WITH_LIMITATIONS` for a bounded readiness study of
the existing generated structured TET4 linear-static route. The campaign
completed matrix-free CG through 750141 DOF, recorded a separate 311469-DOF
assembly-only probe, and classified the 1M attempt as `RESOURCE_LIMITED_TIME`.
SciPy CG/direct limits and PETSc/SLEPc unavailability are explicit. The
optimization caches existing grouped connectivity and flattened DOF indices in
the matrix-free operator; targeted numerical equivalence passes and no FEM
formulation changed. This is evidence for `027-OD-005`, not an Owner closeout:
the decision remains `PROPOSED_OWNER_REVIEW`, and no universal 1M claim is
made.
