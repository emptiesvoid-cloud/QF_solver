# WP12 dynamic and harmonic experiments

**State:** `PREPARATION_ONLY`

**Execution:** `NUMERICAL_EXECUTION_NOT_PERFORMED`

**WP12:** `OPEN`

**Reference checkout:** `codex/wp12-dynamic-harmonic-verification` at `bf8732c49b20cf74af65b0c7a358f997b5b28e1f`
**Scientific status:** no current-HEAD numerical result is claimed here.

## Scope and execution gate

This preparation covers WP05 reduced harmonic response, WP06 modal Newmark, WP07
uniform base acceleration, and WP04 projection only where those routes consume
it. It does not cover element convergence, contact, nonlinear response, or
rotordynamics.

The current [`development_autonomous_policy.json`](../../../../development_autonomous_policy.json)
registers D01, C01, and E01 nodeids; it does not register the WP05, WP06, or WP07
nodeids below. Under [`AGENTS.md`](../../../../AGENTS.md), no dynamic FEM test may
be launched until the responsible policy change registers its exact nodeid,
checkout, attempt limit, and envelope. No pytest, solver, FEM, or benchmark was
run while preparing this document. The tests added below are prospective
measurement cases, not results or approvals.

The current base already contains the WP07 serialization correction as
integration commit `bf8732c49b20cf74af65b0c7a358f997b5b28e1f`, cherry-picked from
the separate WP07 fix branch. That integration identity is the base for these
preparations; the source branch and its historical evidence were not altered.

## Existing contracts and historical evidence

All figures in this section are copied from their existing reports and refer to
the implementation identities recorded there. They are historical evidence,
not reruns on the reference checkout above.

| Domain | Normative source and historical identity | Recorded evidence | Important limit |
| --- | --- | --- | --- |
| WP04 projection | [`wp04_modal_basis_damping_contract.json`](../../wp04_modal_basis_damping_contract.json), [`wp04_modal_basis_damping_report.md`](../../wp04_modal_basis_damping_report.md) | The analytical coupled two-DOF generalized eigenproblem and projected-operator identity are named required checks. | Projection correctness does not establish forced or transient response accuracy. |
| WP05 reduced harmonic | [`wp05_reduced_harmonic_contract.json`](../../wp05_reduced_harmonic_contract.json); report records implementation commit `7c03166f90d418f80a00777d19339b935a156c76` | Historical TET4 full-basis/direct relative response differences at 0, 1, and 3 Hz were `1.52e-16`, `7.43e-20`, and `2.97e-19`. Reduced and physical free-equation backward errors were `7.62e-17` and `5.55e-17`. The two-mode fixture differed from the full three-mode response by 19.8% at 1 and 100 Hz, 16.1% at 1,000 Hz, 45.6% at 5,000 Hz, and 54.4% at 10,000 Hz. | Direct/reduced agreement shares assembled K/M and is route consistency, not an independent physical oracle. Truncated physical residual is diagnostic only; exact truncation error is unavailable. |
| WP06 modal Newmark | [`wp06_modal_newmark_contract.json`](../../wp06_modal_newmark_contract.json); report identifies implementation source SHA `7122a85338d0b99868eb0f25b547b21dcad64ad3` | Historical SDOF final-displacement relative errors: free undamped `3.05e-8`, free damped `1.92e-6`, constant force `7.05e-5`, sinusoidal force `9.39e-7`. A TET4 full-basis/direct comparison recorded final u/v/a differences `1.33e-15`, `4.12e-16`, `4.08e-14` and physical free residual `9.46e-17`. | The existing refinement test holds 40 steps while changing dt, so the final observation time changes; its reported order is not the conventional fixed-final-time refinement. Existing analytic SDOF figures report displacement errors, not a complete u/v/a error table. |
| WP07 base acceleration | [`wp07_uniform_base_acceleration_contract.json`](../../wp07_uniform_base_acceleration_contract.json), [`wp07_uniform_base_acceleration_report.md`](../../wp07_uniform_base_acceleration_report.md) | Historical checks cover full-mass coupling, harmonic complex response and frames, transient constant-acceleration SDOF, initial equilibrium, absolute acceleration and serialization. The contract freezes harmonic `1e-11` relative / `1e-13` absolute tolerances and the transient `dt=1e-4 s`, 100-step state tolerances. | The route remains `EXPERIMENTAL` / `NOT_ASSESSED`; its old report predates the integrated signed-zero serialization correction. No regression rerun on `bf8732c` is claimed. |

