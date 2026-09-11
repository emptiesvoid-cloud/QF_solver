---
doc_id: DOC-029-WP02-001
revision: 1.0
status: prospective_contract
applicable_version: 0.2.9-development
---

# WP02-A — prospective state and checkpoint contract

> Current implementation phase: **ARC_LENGTH_RESTART** (WP02-D), 0/6
> points. This contract remains the frozen basis; independent WP02-E closure
> is still required before any points are awarded.

This is a contract record based on baseline SHA
`cced3d30ac12f2e405915766c5329ac53b7b07bb`. The implementation records for
WP02-B, WP02-C and WP02-D document the subsequent bounded implementation;
this page does not award WP02 points.

## Target authority

The persisted nonlinear state is exactly one **accepted** `NonlinearState`.
It contains:

- displacement;
- load factor;
- material state;
- contact state, which may be empty for stateless penalty contact;
- continuation state, including accepted arc-length variables;
- accepted-increment metadata.

Rejected trials, predictor values, transient contact search data and next-trial
controller values are never checkpoint state.

The current implementation still has schema-1 `NonlinearCheckpoint`, separate
fixed-load/continuation restore methods and raw displacement/material save
arguments. WP02-B must make the composite state the persistence boundary.

## Target schema

The prospective checkpoint schema is **version 2**. Required top-level fields:

| Field | Contract |
| --- | --- |
| `schema_version` | `2`; unsupported versions are rejected explicitly |
| `state_schema_version` | Version of the accepted `NonlinearState` payload |
| `model_signature` | Deterministic physical-model and state-topology signature |
| `completed_step` | Accepted increment index only |
| `state_topology` | DOF, material, contact and continuation topology |
| `accepted_state` | The six accepted `NonlinearState` components |
| `component_digests` | Digest for each accepted component |
| `composite_digest` | Digest of the complete accepted state |

Serialization remains NPZ-based with `allow_pickle=False`. The metadata uses
the tagged canonical representation already defined by
`deterministic_state_digest`: sorted mapping keys, exact finite-float encoding,
NumPy `dtype.str`, shape and C-order bytes. Arbitrary Python objects and
executable deserialization are forbidden.

## v1 compatibility

The bounded policy is **READ_V1_WRITE_V2**:

1. Validate the legacy v1 signature and payload.
2. Map its displacement, load factor, material states and continuation state
   into one accepted `NonlinearState`.
3. Initialize an empty contact state only for a contact-free or explicitly
   stateless-compatible route.
4. Add a migration marker to accepted metadata; do not invent metadata that
   v1 did not store.
5. Recompute all component and composite digests.
6. Write schema 2 on the next checkpoint.

Legacy contact-bearing/stateful v1 checkpoints are rejected explicitly because
v1 cannot prove their contact history or topology. This boundary is tracked by
[OD-029-02](owner-decisions.md); no frictional-contact restart support is
claimed.

## Model signature

The v2 signature must include nodes, ordered element connectivity and types,
materials, boundary conditions, nodal/distributed loads, springs, concentrated
masses, MPC/RBE definitions, contact topology, analysis type/method, all
physically relevant load/kinematic/contact/continuation parameters, derived DOF
count and accepted-state topology.

It must exclude checkpoint path, interval, keep-step preference, restart path
and pure output/cache/reporting settings. The current `_signature_payload`
does not yet include all of these physical entities or explicit topology; that
is an implementation requirement for WP02-B, not a WP02-A source change.

## Atomic save and restart

The required order is:

```text
global increment commit
  → validate accepted composite state
  → serialize to same-directory temporary file
  → flush/durably prepare
  → atomic replace canonical checkpoint
  → optional retained-step copy
```

A checkpoint save never decides convergence. A write failure raises
`CHECKPOINT_FAILURE`, does not trigger physical cutback by default and cannot
expose a half-written canonical file.

Two restart gates are frozen:

1. Save/load reproduces every component and composite digest exactly.
2. Continuous versus interrupted-and-restarted fixed/adaptive/arc-length
   execution agrees in accepted path and final physical results.

Persisted deterministic state uses relative `1e-12`, absolute `1e-14`; physical
restart comparisons use relative `1e-9`, absolute floor `1e-12`, unless an
existing test is stricter.

## Scope exclusions

WP02-A does not implement frictional persistence, adaptive penalty-contact
qualification, geometric or J2 formulation changes, PETSc/MPI restart,
nonlinear dynamics/HDF5 checkpoint migration or arbitrary object serialization.
OD-029-01 remains OPEN and blocks WP09 only.
