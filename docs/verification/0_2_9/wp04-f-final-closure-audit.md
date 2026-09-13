---
doc_id: DOC-029-WP04-F-001
revision: 1.0
status: owner_review_required
applicable_version: 0.2.9-development
---

# WP04-F independent geometric-nonlinear closure audit

Audit SHA: `70e1bf953c8e6f37b8070e78ca97e58b21499291`
Branch: `0.2.9-unified-nonlinear`
Audit mode: evidence-only; no structural solve, H4, PETSc or full repository suite.

## Decision

The independent audit is **GO_WITH_LIMITATIONS**. All twelve frozen WP04 gates
close as `PASS` or `PASS_WITH_LIMITATION`; no in-scope blocking limitation was
found. WP04 is therefore recorded as **CLOSED — 12/12**, bringing the validated
total to **41/100**. The public maturity registry is intentionally unchanged
in this audit; the bounded `QUALIFIED_BOUNDED` wording for TET4 and HEX8
`geometric_nonlinear_static` remains subject to Owner approval and integration
review.

The machine-readable decision and evidence index are in
`qualification/0_2_9/wp04f/wp04_final_closure_audit.json`.

## Independent method and source freeze

Evidence was evaluated in this order: raw numeric records, machine-readable
derived records, controlled documentation, then summary/status text. No
production source changed from the audit SHA. The audit checked the relevant
source files and the Git source diff; only this audit's governance, evidence
and focused test files are new.

The implemented mechanics inspected by the audit are the bounded
Total-Lagrangian Saint-Venant–Kirchhoff route:

```text
F = I + Grad(u)
C = F^T F
E = 0.5 (C - I)
S = lambda tr(E) I + 2 mu E
P = F S
f_int = integral(B^T P) dV0
K_T = material tangent + geometric tangent
psi = 0.5 lambda tr(E)^2 + mu E:E
sigma = det(F)^-1 F S F^T
```

The qualification boundary is homogeneous `isotropic_3d` StVK, TET4 and HEX8,
static dead loading, fixed displacement constraints, fixed or bounded adaptive
proportional continuation, serial execution, and quality-controlled positive
elements. Every counted structural state satisfies `det(F) >= 0.20`, principal
stretches in `[0.75, 1.30]`, and `||E||F <= 0.30`. Contact, friction, J2 plus
geometry, dynamics, distributed MPI/PETSc execution, reduced-integration or
hourglass HEX8, high-order elements, follower loads, updated Lagrangian and
corotational claims remain excluded.

## Provenance and preservation of the original failure

The WP04 chain is preserved rather than rewritten:

| Phase | Source SHA | Evidence | Audit treatment |
| --- | --- | --- | --- |
| WP04-A | `eaa3119ffdd4b5dc85659b60431cd23d23870736` | contract, formulation map, historical debt, gate matrix | frozen contract input |
| WP04-B | `2cd96b6695be1e90a8cc2dff81f6534774ab04d2` | mechanics identities | independently checked |
| WP04-C | `48bfa83bc517e031cdab4876970a4f511f744e35` | original TET4 campaign and summary | failure retained |
| WP04-C1/C2 | `c4d2fd9b8bf0154bad9a30389d5ba426fe6fc7d9` | mesh diagnosis, requalification contract, owner-abort record | diagnosis/authorization retained |
| R1/R2/R2B | `bee8cb606a975a8714947776be489e00af8fa623` | linear-solver remediation chain | failed and passing campaigns retained |
| C2R3–C2R6 | `2c52bf8196a7d47d14ce1784290580160de26590` | floor-aware policy, recovered M2/M3 and threshold audit | final TET4 source |
| WP04-D | `0c23b11477140fa64b5dd2a74def3a042bfe3d8e` | HEX8 contract, campaign, G04-11 audit | final HEX8 source |
| WP04-E | `70e1bf953c8e6f37b8070e78ca97e58b21499291` | cross-family audit | final cross-family source |

