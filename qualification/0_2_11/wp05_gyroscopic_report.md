# WP05 — Disk gyroscopic foundations and `rotating_modal`

## Decision summary

WP05 adds an experimental, serial, dense gyroscopic modal route for the
bounded model defined below. The implementation source is
`f2690bcac8f1b5b34c6b01a6cf5a9e19ecb725a9`; the three machine-readable
records in this directory bind their runs to that source and to the frozen
WP05 contract. This report and those records are governance/evidence files;
they do not change the source identity used by the numerical runs.

| Item | Result |
| --- | --- |
| Branch | `codex/v0.2.11-wp05-rotating-modal` |
| WP05 base | `a0e8acd87ea535086dc8b78ae6a2032449fb3a5e` |
| Numerical source SHA | `f2690bcac8f1b5b34c6b01a6cf5a9e19ecb725a9` |
| Scope | Straight, unbranched BEAM2 chain with centered rigid axisymmetric disks |
| Maturity | `EXPERIMENTAL`; no promotion |
| QF0211-G04 | PASS — gyroscopic formulation |
| QF0211-G05 | PASS — QEP and result contract |
| WP06 / Campbell | Not started; explicitly out of scope |

The authoritative tolerances and accepted-input contract are in
[`wp05_gyroscopic_contract.json`](wp05_gyroscopic_contract.json). Exact
execution identities, environment, provenance, case outcomes, and hashes are
in [`wp05_gyro_verification_records.json`](wp05_gyro_verification_records.json),
[`wp05_dense_characterization.json`](wp05_dense_characterization.json), and
[`wp05_gate_summary.json`](wp05_gate_summary.json).

## Implemented scientific scope

The route solves the small-perturbation, fixed-frame equation

```text
M q¨ + Ω G q˙ + K q = 0
(λ² M + λ Ω G + K) φ = 0
```

with signed `Ω` in rad/s and the frozen global, right-hand-rule axis
convention. `G` is the unit-speed matrix: `Ω` is applied exactly once in the
quadratic pencil. For a centered axisymmetric disk with unit axis `a`, mass
`m`, diametral inertia `Jd`, and polar inertia `Jp`, the local contributions
are `Mdisk = diag(m I, Jd(I-aaᵀ)+Jp aaᵀ)` and
`Gdisk = diag(0, -Jp[a]×)`. The disk owns both contributions; a duplicate
generic concentrated mass at its node is rejected. The implementation checks
the local sign convention, skew symmetry, frame covariance, signed-speed
behavior, and fail-closed input validation without repairing `G` by
symmetrization.

The accepted structural model is a connected, unbranched, collinear BEAM2
shaft with circular isotropic sections, one fixed global spin axis parallel
to the shaft, centered rigid axisymmetric disks at beam nodes, homogeneous
fixed DOFs, and only admissible fixed-ground linear springs. Damping,
prestress, nonzero loads, unsupported constraints, contact, shells/solids,
variable speed, centrifugal stress stiffening, distributed beam gyro terms,
and nonlinear rotor response are rejected. PETSc, SLEPc, MPI, and sparse QEP
are not implemented for this route.

Existing structural assembly supplies `K` and structural `M`; supported
discrete contributions are included through the existing assembly path. The
dedicated gyro assembly contributes disk `G` separately. The same homogeneous
fixed-DOF reduction is applied consistently to `M`, `K`, and `G`; reduced
matrices are checked before solving. Existing analyses do not assemble `G`.

## Solver-method choice

The public analysis setting has separate method choices per analysis family.
For `rotating_modal`, the only enabled method is `dense_qep`, implemented by
a dedicated `QuadraticEigenSolver` using SciPy's generalized dense eigensolver
on a scaled first-companion pencil (`scipy.linalg.eig(A, B)`). This is a
non-Hermitian complex QEP; symmetric real `eigh`/`eigsh` methods are not
interchangeable substitutes. The dense method also retains the raw complex
spectrum and applies the contract's residual, conditioning, growth, conjugate
pair, and mass-normalization checks.

