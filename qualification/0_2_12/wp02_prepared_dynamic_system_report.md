# WP02: Prepared Dynamic System

**Status:** `PASS`
**Branch:** `codex/v0.2.12-wp02-prepared-dynamics`
**Base:** `f1bbf0253966b83c49b0ebec50b1040422fede02`

## Scope delivered

WP02 adds an internal `PreparedDynamicSystem` facade. It snapshots an admissible
linear model, uses the existing `GlobalAssembler` and `AssemblyPlan` for one
paired sparse K/M assembly, then applies the existing `DynamicDofReducer` to
produce the fixed/free and reduction mappings. It adds no reduced modal,
harmonic, or transient solver and does not modify element formulations.

Preparation requires the caller to provide a full source SHA. The physical,
operator, and excitation identities are separate. Identity payloads use the
repository's canonical checkpoint-signature mechanism, with explicit
family/schema domain fields. Sparse operator content is hashed after canonical
CSR normalization. Nodal/distributed loads and existing dynamic load
function/table/factors or harmonic frequency-grid parameters are excluded from
physical and K/M operator identity and instead contribute to the separate
excitation identity.

No global cache exists. A prepared object owns its copied model snapshot,
assembly plan, reduction state, and sparse matrices. It performs one assembly;
compatibility checks recompute identities and assembly-option compatibility
without reassembling. Matrix properties return defensive sparse copies, and the
physical snapshot is exposed as immutable canonical bytes. WP02 creates no
factorization cache.

## Admissible scope and fail-closed behavior

The prepared path accepts TET4, TET10, HEX8, HEX20, and non-rotating BEAM2 with
linear isotropic solid or beam material, positive density, fixed homogeneous
boundary conditions, and concentrated masses/springs restricted to structural
DOFs already present. It rejects shells, other element families, rotating
disks, non-isotropic/nonlinear materials, MPC/RBE, contact, and discrete
entities that introduce new structural DOFs. These checks apply only to the new
preparation facility; legacy analysis routing remains unchanged.

The preparation checks matrix dimensions and finite sparse coefficients. It
does **not** claim global positive definiteness. WP00 makes definiteness
method-specific; each future consumer must fail closed using its own frozen
method contract. WP02 adds no eigensolver or new numerical threshold to test
that property.

## Newmark checkpoint identity

The existing checkpoint storage schema remains readable. Newly written
signatures use `qf-newmark-resume/v2:` and include masses, springs, constraints,
units, physical model data, loads, and dynamic settings. Storage paths and
checkpoint retention settings remain operational metadata. An unversioned
historical signature can still be loaded, but restart is refused because its
physical coverage cannot be established. No historical checkpoint is rewritten
or silently rebound.

## Evidence

The targeted suite reports **109 passed** across prepared-system tests, Newmark
checkpoint cases, assembly-plan checks, and existing TET/HEX/BEAM and legacy
modal/harmonic/transient routes. Tests compare prepared and direct K/M for all
five in-scope element families, exercise physical mutation invalidation and
excitation-only reuse, prove one paired assembly, verify sparse storage and
snapshot isolation, and reject mass/spring-mutated or insufficiently identified
checkpoint resumes.

Direct-versus-prepared matrix comparison is integration/non-regression
evidence, not an independent physical validation. Single-element sparse
storage observations are recorded in
[`wp02_prepared_dynamic_system_contract.json`](wp02_prepared_dynamic_system_contract.json).
They are not a repeated runtime/RSS characterization or a large-model
performance claim.

Ruff passes for changed production and test files, and mypy passes for the new
prepared-system module. A broader mypy invocation on the legacy `dynamic.py`
reports pre-existing typing diagnostics outside the WP02 hunks; this does not
change runtime behavior and is not presented as a pass for that module.

## Gate and handoff

WP02 supplies passing implementation evidence for the PreparedDynamicSystem
and identity portion of `QF0212_G02`. The overall gate remains open for later
architecture and consumer contracts. G03/G04 numerical gates remain
`NOT_YET_APPLICABLE`; no formulation or new response route was implemented.

WP03 can now define explicit excitation channels independently of the prepared
K/M operators. WP04 remains downstream of WP03 and must enforce its own
method-specific definiteness, modal-basis, damping, and cluster contracts.

Historical `G03 = FAIL_PRESERVED`, `WHOLE_REPOSITORY_ARCHIVE_CLEARED = NO`, and
`WP14 = HOLD_NOT_PROMOTED` remain unchanged.
