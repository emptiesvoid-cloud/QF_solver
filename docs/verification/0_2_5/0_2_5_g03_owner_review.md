---
doc_id: DOC-NL-025-034
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: Owner
approver: pending
---

# QF Solver 0.2.5a0 — Owner Review 025-G03

## Decision scope

This review covers the bounded first tangent-instability path only. It does
not qualify post-buckling, imperfection-sensitive collapse, nonlinear
stability beyond the first tangent loss, or external buckling for every solid
family.

## Evidence

| Evidence | Result | Location |
|---|---|---|
| Sparse initial-stress geometric tangent | PASS | `src/solveur/core/buckling.py` and solid assembly implementations |
| Exact pure-geometric tangent unit check | PASS | `tests/unit/test_linear_buckling.py` |
| Targeted buckling/regression tests | `26 passed` | local targeted run on qualified source SHA |
| Euler refinement | PASS | `results/vnv_0_2_5/g03_euler_final/summary.json` |
| Code_Aster factor/mode probe | PASS_EXTERNAL_CORRELATION_BOUNDED | `results/vnv_0_2_5/g03_final/summary.json` |
| Adversarial failure contract | PASS | `results/vnv_0_2_5/g03_final/adversarial.json` |

The qualified source SHA is:

`85c75d06955976251dd54ad782f57f1eb5a7f8f4`

Both final evidence manifests record `dirty=false` at generation time. The
Code_Aster image is pinned to
`simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435`.
The current local replay could not start because the image launcher lacks
`mpi4py`; this is recorded as an environment limitation and does not replace
the archived Code_Aster execution.

## Measured correlation

| Quantity | QF Solver | Code_Aster | Difference |
|---|---:|---:|---:|
| First critical factor | 221.54828247814925 | 221.774 | 1.018e-3 relative |
| Best modal MAC | 0.9999999989229131 | 1.0 reference | bounded agreement |
| QF critical-mode residual | 1.72e-15 | archived residuals <= 5.07e-15 | converged |

The Euler four-level campaign reports critical-load changes of `15.63 %`,
`6.57 %` and `3.31 %` between successive levels. The finest level is within
`5.89 %` of the analytical Euler reference. These results support a bounded
refinement trend; they do not establish universal convergence.

## Qualified claim

`linear_buckling` is qualified for the sparse first tangent-instability path
in the recorded total-Lagrangian solid scope, with TET4 as the externally
correlated family. TET10, HEX8 and HEX20 remain internal/research for this
gate. CalculiX remains a SHOULD comparison and its negative high-order probe
is retained as diagnostic evidence; it is not a G03 blocker.

`CONTRACT_LOWERED = NO`

## Owner decision

**Recommended decision: APPROVED for the bounded scope above.**

The release-level Owner signature remains a separate governance action. No
push, tag or PyPI publication is authorized by this document.
