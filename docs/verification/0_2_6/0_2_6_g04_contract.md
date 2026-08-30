# 0.2.6 G04 controlled contract

## Status and boundary

G04 is the official `Linear / element robustness` gate. This document and the
machine-readable files beside it define a controlled execution contract; they
do not close G04, change the global gate manifest, or promote a capability.

The base claim is limited to `linear_static`, small-displacement, linear-elastic
routes already present in the capability registry. Unsupported combinations are
expected to be rejected. Modal, dynamic/Newmark, harmonic, buckling, J2,
geometric nonlinear/TL, arc-length, contact, RBE extensions, and any new
formulation are outside this contract.

The source of truth is:

- contract: `qualification/0_2_6/g04_requirements.json`;
- case mapping: `qualification/0_2_6/g04_case_mapping.json`;
- capability maturity: `qualification/capability_registry.json`;
- case execution state: `qualification/0_2_6/case_registry.json`.

## Element and route matrix

| Element | Material route | Linear static loads | Boundary conditions | Expected V&V | Known boundary |
|---|---|---|---|---|---|
| BEAM2 | `beam_isotropic` | nodal, line load | fixed/prescribed DOFs | L2 | variable sections and curved beams excluded |
| MITC3 / MITC3+ alias | `shell_isotropic` | nodal | fixed/prescribed DOFs | L2 | laminate route deferred from base claim |
| MITC4 | `shell_isotropic` | nodal, pressure, surface/edge traction | fixed/prescribed DOFs | L2 | laminate route deferred from base claim |
| TET4 | `isotropic_3d` | nodal, gravity, body force, pressure, surface traction | fixed/prescribed DOFs | L3 | coarse flexure and near-incompressibility bounded by existing limits |
| TET10 | `isotropic_3d` | nodal, gravity, body force, pressure, surface traction | fixed/prescribed DOFs | L3 | positivity is sampled, not globally proven |
| HEX8 | `isotropic_3d` | nodal, gravity, body force, pressure, surface traction | fixed/prescribed DOFs | L3 | finite-kinematic and J2 routes excluded |
| HEX20 | `isotropic_3d` | nodal, gravity, body force, pressure, surface traction | fixed/prescribed DOFs | L3 | finite-kinematic and J2 routes excluded |
| DISCRETE | `discrete_linear` | nodal | fixed/prescribed DOFs | L2 | the existing 0.2.6 record is planned/mixed and is not a ready base case |

MITC3+ is an alias used in documentation for the registered MITC3 capability;
it is not a new registry element or an invented combination.

## Requirements and evidence levels

| ID | Requirement | Evidence expected |
|---|---|---|
| G04-LIN-001 | route and element dispatch | supported declarations pass; unsupported combinations reject deterministically |
| G04-LIN-002 | patch/constant strain and rigid-body behaviour | analytical patch or invariant where mathematically applicable |
| G04-LIN-003 | load diversity and equilibrium | compatible distributed loads, reaction resultant/moment, free residual |
| G04-LIN-004 | material and orientation boundaries | isotropic routes; orientation only where formulation supports it; laminate deferred |
| G04-LIN-005 | mesh refinement, quality and distortion | coarse/medium/fine continuum sequences and recorded quality metrics |
| G04-LIN-006 | invalid inputs and failure modes | safe rejection of degenerate/inverted mesh and invalid data |
| G04-LIN-007 | compatible external correlation | pinned tool/version and identical model data; unavailable tools are skipped, never pass |
| G04-LIN-008 | provenance and anti-forgetting | SHA, clean state, environment, case IDs, digests, registry and requirement links |

The mapping currently contains 72 LIN/SHL registry records: 65 `READY`, 4
`PLANNED`, and 3 `NOT_APPLICABLE`. READY records originating in G05 or G06
are explicitly reuse candidates and cannot be counted twice for a future G04
closeout. The three planned SHL records declare `mixed` and have no executable
input model, so they remain traceability records rather than G04 base claims.

## Proposed minimums and policies

The proposed per-element minimums are deliberately marked
`PROPOSED_OWNER_REVIEW` in the JSON contract. They are not approved thresholds:

| Element | Proposed unique cases | Required route samples |
|---|---:|---|
| BEAM2 | 2 | nodal, line load |
| MITC3 | 2 | membrane, bending or shear |
| MITC4 | 3 | membrane, bending, pressure or edge traction |
| TET4/TET10/HEX8/HEX20 | 3 each | traction/compression, distributed load, refinement |
| DISCRETE | 1 | nodal static spring or mass |

Existing policies remain authoritative: exact invariants, the existing
deterministic floating-point foundation policy, case-defined analytical error,
and `SKIPPED_EXTERNAL_UNAVAILABLE` for unavailable external tools. The contract
also records three proposed owner-review policies for free residual, force
balance, and final adjacent-mesh response change. No tolerance is weakened by
this contract.

## Execution and approval

Execution must emit per-case inputs, source SHA, clean-worktree state, solver
settings, results, audit checks, oracle provenance, tolerance provenance, and an
artifact manifest. Registry and anti-forgetting checks are prerequisites. An
Owner decision is required before any official G04 closeout; the global G04
manifest remains unchanged by this preparation.
