---
doc_id: DOC-029-WP05-INTEGRATION-001
revision: 0.1
status: owner_review_required
applicable_version: 0.2.9-development
---

# QF Solver 0.2.9 — WP05 governing-branch integration audit

## Decision

The Owner-frozen high-order candidate was integrated by explicit
non-fast-forward merge into `0.2.9-unified-nonlinear`. Targeted governing-tree
revalidation passes for the bounded TET10/HEX20 mechanics identities and the
structural-contract harness. Therefore **WP05-A = PASS (1/1)** and **WP05-B =
PASS (1/1)**. WP05 is **2/5** and the validated total becomes **45/100**.

WP05-C, WP05-D, and WP05-E remain **0/1** each. This integration ran no H1,
H2, H3, or cross-family structural solve and makes no maturity change.

## Provenance and merge

| Item | Value |
| --- | --- |
| Governing pre-merge SHA | `12b5331bcbec49e38145ba4a6263df60b8bf4575` |
| Child head | `2ec2cbadf05e12a9ff73d139c5513d549925b9ec` |
| Merge base | `2c52bf8196a7d47d14ce1784290580160de26590` |
| Merge commit | `2f1de58ebb9395f05d722dfa411222774787a881` |
| Conflict | `docs/document_registry.json` only |

The registry was resolved semantically: the governing WP04-F/WP15 records and
all WP05 readiness, identity, and structural-contract records are retained.

## Preserved high-order contract

The historical equal-share end-face load rule remains explicitly **rejected**.
Future qualification uses uniform traction at `x=L`, with resultant
`[0,-50,0]` and global-origin moment `[12.5,0,-200]`. The qualification harness
alone converts that traction to public-solver nodal dead loads:

- TET10 uses quadratic T6 faces and three-point degree-2 barycentric surface
  integration.
- HEX20 uses quadratic Q8 faces and tensor 2x2 Gauss surface integration.

The frozen H2-to-H3 limits remain displacement/reaction-resultant/reaction-
moment/energy `<=2%`, representative stress `<=8%`, vector equilibrium
`<=1e-8`, envelope `det(F)>=0.20`, stretches `[0.75,1.30]`,
`||E_GL||_F<=0.30`, and H1 replay relative/absolute limits `1e-12/1e-14`.
No threshold was changed.

## Governing-policy binding

Future WP05-C/D execution is bound to governing SHA
`12b5331bcbec49e38145ba4a6263df60b8bf4575` and policy digest
`93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`, computed
over the geometric-static and nonlinear control/robustness/driver/iteration/
linear-solver/state sources. The frozen future route is canonical line search,
floor-aware termination, MINRES with Jacobi, `rtol=1e-11`, `atol=1e-14`,
`maxiter=10000`, and direct fallback disabled.

## WP04/WP15 protection

The WP05 child contributes no production source files. The post-merge diff
does not change the WP04 mechanics, nonlinear termination, router, or WP15
telemetry surfaces. WP04 remains CLOSED 12/12 and WP15 remains CLOSED 2/2.

## Validation

The WP05 identity/readiness selection reports **60 passed**; the final combined
integration selection reports **141 passed**. Ruff, targeted mypy, compileall,
JSON validation, document-registry checks, and MkDocs strict pass. No full
repository suite, H2/H3 structural qualification, PETSc work, or WP06 work is
included.

## Next step

Owner review before WP05-C/D structural execution, or integrate the next
separately Owner-frozen child. This audit does not authorize merging WP06.
