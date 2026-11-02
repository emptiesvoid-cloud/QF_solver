# WP13 CI Eight-Failure Remediation — Independent Review

## Scope

Two read-only Luna reviews examined the DA-001 fixture change and DA-005 residual certificate change. Neither reviewer edited files or ran tests. Terra separately ran the authorized targeted tests and checked the resulting code and numerical evidence.

## DA-001 review

The independent reviewer confirmed that the revised fixture has no discrete spring, includes a supported nondegenerate TET4 and valid material, and retains a contact projection within the master triangle. It therefore reaches contact-parameter validation before assembly. The production spring guard remains in its intentional position, preserving rejection of unsupported spring models. Terra then ran the exact failing nodeid and observed one passing test.

## DA-005 mathematical review

The independent reviewer examined the real float64 CSR `gamma_(2k)` bound and the follow-up fixes for typed dispatch and exact-zero cases. It confirmed that:

- the tighter helper is restricted to native float64 operands; exact promotion is already performed by the validated solver path;
- nonzero products that underflow to zero retain product-sum and operation underflow allowances;
- all-zero rows have exact zero dot-product uncertainty;
- subtraction uncertainty is omitted only when the represented operands are equal, giving an exact zero subtraction;
- when uncertainty is positive but the denominator lower bound is zero, the certificate fails closed;
- complex and other dtypes remain on the prior conservative route.

The reviewer found no reproducible false-pass path in the solver certification path. It noted the operation model and IEEE assumptions that remain part of the bound's scope, and that residual certification is not forward-error certification.

## CSR operation model

The source for the installed SciPy 1.15.2 implementation shows that the CSR matvec initializes each row sum, then loops over the stored row entries and performs `sum += Ax[jj] * Xx[Aj[jj]]`. This supports a bound using at most one product and one accumulation per stored entry. The implementation remains dependent on IEEE round-to-nearest and gradual underflow; unsafe compiler reassociation or a materially different backend is outside the verified scope. See the [SciPy 1.15.2 CSR implementation](https://github.com/scipy/scipy/blob/v1.15.2/scipy/sparse/sparsetools/csr.h#L1035-L1070).

The bound explicitly rounds componentwise error enclosures outward, adds subnormal allowances for products and accumulations, accounts for final subtraction, and rounds the norm, denominator and ratio bounds outward. A Fraction-based regression test independently checks severe cancellation and a half-minimum-subnormal case against exact rational arithmetic over the stored binary64 inputs.

## Evidence and decision

The seven failed CI states were captured before remediation and checked with 100-digit arithmetic. Their exact represented-system relative residuals were all below `1e-7`; the new upper bounds are `9.732e-8` at the largest (MITC4), `2.225e-8` for the arc-length states, and below `4.724e-9` for the two TET reference cases. All seven tests passed after the correction, and the DA-001 nodeid also passed. The unchanged MITC4 displacement oracle differed by `0.2191%` against the test's `0.3%` tolerance. Arc-length branch/restart/rollback assertions passed. Both TET summaries remain `WARNING`: their TET10 analytical-reference errors exceed the existing 1% criterion. Those two tests only assert report creation and load-contract metadata, so their pass is not a numerical qualification result. Historical float32 cancellation, complex64, exact-integer, CSR/CSC, zero, nonfinite and overflow-related regression nodeids passed; two platform-specific wide-precision tests skipped as documented.

**Independent review finding:** no blocking defect identified in the changes examined, under the explicit real float64 CSR and IEEE assumptions above.

**Limits:** no Linux post-fix tests, full CI, v8 smoke tests, WP12 campaigns or global qualification were performed. The exact test results and numerical values are in [WP13_CI_TARGETED_TEST_RESULTS.json](WP13_CI_TARGETED_TEST_RESULTS.json). The v8 artifacts remain tied to the original source commit and do not qualify this corrective commit.

The targeted evidence supports a corrective PR for independent acceptance. It does not authorize merge or publication. G03 remains `FAIL_PRESERVED`, legal review remains `NOT_ACQUIRED`, and release remains `BLOCKED`.