### Frozen numerical criteria used below

The experiments reuse existing limits only:

* WP04: symmetry `1e-12`, scaled SPD minimum eigenvalue `>1e-12`, modal
  residual and mass orthogonality `1e-8`.
* WP05: reduced backward error `1e-8`, full-basis physical free-equation
  backward error `1e-8`, full-basis/direct relative difference `1e-8`, and
  analytical scalar-fixture relative error `1e-10`. Exact/near-resonance
  conditioning policy remains failure at indicator `<=1e-12` and warning at
  `<=1e-8`. No truncation-error tolerance is defined.
* WP06: reduced equilibrium relative error `1e-7`, full-basis physical free
  residual `1e-7`, displacement refinement order at least `1.8`, and undamped
  discrete energy drift at most `1e-10`.
* WP07: harmonic analytic response `rel=1e-11`, `abs=1e-13`; transient
  constant-base SDOF tolerances remain exactly those in its contract. No
  post-observation relaxation is permitted.

The new cases record v/a refinement and frequency-dependent complex response,
but do not add an acceptance threshold where the contracts have none. All
metrics beyond existing limits are reported as measurements, not pass criteria.

## Prospective experiments

| Changed test source | Contracted behavior | Exact prospective nodeid | Main residual risk |
| --- | --- | --- | --- |
| `tests/unit/test_modal_newmark.py` | WP06 Newmark recurrence, time refinement, reduced equilibrium and energy | `test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables` | v/a accuracy is measured, but the contract has no acceptance threshold for those state errors. |
| `tests/unit/test_reduced_harmonic.py` | WP04 basis consumed by WP05; complex impedance solve, full-basis route match, modal truncation diagnostics | `test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation` | Direct/reduced share assembled operators; no independent physical oracle for the TET4 structure. |
| `tests/unit/test_wp07_uniform_base_acceleration.py` | WP07 inertial forcing, absolute/relative frames, DC availability, result round trip | `test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization` | Single-axis, single-free-coordinate model; no general multi-support or damping model. |

The matrix is a selection hypothesis derived from the changed tests and
contracts; it is not evidence that the selected tests are exhaustive.

### DYN-NEWMARK-FIXED-TIME-001 — WP06

**Exact nodeid:**
`tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables`

**Fixture and assumptions:** straight BEAM2 axial response with one free
translation, linear elastic material, one retained mode spanning the complete
free space, homogeneous fixed supports, zero damping, no applied force, and
initial displacement `q0=1e-3 m` with zero velocity. Use `beta=1/4`, `gamma=1/2`
and fixed final time `T=0.08 s` at `dt=0.002, 0.001, 0.0005 s` (40, 80, 160
steps). The fixture tests the time integrator on a one-coordinate assembled
system; it does not independently validate the BEAM2 element formulation.

**Independent reference:** compute `omega=sqrt(Kr/Mr)` from the prepared scalar
operators and compare the probe at every time sample with
`u=q0 cos(omega t)`, `v=-q0 omega sin(omega t)`, and
`a=-q0 omega^2 cos(omega t)`. This is an independent closed-form integration
oracle conditional on the assembled scalar K/M.

**Measurements:** maximum absolute and relative errors for u/v/a; successive
observed orders from each error series; maximum reduced equilibrium relative
error; maximum relative total-energy drift; actual beta, gamma, dt, step count,
and final time. For each state, `E_abs(dt)=max_i |y_num(t_i)-y_exact(t_i)|`
uses all recorded samples, and `E_rel(dt)=E_abs(dt)/max_i |y_exact(t_i)|` uses
the exact state on that same fixed `[0,T]` sample grid. Each successive order is
`p=log2(E_rel(dt)/E_rel(dt/2))`. The test checks that the start, final sample,
and `steps+1` sample count match the requested fixed interval. Displacement,
velocity, and acceleration are reported in m, m/s, and m/s^2; relative errors
and observed orders are dimensionless. The test asserts only the existing
displacement order, reduced residual, and energy limits. It prints a
deterministic JSON observation record for capture by an authorized `-s`
invocation. It does not use v/a error limits that are absent from the frozen
contract.

