---
doc_id: DOC-028-WP13-02A-READINESS-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP13-02A mixed dynamics readiness and frozen contracts

WP13-02A is a readiness and contract-freeze step. It does not execute a
Newmark or harmonic campaign, change an element formulation, promote maturity,
or alter any 0.2.7 evidence.

The machine-readable audit is
[`wp13_02a_readiness.json`](../../../qualification/0_2_8/wp13_02a_readiness.json).
The frozen contracts are the [Newmark contract](../../../qualification/0_2_8/wp13_02a_newmark_contract.json)
and the [harmonic contract](../../../qualification/0_2_8/wp13_02a_harmonic_contract.json).
They were committed before the readiness measurements under commit
`e7c75286dbf073b7b82f05eaef276dabc05684e0`, from baseline
`889fbf27328e843813b670bcbded98327e320b24`.

## Readiness outcome

The generic small-system solvers already provide Newmark and harmonic paths,
consistent K/M assembly, Rayleigh damping, temporal/harmonic loads, initial
conditions and result records for declared pure routes. Existing targeted
tests confirm the pure TET4 and HEX8 routes, while the WEDGE6 kernel provides
stiffness and consistent mass matrices.

The public compatibility boundary is the blocker: WEDGE6 declares only
`linear_static` and `modal`. A mixed model containing WEDGE6 is therefore
rejected by preflight for both `transient_dynamic` and `harmonic_response`
before the generic solver is entered. This is an explicit unsupported route,
not a silent fallback. WEDGE6 dynamic damping, loads, interface transfer and
post-processing consequently remain unvalidated.

## Connected campaign model

The frozen future campaign uses the conditioned compact elbow already used for
the bounded connected static MVP: 3 TET4, 2 WEDGE6 and 1 HEX8 in one connected
component, with the mechanical path

`LOAD -> TET4 -> WEDGE6 -> HEX8 -> SUPPORT`.

The load is applied only on TET4 and the support only on HEX8; there is no
direct support bypass. The pre-run geometry proxies are aspect ratio `1.7321`,
Jacobian determinant range `[0.125, 1.0]`, maximum affine Jacobian condition
`3.7321`, assembled positive-K diagonal ratio `10`, and assembled consistent-M
diagonal ratio `5.5556`. A global condition number was not computed and is not
claimed.

## Frozen V&V policy

Newmark uses average acceleration (`beta=0.25`, `gamma=0.5`), an independent
dense K/M generalized-eigen reference and the closed-form first-mode oscillator
for the declared initial-condition case. Its frozen levels are `T1/20`,
`T1/40`, `T1/80` and `T1/160`, with amplitude, phase, frequency, residual,
energy, interface-transfer and two-replay gates. Harmonic uses the same
independent first-mode reference, 2% mass-proportional damping and the fixed
frequency ratios `0, 0.5, 0.8, 0.95, 1.0, 1.05, 1.2, 1.5, 2.0` times `f1`,
covering the static limit, off-resonance and near-resonance behavior.

No tolerance is result-dependent. No external-correlation claim is made. A
separate Owner decision is required after 02B/02C evidence; these contracts do
not authorize implementation or promotion.

## Targeted checks

The readiness checks passed: 12 targeted tests, JSON validation, K/M and
conditioning precheck, Ruff, compileall and diff checks. The WEDGE6 dynamic
compatibility smoke check returned the expected explicit
`ANALYSIS_NOT_SUPPORTED` result for both routes. The full suite remains
deferred to the WP13 final gate.

`WP13-02A = PASS_WITH_LIMITATIONS`: the 3 readiness/contract points are
validated, but WP13-02B is not ready to execute until the WEDGE6 dynamic route
is separately enabled and its missing V&V path is addressed.
