# WP03: Excitation Channels / Phasors

**Status:** `PASS`

**Branch:** `codex/v0.2.12-wp03-excitation-channels`

**Base:** `7005d6151f39f05a12237bd280d6b18c55bf2aab`

## Scope delivered

WP03 adds `ExcitationChannel`, `ExcitationChannelSet`, and
`BoundExcitationChannels` in
`src/solveur/core/analyses/excitation_channels.py`. A channel has a stable ID,
a real distribution keyed by physical node/DOF, explicit units/frame/sign,
one real constant, real history, or complex phasor signal, and provenance.
Phasors serialize only as finite `{real, imag}` values. Frequency is accepted
in Hz and `HarmonicAmplitude` resolves `omega = 2*pi*f` once at construction.
The stated convention is `response(t) = Re(U * exp(+i*omega*t))`.

The channel set canonicalizes by channel ID and hashes a domain-separated
`qf-excitation-identity/v1` payload using the repository's
`checkpoint_signature`. Identified-channel ordering therefore does not affect
identity. Distribution, amplitude, phase, history, frequency, units, frame,
sign, and provenance changes do. Runtime binding creates an instance-local CSC
DOF-by-channel map. It does not retain a dense `B` matrix or a mutable model.

The set composes full real or complex right-hand sides and provides reduced
right-hand sides through the existing `PreparedDynamicSystem` reducer. The
small addition `PreparedDynamicSystem.reduce_load` applies the existing real
reduction linearly to the real and imaginary parts independently. It does not
reassemble K/M or perform modal projection.

## Legacy loads and exactly-once composition

`ExcitationChannelSet.from_legacy_model` explicitly adapts existing nodal and
distributed loads using `GlobalAssembler.assemble_load_vectors`. It preserves
the assembler's nodal-then-distributed ordering and assigns deterministic
`legacy:nodal:i` / `legacy:distributed:i` IDs. Existing Newmark temporal
factors, including per-load factors, are evaluated by the existing solver
helpers. The assembled legacy load magnitude is already in the spatial vector;
only its temporal factor is applied during composition. A legacy real load is
also available as a zero-phase harmonic coefficient when the caller supplies
an explicit frequency in Hz.

Legacy loads mixed with explicit channels are rejected. Explicit channels
mixed with legacy temporal controls are also rejected. WP03 does not implement
a disjoint-channel combine mode, so there is no implicit add, override, or
double application. The existing `FiniteElementModel` JSON shape is unchanged;
new channel sets use their own versioned serializer.

| Input path | Spatial data | Temporal data | Mixed with other path |
| --- | --- | --- | --- |
| Historical model loads | Existing nodal/distributed assembler vectors, real | Existing Newmark controls; harmonic legacy loads are zero-phase | Rejected with explicit channels |
| Explicit WP03 channels | Real node/DOF weights | Real constant, piecewise-linear history, or complex harmonic phasor | Rejected with legacy loads/controls |

The current unit policy is deliberately exact-label: channels in one set must
declare the same spatial/amplitude/result units, frame, and sign convention.
No implicit conversion or unit-alias inference is performed. Histories use
piecewise-linear interpolation with endpoint hold in seconds. This is an
explicit WP03 data contract, not a new time integrator.

## Identity, reuse, and domain

Explicit channel identities are independent of operator identity. Changing a
load changes the excitation ID while `PreparedDynamicSystem` continues to
match the same physical/operator inputs and its K/M remain reusable. A bound
map is tied to the prepared operator identity and full DOF signature. Legacy
distributed loads additionally retain their source operator identity because
their integrated distribution depends on the exact prepared geometry and
assembly context.

Binding rejects inactive or incompatible DOFs and requires an admissible
`PreparedDynamicSystem`, which constrains the new path to WP00's TET4, TET10,
HEX8, HEX20 and straight non-rotating BEAM2 domain. This rejection is local to
the new channel interfaces; historical analysis routes were not changed.
Legacy adaptation temporarily receives the dense vectors returned by the
existing assembler API, then stores their sparse node/DOF representation.

## Verification

The targeted command covered the new tests plus prepared-system, Newmark
control, initial-condition, harmonic post-processing, analysis, distributed
load, schema-validation, MITC4 dynamic, Code_Aster BEAM2/TET4 Newmark, and a
BEAM2 integration workflow:

```text
165 passed
Ruff: PASS for changed production and test files
mypy: PASS for changed modules and the repository progressive typing gate
```

An additional `python -m pytest tests/unit -q` run was stopped by the operator
around 45% after prolonged CPU-bound legacy numerical tests. It had reported no
failure before interruption, but is not counted as a full-suite PASS.

The independent arithmetic oracle constructs the expected complex RHS
directly from channel coefficients and node/DOF weights. Direct comparisons
with `GlobalAssembler` establish compatibility/integration only, not
independent physical validation. The tested element families are all five
allowed WP00 families. Tests also cover phase 0/90/180 degrees, exact and near
cancellation, no imaginary truncation during reduction, zero channels,
serialization round-trip, frequency consistency, signal mutation identities,
legacy individual factors, rejected mixed syntax, and unchanged model JSON.

Bounded local sparse-storage smoke: one TET4 model with 12 physical DDL and 64
one-entry channels produced 64 CSC nonzeros using 1,028 bytes for the map;
the equivalent dense coefficient array would use 6,144 bytes. Binding was
observed at 0.000244 s once. One thousand RHS compositions took 0.033342,
0.0330535 and 0.033123 s over three local repetitions. These are small local
measurements only, not a scaling or performance claim.

## Gate status and handoff

- `QF0212_G02_WP03_EXCITATION_IDENTITY_AND_INTERFACE = PASS`.
- `QF0212_G02_GLOBAL = OPEN`; the overall architecture gate spans later work.
- `QF0212_G03_DYN = NOT_YET_APPLICABLE`; no new physical formulation or
  response solve was added.
- `QF0212_G04_DYN = NOT_YET_APPLICABLE`; no dynamic response was solved.
- `QF0212_G05_WP03_INTERFACE_AND_LEGACY_SUBSET = PASS`; release-level gate
  remains open.

No maturity or qualification state was promoted. WP04 can be considered
separately because the frozen DAG allows it alongside WP03 once WP01 and WP02
are complete. WP05 and WP06 remain blocked on WP04 and their own authorization.
No numerical solve was introduced. Historical `G03 = FAIL_PRESERVED`,
`WHOLE_REPOSITORY_ARCHIVE_CLEARED = NO` and `WP14 = HOLD_NOT_PROMOTED` remain
unchanged.
