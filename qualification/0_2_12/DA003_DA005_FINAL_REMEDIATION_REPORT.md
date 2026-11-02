# DA-003 and DA-005 final remediation

## Follow-up after acceptance review of 4cf69066

The float32 BiCGSTAB counterexample and direct HEX20 load-integrator findings were subsequently addressed. Residual certification now promotes the represented matrix, right-hand side and solution to float64/complex128 before the product and subtraction, with exact-conversion checks. The direct load integrator checks targets and rejects non-finite local and accumulated contributions before filtering; distributed-load parsing rejects coerced element indices, and the HEX20 body-load path rejects non-finite coordinates, force density and Jacobians. See `PR119_FINAL_NUMERICAL_CORRECTIONS.md` for the reproductions, limits and current verdict. The historical review and evidence below remain applicable to their stated commits.

## Identity and scope

- PR #119 source at start: `75241bc57eb6b49d6ba67ace011c277a9137eadf`; target base: `d31614f59341d175d8e2daade92daf7d8149d199`. The final commit is identified by the PR head.
- The original unstaged HEX20 fix was preserved. No worktree, branch, historical oracle, WP12 result, or v7 ledger was removed or rewritten.
- Two independent read-only explorers using the available runtime examined the residual bound and HEX20 paths. Luna workers were not routed: the current model-router identity does not authorize claiming or routing a Luna-only worker. The coordinator reproduced the decisive counterexamples and performed the edits and checks below.

## DA-003: local HEX20 matrices

The existing determinant guard accepted a regular cube scaled by `1e-100` with `E=1e200`; `B.T @ C @ B` overflowed before multiplication by the determinant. The former implementation returned 2,988 NaNs and 612 infinities. `stiffness` now checks the final symmetrized matrix and raises `ValueError` if any entry is non-finite. The reported example is rejected by a regression test. The `1e-107` subnormal and `1e-108` zero determinant cases remain rejected, while the existing regular stiffness/mass test and scales `1e-100` and `1e100` pass.

An additional local reproduction with `density=1e200` and cube scale `1e40` returned 3,600 non-finite mass entries. A test first failed on the old code; `mass` now also rejects a non-finite final matrix. This does not establish accuracy of finite matrices, nor change any geometry threshold.

Other HEX20 paths were examined. The nonlinear assembler has a downstream non-finite force/tangent check. At the earlier reviewed commit, `_hex20_body_vector` was observed to return non-finite components for directly supplied NaN coordinates; the follow-up described above addresses that direct path. No other element family was changed in this earlier remediation.

## DA-005: residual bound and integer inputs

The previous guard estimates each sparse row's matvec and subtraction error with a multiple of `eps*(nnz+1)*sum(abs(a)*abs(x))`, a subnormal allowance, and a norm margin. Under finite IEEE binary64/complex128 values, round-to-nearest, gradual underflow, and a conventional bounded-operation CSR multiply/add, a standard gamma-n absolute error analysis makes such a conservative factor plausible. `math.fsum` accumulates already rounded magnitude products; the 32-epsilon margin is intended to cover their rounding and complex real-component operations. Neither a formal proof of every implementation step nor a guarantee for arbitrary dtype, compiler, BLAS, flush-to-zero mode, or platform is established. The prior reviewer classified the general claim as `INSUFFICIENT_EVIDENCE`; this report does not upgrade it to a mathematical theorem.

A further counterexample was reproduced: integer matrix `A=[[-2**63,2**63-1],[0,1]]`, `b=[0,1]` produced `x=[1,1]`, reported zero residual and `converged=True`, while exact integer arithmetic gives residual -1. `np.abs` of the signed minimum overflowed in integer arithmetic and `2**63-1` was rounded during conversion to float64. Magnitudes are now promoted before absolute value; integer matrix and RHS inputs not exactly representable in float64 are rejected before ordinary, complex, or reusable-factorization solves and at residual validation. Exact integer inputs remain accepted. This preserves input identity instead of silently certifying a rounded system.

The original CG underflow and floating cancellation examples remain rejected. A deterministic coordinator check using exact `Fraction` arithmetic and NumPy RNG seed `20261103` covered 60 real and 60 complex matrices, sizes 1, 3, and 10, five samples at each of four scales (`1e-140`, `1e-20`, `1`, `1e140`): 280 rows per type, zero violations of the row bound. Largest observed exact-error/bound ratios were 0.0077595 (real) and 0.0074771 (complex). These finite samples do not prove the bound generally. The existing review found 0 false rejections in 40 ordinary real systems; no new global false-rejection rate is claimed.

The computed residual, its arithmetic uncertainty, backward error and forward solution error are distinct. The convergence guard does not prove a small solution error in an ill-conditioned system. Conservative bounds can reject usable solutions; unrepresentable integer inputs now raise `NumericalConvergenceError`. An integer-valued input accepted before this change can therefore be rejected explicitly.

## Validation and preservation

Each invocation selected one test-function nodeid. Final targeted checks: 27 functions and 34 parameterized cases PASS. They cover both non-finite HEX20 regressions, standard rigidity/mass, small/large scales, inverted/degenerate/distorted geometry, historical residual counterexamples, exact-zero and ordinary solves, signed/unsigned integer inputs, reusable factorization, complex solve, the three spring guards, contact JSON/Markdown, and nodal input validation. Ruff and in-memory compilation of the four changed Python files passed; `git diff --check` passed. The initial red regressions for integer cancellation and mass overflow were observed before their corrections. The initial stiffness regression had already been reproduced in the independent review and passes against the preserved local fix.

No global FEM solve, WP12 campaign, v7 smoke, full CI matrix, or package rebuild was run. The v7 hashes and six smoke results continue to identify only the old artifacts. A new package requires a new artifact contract and applicable authorizations. G03 remains `FAIL_PRESERVED`, independent legal review `NOT_ACQUIRED`, and no global scientific qualification is claimed.

## Recommendation

`REMEDIATION_READY_FOR_INDEPENDENT_ACCEPTANCE` for the identified stiffness/mass and integer-conversion defects, subject to independent assessment of the conditional bound and the explicitly open helper and numerical-domain risks. This recommendation does not authorize merge, tagging, or publication.
