---
doc_id: DOC-027-020
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: Owner review recorded in WP20
approver: Owner decision recorded in the machine-readable state
---

# 0.2.7 WP20 - Residual J2 and external V&V closure

WP20 closes the remaining Owner-review item attached to the WP11
small-strain J2 characterization. It is a qualification and governance
closeout, not a new constitutive implementation or a new numerical campaign.
The review started from `26a734d1656c1c824c27f4708a8783abfddde17c`.

## Owner decision

The Owner decision is `OWNER_APPROVED_BOUNDED_KEEP_EXISTING_SCOPE` with
work-package status `PASS_WITH_LIMITATIONS`. TET4, TET10, HEX8 and HEX20 are
each `KEEP`: the existing `MAT-J2-SMALL` maturity remains
`QUALIFIED_BOUNDED`, with no promotion or demotion. `MAT-FINITE-J2` remains
`EXPERIMENTAL`/`NOT_QUALIFIED`.

The bounded claim is small-strain isotropic J2 with radial return on the four
existing solid families through the accepted full-Newton nonlinear-static
route. It does not qualify finite-kinematic J2, Total-Lagrangian J2, coupled
nonlinear routes, modal/dynamic behavior or a universal physical response.

## Evidence reviewed

The controlled WP11 evidence is preserved unchanged:

* case catalog: `qualification/0_2_7/wp11_j2_cases.json`;
* evidence: `qualification/0_2_7/wp11_j2_evidence.json`;
* execution/evidence source SHA: `94461602dfd1782be57c20e1801a0d5d8e262ef1`;
* result digest: `5e4825625d40f2363ecefb8f96baa43acac42f23db7195d000ca0c09717ef536`;
* historical execution contract: `qualification/0_2_7/wp11_state.json`.

The evidence passes elastic prediction, yield detection, radial return,
internal-variable and stress updates, unloading/reloading, a simple cycle,
finite-difference tangent checks, multi-element paths, energy diagnostics,
rollback/state digest restoration, full Newton and explicit failure modes on
all four families. The maximum reported finite-difference tangent error is
`2.120472111937634e-10` against the existing G06 limit `1e-6`.

The 1/2/4 subdivision study characterizes increment sensitivity on all four
families. It deliberately introduces no universal structural
increment-independence threshold. Tangent symmetry remains a diagnostic only;
modified Newton non-convergence remains an explicit diagnostic and is not
silently promoted.

## External evidence

The Code_Aster 18.1.0 correlation from
`qualification/0_2_6/g06_depth_evidence.json` is reused as controlled,
formulation-compatible constitutive evidence. Its source SHA is
`8bd0f2d8fdce7bf27ffc4c28e6aa26e69288fa63` and its archived artifact digest
is `86e238847ca45d4b7024c5bd9dcb15cb07ea5eb72444486204c4d9c3d3c657c2`.
This is a partial external-V&V result for WP20: no new structural external
run is claimed, and it does not extend the increment-independence claim.
External evidence is therefore a limitation, not a reason to invent a new
tolerance or to relabel the internal evidence.

## Failure and reproducibility policy

Invalid material inputs fail closed with deterministic diagnostics. The
controlled rollback path restores the committed-state digest before retry.
Non-convergence in the modified-Newton diagnostic is recorded as a controlled
failure mode. No NaN/Inf or silent pass is accepted, and the WP11 result
digest remains stable on replay.

No solver, material, element, formulation or tolerance was changed by WP20.
Full regression is intentionally not run under the targeted WP20 policy.
The next work package is WP21.
