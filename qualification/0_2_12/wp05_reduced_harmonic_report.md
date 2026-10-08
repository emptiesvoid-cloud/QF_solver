# WP05: Reduced Harmonic Response

**Status:** `PASS`

**Branch:** `codex/v0.2.12-wp05-reduced-harmonic`

**Base:** `436627b23ae079ae33646364f6333193a67695ba`

**Implementation commit:** `7c03166f90d418f80a00777d19339b935a156c76`

## Scope delivered

WP05 adds the explicitly selected method
`harmonic_response/modal_superposition`. The legacy
`harmonic_response/direct_frequency` route remains the default and continues
to use `HarmonicResponseSolver`. The new route composes the existing
`PreparedDynamicSystem`, `ExcitationChannelSet`, `ModalBasis`, and
`LinearSystemSolver.solve_complex`; it does not add an eigensolver or a time
integrator. Its maturity is `EXPERIMENTAL`, and numerical `PASS` is recorded
separately from qualification (`NOT_ASSESSED`).

The implementation is split across:

- `src/solveur/core/analyses/reduced_harmonic.py`: reduced frequency-domain
  solve, explicit damping selection, condition checks, residuals, provenance,
  and bounded timing/storage diagnostics;
- `src/solveur/core/results.py`: versioned `ReducedHarmonicResult` with
  explicit complex `real`/`imag` serialization and availability records;
- `src/solveur/core/router.py`, `src/solveur/core/analyses/settings.py`,
  `src/solveur/core/qualification.py`, and
  `src/solveur/compatibility/preflight.py`: additive method dispatch and
  method-specific experimental maturity;
- `src/solveur/core/analyses/prepared_dynamic_system.py` and
  `src/solveur/core/analyses/excitation_channels.py`: small consumer accessors
  for complex state reconstruction and stable bound channel identifiers.

No global cache is used. A supplied prepared system and modal basis are checked
against the current operator identity. Load-only changes preserve K/M and basis
identities while changing excitation and execution identities. When the
solver constructs its own prepared system, an exact source SHA is required
from a clean checkout, explicit `source_sha`, `QF_SOURCE_SHA`, or
`GITHUB_SHA`. An installed/API caller without those must provide an explicitly
identified prepared system or source SHA; no synthetic source identity is
invented.

## Numerical and input contract

For the explicit projected operators, the solver uses

```text
Zr = Kr + i*omega*Cr - omega^2*Mr
Fr = Phi.T*Fhat
Zr*Q = Fr
U = expand(Phi*Q)
omega = 2*pi*f, with input f in Hz
u(t) = Re[U*exp(+i*omega*t)]
```

`Mr`, `Kr`, and `Cr` are the actual WP04 projected matrices. The solver does
not replace them with an identity or diagonal matrix. Frequencies are finite,
non-negative Hz values. A single explicit channel set serves its matching
frequency; a sweep with frequency-bound phasors uses an exact
`frequency_hz -> ExcitationChannelSet` mapping. There is no interpolation.
Legacy real model loads continue through the WP03 adapter. Explicit channels
cannot be mixed with legacy loads or legacy temporal-load controls, preventing
ambiguous or duplicate amplitude application.

Two damping contracts are implemented:

- Rayleigh physical projected: `C = alpha*M + beta*K` and
  `Cr = alpha*Mr + beta*Kr`, using the existing coefficient definition
  (`alpha` in `s^-1`, `beta` in `s`). The full physical Rayleigh operator is
  available for the free-equation residual, but WP05 does not compute physical
  reactions.
- Prescribed modal: the WP04 reduced damping operator, including its invariant
  treatment of identified clusters. It is a reduced model, not an inferred
  full-space physical C. Physical residuals and reactions are therefore
  `UNAVAILABLE` with a reason; no full-space C is fabricated.

The preregistered values are in
[`wp05_reduced_harmonic_contract.json`](wp05_reduced_harmonic_contract.json):
scaled-impedance warning indicator `1e-8`, fail-closed indicator `1e-12`,
reduced backward error `1e-8`, full-basis physical free-equation backward
error `1e-8`, analytical fixture relative error `1e-10`, and bounded
full-basis/direct comparison relative error `1e-8`. The impedance is scaled
with `S*Zr*S`, `S=diag(1/sqrt(diag(Kr)))`; both a reciprocal condition estimate
and a singular-value floor are checked. This catches the scalar near-zero
impedance case as well as ill-conditioned multi-mode cases. Zero RHS does not
bypass the impedance check.