**Stability interpretation:** the contract's parameter domain is
`gamma >= 0.5`, `beta >= 0.25*(gamma+0.5)^2`, `dt > 0`; these are the selected
Newmark linear stability conditions. The second-order claim applies only at
`gamma=0.5` with sufficiently regular histories. This case uses the average
acceleration choice and zero forcing, so input interpolation does not limit
the order. The experiment does not cover nonlinear stability or adaptive dt.

### HARMONIC-COMPLEX-SWEEP-001 — WP05 / WP04 dependency

**Exact nodeid:**
`tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation`

**Fixture and assumptions:** existing bounded TET4 three-free-coordinate
fixture, linear isotropic elasticity, homogeneous supports, real legacy nodal
force, Rayleigh damping as configured by that fixture. Build the frequency set
from the prepared eigenvalues: DC, half and +/-2% around the lowest natural
frequency, and +/-2% around the highest retained/full-basis natural frequency.
The +/-2% points probe resonant neighborhoods without requesting an exactly
singular undamped solve. The configured damping remains unchanged.

**References and decomposition:** solve each frequency with (1) the historical
direct-frequency route, (2) WP05 with the full basis, and (3) WP05 with two
modes. Direct/full-basis agreement isolates projection, reconstruction and
route-level solve differences on shared assembled K/M/C. Two-mode/direct
difference includes omitted-subspace truncation plus solve error; report it
alongside the reduced backward error and physical free residual, but do not
call it an exact truncation-error estimate. The existing scalar SDOF analytical
test remains the independent complex-amplitude/phase oracle; the existing
coupled two-DOF test remains the non-diagonal projected-operator oracle.

**Measurements:** per frequency, complex probe value, amplitude, and principal
phase for all three routes; wrapped phase differences relative to the direct
route; complex-vector relative errors; reduced and physical free-equation
backward errors; conditioning indicator/status; and natural frequencies.
Probe displacement is in m, frequency in Hz, phase in rad, and residual/
conditioning indicators are dimensionless. The probe is node 1 UX in the
global model frame, and the phasor convention is `exp(+i omega t)`. Acceptance
uses only WP05 frozen
full-basis/direct and residual criteria. Truncated differences are descriptive.
Deterministic JSON is printed for authorized capture.

**Not claimed:** comparison with the direct route is not independent physical
validation; agreement at a finite set of frequencies does not bound response
error elsewhere; this case does not assert general modal truncation adequacy.

### BASE-HARMONIC-FRAME-SWEEP-001 — WP07 / WP05 / WP04 dependencies

**Exact nodeid:**
`tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization`

**Fixture and assumptions:** existing one-free-translation BEAM2 harmonic
fixture; x-axis unit base influence, homogeneous supports explicitly declared
comoving, zero Rayleigh damping, and a complex acceleration phasor
`0.7-0.4i m/s^2` at positive frequencies. Sweep DC, half the scalar natural
frequency, and +/-2% around that frequency. The DC input is exactly zero as
required by WP07. No direct-frequency route is used because WP07 explicitly
rejects base excitation on that route.

**Independent reference:** independently assemble the free equation from the
prepared full mass/stiffness and global influence vector:
`Z=(K_ff - omega^2 M_ff)`,
`F_base=-[M_full r_full]_f A_g`,
`U_rel=F_base/Z`; then use `X_g=-A_g/omega^2`,
`U_abs=U_rel+X_g`, `V_rel=i omega U_rel`,
`V_abs=i omega U_abs`, `A_rel=-omega^2 U_rel`, and
`A_abs=A_rel+A_g`. This independently checks the response algebra against the
full free equation but shares assembled BEAM2 matrices.

