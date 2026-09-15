# WP08-D hybrid stick/slip M2 requalification

## Scope and provenance

The authorized base was `48b8059b9b626601f9cfdff7afbc1f7c4e520279`. The
production correction is limited to the hybrid active-slip root: the direct
iteration classification is retained, stick contacts contribute elastic KKT
terms, and only observed slip contacts enter the nonlinear root. The normal
active-set, cone, open-contact, finite-state and rollback checks remain
fail-closed.

No threshold, mesh, load, material, friction coefficient, tangential stiffness,
tolerance, iteration limit, backend, fallback policy or contract changed.

## M2 production

The new production evidence completed all 7 frozen increments with no fallback.
The active normal set was `[3, 7, 11]` at every increment. The observed states
were:

| Increment | States at contacts 3, 7, 11 | Route |
|---:|---|---|
| 1 | slip, slip, slip | hybrid root |
| 2 | stick, stick, stick | direct |
| 3 | stick, stick, stick | direct |
| 4 | stick, stick, stick | direct |
| 5 | stick, stick, slip | hybrid root |
| 6 | stick, stick, stick | direct |
| 7 | slip, slip, slip | hybrid root |

At the required mixed state on increment 5, the root used contacts 3 and 7
as stick contributions and contact 11 as the only slip unknown (dimension 2).
The post-root normal set remained `[3, 7, 11]`; the maximum complementarity
was `2.1828783600599047e-14`. Stick-cone, slip-cone/alignment, open-contact
zero-force/reference, finite-state and rollback checks passed. The independent
forensic SSK residual is `2.2752821848825988e-10`.

Production equilibrium passed with force relative error
`2.5698104088128976e-14` and moment relative error
`4.504766104249868e-14`.

## Independent reference and fail-closed outcome

The independent NumPy/KKT reference did not pass the same M2 dependency. It
accepted increments 1–4, then failed at increment 5 with:
`Independent active-slip root failed: residual=3.290e+00.`
It did not import production contact routines. Per the authorization, replay
was not run and M3 was not run.

Therefore the production result is retained as a candidate execution result,
but the M2 campaign is `FAIL_CLOSED_REFERENCE`; this task awards no points.

## Validation and governance

Targeted contact/friction tests: 49 passed. Ruff, targeted mypy, compileall,
JSON/JSONL/manifest-hash validation and `git diff --check` passed. The full
repository suite was not run. WP05, WP06, H4 and M3 were not run.

`WP08D_FORMAL_POINTS = 0/2` and `WP08_FORMAL_POINTS = 0/8`. The raw production
and reference artifacts are preserved under
`qualification/0_2_9/wp08d_phase1_hybrid_stick_slip_requalification/`.

Final source SHA at execution/report generation: `624e5ba6759a296efba24ca4f5b1b7bc1c4b8238` (the evidence
commit added afterward is reported by Git). Final status:
`OWNER_REVIEW_REQUIRED_BEFORE_M3`.
