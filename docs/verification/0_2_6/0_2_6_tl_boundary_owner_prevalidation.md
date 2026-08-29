# TL Boundary Owner Pre-validation

Status: `PASS_DIAGNOSTIC`; this decision approves bounded diagnostic policies and does not promote Total-Lagrangian capability.

## Provenance

- Decision start SHA: `3601e13263960e854d2b1c3231ba115b6ddc3990`
- Campaign source SHA: `5d16ab839679dcee64e6251085ba52c4b494847c`
- Campaign capture: `dirty=false`
- Controlled decision: `qualification/0_2_6/tl_boundary_study/tl_boundary_owner_prevalidation.json`

## Owner-approved bounded policies

### Mesh

`MESH_POLICY = OWNER_APPROVED_BOUNDED`

- No universal threshold is derived from nominal aspect ratio alone.
- Jacobian, mesh quality/distortion and measured diagnostics are mandatory checks.
- The stable, degraded and out-of-scope zones describe the tested domain only.

### Tangent conditioning

`CONDITIONING_POLICY = OWNER_APPROVED_BOUNDED`

- Tangent conditioning remains a mandatory diagnostic.
- No universal numeric cutoff is approved.
- Severe conditioning together with Newton failure remains explicit and fail-closed.

### Adaptive cutback

`ADAPTIVE_CUTBACK_POLICY = OWNER_APPROVED_BOUNDED`

- Opt-in cutback is allowed as a robustness mechanism.
- Rollback is mandatory.
- Reaching the minimum increment is an explicit failure.
- Adaptive recovery never erases the fixed-step history.

## Frozen evidence

| Item | Result |
| --- | ---: |
| TET4 cases | 75 |
| HEX8 cases | 75 |
| Fixed-step successes | 134/150 |
| Adaptive successes | 146/150 |
| Recovered by cutback | 12 |
| Failed in both modes | 4 |
| Stable conditioning median | ~3.97e3 |
| Degraded conditioning median | ~9.25e4 |
| Out-of-scope conditioning median | ~8.22e6 |

The four persistent failures, the twelve degraded cases and the historical CASE2 anchor remain in the [failure zoo](../../../qualification/0_2_6/tl_boundary_study/tl_boundary_failure_zoo.json). These values are observations, not acceptance thresholds.

## Technical decision

- `TL_FORMULATION_FIX_REQUIRED = NO`
- `NEWTON_FIX_REQUIRED = NO`
- `TL_BOUNDARY_STUDY = PASS_DIAGNOSTIC`
- `TL_PROMOTION = DEFERRED`
- `026-G07` remains `NOT_STARTED`; this pre-validation does not close it.
- `CONTRACT_LOWERED = NO`

The next step is a separate TL numerical robustness R&D plan. No R&D implementation, Arc-Length/G08 work or promotion is authorized by this document.
