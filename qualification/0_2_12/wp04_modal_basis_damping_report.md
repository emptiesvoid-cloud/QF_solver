# WP04: Modal Basis / Damping

**Status:** `PASS_WITH_RECORDED_LIMITATIONS`

**Branch:** `codex/v0.2.12-wp04-modal-basis-damping`

**Base:** `62bf6bfe6296b4b68ac372c32fc59e020dfbe78c`

## Scope delivered

WP04 adds an operator-bound `ModalBasis` for the bounded WP00 domain. It uses
the existing `PreparedDynamicSystem` K/M and the existing
`ModalAnalysisSolver._solve_eigenproblem` dense, `eigsh` or `lobpcg` backend.
It constructs and retains the actual projected `Mr = Phi.T M Phi` and
`Kr = Phi.T K Phi`, checks modal residuals and mass orthogonality, and offers
full/reduced RHS and WP03 real/complex channel projection. It does not solve a
forced harmonic or transient problem and does not alter element formulations
or the historical `ModalAnalysisSolver` route.

The implementation is split into:

- `src/solveur/core/analyses/modal_basis.py`: basis lifecycle, extraction,
  projection, identity, truncation diagnostics and damping factories;
- `src/solveur/core/analyses/modal_basis_numerics.py`: preregistered spectral
  screens, cluster and residual metrics, validation and immutable snapshots;
- `src/solveur/core/analyses/modal_basis_damping.py`: immutable reduced
  damping record and damping provenance.

The basis stores copied read-only arrays and no model or prepared-system
reference. Its exact identity includes the WP02 operator identity and DOF map,
extraction settings, selected eigenpairs, projected operators, clusters and
contract version. Consumers must pass a compatible `PreparedDynamicSystem`;
operator or mapping mismatch is rejected. An excitation-only change does not
change the operator identity and therefore does not invalidate the basis.
There is no process-global cache.

## Spectral domain and selection

The new path requires finite sparse real symmetric K/M. It applies diagonal
congruence scaling and the frozen positive-definiteness screen to each
operator. Up to 256 reduced DOFs, the screen uses Cholesky plus a symmetric
eigenvalue check. Above that size, it uses the smallest-algebraic Ritz pair
from sparse `eigsh`, checks convergence and its residual, and records that this
is a numerical screen, **not a formal proof** of global SPD. Non-positive or
rigid eigenvalues, non-finite eigenpairs, excessive modal residuals, and
unacceptable mass orthogonality fail closed. This is stricter and local to the
new infrastructure; historical analysis routing is unchanged.

The requested lowest positive modes are selected with one look-ahead mode.
Clusters use the preregistered relative eigenvalue-gap threshold `1e-8`; an
identified cluster crossing the requested cutoff is rejected, never silently
expanded. Exact-degenerate spans no greater than `1e-12` may be mass
orthonormalized within their subspace. Near-degenerate but distinct modes are
not rotated. Subspace comparison uses the mass metric and is invariant to
sign, ordering and admissible subspace rotation. These are numerical cluster
rules, not statements that two physically distinct modes are identical.

The basis reports selected mode count, frequencies, modal residuals, mass
orthogonality, projected stiffness consistency, clusters, retained frequency
band, unrepresented spectrum and explicit limits on participation ratios.
Modal residual is not presented as a physical truncation-error estimate.
Residual flexibility is not implemented; it remains OPTION-A.

## Damping and result availability

Rayleigh damping reuses the existing `rayleigh_damping_definition` and
projects the declared physical model `C = alpha M + beta K`, checking the
result against `alpha Mr + beta Kr`. Coefficient units are `alpha: s^-1` and
`beta: s`. Reaction availability is `NOT_COMPUTED` because WP04 does not
perform a full-space response equilibrium.

Prescribed modal damping constructs a reduced operator from `zeta_j` and
`omega_j`. Ratios must be finite and non-negative; zero is valid. For an
identified cluster, unequal damping ratios beyond the frozen absolute spread
`1e-12` are rejected. A cluster instead receives the explicitly recorded
invariant scalar block `2*mean(zeta_j*omega_j)*I`. This is a prescribed reduced
model, not a projection of a complete physical full-space C. Its physical
reaction status is `UNAVAILABLE`; no full-space C is fabricated.

The result-availability contract distinguishes available eigenpairs and
reduced modes, full modes that are reconstructible only with the same prepared
system, reactions not computed or unavailable, stress not applicable, and
full response not applicable in WP04. Numerical `PASS` does not imply
qualification. `ModalBasis.maturity` remains `EXPERIMENTAL`.

## Verification