Assembly composition is a separate concern: contributions are assembled
into `K` and `M`, while disk gyroscopy contributes `G`; changing which
physical matrices are assembled does not itself select a numerical solver
algorithm. WP05 intentionally adds no backend registry or alternative QEP
backend. The dense measurements below provide evidence for a future backend
decision, not authorization to add one. Any later sparse/PETSc/SLEPc or other
QEP implementation must preserve this input, result, residual, and
fail-closed contract and be separately verified.

## Verification records

All four frozen gyro cases passed:

| Case | Purpose | Result |
| --- | --- | --- |
| GYRO-01 | `Ω=0` recovery of the classical modal spectrum and eigenspaces | PASS |
| GYRO-02 | Local disk `M/G`, skew property, covariance, signed speed, ownership, invalid-input rejection | PASS |
| GYRO-03 | Independent analytical disk oscillator over the frozen signed-speed values | PASS |
| GYRO-04 | Signed-speed spectral splitting, conjugate pairs, and QEP residuals | PASS |

The gate summary records QF0211-G04 and QF0211-G05 as PASS. QEP residuals
are evaluated on the original quadratic polynomial; complex modes are
mass-normalized and serialized with explicit real and imaginary parts. The
raw spectrum remains available. The selected oscillatory view is a
deterministic convenience view and is not a Campbell branch tracker.

## Dense-backend characterization

The frozen characterization used formula-generated finite SPD `M/K` and
skew `G` matrix pencils, five sizes, and three repetitions per size. It ran
on Windows 10, Python 3.13.1, NumPy 2.2.6, SciPy 1.15.2, with one BLAS thread.
These are solver-invariant synthetic pencils, not five physical rotor
benchmarks. Measurements are:

| Physical DOFs | Linearized dimension | Median solve (s) | Max peak RSS (bytes) | Max relative QEP residual | Result |
| ---: | ---: | ---: | ---: | ---: | --- |
| 50 | 100 | 0.04573 | 74,477,568 | 8.12e-15 | PASS |
| 100 | 200 | 0.15118 | 78,495,744 | 2.41e-14 | PASS |
| 250 | 500 | 2.17606 | 102,916,096 | 9.67e-14 | PASS |
| 500 | 1,000 | 25.30427 | 186,372,096 | 5.78e-13 | PASS |
| 1,000 | 2,000 | 271.21784 | 516,771,840 | 5.04e-12 | PASS |

For repository-facing evidence, absolute machine-specific BLAS library paths
were normalized to site-packages-relative library identifiers. The record
and suite hashes were recomputed and verified after that provenance-only
normalization; execution identities, solver inputs, measurements, and
numerical outcomes were not changed. The original runner outputs remain
outside the repository.

The recorded characterization bound is 1,000 physical DOFs, the largest
completed target, with no extrapolation. It is evidence about this dense
backend under the recorded environment and synthetic workload—not a
universal capacity guarantee, a performance promise, or a claim that every
1,000-DOF rotor model is practical. Runtime growth is already substantial at
the largest tested size. Larger sizes, other environments, and application
models remain uncharacterized; sparse and distributed solving remain out of
scope.

## Regression, limitations, and maturity

The WP05 targeted gyro and affected regression selection previously completed
with `122 passed, 1 warning`; the warning is the repository's advisory source
size warning. The exact final WP05 head still requires the prescribed PR CI
campaign before closure. A locally selected full Quality suite was not
completed and is not reported as PASS. See the final WP05 handoff for the
exact-head CI results.

This capability is **EXPERIMENTAL**. Passing these tests does not qualify
general rotordynamics, physical validation, all BEAM2 rotor configurations,
or any out-of-scope formulation. There is no Campbell sweep, modal tracking,
forward/backward whirl classification, forced unbalance response, or general
HPC support in WP05. G03 remains `FAIL_PRESERVED`; the whole-repository archive
is not cleared. WP14 remains `HOLD_NOT_PROMOTED`. No historical result or
maturity decision is changed.
