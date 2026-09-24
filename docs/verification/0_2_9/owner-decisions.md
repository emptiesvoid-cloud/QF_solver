---
doc_id: DOC-029-007
revision: 0.2
status: controlled
applicable_version: 0.2.9-development
---

# 0.2.9 Owner decision log

## WP05-C/D/E bounded closure decision

**Status:** CLOSED — `APPROVED_WITH_LIMITATIONS`; local integrated WP05 score
**5/5**, local validated total **61/100** (58/100 before integration).

The Owner authorized integration of the passed WP05-C TET10 structural
campaign, accepted WP05-D at 1/1 within its documented HEX20 scope, and
accepted WP05-E at 1/1 candidate after the WP05-C/D evidence was integrated.
The cross-family stress gate is specific to the common historical
`representative_sigma_xx` observable. The HEX20-only clipped-window stress
value is excluded from E.

The Owner directs that Code_Aster or another external-solver comparison be
performed later. That correlation is deferred future V&V, not claimed by this
bounded closure. No general element-family or stress-field equivalence is
asserted. Historical WP05-D `FAIL_CLOSED` evidence remains preserved.

This decision updates the local integration ledger only. No push was
authorized or performed; the remote governing total remains **58/100** until
publication. The evidence, comparisons and retained limitations are recorded
in the [WP05-C/D/E integration audit](wp05-cde-owner-integration.md) and
`qualification/0_2_9/wp05cde_integration/wp05_cde_integration_audit.json`.

## WP08 closure decision

**Status:** CLOSED — `APPROVED_WITH_LIMITATIONS`.

The Owner accepted WP08-A, WP08-B, WP08-C, WP08-D and WP08-E, awarded
**8/8 official points** to WP08, and authorized the official-ledger update,
reviewed-lineage merge and governing push. The official roadmap total moves
from **50/100** to **58/100**.

The approval applies only to the serial/direct `linear_static`
frictional-contact route under small displacement with fixed initial
search/face/normal and positive friction coefficient and tangential stiffness.
It excludes frictional updated search, finite sliding, general nonlinear
friction, mid-Newton or general nonlinear restart, global pressure-coupled
tangent consistency, complete global energy decomposition, external-solver
correlation, MPI/PETSc and dynamics claims.

The reviewed package, direct-inspection artifact and detailed retained
limitations are recorded in [the WP08 Owner approval](wp08-owner-approval.md).
Historical FAIL_CLOSED evidence and all execution SHAs remain preserved. No
M1/M2/M3 solve or raw evidence is regenerated or overwritten by this decision.

## WP01 closure decision

The Owner approved closure of WP01 Unified Nonlinear Core at audit SHA
`6876d867cdd845195e8946b05329b0bc82937fdc` with
`GO_WITH_LIMITATIONS`. WP01 receives **12/12 points**, bringing the validated
roadmap total to **16/100** including WP00 (4/4). The detailed record is
[WP01 Owner closure](wp01-owner-closure.md).

This decision records no production-source, numerical-formulation or maturity
change and does not alter the WP01-A/B/C/D evidence. The subsequent independent
WP02-E audit closes State Transactions & Rollback at **6/6**, bringing the
validated roadmap to **22/100** with `GO_WITH_LIMITATIONS`. Its scope remains
bounded to supported single-process fixed/adaptive/arc restart; frictional
contact migration, adaptive penalty-contact qualification, distributed restart
and inherited mypy/mixin typing debt remain outside that closure. Owner review
is required before WP03 authorization.

## OD-029-01 — bounded J2 plus geometric formulation

**Status:** OPEN. Required before WP09 implementation or any public claim.

The Owner must select one bounded physical direction after reviewing the
stress/strain measures, state transport and required validation basis:

| Option | Direction | Default status before approval |
| --- | --- | --- |
| A | Corotational/large-rotation model with explicitly bounded small-strain J2 | Not selected |
| B | Existing `total_lagrangian_j2` research formulation | Research only |
| C | Proper finite-strain multiplicative plasticity, \(F=F_eF_p\) | Not selected; substantial new work |
| D | Defer public J2 plus geometry claim | **Default** |

No option is selected by the existence of code alone. The selected option must
receive a prospective constitutive/objectivity contract, tangent and
state-transport verification, bounded external correlation and failure limits.

## OD-029-02 — legacy v1 checkpoint compatibility boundary

**Status:** CLOSED — Owner-approved decision:
`READ_V1_WRITE_V2_BOUNDED`.