**Measurements:** complex relative and absolute displacement/velocity/
acceleration values, amplitudes, and principal phases, reduced and physical
free residuals, exact DC availability behavior, and equality before/after the
`ReducedHarmonicResult` round trip. Displacement is in m, velocity in m/s,
acceleration in m/s^2, frequency in Hz, phase in rad, and residuals are
dimensionless. The base direction is global +X and the probe is node 1 UX in
the global model frame; the phasor convention is `exp(+i omega t)`. Existing
WP07 tolerances remain unchanged. The latter is particularly relevant because this
base contains the WP07 signed zero serialization fix; the historical WP07
report is not a current-HEAD rerun.

## Existing targeted nodeids to consider in the same authorization

These tests are not run by this preparation and are not currently registered
in the development policy:

* WP04 projection oracle:
  `tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators`
* WP05 independent scalar complex oracle:
  `tests/unit/test_reduced_harmonic.py::test_reduced_impedance_matches_independent_analytical_sdof_amplitude_and_phase`
* WP05 coupled projected operator check:
  `tests/unit/test_reduced_harmonic.py::test_coupled_two_dof_complex_response_uses_full_projected_operators`
* WP05 exact/near-resonance refusal:
  `tests/unit/test_reduced_harmonic.py::test_reduced_impedance_detects_exact_and_near_resonance_before_solving`
* WP05 current direct/full-basis check:
  `tests/unit/test_reduced_harmonic.py::test_full_basis_reduced_harmonic_matches_direct_rayleigh_route_and_zero_hz`
* WP06 analytic SDOF cases:
  `tests/unit/test_modal_newmark.py::test_sdof_free_undamped_matches_analytic_solution_and_initial_projection`
  and
  `tests/unit/test_modal_newmark.py::test_sdof_free_damped_matches_under_damped_analytic_solution`
* WP07 harmonic full-free-equation and result round trip:
  `tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames`
* Signed-zero serialization regression integrated with the WP07 fix:
  `tests/unit/test_result_serialization_contracts.py::test_reduced_harmonic_json_round_trip_preserves_signed_zero_phase_metadata`
* WP07 transient constant-base analytic trajectory:
  `tests/unit/test_wp07_uniform_base_acceleration.py::test_transient_base_sdof_matches_independent_constant_acceleration_solution`

Policy registration should add only the approved nodes and their source/test
identities, with one nodeid per invocation. The new measurement tests are
prospective, not authorized by their existence. Existing historical test counts
must not be summed across overlapping WP05/WP06/WP07 campaigns.

## Expected plots after authorization

No plot is produced because no solver output was generated. After authorized
runs, archive plots from captured JSON only:

1. Newmark: `dt` versus max relative u/v/a error on log-log axes, with separate
   observed-order labels; residual and energy drift in separate panels.
2. Harmonic: frequency versus amplitude and phase for direct/full/two-mode
   routes; complex relative difference and residual in companion panels;
   mark modal frequencies and conditioning warnings.
3. Base excitation: frequency versus relative/absolute response amplitude and
   phase, plus acceleration frames; mark unavailable DC displacement/velocity
   rather than plotting them as zero.

Plots are diagnostic summaries, not new acceptance criteria. Preserve the raw
JSON, JUnit, stdout/stderr, environment and provenance with the run evidence.

## Bounded verdict and next action

Static preparation checks on this worktree: Python source compilation and
local documentation-link/nodeid existence checks passed; `ruff check` passed
for the three touched test modules; `git diff --check` passed. Ruff formatting
reports no changes for the Newmark and WP07 modules and one pre-existing
formatting difference in the WP05 test module at its earlier truncation
assertion; the unrelated historical line was left unchanged. No pytest
collection, pytest test, solve, or numerical calculation was performed.

**Current verdict:** preparation complete; all three proposed calculations and
the supporting WP04/WP05/WP06/WP07 nodeids remain `NOT_RUN` on this checkout.
The existing historical numerical reports provide bounded prior evidence, but
do not establish these new measurements on `bf8732c49b20cf74af65b0c7a358f997b5b28e1f`.

Next, the policy owner must register the exact approved dynamic nodeids and
worktree/source/test identities. Then run sequentially through the existing
autonomous development launcher, retain every result, and review the raw
observables and oracle assumptions before making any WP12 decision. WP05/WP06/
WP07 remain `EXPERIMENTAL`; WP12 remains `OPEN`.