An initial development check showed that a full-space residual is generally
nonzero for a truncated basis. The contract therefore applies its strict
physical residual threshold only to a full-basis equivalence check; on a
truncated basis the same residual is reported as a diagnostic, not promoted
to a truncation-error estimate. No numerical tolerance was raised. This
clarification is recorded in the contract and was made before the WP05
qualification evidence was assessed.

## Results and availability

`ReducedHarmonicResult` stores complex response vectors and modal coordinates
without real truncation. JSON carries separate `real` and `imag` arrays and
round-trips through the versioned `qf-reduced-harmonic-result/v1` schema. Each
frequency record includes the requested frequency and resolved angular
frequency, channel identity, reduced backward error, physical free-equation
residual availability, and impedance conditioning diagnostics.

The result distinguishes:

- the reduced equation backward error, which is checked against the frozen
  numerical threshold;
- the full physical free-equation residual, available with Rayleigh C and
  strictly checked only for a full basis;
- physical reactions, `NOT_COMPUTED` for Rayleigh and `UNAVAILABLE` for
  prescribed modal damping;
- stress, `NOT_COMPUTED`;
- exact physical truncation error, `UNAVAILABLE`.

The reduced residual is not evidence that the omitted physical subspace is
unimportant. Participation diagnostics, where inherited from WP04, do not
guarantee local displacement or stress accuracy. Optional response probes
retain selected DOFs only; frequencies are solved sequentially, so no dense
`N_DOF x N_FREQUENCIES` response block is formed. This response-selection
feature is an output-retention control, not a stress-recovery feature.

The route is bounded to the WP00/WP04 admissible TET4, TET10, HEX8, HEX20, and
straight non-rotating BEAM2 domain with isotropic linear elasticity, fixed
homogeneous supports, admissible masses/springs, and accepted K/M operators.
Unsupported entities and methods fail closed on this route only. No contact,
rotor, shell, general prestress, MPC/RBE, nonlinear harmonic response, or
unhandled algebraic-coordinate support is added.

## Verification

The focused WP05 tests include an independent scalar SDOF complex response,
a coupled two-DOF system with non-diagonal M, zero and nonzero force, zero
frequency, exact and near resonance, phase factors 0/90/180 degrees, exact
multi-channel cancellation, frequency-specific channels, Rayleigh projection,
prescribed modal damping and reaction availability, serialization, response
probes, stale basis rejection, excitation-only reuse, the public router, and
each of the five bounded element families. The full-basis/direct check uses
the same K/M, supports, excitation, Rayleigh damping and frequencies; it is an
integration/non-regression check, not an independent physical oracle.

For the bounded TET4 direct comparison at 0, 1, and 3 Hz, the maximum relative
response differences were respectively `1.52e-16`, `7.43e-20`, and `2.97e-19`.
The maximum reduced backward error was `7.62e-17`; the maximum full-basis
physical free-equation backward error was `5.55e-17`. The analytical SDOF and
coupled two-DOF checks use independent closed-form / dense linear algebra
references and their tolerances are asserted in tests.

Truncation was characterized on the bounded three-DOF TET4 fixture. A request
for one mode is rejected because it cuts an identified modal cluster. With
two modes and three real spatial channels, the response-vector relative
difference from the full three-mode result was `19.8%` at 1 Hz, `19.8%` at
100 Hz, `16.1%` at 1,000 Hz, `45.6%` at 5,000 Hz, and `54.4%` at 10,000 Hz.
The two-mode reduced residual remains an equation-solve diagnostic and does
not expose this omitted-subspace discrepancy. These values are fixture
observations, not acceptance bounds or accuracy claims. They demonstrate why
truncation must be assessed by observable and frequency. Residual flexibility
remains OPTION-A and is not implemented.

```text
python -m pytest tests/unit/test_reduced_harmonic.py -q
19 passed

Targeted WP02/WP03/WP04 and WP05 regression set
135 passed

python -m pytest tests/unit -q
3232 passed, 93 skipped, 0 failed, 6 warnings

python -m pytest tests/documentation/test_docs_generation.py tests/documentation/test_docs_fields.py -q
69 passed, 2 skipped
```

