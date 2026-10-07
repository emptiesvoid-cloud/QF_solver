# QF Solver 0.2.12 — WP01 shared contracts

Status: `CONTRACTS_FROZEN_TESTED`

Baseline: WP00 commit `99ea0ac0085b1e374b2d6e3b586fa6844e39d590`

Contract: `wp01_shared_contracts.json`

WP01 freezes cross-cutting semantics and validation rules before any numerical
implementation. This deliverable is a design contract, not a solver feature.
No operator, excitation, modal reduction, transient integration, base-motion
solver, constitutive update, tangent correction or checkpoint migration code
was added.

## Decisions and invariants

### Method-aware maturity and qualification

Maturity and qualification lookup use the exact composite key:

`analysis + method + element family + material + damping + excitation + formulation scope`.

There is no fallback from a new method to its analysis type or to a nearby
legacy route. An unknown key rejects with `UNREGISTERED_METHOD_SCOPE`.
The new reduced basis, modal-superposition harmonic route, modal Newmark route
and base-acceleration routes target `EXPERIMENTAL`. Numerical status,
evidence availability, qualification decision and maturity remain separate
fields. A numerical `PASS` never promotes qualification or maturity.

Qualification scope is derived from the same resolved method tuple plus
boundary-condition and result-contract versions. In particular,
`harmonic_response/direct_frequency` and
`harmonic_response/modal_superposition` are distinct scopes, as are
`transient_dynamic/direct` and `transient_dynamic/modal_newmark`.

### Identity model

Five typed, versioned identities are distinct:

| Identity | What it binds | What it deliberately does not bind |
|---|---|---|
| Physical | Geometry/connectivity, formulations, materials/state, BCs, active DOFs and ordering, units/frames, concentrated masses, springs | Loads, excitation time/frequency content, numerical tolerances |
| Operator | Physical identity, source/assembly version, constraints/reduction, full/reduced M and K content, and an explicitly defined physical damping operator if present | Force amplitudes, phase, histories or frequency sweep |
| Excitation | Stable channels, real spatial load distribution, units/frame/sign, temporal amplitudes/phasors/histories and their content hashes | M/K assembly identity itself |
| Modal basis | Operator identity, eigensolver contract, dimensions/maps, normalization, eigenpairs, clusters and truncation policy | A basis from a different operator or constraints |
| Execution | Source, physical/operator/excitation/basis IDs, damping, initial state, algorithm settings, tolerances, requested results and relevant environment | Timestamps, process IDs, output directories and temporary paths |

Identity payloads use canonical UTF-8 JSON with sorted object keys, finite
numbers, resolved units, stable identifiers for unordered entities, and
semantic order retained for vectors and histories. File inputs are identified
by logical role, byte size and SHA-256. Private absolute paths and operational
metadata are not scientific identity.

The WP00 finding
`NEW_MARK_PHYSICAL_IDENTITY_INCOMPLETE = CONFIRMED` is addressed at the
contract level: masses and springs are mandatory physical identity components.
Consequently, a Newmark checkpoint/cache omitting either cannot match a current
physical identity and cannot authorize reuse.

### Checkpoints and migrations

`READABLE != SAFE_TO_RESUME`. A historical checkpoint can be decoded for
inspection yet remain non-resumable. Safe resume requires supported schema and
semantics, exact physical/operator/excitation/execution identity matches,
complete accepted state, and verified hashes for required artifacts. If any
identity is absent or insufficient:

```text
SAFE_RESUME = NO
FAIL_CLOSED = YES
ACTION = REFUSE_RESUME
```

The confirmed `NL_V1_TO_V2_MIGRATION_UNSAFE_CASE` remains a tracked defect for
WP10. WP01 authorizes no in-place rewrite, synthetic identity, or historical
checkpoint mutation. A future adapter must be named, versioned, lossless for
the state it resumes, and preserve the original bytes and source hash.

### Damping and modal basis

The contract distinguishes:

1. **Rayleigh physical/projected damping:** `C = alpha*M + beta*K`, with units,
operator identity and full-to-reduced projection explicitly recorded. A
reduced-only construction is not called physical unless it is proven to be
the projection of the declared full-space operator.
2. **Prescribed modal damping:** `C_modal = diag(2*zeta_j*omega_j)` in the
identified selected basis. It defines a reduced model; it does not imply a
complete physical full-space `C`.

For a degenerate or policy-defined near-degenerate cluster, damping must be
invariant under basis rotations: equal damping over the cluster or a separately
contracted invariant cluster operator. Otherwise the assignment is rejected.
Direct-versus-reduced equivalence is conditional on matching operators,
constraints, damping, excitation, initial conditions, retained basis and
numerical scheme. It is not inferred from matching analysis names.

Modal basis identity includes its exact M/K/constraint system, dimensions,
DOF maps, extraction configuration, normalization and cluster/truncation
contract. The basis is mass-normalized and the M-orthogonality and eigenpair
residuals are recorded. Sign/phase is nonphysical; clusters are compared as
subspaces. If a requested mode count cuts an identified cluster, the request
is rejected explicitly. No silent mode-count expansion is allowed. Numerical
cluster tolerances must be preregistered before benchmark results.

### Excitation channels and phasors

The spatial load distribution is real and separate from temporal amplitude or
frequency phasor. Harmonic phasors serialize as `{real, imag}` and use:

```text
response(t) = Re(U * exp(+i*omega*t))
input frequency: Hz
internal angular frequency: rad/s
omega = 2*pi*f, converted once at the API boundary
```

