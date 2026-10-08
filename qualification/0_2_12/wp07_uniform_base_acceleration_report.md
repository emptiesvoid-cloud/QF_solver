# WP07: Uniform Base Acceleration

**Status:** `PASS` for the bounded WP07 scope on the dedicated branch.
**Branch:** `codex/v0.2.12-wp07-uniform-base-acceleration`
**Base:** `08f49907d27ed822537d7ae488f12869506e4475`
**Maturity target:** `EXPERIMENTAL`; qualification remains `NOT_ASSESSED`.

## Scope and formulation

WP07 adds the explicit `uniform_base_acceleration` input only to
`harmonic_response/modal_superposition` and `transient_dynamic/modal_newmark`.
The historical `direct_frequency` and direct `newmark` methods are not changed
to consume it, and no implicit direct/reduced routing is introduced. The
feature composes WP02 `PreparedDynamicSystem`, WP03 force channels, WP04
`ModalBasis` and damping, WP05 harmonic response, and WP06's Newmark/checkpoint
path.

The input contract requires a normalized global-axis direction, SI acceleration
units, an explicit comoving-support declaration, and route-specific phasors or
time histories. The absent WP07 object does not reinterpret historical fixed
DOFs. A spring connected to ground is rejected unless its reference is
explicitly declared to move with the base. Fixed-in-absolute-frame springs,
multi-support motion, arbitrary imposed motion, rotor/contact/prestress and
unhandled condensed-coordinate maps fail closed on these new routes.

The implemented relative equation is

```text
u_abs = P*u_rel + r_full*x_g
v_abs = P*v_rel + r_full*v_g
a_abs = P*a_rel + r_full*a_g
F_base,free = -P.T*M_full*r_full*a_g
F_base,modal = Phi.T*F_base,free
```

The complete assembled `M_full` is multiplied by the influence vector before
constraint reduction. `P` is explicitly constructed as the full-to-free
selector for the WP00 scope; a non-identity reduction or condensed algebraic
DOF map is rejected, not silently approximated. This preserves the consistent
mass coupling from constrained to free coordinates. Translational influence
entries follow the declared global direction; rotational entries are zero,
although `M_full*r_full` can still have rotational generalized-force entries.

The adopted physical contract uses homogeneous comoving supports and relative
structural coordinates. Structural stiffness and damping act on relative
deformation/velocity. Consequently there is no separate `K*r*x_g` term for
rigid translation, and no artificial damping force from rigid base velocity is
added. This is not a general model of absolute-frame dashpots. Ground-referenced
springs are admitted only with an explicit comoving reference. These are
assumptions of the bounded WP07 route, not inferred properties of legacy BCs.

## Harmonic and transient behavior

Harmonic acceleration phasors use
`a_g(t) = Re[A_g exp(+i*omega*t)]`, retain real and imaginary parts, and resolve
frequency from Hz to rad/s once. At positive frequency,
`X_g=-A_g/omega^2` and `V_g=A_g/(i*omega)` define absolute kinematics. A nonzero
acceleration phasor at 0 Hz is rejected. At 0 Hz with a zero acceleration
phasor, the relative DC response is calculable, but absolute displacement and
velocity remain unavailable because acceleration alone does not define their
integration constants. Relative acceleration and absolute acceleration remain
available (`a_rel=-omega^2*U_rel`, `a_abs=a_rel+r_full*A_g`).

Transient input uses finite real acceleration samples from `t=0`, seconds, and
WP03's `linear_endpoint_hold` interpolation. The equivalent base force is added
to the external WP03 channel force exactly once at the sampled time and then
projected. The relative initial state is retained. The route reports absolute
acceleration using `P*a_rel+r_full*a_g`; it does not integrate the base history
to invent absolute displacement or velocity.

Rayleigh damping follows WP04 and acts on relative structural velocity in this
base-motion contract. With a reconstructible full Rayleigh operator, the
transient fixed-DOF residual uses the full mass and stiffness balance and the
relative damping velocity. Prescribed modal damping does not define a full
physical `C`, so these reactions remain `UNAVAILABLE`. The force at a
comoving ground-spring reference is separately `UNAVAILABLE` because that
reference has no physical DOF/reaction mapping in the model; it is not folded
into the fixed-DOF reaction vector. Reduced harmonic reactions remain
`NOT_COMPUTED`; a generalized reduced force is not labeled a support reaction.

