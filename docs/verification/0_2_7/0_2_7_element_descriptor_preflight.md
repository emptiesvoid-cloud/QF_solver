---
doc_id: DOC-027-017
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Element Descriptors and Compatibility Preflight

WP03 installs a technical descriptor layer for the element families already
present in QF Solver and a deterministic compatibility check before assembly
and solve. It adds no element, formulation, material model or qualification.

## Source-of-truth boundary

The descriptor answers **what an element can technically route**: topology,
DOFs, faces, integration family, material/analysis/load categories, mass and
recovery availability, backend restrictions and route restrictions.

`qualification/0_2_7/capability_registry_v2.json` remains the source of truth
for **maturity of a combination**. Descriptor data must not be read as a
qualification claim. `SUPPORTED`, `TESTED`, `VERIFIED` and
`QUALIFIED_BOUNDED` remain distinct registry states.

Descriptors are available for `BEAM2`, `MITC3`, `MITC4`, `TET4`, `TET10`,
`HEX8`, `HEX20`, `WEDGE6` and `DISCRETE`. `WEDGE6` describes the implemented
technical elemental kernel, while its registry combination remains
`EXPERIMENTAL` and no public qualified capability record is created.

## Preflight contract

The public router runs a fail-closed preflight after analysis normalization
and before assembly. It checks the element family, analysis, material,
formulation/route, load categories and requested backend. Unknown or
technically unsupported combinations return `UNSUPPORTED_ROUTE`. A known
technical route whose registry state is `EXPERIMENTAL` or
`NOT_QUALIFIED` is reported explicitly as `EXPERIMENTAL_ROUTE` or
`NOT_QUALIFIED_ROUTE`; a qualified bounded registry combination is reported as
`SUPPORTED_ROUTE`.

Results carry a deterministic status, reason code, reader-facing message and
the normalized combination fields. The distinction is intentional: lack of
qualification is not silently converted into technical support, and a missing
technical route is not inferred from an element alias.

The compact access contract is exposed from `solveur.compatibility` through
`get_element_descriptor`, `check_compatibility`, `get_supported_analyses`,
`get_supported_loads`, `get_maturity` and `explain_compatibility`.

## Evidence and boundary

Targeted evidence covers descriptor completeness, deterministic aliases,
registry/descriptor consistency, supported and experimental route handling,
explicit non-qualified handling, malformed inputs, unsupported loads and
deterministic model preflight. Existing BEAM2, MITC3, HEX8, discrete/contact,
analysis-feature and public API workflows remain green in the targeted set.

The WEDGE6 descriptor is limited to the technical `linear_static` elemental
route with homogeneous isotropic material, nodal loads and the declared
SciPy route. It does not declare modal/dynamic, nonlinear, contact, face-load,
Gmsh or user-workflow support. This work package does not make experimental
routes qualified or authorize a full regression or engineering V&V campaign.