`qualification/0_2_9/wp04_c_tet4_structural_summary.json` remains Git blob
`0138e7583c2e0ce0488c69ab8630f87118a299e6` both at the original failure commit
`a5c3031f6b28b00476e328daff4845a741a5c161` and at the audit SHA. Its original
G04-10 result is still `FAIL`, with fine/medium displacement, energy and stress
differences `0.1640618103457515`, `0.16379509145773455` and
`0.24310580151133324`. Thus:

`ORIGINAL_G04_10_FAILURE_PRESERVED = YES`.

The sequence is original failure → C1 diagnosis of slow TET4 discretization
convergence → authorized C2/C2R6 requalification → final bounded pass. No
historical failure was hidden or overwritten.

## Mechanics identity audit

The WP04-B raw record independently supports the following results:

| Identity | TET4 evidence | HEX8 evidence | Frozen limit | Result |
| --- | ---: | ---: | ---: | --- |
| Objectivity, max scaled energy | `5.925938290422264e-32` | `5.612207511551394e-32` | `1e-12` | PASS |
| Objectivity, max scaled internal force | `7.1452248095509635e-16` | `2.750946359148772e-16` | `1e-11` | PASS |
| Affine patch, maximum production error | `2.1316282072803006e-14` | `2.842170943040401e-14` | rel `1e-10`, abs `1e-12` | PASS |
| Energy gradient, max selected relative error | `3.729729708567283e-09` | `6.225887413721546e-10` | `1e-7` | PASS |
| Tangent, max Frobenius relative error | `6.07839709319373e-11` | `1.170521763198485e-10` | `1e-6` | PASS |
| Tangent, max column relative error | `1.1757631899319535e-10` | `1.5062326759762644e-10` | `5e-6` | PASS |
| Tangent symmetry defect | `0.0` | `0.0` | `1e-12` | PASS |

The accepted-state observer contains six detached accepted snapshots, zero
rejected-trial snapshots, and no later-trial mutation. Accepted-path work uses
the 12/24/48/96 trajectories. The finest DeltaU/work errors are
`2.416066138923941e-08` (TET4) and `5.033743397600643e-08` (HEX8); the 96-vs-48
work changes are `7.247967951863676e-08` and `1.5101242176369792e-07`, below
the frozen `1e-6` and `2e-7` limits. Historical WP13-11 value
`1.3963468382007748e-05` is unchanged.

## Gate reconstruction

| Gate | Independent status | Reconstructed basis |
| --- | --- | --- |
| G04-01 | **PASS** | Scope, envelope and exclusions match the frozen WP04-A contract. |
| G04-02 | **PASS** | Four rigid-motion cases per family; energy and force margins above. |
| G04-03 | **PASS** | Four finite-deformation affine states per family agree with the independent oracle. |
| G04-04 | **PASS** | Centered finite-difference energy-gradient checks pass for both families. |
| G04-05 | **PASS** | Per-column tangent, global tangent and symmetry checks pass for both families. |
| G04-06 | **PASS_WITH_LIMITATION** | TET4 smallest-load displacement/reaction errors are `2.1032185690777483e-05` and `3.384021633463905e-11`. HEX8 displacement is `2.5607163831358572e-05`, but its supporting reaction error is `2.7738177407149553e-04`. |
| G04-07 | **PASS** | TET4 final fine force/moment errors `2.5505039661180956e-14` / `7.63053276664867e-16`; HEX8 `2.7493855285792547e-14` / `3.257786891417962e-15`. |
| G04-08 | **PASS** | Accepted-state energy/work refinement passes for both families; historical debt unchanged. |
| G04-09 | **PASS_WITH_LIMITATION** | TET4 load-step and replay evidence and HEX8 H1 replay pass. The TET4 `SOLVE_COMPLETED` aggregate undercounts Newton iterations by 12 per case, while raw iteration/accepted-step totals are complete. |
| G04-10 | **PASS** | C2R6 TET4 M2→M3 deltas: displacement `0.01692700586415766`, reaction `1.563194018672221e-15`, energy `0.016890467524899724`, stress `0.02164607184507869`; all pass `0.02/0.02/0.02/0.10`. |
| G04-11 | **PASS** | HEX8 H2→H3 deltas: displacement `0.01999034019793022`, reaction `9.224898992711293e-14`, energy `0.019943897062970836`, stress `0.046483239095767515`; all pass `0.02/0.02/0.02/0.10`. H4 was not run because the predeclared rescue condition was not triggered. |
| G04-12 | **PASS** | TET4 C2R6 M3 vs HEX8 H3 deltas: displacement `0.004566585385421973`, reaction `7.105427357601005e-16`, energy `0.004553762679948579`, stress `0.05163720669059609`; all pass `0.03/0.03/0.03/0.12`. |

