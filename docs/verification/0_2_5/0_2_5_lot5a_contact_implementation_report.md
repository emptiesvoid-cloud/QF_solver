---
doc_id: DOC-NL-025-025
revision: 1.0
status: approved
applicable_version: 0.2.5a0
reviewer: Owner
approver: Owner
---

# QF Solver 0.2.5a0 - Lot 5A contact implementation report

**Scope:** implementation blockers for `025-G05` only.

**Implementation base commit:** `d6ede9d8c3cf01ea6d381ff84441ad2067482095`

The implementation snapshot above is historical. The controlled G05 replay
was generated later on qualified source SHA
`a3ab8de707ffc88fc5e39e4f999eb872c9223b73` with `dirty=false`; its evidence
manifest is `results/vnv_0_2_5/g05_latest/evidence_manifest.json`.

**Gate decision:** `025-G05 = PASS` for the bounded contract below.

This report retains the implementation history and records the subsequent
controlled closure. It does not qualify general contact.

## 1. Implementation result

The existing contact contribution remains on the common sparse penalty path:

```text
R_total = R_internal - R_external + R_contact
K_total = K_material + K_geometric + K_contact
```

No second Newton driver was introduced. The implementation adds a bounded
slave-node patch representation while retaining the legacy `slave_node` input.
Each node in `slave_nodes` is expanded into a stateless contribution against
the selected triangulated master facet. This is an explicit node-patch
approximation, not a mortar or segment-to-segment formulation.

The updated-search path recomputes the selected facet, projection, normal and
tangential basis from the current trial configuration. The sparse contact
tangent is assembled together with the other global contributions.

## 2. Evidence produced

| Requirement | Internal observation | Result |
|---|---|---|
| A - multi-facet plane | Two slave nodes, two master facets, both active, sparse tangent non-empty | `PASS_INTERNAL_RESEARCH` |
| B - updated normal | Master facet node displaced in `UZ`; normal becomes `[0, -0.4472136, 0.8944272]` and remains unit length | `PASS_INTERNAL_RESEARCH` |
| C - finite sliding | One slave node selects facets `[0, 1, 2]` across a connected three-facet strip; two switches observed | `PASS_INTERNAL_RESEARCH` |
| D - open/close/recontact | Existing common-driver contact path retains the bounded open/close/recontact tests | `PASS_INTERNAL_RESEARCH` |
| E - transition rollback | Committed facet `1`, failed trial facet `2`, rollback facet `1`, retry facet `2`; deterministic replay | `PASS_INTERNAL_RESEARCH` |
| F - common Newton | Existing contact composition uses the common nonlinear residual/tangent/Newton path | `PASS_INTERNAL_RESEARCH` |
| G - penalty sensitivity | Existing bounded penalty sweep remains available | `PASS_INTERNAL_RESEARCH` |
| H - local tangent FD | Existing fixed-active contact tangent error is approximately `6.0e-9` | `PASS_INTERNAL_RESEARCH` |

The new direct benchmark observations are:

```text
surface patch:
  slave_surface_mode = node_patch_to_faceted_surface
  slave_node_count = 2
  selected_face_indices = [0, 1]
  active_contacts = [0, 1]
  gaps = [-0.1, -0.1]
  tangent_nnz = 21

three-facet sliding:
  selected_face_indices = [0, 1, 2]
  face_switch_count = 2
  facet_count = 3
  gap = -0.1 on each position

facet-transition rollback:
  committed_face = 1
  failed_trial_face = 2
  rollback_face = 1
  retry_face = 2
  clean_retry = true
```

## 3. Tests executed

The targeted regression command was executed with the authoritative source
tree on `PYTHONPATH`:

```text
python -m pytest tests/unit/test_contact_finite_sliding.py \
  tests/unit/test_nonlinear_contact_composition.py \
  tests/unit/test_frictionless_contact.py \
  tests/unit/test_large_solver_and_serialization_edges.py \
  tests/unit/test_schema_entity_validation_paths.py -q
```

Result: **55 passed in 2.86 s**.

The run covers backward-compatible serialization, schema validation, sparse
assembly, updated search, common Newton diagnostics, patch expansion, three
facet traversal, updated normals and facet-transition replay. No full
regression or coverage campaign was launched for this implementation slice.

## 4. Files changed

- `src/solveur/contact/entities.py`
- `src/solveur/contact/support.py`
- `src/solveur/contact/solver.py`
- `src/solveur/core/model.py`
- `src/solveur/io/contact_schema.py`
- `src/solveur/io/model_writer.py`
- `src/solveur/mesh/validation.py`
- `src/solveur/verification/robustness_contact.py`
- `tests/unit/test_contact_finite_sliding.py`
- `docs/verification/0_2_5/0_2_5_vnv_matrix.md`
- `docs/verification/0_2_5/0_2_5_known_limitations.md`

The document registry also records this report and the pre-existing Lot 4
implementation report so controlled-document tests can enumerate every
Markdown source consistently.

## 5. Explicit limitations

1. The surface representation is a bounded collection of slave nodes against
   a triangulated master surface. It is not a continuum surface-to-surface,
   mortar or segment-to-segment formulation.
2. The finite-sliding projection is a bounded closest-point-on-triangle
   approximation when the orthogonal projection leaves a facet. It can be
   nonsmooth at active-set and facet transitions; a classical smooth FD tangent
   claim does not apply exactly at those kinks.
3. The master search is local to the explicitly supplied faceted surface. A
   generalized broad-phase search, self-contact and arbitrary deformable
   surface pairing are not included.
4. Friction is unchanged and remains outside this Lot 5A implementation.
5. The current external correlation is bounded to compatible Code_Aster normal
   contact histories; CalculiX is supporting pre-contact evidence only.
6. The contact claim is qualified only for the bounded node/patch-to-faceted-
   surface contract. General surface-to-surface contact, friction, impact,
   self-contact and unrestricted large sliding remain outside scope.

## 6. Status

```text
IMPLEMENTATION STATUS = COMPLETE
SURFACE_TO_SURFACE = PARTIAL
FINITE_SLIDING = PASS
UPDATED_NORMALS = PASS
FACET_TRANSITIONS = PASS
ROLLBACK = PASS
FD_TANGENT = PASS
TESTS = 55 passed in 2.86 s
READY_FOR_G05_VNV = COMPLETE
G05 = PASS
```

The implementation blockers addressed here are complete within the bounded
node-patch/faceted-surface scope. The controlled closure used the current
internal contact suite, bounded penalty characterization and the archived
Code_Aster additional-model campaigns. It does not promote the implementation
to a general surface-contact claim.

## Owner closure record

| Field | Value |
|---|---|
| Gate | `025-G05` |
| Owner decision | `APPROVED` |
| Qualified source SHA | `a3ab8de707ffc88fc5e39e4f999eb872c9223b73` |
| Source worktree | `CLEAN` |
| Contract lowered | `NO` |
| Internal targeted tests | `82 passed / 2 skipped` |
| Code_Aster | `PASS_EXTERNAL_CORRELATION` on 768 and 9,984 TET4 confirmations |
| CalculiX | supporting SHOULD evidence; not release-blocking |

The resulting qualified scope is `025-REQ-018` through `025-REQ-021`: common
sparse frictionless penalty contact, bounded open/close/recontact, opt-in
updated finite-sliding projection over an explicitly supplied triangulated
master surface, penetration/enforcement sensitivity, and exact transaction
replay. This closure does not close G06 or promote G07.
