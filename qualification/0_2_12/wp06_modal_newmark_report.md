# WP06: Modal Newmark Transient

**Status:** `PASS` (bounded, experimental scope)

**Branch:** `codex/v0.2.12-wp06-modal-newmark`

**Base:** `eeb8b193b0956ec97c721ebbeff5b16eaad82bf9`

**Implementation source SHA used for the complete unit campaign:**
`7122a85338d0b99868eb0f25b547b21dcad64ad3`

**Maturity:** `EXPERIMENTAL`; numerical PASS does not imply qualification.

## Scope and implementation

WP06 adds the explicit `transient_dynamic/modal_newmark` method. The historical
direct `newmark` method remains the default and is not auto-selected or replaced.
The implementation composes WP02 `PreparedDynamicSystem`, WP03 real
`ExcitationChannelSet`, WP04 `ModalBasis` and damping, and the existing Newmark
effective-matrix, right-hand-side, state-recovery, validation, and reusable
factorization routines. The direct route uses the same state-recovery arithmetic
after a minimal extraction of that recurrence; its full-coordinate equations
and defaults are unchanged.

The reduced equations use the actual projected operators:

```text
Mr = Phi.T M Phi
Kr = Phi.T K Phi
Cr = WP04-declared projected damping
Mr qddot + Cr qdot + Kr q = Phi.T F(t)
u = Phi q; v = Phi qdot; a = Phi qddot
```

Initial displacement and velocity are projected in the mass metric. Projection
errors are recorded, and the configured policy can reject incompatible initial
states. Initial acceleration is solved from reduced equilibrium at `t=0`.
Displacement, velocity, and acceleration outputs correspond to the same accepted
time state. Real WP03 channels are sampled on `t_n = n*dt` according to their
declared time-history interpolation. Base acceleration and moving-support input
are rejected here and remain WP07 scope.

The method accepts only the WP00-bounded TET4, TET10, HEX8, HEX20, and straight,
non-rotating BEAM2 domain, linear isotropic elasticity, supported homogeneous
fixed constraints, admissible concentrated masses/springs, and the WP04 spectral
domain. Unsupported features fail closed on this method without changing the
historical direct route.

## Damping, restart, and result contract

Rayleigh damping projects the physical operator using
`Cr = alpha*Mr + beta_R*Kr`; `beta_R` is distinct from Newmark `beta`.
Prescribed modal damping uses the WP04 reduced operator
`Cr[j,j] = 2*zeta_j*omega_j`. It is a reduced model, not an inferred physical
full-space damping matrix. Physical reactions are therefore explicitly
`UNAVAILABLE` for prescribed modal damping; no artificial `C` is constructed.

Restarts use the separate `qf-modal-newmark-checkpoint/v1` NPZ schema. A resume
requires matching source, physical and operator identities, excitation content,
damping, exact basis content/identity, initial state, step count, `dt`, beta,
gamma, and the hash of the accepted `q/qdot/qddot` arrays. Direct Newmark
checkpoints are rejected by the modal reader. Corrupt or incompatible states
fail closed. The interrupted/resumed and continuous run final states agree
within the preregistered `1e-12` relative threshold.

The versioned `ModalNewmarkResult` marks maturity `EXPERIMENTAL` and
qualification `NOT_ASSESSED`. Final physical states are retained. Full physical
time histories are not retained by default; explicitly requested probes and
modal histories are bounded outputs. Stress is `NOT_COMPUTED`. The exact physical
modal truncation error is `UNAVAILABLE`; a reduced equilibrium residual is not
an estimate of that error.

The exact scope and preregistered limits are in
[`wp06_modal_newmark_contract.json`](wp06_modal_newmark_contract.json). They
include reduced equilibrium `1e-7`, full-basis physical free residual `1e-7`,
exact mass-projection error `1e-10`, full-basis/direct final-state difference
`1e-8`, restart/continuous difference `1e-12`, and minimum observed refinement
order `1.8`. The contract records `post_observation_relaxation: false`.

## Numerical evidence

Independent SDOF analytic checks and their measured final-displacement errors:

| Case | Relative error | Absolute error |
| --- | ---: | ---: |
| Free, undamped | `3.05e-8` | `5.95e-11` |
| Free, damped | `1.92e-6` | `1.10e-9` |
| Constant force | `7.05e-5` | `5.57e-8` |
| Sinusoidal force | `9.39e-7` | `3.39e-10` |