The full unit campaign ran to completion in 21m41s of pytest-reported runtime.
The six warnings were the repository source-size advisory and five NumPy
determinant runtime warnings in existing WP15b/WP19 tests. The 93 skips remain
`SKIPPED`, not PASS. The final public-router policy assertion was also rerun
after the full campaign and passed. No test failure or interruption occurred
at the earlier WP03 campaign's approximate 45% point: this run crossed that
region; the delay came from CPU-bound release-readiness/audit script tests,
whose subprocess CPU time increased while pytest remained alive.

Ruff check passed for all changed Python source and test files. Ruff format
check passed for the new production module, its test module, and the method
registration file. Five touched legacy files already failed Ruff format
check at the WP04 base; their unrelated existing formatting was not rewritten.
Mypy passed on all eight changed source files. An exploratory whole-package
mypy run reported 2,747 errors across 260 files; no errors were reported in
the eight changed source files, and the broad repository result is not claimed
as a WP05 typing pass. The source-size advisory reported the new
`reduced_harmonic.py` module at 808 lines; this maintainability debt is
recorded rather than hidden, but is not a hard behavior gate. The contract
parses as valid JSON and `git diff --check` passed.

## Bounded performance observation

Single local smoke measurement on implementation commit
`7c03166f90d418f80a00777d19339b935a156c76`, Windows 10, Python 3.13.1,
NumPy 2.2.6, SciPy 1.15.2, serial execution. Fixture: TET4, 12 full DOFs,
3 reduced DOFs/modes, 2 frequencies, one channel with one nonzero spatial
entry. These are one-run timings, not a speedup or scaling claim.

| Stage or retained data | Observation |
| --- | ---: |
| K/M preparation | 3.31 ms |
| Modal extraction | 2.00 ms |
| RHS projection, each frequency | 0.165 ms; 0.101 ms |
| Reduced solve, each frequency | 1.477 ms; 1.141 ms |
| Reconstruction, each frequency | 0.197 ms; 0.167 ms |
| Full sparse K/M storage | 916 B / 628 B |
| Reduced sparse K/M storage | 52 B / 52 B |
| Modal basis modes | 72 B |
| Projected Mr/Kr/Cr arrays | 216 B |
| Bound channel distribution | 20 B, 1 nonzero |
| Retained complex responses and modal coordinates | 480 B |

Byte counts cover numerical array/sparse payloads, not Python object overhead,
allocator fragmentation, or native solver workspace. The run retained one
frequency's temporary full response at a time. No speedup is claimed; the
fixture is too small to establish scaling behavior.

## Gate contribution and limitations

- `QF0212_G02_WP05_METHOD_COMPOSITION = PASS`; global G02 remains open for
  later consumers and architecture integration.
- `QF0212_G03_DYN_WP05_HARMONIC_EQUATION = PASS` for this bounded method and
  its analytical fixtures; the global dynamic gate remains open.
- `QF0212_G04_DYN_WP05_NUMERICS = PASS` for the preregistered analytical,
  conditioning, residual, phase, and bounded equivalence checks. Truncation
  accuracy remains case-dependent and is not certified by a small reduced
  residual.
- `QF0212_G05_WP05_INTERFACE_AND_NONREGRESSION = PASS` for additive routing,
  serialization, method-specific maturity, and the preserved direct route;
  global G05 remains open for later result/API consumers.

Recorded limitations: the method is experimental and serial; the spectral
domain is inherited from WP04; source identity must be supplied when no clean
source checkout is available; prescribed modal damping has no physical full-
space C or reactions; physical reactions are not computed even under Rayleigh
damping; stress recovery and residual flexibility are absent; and a truncated
basis can miss a response component despite a near-zero reduced residual. No
historical maturity or qualification was promoted. Historical
`G03 = FAIL_PRESERVED`, `WHOLE_REPOSITORY_ARCHIVE_CLEARED = NO`, and
`WP14 = HOLD_NOT_PROMOTED` remain unchanged.

WP06, WP07, and OPTION-A were not started. No push, merge, tag, or publication
was performed.
