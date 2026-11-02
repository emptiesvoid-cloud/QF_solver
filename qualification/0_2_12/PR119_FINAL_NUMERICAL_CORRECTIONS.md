# PR #119 — final numerical corrections

## Identity and scope

- Starting PR HEAD: `4cf69066b191936550548073e4aae9ff5b989128`; target base: `d31614f59341d175d8e2daade92daf7d8149d199`.
- The review documents in `final_acceptance_4cf69066` were read. Two workers using the available runtime worked on disjoint residual and distributed-load files; no Luna worker was claimed or routed under the active model identity policy. The coordinator reproduced the counterexamples, reviewed the diff and reran selected tests.
- The final commit is identified by the PR head. No source branch other than the corrective branch was modified.

## DA-005 — residual certification

Before the change, CSR `float32` matrix `[[10000, 0.0001, -10000], [0,1,0], [0,0,1]]` and `b=[0,1,1]` produced `bicgstab` solution `[1,1,1]` in float32. The float32 product gave `[0,1,1]`, and the solver incorrectly returned `converged=True`, relative residual zero. Exact `Fraction` arithmetic on the represented float32 values gives first-row residual `9.999999747378752e-5`, relative `7.071067615557609e-5`, above the existing `1e-7` limit.

Certification now promotes matrix coefficients, RHS and returned solution to float64/complex128 **before** the sparse product and subtraction. This exact widening preserves the represented binary32/complex64 inputs; it cannot recover information already lost during the original solve. A conversion that changes a represented value or is non-finite is rejected. Matrix conversion is checked in bounded chunks, before a CSC-to-CSR format conversion can reorder entries. Existing integer identity checks remain, and reusable real factorization checks the original RHS before converting it.

The counterexample now raises `NumericalConvergenceError` with relative residual `7.071068e-05`. Independently, CG, GMRES and BiCGSTAB on float32 `A=[[3]], b=[1]` report relative residual about `2.98023215e-8` and pass at `1e-7`; they reject it at `1e-10`. Ordinary float64, complex64, CSC, zero RHS, previous cancellation/underflow, non-finite solution diagnostics, integer and direct-refinement cases were tested. On this Windows runtime `longdouble` has no extra precision: three tests requiring a wider type were skipped and must not be represented as passing evidence for other platforms.

The residual is measured for the represented inputs and returned solution, not the exact physical solution. Its arithmetic uncertainty bound, backward error and forward solution error are different quantities. The existing bound still relies on the documented binary64/complex128, rounding and gradual-underflow assumptions and is not proven for every platform or floating-point mode. Conservative rejection remains possible; no tolerance or historical oracle changed.

## Direct HEX20 distributed-load integration

Before correction, calling `DistributedLoadIntegrator.integrate_sparse` directly on a `from_raw` HEX20 model with a NaN coordinate returned an empty load vector and NaN resultant; finite coordinates scaled to `1e104` produced 12 non-finite sparse values. These were direct Python integration calls, not global FEM solves. Model-based solver routes using `MeshValidator` already rejected those models.

The integrator now validates selected element indices, rejects non-finite local contributions and accumulated nodal values before its sparse filter, checks balance and norm outputs, and uses a stable L2 norm. The HEX20 body-load routine checks coordinate and force-density shape/finiteness, determinant finiteness and local-vector finiteness. Both historical examples now raise `InputValidationError`. Valid regular HEX20 resultant, dense/sparse agreement and large finite load norm tests pass. Empty explicit target lists retain their existing no-op behavior. The historical `1e-30` sparse cutoff and the existing HEX20 Jacobian cutoff are unchanged; this work does not establish a new mesh or load qualification domain.

Review of target selection found an earlier conversion in `from_raw`: body target `0.9` was silently converted to element `0`, and booleans and strings were also coerced. Regression tests first reproduced those three cases. Distributed-load parsing now requires integral, non-boolean element indices for body, gravity, surface, edge and line loads; a NumPy integer target and normal JSON integers remain supported. This is a documented API tightening in `docs/schema_json.md`. It prevents selecting an unintended element without changing any load formula.

## Validation

On Python 3.13.1 / Windows, the coordinator ran 39 distinct exact test-function nodeids, one per pytest invocation: 55 cases passed and 3 were skipped because long double has no additional precision on this platform. Tests cover the corrections, standard systems, float32/complex64, CSC, chunk boundary, integer checks, zero RHS, overflow/underflow, direct refinement, target indices and raw-index coercion, accumulation overflow, stable load norms, DA-001 spring rejection, DA-002 contact metadata, DA-003 non-finite element matrices and DA-004 nodal inputs. Workers also ran targeted tests. No module or full-suite pytest target was used for this follow-up.

Ruff, Python syntax compilation and `git diff --check` passed on the changed files. No global FEM solve, WP12 campaign, v7 smoke, benchmark or full CI matrix was run. The tests are targeted engineering evidence, not scientific qualification.

## Release impact and verdict

The distributed solver source changed. WP13 v7 hashes and smoke results apply only to the earlier frozen artifacts; a future package needs a new artifact contract and applicable installed-package checks. G03 remains `FAIL_PRESERVED`, independent legal review `NOT_ACQUIRED`, and no global scientific qualification is claimed.

`PR119_READY_FOR_FINAL_ACCEPTANCE` — ready for independent counter-review of these bounded changes. It does not authorize integration, tag, publication or a new FEM campaign.