The frozen numerical thresholds are in
[`wp04_modal_basis_damping_contract.json`](wp04_modal_basis_damping_contract.json).
They were not relaxed or changed after observing results.

WP04-specific tests cover an analytical two-DOF generalized eigenproblem with
non-diagonal M, mass normalization, residuals, projected operators, all five
WP00 element families, a sparse 270-DOF extraction, cluster cutoff rejection,
degenerate-subspace and sign invariance, Rayleigh and prescribed modal damping,
reaction availability, inadmissible spectral matrices, WP03 real/complex RHS
projection, operator mutation invalidation, defensive snapshots, and the
historical modal route.

```text
python -m pytest tests/unit/test_modal_basis_damping.py -q
15 passed

Targeted WP02/WP03/WP04 modal, excitation and dynamic-controls regression set
92 passed

python -m pytest tests/unit -q
3213 passed, 93 skipped, 0 failed, 6 warnings
```

The earlier WP03 full-suite attempt had been interrupted by the operator at
about 45% after prolonged CPU-bound legacy numerical tests. The complete run
above crossed that point and finished successfully; the earlier interruption
was not a test failure. The 93 skips remain `SKIPPED`, not PASS. The six
warnings comprise the repository's source-size advisory and five existing
NumPy determinant runtime warnings in WP15b/WP19 tests. No new WP04 source
file exceeds the repository's 700-line maintenance objective.

Repository-wide Ruff check passed for `src/qf_solver`, `src/solveur`, `tests`
and `scripts`. Ruff format check passed for changed code/tests. Mypy passed on
all three new production modules. The WP04 contract parsed as valid JSON.

## Bounded performance observations

These are local smoke measurements, not scaling or industrial-performance
evidence. Times are single bounded-fixture observations except for the
synthetic dense/sparse comparison, which reports the measured median.

| Fixture | Reduced DOFs / retained modes | Preparation | Extraction | Basis-owned arrays | Projected damping | RHS projection |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TET4 | 3 / 3 | 0.00420 s | 0.00195 s | 216 B | 72 B | 8.07 us/RHS best of local repeats |
| HEX20 | 36 / 36 | 0.07097 s | 0.00426 s | 31,104 B | 10,368 B | 8.22 us/RHS best of local repeats |
| Synthetic diagonal sparse operator | 270 / 6 | n/a | dense median 0.014264 s; `eigsh` median 0.002920 s | 13,536 B | not measured | not measured |

Prepared sparse K/M storage for the small fixtures was: TET4 full K/M 916/628
B and reduced K/M 52/52 B; HEX20 full K/M 43,444/14,644 B and reduced K/M
15,700/5,332 B. Extraction timing includes eigensolver, normalization and
validation; normalization was not isolated as a separate timing. Projection
measurements are local microbenchmarks. Defensive property access returns
copies, so consumers incur copy cost when requesting exposed matrices; no
global cache or factorization reuse is introduced by WP04.

The synthetic diagonal comparison is an algorithm smoke test only. It does
not characterize structural sparse scaling. Full-basis projection equality
was checked on bounded analytical/element fixtures only and is conditional on
matching K/M, constraints/mapping, damping model, excitation, initial state
and numerical scheme. It is not asserted for a truncated basis or for
prescribed modal damping compared with a different direct damping model.

## Gate contribution and limitations

- `QF0212_G02_WP04_MODAL_BASIS = PASS`; `QF0212_G02_GLOBAL = OPEN` for later
  consumers and architecture integration.
- `QF0212_G03_DYN_MODAL_EXTRACTION = PASS` for the bounded symmetric
  generalized eigenproblem; `QF0212_G03_NL = NOT_YET_APPLICABLE`.
- `QF0212_G04_DYN_WP04 = PASS` for the analytical, residual, projection,
  cluster and damping checks; response-solver behavior remains
  `NOT_YET_APPLICABLE`.
- `QF0212_G05_WP04_AND_UNIT_NONREGRESSION = PASS`; the global interface gate
  remains open for later WPs.

Recorded limitations: the sparse SPD test is an estimate rather than formal
proof; numerical cluster thresholds do not encode physical mode identity;
truncation diagnostics do not estimate local displacement/stress error;
prescribed modal damping has no inferred physical full-space matrix or
physical reactions; and no forced harmonic/transient solve or residual
flexibility correction is included. No maturity, qualification or historical
decision was promoted or rewritten. Historical `G03 = FAIL_PRESERVED`,
`WHOLE_REPOSITORY_ARCHIVE_CLEARED = NO`, and `WP14 = HOLD_NOT_PROMOTED`
remain unchanged.

WP05 can consume the modal basis and damping interfaces after separate Owner
authorization. WP06 remains dependent on WP05. No later work package has been
started.
