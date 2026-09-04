---
doc_id: DOC-027-F2-BUG-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 F2 Bug and Sensitive-Zone Hunt

## Decision

`F2_STATUS = PASS_WITH_LIMITATIONS`

The adversarial audit found no P0 issue and fixed all three P1 findings. The
remaining P2/P3 items are explicit deferred debt. No FEM formulation,
numerical tolerance, capability maturity, or historical evidence was changed.

The machine-readable source of this report is
`qualification/0_2_7/f2_bug_hunt.json`.

## Audit surface

The audit covered fail-open error paths, MPI/PETSc collective ordering,
solver/backend route selection, maturity guards, state and checkpoint paths,
determinism, input validation, numerical sanity, element dispatch, public and
legacy APIs, environment bootstrap, and snapshot/evidence integrity.

The repository inventory at audit time was 448 source Python modules, 315
scripts, 204 verification modules, 463 test files, and 79 v2 registry records
(33 anchors and 46 combinations). The prior F1 tree was clean before this
audit.

## Findings fixed

| ID | Priority | Finding | Disposition |
| --- | --- | --- | --- |
| F2-P1-001 | P1 | The v2 registry was absent from the wheel runtime data. | `FIXED`: versioned data-file destination and portable resource resolution. |
| F2-P1-002 | P1 | Dynamic and harmonic aliases did not match canonical registry rows. | `FIXED`: request and row analysis normalization share the alias map. |
| F2-P1-003 | P1 | Duplicate model JSON keys silently used last-write-wins behavior. | `FIXED`: strict object-pairs parsing raises `InputValidationError`. |
| F2-P2-001 | P2 | Evidence manifest duplicate keys were accepted. | `FIXED`: verifier rejects duplicate keys. |
| F2-P2-002 | P2 | Result JSON could emit NaN or Infinity. | `FIXED`: finite-only serialization. |
| F2-P2-003 | P2 | Preflight geometry rejection bypassed the legacy mesh error contract. | `FIXED`: safe preflight rejection preserves `MeshValidationError` behavior. |

## Deferred findings

Descriptor aliases are not yet input aliases; this remains an API decision.
The legacy generic maturity map and registry-v2 combination authority remain
duplicated conservatively. The broad modal refinement diagnostic catch,
repository launcher environment isolation, and conservative handling of a
missing registry remain P2 work. Root export ordering remains P3 because it is
not a documented public contract.

No deferred item produces a qualified claim without evidence. Experimental and
not-qualified routes remain visible, unsupported routes remain fail-closed, and
WEDGE6 maturity was not promoted.

## Validation

- F2 regression guards: `11 passed`.
- Core targeted contracts: `110 passed, 35 skipped`.
- Adversarial, existing-route, WEDGE6, state, and snapshot checks: `179 passed, 3 skipped`.
- Isolated wheel probe: the installed `qualification/0_2_7/capability_registry_v2.json` exists and static/transient dynamic preflight resolve the bounded registry state.
- Ruff, compileall, and `git diff --check`: `PASS`.

No full regression, global coverage, or heavy benchmark was run. A new
qualification campaign is not required for these boundary and serialization
fixes.

## Release boundary

`F2_READY_FOR_F3 = YES`

F2 changes are limited to runtime resource resolution, strict input/evidence
serialization, a legacy error-category compatibility guard, tests, and audit
governance. The 0.2.6 historical snapshots and all capability maturity
decisions remain unchanged.
