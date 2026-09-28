---
doc_id: "DOC-MARKDOWN-625169A6DE54F958"
revision: "0.1"
status: "controlled_evidence"
applicable_version: "0.2.9"
reviewer: ""
approver: ""
---
# WP08 area-supported contact — R1.11 optimizer-stop candidate

## Purpose and status

R1.11 is a prospective, experimental M1/M2/M3 diagnostic campaign for the
area-supported TET4 contact benchmark. It evaluates one algorithmic change
after the preserved R1.10 M4 slip diagnostic stopped at `xtol` while the
contact-equation residual remained above its physical acceptance gate.

This is not a formal WP08 qualification, an independent global FEM reference,
a solver replay, a mesh-convergence claim, or a point award.

## Single implementation change

The trust-region least-squares fallback uses an internal stop tolerance

```text
optimizer_tolerance = max(32 * machine_epsilon,
                          min(1e-3 * physical_tolerance, 1e-12))
```

For the frozen physical contact tolerance `1e-9`, this gives `1e-12`. The
physical acceptance gate remains the maximum normalized per-contact residual
`<= 1e-9`; optimizer `success` alone never accepts a contact solution. The
optimizer's cost, optimality, gradient norm, and stop tolerances are recorded
when the candidate still fails.

Unchanged: model geometry and mesh hierarchy; material; boundary conditions;
normal and tangential loads and load steps; friction coefficient; surface
stiffness density; solver backend; 500-evaluation least-squares cap; 30-step
semismooth refinement budget; 25-iteration normal active-set cap; enumeration
guard; fallback policy; and all physical gates.

## Execution order

Run one process at a time in this order:

1. M1 stick, then M1 slip.
2. Only if both M1 cases pass: M2 stick, then M2 slip.
3. Only if both M2 cases pass: M3 stick, then M3 slip.

Stop at the first failed process or diagnostic gate. Never overwrite results or
retry a case. Outputs belong only in
`qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_11_optimizer_20260926/`.

M4 is not part of this contract. Any new M4 attempt requires a separate
prospective contract, a fresh output directory, and separate Owner
authorization. Historical R1.10 M4 evidence remains immutable.

## Interpretation limits

Passing M1/M2/M3 demonstrates only that the declared experimental, bounded
cases passed their frozen diagnostic gates on this source revision. It does
not establish general frictional-contact robustness, independent global FEM
agreement, replay determinism, formal WP08 points, or release readiness.