For the bounded TET4 full-basis/direct comparison with identical K/M, supports,
initial state, excitation, and Rayleigh damping, final displacement, velocity,
and acceleration relative differences were respectively `1.33e-15`,
`4.12e-16`, and `4.08e-14`; the full physical free-equation residual was
`9.46e-17`. This is an integration/non-regression comparison between QF routes,
not an independent physical validation.

For smooth free vibration with `gamma=0.5`, the observed errors at
`dt = 0.002, 0.001, 0.0005` were `4.13e-6`, `4.46e-7`, and `6.09e-8`, giving
successive observed orders `3.21` and `2.87` for this finite-time observable.
The implementation does not claim second order solely from the value of gamma;
the result reports the order claim as conditional on regular input history.

A bounded three-DOF TET4 mode-count refinement used an initial state aligned
with the third mode. The two-mode acceleration difference from the direct
reference was `1.1999e1`; the three-mode/full-basis difference was
`9.947e-9` (ratio `8.29e-10`). This demonstrates the consequence of omitting an
excited mode in this fixture only. It is not a general convergence guarantee;
exact truncation error remains unavailable in the result contract. The separate
WP04 policy still rejects a request that silently cuts an identified cluster.

## Bounded performance and storage observation

One local TET4 observation on Python 3.13.1, NumPy 2.2.6, SciPy 1.15.2, Windows,
using the WP06 implementation source SHA above: 12 physical DOFs, 3 prepared
reduced DOFs, 2 retained modes, 1 real channel, 100 steps, no retained history.
Preparation took `0.00300 s`, modal extraction `0.00161 s`, integration
`0.02146 s`, and total wall time `0.02726 s`. There was one effective-matrix
factorization and 100 solves. Sparse K/M storage was 104 bytes; basis plus
projected arrays were 208 bytes; the final physical state used 288 bytes;
retained time-history storage was zero. The checkpoint modal state arrays used
48 bytes; each of three compressed checkpoint files was 1,580 bytes.

These measurements are a small fixture characterization, not a performance
claim or evidence of industrial scaling. They do not establish a speedup over
direct Newmark on representative production workloads.

## Verification and non-regression

```text
python -m pytest tests/unit/test_modal_newmark.py -q
32 passed

python -m pytest tests/unit -q
3264 passed, 93 skipped, 0 failed, 6 warnings, 1304.71 s

python -m mypy [seven WP06 source modules excluding legacy dynamic.py]
Success: no issues found in 7 source files

python -m ruff check [all changed Python modules]
PASS

python -m ruff format --check [all changed Python modules]
PASS

python -m pytest tests/documentation -q
88 passed, 6 skipped
```

The complete unit campaign was run on the WP06 implementation source SHA above.
The six warnings comprise the repository's source-size advisory and five
pre-existing NumPy determinant runtime warnings in WP15b/WP19 tests. The 93
skips remain `SKIPPED`, not PASS.

Scoped mypy over all eight changed source modules reports 12 errors in the
pre-existing portions of `core/analyses/dynamic.py` (generic parameter
conversions/iteration around legacy load and history helpers). Those lines are
outside the shared state-recovery helper changed by WP06. The other seven
changed source modules pass mypy. No global typing-clean claim is made.

The final WP06 tests also verify restart refusal after mutation of mass, spring,
material, or boundary conditions; refusal of a direct checkpoint by the modal
route; interrupted/continuous equivalence; serialized result round-trip; all
five allowed element families; energy behavior; timestep refinement; damping
availability; and preservation of the direct method default.

The test suite asserts availability and qualification separately. Historical
maturities and qualification records were not promoted or rewritten.

## Gate contribution and remaining boundaries

| Gate contribution | WP06 subcheck | Scope status |
| --- | --- | --- |
| `QF0212_G02` | Method identity, prepared-system/basis binding, checkpoint identity | `PASS` |
| `QF0212_G03_DYN` | Reduced Newmark equations, projection, initial equilibrium | `PASS` |
| `QF0212_G04_DYN` | Analytic checks, residuals, energy, time/mode refinement, restart | `PASS` |
| `QF0212_G05` | Direct-route default, result availability/serialization, full unit regression | `PASS` |

These are WP06 contributions only; they do not close any release-wide gate whose
other work packages remain outstanding. WP07 base acceleration and OPTION-A
residual flexibility were not implemented. No merge, push, tag, or publication
was performed.