Schema 1 has no contact-state payload, contact topology, accepted metadata or
composite digest. The approved boundary is therefore to read/migrate
contact-free v1 checkpoints, and stateless-compatible penalty-contact v1
checkpoints only when compatibility is proven from the current model. Any
ambiguous, stateful or contact-history-dependent v1 checkpoint is rejected
explicitly. Missing history is never invented, and all new writes use schema
2. The implementation record is [WP02-B schema-v2 foundation](wp02-b-schema-v2-foundation.md).

## WP07-D and WP07-E closure and score-ledger reconciliation

**Status:** CLOSED — Owner accepted WP07-D at **3/3** and WP07-E at **2/2**;
WP07 is **10/10 with bounded limitations**.

WP07-D R1 was accepted on 2026-09-17 as `PASS_REPLAY_VERIFIED`. WP07-E R2
was separately accepted on 2026-09-18 after the complete fail-closed evidence
package passed its checker, including all six required negative cases. E
reused the accepted D R1 package; D was not rerun. The immutable E candidate
record remains `PASS_CANDIDATE`; the separate Owner acceptance artifact is
the authority for the official 2/2 award.

The ledger arithmetic is reconciled as follows: the committed pre-D ledger was
61/100 and already included WP05 at 5/5 and WP07 at 5/10. D adds 3 points,
yielding 64/100 and WP07 8/10; E adds 2, yielding **66/100** and WP07
**10/10**. The earlier Owner-stated 61/100 after D used a 58/100 baseline
before the local WP05 +3 integration. This is a baseline difference, not
duplicated credit.

The frozen roadmap declares 100 total points, and its package allocations
also sum to 100. This ledger update does not change the frozen weights.
WP07 limitations remain those in the accepted
R2 contract: bounded routes and frozen cases only; no general updated-search
or finite-sliding claim.

Evidence: [WP07-E Owner acceptance](wp07e-owner-acceptance-r2.md), [R2
closure audit](wp07e-closure-owner-review-r2-final.md), and the machine-readable
award in `qualification/0_2_9/owner_decisions.json`.

## WP06-A/B/C partial closure decision

**Status:** CLOSED for the accepted A/B/C scope — `APPROVED_WITH_LIMITATIONS`.

On 2026-09-18, the Owner accepted WP06-A at **1/1**, WP06-B at **1/1** with
limitations, and WP06-C at **2/2** within its bounded scope. WP06 therefore
receives **4/8 official points**, and the consolidated official ledger moves
from **66/100** to **70/100**. This is a branch-local ledger update on
`codex/wp06-score-requalification`; it has not been merged or pushed to the
governing branch.

The accepted evidence supports the bounded formulation/route, continuation
state/rollback and algebraic/toy identity claims only. WP06-B does not claim
structural restart suffix or distributed/MPI restart qualification. WP06-C
does not claim structural postbuckling qualification. Historical WP06-D1 M2
`FAIL_CLOSED` evidence remains unchanged.

The Owner explicitly **did not authorize WP06-D R2 structural execution**.
No D solve, replay, merge, or push was performed by this decision. Any future
D execution requires its own frozen current-source contract/runner and a
separate explicit Owner authorization. The immutable decision and its
revalidation evidence are recorded in [the WP06 A/B/C Owner decision](wp06-abc-owner-decision.md)
and `qualification/0_2_9/wp06_abc_owner_decision.json`.

## WP13 R2.1 bounded multi-family characterization

**Status:** CLOSED — Owner accepted WP13 R2.1 at **1/1** with limitations.
The official total moves from **94/100 to 95/100**.

The Owner accepts the recorded TET4/TET10/HEX8/HEX20 performance, API, and
diagnostics characterization within its frozen contract. The active scoring
allocation is confirmed as WP13=1, WP14=1, WP15=2, totaling 100 points. This
explicit reduced allocation supersedes the original WP13/WP14 weights for
current scorekeeping; the original frozen roadmap itself remains preserved
unchanged as historical evidence.

This award is not a comparative performance benchmark or solver ranking.
The recorded memory metric is `tracemalloc`, not process RSS; there is no mesh
convergence, scaling, HPC, cross-machine, external-solver, or independent
global FEM/Newton claim. The R2 raw artifacts remain local and Git-ignored
pending the planned WP16 archive. The archived targeted test result is
**21 passed**; no full repository suite was run for this decision. No
qualification solve was rerun. The decision record is
`qualification/0_2_9/wp13_r2_multifamily/wp13_owner_acceptance_r2_1.json`.
