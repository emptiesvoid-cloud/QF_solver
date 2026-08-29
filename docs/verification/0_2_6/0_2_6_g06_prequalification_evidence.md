# 026-G06 J2 Prequalification Evidence

## Decision boundary

`026-G06` remains **NOT_STARTED** as an official gate. This pack records a
controlled prequalification replay and proposes `PASS_WITH_LIMITATIONS`; it
does not promote the J2 maturity claim or close the gate automatically.

The official scope is the **J2 maturity extension**. Small-strain J2 is the
in-scope capability. Finite-kinematic J2 remains `RESEARCH_NOT_QUALIFIED`, and
coupled nonlinear workflows remain `EXPERIMENTAL_NOT_QUALIFIED`.

## Provenance

| Item | Value |
| --- | --- |
| Execution source SHA | `ad99f699a3b07368401f7607060bc06bb1860205` |
| Branch | `chore/0.2.6-foundation` |
| Source worktree | `dirty=false` |
| Solver | `qf_solver 0.2.6a0` |
| Registry digest | `d2e5f587ac2d67c3c875782c8558aa7aac60cec09df9f43614319eff1b99ea59` |
| Campaign manifest SHA-256 | `9bb8f3ab3642b9a9bf3f1e13f4053d25aa8ebdca7bcd3145eb5deed6601851c8` |
| Quantitative manifest SHA-256 | `ee9c3d7b894f034e87384c2a6251100b9416291af35c5d7ed82c1a9bb543e5b5` |
| Environment | Windows AMD64, CPython 3.13.1, NumPy 2.2.6, SciPy 1.15.2 |

## Controlled G06 corpus

Command:

```text
python scripts/run_vnv_026.py --profile G06 --output results/vnv_026_g06_prequalification
```

| Result | Count |
| --- | ---: |
| PASS | 79 |
| EXPECTED_FAILURE | 1 |
| FAIL | 0 |
| BLOCKED | 0 |

The 80 cases contain 19 TET4, 6 TET10, 33 HEX8, 17 HEX20, 2 MITC3, 2 MITC4
and 1 BEAM2 case. The J2 subset is **7 PASS**: TET4 (3), HEX8 (2) and HEX20
(2). There is no dedicated TET10 J2 case in the current G06 registry. TET10
J2 V&V tests outside this corpus pass, but they are not silently counted as a
G06 corpus case.

The single expected failure is `VNV026-RBT-G06-024`, an inverted TET4 rejected
as `INVALID_ELEMENT`. It is a controlled negative case, not an unexpected
failure.

## Quantitative evidence

The independent analytical study passes **20/20** cases across TET4, TET10,
HEX8 and HEX20 with maximum relative error `0.0` against the constrained
free-DOF stiffness oracle and tolerance `1e-10`. This is linear-elastic
evidence and is not a J2 constitutive oracle.

The separate HEX8 uniform axial bar study uses four levels (`nx=1,2,4,8`).
Relative tip-displacement errors are `0.09`, `0.0577737`, `0.0441261` and
`0.0399926`; the trend is non-increasing. Residuals remain between
`9.04e-17` and `2.46e-15`. This is bounded mesh evidence for that bar only,
not a general J2 mesh-convergence claim.

## Targeted verification

The J2, nonlinear-state, tangent, solid-element and robustness selection
returned **102 passed, 3 skipped, 0 failed** in `186.66s`. Ruff, compileall,
registry validation, anti-forgetting validation and `git diff --check` passed.
Full regression was not rerun because the G05 closeout and this pack contain
no functional FEM change.

## External evidence and limits

No compatible Code_Aster or CalculiX G06 deck was executed in this local
prequalification. Both external entries are therefore `SKIPPED`, never
`PASS`. The pack makes no external-correlation claim.

Remaining evidence required before an official G06 closeout is a dedicated
TET10 small-strain J2 corpus case if the family-wide scope is retained, a
compatible external correlation, and an explicit Owner promotion decision.
Finite-kinematic J2 and coupled nonlinear workflows remain outside the
qualified claim.

## Status

| Item | Status |
| --- | --- |
| Prequalification pack | `PASS_WITH_LIMITATIONS` |
| Official `026-G06` | `NOT_STARTED` |
| Proposed decision | `PASS_WITH_LIMITATIONS` |
| Unexpected failures | `0` |
| Numerical source change | `NO` |

`SUPPORTED != TESTED != VERIFIED != QUALIFIED` remains enforced.
