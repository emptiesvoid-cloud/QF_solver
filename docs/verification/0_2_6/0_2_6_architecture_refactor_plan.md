# Architecture Refactor Plan

## 026-WP04-ARCH implementation result

The first completed architectural batch groups the existing core
implementations by responsibility without changing numerical bodies, public
API, file formats or solver options:

| Domain | Implementation package |
| --- | --- |
| Assembly | `solveur.core.assembly` |
| Linear solvers and backend policy | `solveur.core.solvers` |
| Modal, dynamic, harmonic and stability analyses | `solveur.core.analyses` |
| Nonlinear state, contracts and strategies | `solveur.core.nonlinear` |

Legacy flat imports such as `solveur.core.assembler` and
`solveur.core.nonlinear_iteration` remain compatibility facades. They resolve
to the new implementation modules so existing 0.2.x callers and tests retain
their import paths while new code has explicit ownership boundaries.

The verification package remains intentionally flat in this batch. Its future
oracle/campaign migration is separate work and is not required to reorganize
the numerical core.

Modules near the repository 700-line limit are inventory candidates, not
automatic refactor targets. This batch did not split numerical functions or
change algorithmic thresholds merely to satisfy a line count.

### Migration Guard

Before every migration: capture fingerprints, run focused tests and keep the
compatibility facade. After it: rerun the same checks, compare results and
record the evidence. Stop on numerical drift, changed output schema or import
breakage.

## G04 acceptance boundary

- New implementation modules must be importable directly.
- Legacy flat module paths must resolve to the same module objects.
- Public `qf_solver` imports, CLI routes and serialized outputs must remain
  unchanged.
- The foundation smoke and representative route fingerprints must match the
  baseline exactly within the existing comparison policy.
- No verification maturity status is promoted by this structural refactor.
