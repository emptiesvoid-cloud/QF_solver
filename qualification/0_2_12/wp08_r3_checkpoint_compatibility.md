# WP08-R3 — Corrected constitutive checkpoint compatibility

**Record type:** bounded restart/identity verification, not a general NL migration policy.

## Version and identity

The repository's existing nonlinear checkpoint container remains schema v2; R3 does not create another checkpoint framework. A corrected checkpoint now records in `migration_metadata`:

- `formulation_id = corrected_corotational_biot_j2/v1`
- `constitutive_state_version = corotational_j2_state/v2`
- existing container `schema_version = 2` and accepted-state schema version

Every corrected integration-point state also carries the corrected formulation ID, state schema, and material identity. The material identity covers the class and parameters consumed by the corrected J2 local return. The existing `model_signature_v2` includes the explicit formulation selector, model geometry/connectivity, analysis parameters (apart from output/checkpoint paths), materials and state topology. Changing the material or formulation therefore invalidates the model signature.

## Fail-closed restart behavior

When the corrected route is selected, restoration refuses a checkpoint unless:

1. its ordinary model signature, DOF count, load-path position, and state topology validate;
2. every persisted material integration-point state has the corrected formulation and state-schema IDs; and
3. checkpoint migration metadata explicitly carries those same IDs.

There is no legacy-to-corrected conversion. A readable legacy file does not establish `SAFE_TO_RESUME`. Corrupt data and material/model mutations are rejected by the existing store/signature checks. No historical checkpoint is rewritten.

## Tested behavior

`test_corrected_checkpoint_restart_is_formulation_bound_and_deterministic` saves the accepted first increment, reloads it under the same corrected model, and compares the final displacements (`rtol=1e-11`, `atol=1e-12`) and material-state digests against the continuous solve. It also inspects the saved formulation metadata.

`test_corrected_restart_rejects_legacy_checkpoint_and_changed_material` verifies rejection of a legacy checkpoint under corrected selection, a corrupt checkpoint, and a corrected checkpoint after changing the material yield stress. `test_corrected_state_is_versioned_detached_and_transaction_safe` verifies state schema/material identity and immutable trials. The broader existing checkpoint and transaction suites are included in the reported R3 regression run.

## Boundary

These checks establish only the listed bounded fixed-load/adaptive load-control path. They do not complete WP10's migration audit, prove compatibility for every historical schema or continuation method, add checkpoint encryption/authentication, or qualify restart for general NL analyses. Until a matching corrected identity is proven, restart is refused.