The HEX8 reaction result is deliberately not hidden: the frozen WP04-D
contract called its H1 small-load sequence a supporting check and explicitly
said it was not a new gate number. It is therefore carried as a public,
non-blocking limitation. If that check were instead treated as an independent
family-wide G04-06 gate, the result would be a fail; that is not the frozen
WP04-D governance contract.

The HEX8 H2/H3 physical load uses consistent Q4 face traction. The TET4 and
HEX8 discrete load vectors differ as disclosed, but their physical resultant,
first moment, geometry, material, constraints, displacement definition,
reaction convention, energy definition and reference-volume stress region
match for G04-12.

## Limitations ledger

| Limitation | Blocking | Rationale |
| --- | --- | --- |
| HEX8 smallest-load reaction support error above `1e-4` | NO | Supporting-only WP04-D check; retained in G04-06 as `PASS_WITH_LIMITATION`. |
| TET4 C2R6 telemetry aggregate Newton undercount | NO | Per-iteration and accepted-step records agree with result totals; no physical or replay corruption. Classified non-blocking WP15 debt. |
| MINRES+Jacobi is local/bounded | NO | No universal scalability claim is made. |
| SPD is not proven; CG rejected | NO | MINRES is the frozen qualification route; no global SPD claim. |
| PETSc/AMG not qualified | NO | Outside WP04 scope. |
| StVK is bounded by the positive-deformation envelope | NO | No universal large-strain constitutive claim. |
| No contact, plastic, dynamic or coupled qualification | NO | Explicit roadmap exclusions. |
| No high-order element transitive qualification | NO | TET10/HEX20 remain outside WP04. |
| Serial/single-process only | NO | Distributed execution is outside the contract. |
| Public maturity registry unchanged | NO | This audit recommends bounded wording pending Owner approval and integration review. |

## Final governance and validation

The audit-only focused test file is
`tests/verification/test_wp04_f_final_closure.py`. It checks the source freeze,
original-failure blob preservation, recomputed WP04-B thresholds, TET4/HEX8
structural deltas and cross-family thresholds. It launches no solver.

The final run records are updated in the machine-readable audit JSON after
validation. The required validation scope is targeted only: WP04-F audit
tests, JSON validation, Ruff, targeted mypy, compileall and MkDocs strict.

Final governance state:

```text
AUDITOR_DECISION = GO_WITH_LIMITATIONS
WP04_STATUS = CLOSED
WP04_POINTS = 12/12
VALIDATED_TOTAL = 41/100
PRODUCTION_MECHANICS_CHANGED = NO
STRUCTURAL_SOLVES_RUN = NO
H4_RUN = NO
PETSC_RUN = NO
FULL_TEST_SUITE_RUN = NO
OD-029-01 = OPEN (blocks WP09 only)
OD-029-02 = CLOSED (READ_V1_WRITE_V2_BOUNDED)
```

Next step: Owner approval of WP04-F, then sequential child-branch integration.
WP05 has not started.
