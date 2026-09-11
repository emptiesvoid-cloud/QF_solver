---
doc_id: DOC-029-WP01-007
revision: 0.1
status: implementation_foundation
applicable_version: 0.2.9-development
---

# WP01-B Unified Nonlinear Core foundation evidence

> **Foundation delivered; migration not started.** This record does not change
> formulations, maturity or any 0.2.8 evidence.

## Implemented internal contracts

- `NonlinearState`: detached displacement plus formulation-neutral material,
  contact, continuation and accepted-increment metadata payloads.
- `NonlinearStateTransaction`: one accepted/trial composite transaction;
  validation precedes publication, rollback is digest-checked, and external
  accepted-state corruption raises `STATE_CORRUPTION` rather than being
  overwritten.
- `deterministic_state_digest`: canonical type/schema/dtype/shape/bytes and
  mapping-order-aware state digests.
- `ContributionResponse` and composite response plumbing: sparse force/tangent
  accumulation, namespaced diagnostics and optional detached state updates.
- `UnifiedNonlinearDriverFoundation`: formulation-neutral lifecycle ownership
  of begin-trial, evaluate, correction callback, trial update, decision and
  commit-or-rollback.

No nonlinear solver has been migrated. The legacy `StateTransaction` and
`MaterialStateSession` are intentionally retained while compatibility adapters
are designed in a later WP01 step.

## Targeted evidence

`tests/unit/test_unified_nonlinear_foundation.py` covers T01–T18: digest
identity/change sensitivity, trial isolation, exact rollback, atomic commit,
failed commit, corruption detection, stateless/stateful contribution plumbing,
sparse composition, diagnostics isolation and deterministic failure metadata.

Targeted legacy regression command: **72 passed, 0 failed, 0 errors**. It
includes state contracts, Full Newton/composite assembly, failure contracts,
small-strain J2, geometric nonlinear and penalty-contact composition tests.

## Gate status

| Gate | Status | Boundary |
| --- | --- | --- |
| G01 | Pending migration | Legacy paths still own loops. |
| G02 | Partial foundation pass | Common response composition is demonstrated; existing paths are not all adapted. |
| G03 | Foundation pass | Rejection keeps exact component/composite committed digests. |
| G04 | Foundation pass | Contributions receive only trial state; no foundation contribution commit exists. |
| G05–G07 | Targeted regression pass, not closed | Existing routes pass targeted regressions; full migration preservation remains pending. |
| G08 | Foundation pass | Identical injected failures produce identical reason/retry metadata. |
| G09 | Pass for this step | No maturity record or claim changed. |
| G10 | Pending migration | Adapter inventory is not yet complete. |

WP01 remains `IMPLEMENTATION_FOUNDATION` with **0 / 12** points awarded. The
next step is Owner review before any migration of legacy solver ownership.
