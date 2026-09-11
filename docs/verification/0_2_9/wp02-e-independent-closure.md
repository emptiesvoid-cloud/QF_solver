---
doc_id: DOC-029-WP02-006
revision: 1.0
status: controlled
applicable_version: 0.2.9-development
---

# WP02-E — independent state, rollback and restart closure audit

> **Independent audit record.** Audit SHA:
> `c4e02fbd2d1262f621f6c8d4f07ee2da89d885f5`.
> Decision: **GO_WITH_LIMITATIONS**. This closes WP02 at **6/6** and brings
> the validated roadmap total to **22/100**. Owner review is required before
> any WP03 authorization.

## Scope and result

The audit reviewed the accepted-state and checkpoint authorities, searched for
hidden commits and save paths, challenged rollback/restore boundaries, and
replayed fixed, adaptive and arc-length restart paths without modifying
production source. `NonlinearStateTransaction` is the one accepted-state
publication primitive used by the public unified drivers; checkpoint persistence
is the one composite `save_state` / `restore_state` boundary. Legacy `save`,
`restore` and `restore_continuation` APIs delegate to that boundary.

The direct frictionless and frictional active-set loops retain local legacy
transactions, but are linear-static or research compatibility routes. They are
not reachable as public nonlinear state/checkpoint authorities: public
nonlinear contact requires `contact_mode='penalty'`.

## Adversarial findings

| Invariant | Result |
| --- | --- |
| Accepted-state / checkpoint authorities | PASS — one public authority each |
| Composite atomic commit and rollback digests | PASS — no partial commit or failed-retry leak |
| Schema-v2 typed serialization and digests | PASS — arrays, typed mapping keys, ordering, malformed and non-finite data challenged |
| Restore integrity | PASS — validation precedes installation; no partial restore |
| Model signature and state topology | PASS — physical changes reject; output/persistence settings remain excluded |
| v1 compatibility | PASS_WITH_LIMITATIONS — only OD-029-02 bounded inputs migrate; ambiguous/stateful and incomplete arc inputs reject |
| Fixed/adaptive restart | PASS_WITH_LIMITATIONS — supported routes agree within `1e-9` relative / `1e-12` absolute floor |
| Arc restart, turning/rejection/radius | PASS_WITH_LIMITATIONS — accepted continuation state and branch direction are preserved |
| D1 material-state ownership | PASS — controller, caller, post-process, final assembly and checkpoint agree at the accepted state |
| Checkpoint write failure isolation | PASS — no physical rollback, cutback or radius shrink; canonical visibility is atomic |

The save path uses a same-directory temporary file, file flush/fsync where the
platform supports it, and atomic replacement. This is an atomic-visibility
claim, not an unqualified cross-platform durability claim.

## Gate decision

| Gate | Decision |
| --- | --- |
| G02-01 Composite checkpoint completeness | PASS |
| G02-02 Round-trip exactness | PASS |
| G02-03 Fixed/adaptive restart equivalence | PASS_WITH_LIMITATIONS |
| G02-04 Arc-length restart equivalence | PASS_WITH_LIMITATIONS |
| G02-05 Checkpoint integrity | PASS |
| G02-06 Atomic persistence | PASS |
| G02-07 Bounded v1 compatibility | PASS_WITH_LIMITATIONS |
| G02-08 One state authority | PASS |
| G02-09 No trial persistence | PASS |
| G02-10 Numerical preservation | PASS_WITH_LIMITATIONS |

## Audit execution

The independent runtime probe passed deterministic mixed-payload
serialization, a failed invalid trial commit, and separately constructed
fixed, adaptive and arc restart comparisons. Existing evidence was also
replayed: WP02-B `28 passed`; WP02-C `25 passed`; WP02-D `28 passed`; WP02-D1
`10 passed`; checkpoint `10 passed`; continuation `22 passed`; failure `21
passed`; and J2/geometric/contact regressions `39 passed`. No full suite was
run.

The legacy `test_029_step_up_baseline.py` documentation guard is independently
classified as pre-existing stale test debt: at the audit SHA it already omits
the pre-existing WP02-D/D1 pages and freezes the earlier 16/100 total. It is
not a production invariant and is not modified by this read-only audit.

## Boundaries retained

This closure does not qualify frictional contact restart, distributed
PETSc/MPI restart, nonlinear-dynamics restart or adaptive penalty-contact
restart. Schema-v1 compatibility remains bounded by OD-029-02. The existing
fifteen mypy diagnostics are inherited; no new audit diagnostic is accepted.
OD-029-01 remains **OPEN** and blocks WP09 only. No numerical formulation,
element formulation, maturity claim or 0.2.8 evidence changed.

The next permitted action is **Owner review of this WP02-E closure; WP03 is
not started**.