Channels have stable unique IDs, resolved units/frame/sign and content identity.
Zero channels are recorded no-ops; cancellations are deterministic and retain
per-channel provenance. A load factor is applied once. Existing load syntax
and defaults remain unchanged if the new syntax is absent. If old and new
syntax coexist, only proven equivalent input or a future explicit versioned
disjoint-channel combine mode is accepted. Ambiguous or contradictory input is
rejected, not silently merged or overridden. Historical loads are not all
converted into complex entities.

### Response frames, base acceleration and reactions

`P` maps reduced relative coordinates to the full physical DOF vector and
`r_full` is the explicit influence vector for uniform translational base
motion:

```text
u_abs = P*q_rel + r_full*x_g
v_abs = P*v_rel + r_full*v_g
a_abs = P*a_rel + r_full*a_g
f_base,red = -P.T*M_full*r_full*a_g
```

The base-inertia term uses the complete supported mass before constrained-DOF
elimination where coupling requires it. Uniform translation has zero entries
on rotational DOFs. Supports must be explicitly comoving and consistent with
the influence vector; incompatible independent support motion is rejected.
Spring-to-ground motion is never inferred. If only base acceleration is
given, relative response and absolute acceleration may be available; absolute
displacement/velocity require base displacement/velocity history or declared
integration constants and initial conditions.

Reaction availability is typed as `AVAILABLE`, `UNAVAILABLE`,
`NOT_COMPUTED` or `NOT_APPLICABLE`, always with a reason and physical/reduced
scope. Physical reactions require a reconstructable full-space equilibrium
balance. Prescribed modal damping alone is not a physical damping matrix and
must not be expanded artificially to produce reaction output. Unavailable
data is never represented by zero or an empty result table.

### Result availability and serialization

Every requested quantity declares whether it was computed, retained,
reconstructible and exportable; whether it is a physical or reduced-model
quantity; its frame, real/complex representation, units, semantic version and
source identities. An export request for a non-retained, unreconstructible
quantity returns an explicit status/error, not an empty table that looks valid.

New result envelopes use `qf-solver-result` schema version 1 and an explicit
semantic version. Complex values use finite `{real, imag}` fields. Historical
readers remain where possible, but read compatibility is not semantic
reinterpretation. The `second_piola_stress` legacy label is not proof that the
payload is a second Piola tensor. Preserve and mark unresolved legacy meaning;
do not rewrite it. New stress output must identify `stress_measure`,
`stress_frame` and `semantic_version`. A model JSON stores declarative inputs,
not runtime `PreparedDynamicSystem` or `ModalBasis` Python objects.

### Nonlinear boundaries

WP01 records, without correcting, these confirmed WP00 findings:

| Finding | Status / later owner |
|---|---|
| `COROTATIONAL_SECOND_PIOLA_LABEL_INCORRECT` | CONFIRMED, WP08 |
| `COROTATIONAL_TANGENT_CENTRAL_DIFFERENCE` | CONFIRMED, WP09 |
| `COROTATIONAL_TANGENT_SYMMETRIZED` | CONFIRMED, WP09 |
| `COROTATIONAL_FD_STEP_ORIGIN_DEPENDENT` | CONFIRMED, WP09 |
| HEX8 / HEX20 force evaluations | 49 / 121, WP09 characterization |

Stress semantics distinguish local-frame stress (which still requires a
measure), first Piola, second Piola and Cauchy stress. The frame/configuration
and recovery path are part of the result contract. Tangent evidence records
the raw finite-difference tangent and the tangent actually returned to Newton,
the symmetrization operation, step/length policy, origin-invariance checks,
evaluation count and raw-versus-returned diagnostics.

Fail-closed rescope rule for WP08/WP09: if a correction requires a substantial
new constitutive formulation, finite-strain or multiplicative plasticity, or a
general corotational-continuum reformulation, STOP, RECORD_LIMITATION and
RESCOPE_REQUIRED. Do not silently expand v0.2.12.

### API compatibility

New methods are additive. Legacy defaults and old input syntax remain usable
without new fields. A new method's out-of-scope rejection is route-local and
does not invalidate a model for a legacy route that already supports it.
Runtime objects are not serialized into model JSON. Legacy checkpoint/result
readability is kept separate from resume safety and semantic equivalence.

## Contract test evidence

`tests/unit/test_wp01_shared_contracts.py` checks the frozen JSON contract and
its cross-field invariants. It does not import solver operators or execute
future numerical features. The test set covers unknown-method rejection,
method-specific maturity/qualification, separate identities, masses/springs,
checkpoint safety, damping distinctions, basis invalidation and cluster
truncation, excitation conventions, base-motion frames, result availability,
serialization semantics, NL rescope and additive compatibility.

## Gate status and readiness

- `QF0212_G01 = PASS` (inherited WP00 baseline/scope).
- `QF0212_G02 = PASS` for the architecture/shared-contract portion.
- `QF0212_G03_DYN/NL = NOT_YET_APPLICABLE`.
- `QF0212_G04_DYN/NL = NOT_YET_APPLICABLE`.
- `QF0212_G05_CONTRACTS = PASS`; runtime non-regression remains
  `NOT_YET_APPLICABLE` until implementation.
- `QF0212_G06/G07 = NOT_YET_APPLICABLE`.

WP02, WP03, WP04 and WP08 have no unresolved shared-contract blocker and are
ready to be considered for separate authorization. Their numeric thresholds,
method-specific implementation details and evidence remain with those WPs and
must be preregistered before observing their results. No later WP is started
by this closeout.

Historical `G03 = FAIL_PRESERVED`, `WP14 = HOLD_NOT_PROMOTED` and
`WHOLE_REPOSITORY_ARCHIVE_CLEARED = NO` are unchanged. No maturity was
promoted; no historical checkpoint, result or qualification record was
rewritten.