## Identity, checkpoint, and result behavior

The input gets a canonical excitation identity containing direction, resolved
units, phase/history content, interpolation and support/reference policy. It is
combined with the WP03 channel identity for the execution/checkpoint identity,
without changing physical/operator identity or invalidating `K/M` and the modal
basis solely because excitation changed. Modal Newmark restart uses its
existing versioned checkpoint and refuses a changed base history. Historical
checkpoint semantics are not rewritten.

Relative and absolute fields carry separate availability entries and frame
labels. Harmonic relative velocity/acceleration and absolute acceleration are
serialized as complex quantities. Harmonic absolute displacement/velocity are
unavailable at DC; transient absolute displacement/velocity are unavailable
from acceleration-only input. Absolute acceleration is serialized separately
from the historical relative state arrays. Missing absolute quantities are
represented as unavailable/`null`, not as zero. Old result payloads without
WP07 additions remain readable.

All WP07 results stay `EXPERIMENTAL`, with qualification `NOT_ASSESSED`.
Numerical success is not a qualification promotion. Historical G03, WP14, and
whole-repository archive statuses remain untouched.

## Evidence and preregistered checks

The contract [`wp07_uniform_base_acceleration_contract.json`](wp07_uniform_base_acceleration_contract.json)
freezes the input/formulation/result semantics and numerical thresholds. The
targeted tests include independent full-mass SDOF equations, constrained/free
consistent-mass coupling in BEAM2 and TET4, BEAM2 rotational influence entries,
complex 90-degree phasors and force superposition, relative Rayleigh damping,
zero-frequency absolute-kinematics unavailability, transient initial
equilibrium, absolute acceleration, restart equivalence/refusal, spring/support
fail-closed behavior, and all five WP00 element families for a bounded transient
case.

The comparison tolerance for the independent harmonic algebra is
`relative=1e-11`, `absolute=1e-13`; full-mass projection comparison uses
`1e-12*max(1, ||projected load||)`. These are implementation checks on small
fixtures, not general accuracy claims. QF direct/reduced comparisons are
integration/non-regression evidence, not independent physical validation.

## Gate contribution and limitations

WP07 contributes bounded evidence to `QF0212_G02`, `QF0212_G03_DYN`,
`QF0212_G04_DYN`, and `QF0212_G05`. It does not close release-wide gates.

## Validation and bounded performance evidence

| Check | Result |
|---|---|
| WP07, modal Newmark, and reduced harmonic targeted tests | 69 PASS |
| Complete `tests/unit` suite | 3,282 PASS, 93 SKIPPED, 0 FAIL, 6 warnings, 1,302.33 s |
| Documentation tests | 88 PASS, 6 SKIPPED |
| Ruff check | PASS |
| Ruff format check | PASS, all 7 changed Python files formatted |
| Targeted mypy | PASS, 5 source files |

The full-unit warnings are one existing source-size advisory and five NumPy
`det` runtime warnings from adversarial robustness tests. Skips remain recorded
as `SKIPPED`, not treated as passes. Global mypy was not run; this is only a
targeted result for the five affected source modules.

Bounded performance observation, Windows 10 / Python 3.13.1 / NumPy 2.2.6 /
SciPy 1.15.2: a BEAM2 fixture with 12 physical DOFs, 1 free DOF, 1 retained
mode, one harmonic frequency, and 11 transient samples. Complete-mass
base-load preparation averaged 0.000529 s over 7 calls when the prepared
operators and basis were already available. CSR storage was 532 bytes each
for full M and K; the influence vector and full inertia load were 96 bytes
each, with 8-byte reduced and modal loads. Harmonic solver phase timings were
0.000195 s for projection, 0.001744 s for the reduced solve, and 0.000200 s
for reconstruction; retained-response storage was 1,168 bytes. The transient
run took 0.0145 s wall time for 11 samples, reported one reusable
factorization, 288 bytes for relative state histories, and 96 bytes for
absolute-acceleration history. These are single-fixture observations, not
scaling or speedup claims.

No WP08–WP13 work or OPTION-A residual-flexibility implementation is included.
