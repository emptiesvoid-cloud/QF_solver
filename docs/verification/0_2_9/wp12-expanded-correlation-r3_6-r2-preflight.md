# WP12 R3.6-R2 — preflight blocked before execution

The frozen R3.6-R2 contract was not executed. Its preflight failed before any Docker runtime probe or Code_Aster case started because the runner checked the legacy contract-builder source path instead of the R2 builder path recorded by the contract.

This is a provenance/tooling guard defect. It is not a solver or numerical result. The R2 contract remains frozen and unchanged; no case output directory, manifest, or numerical result was created. A new R3 contract must explicitly bind its contract-builder path, and the runner must resolve that path from the frozen contract. The R2 preflight failure will remain in the new contract's lineage.

```text
BRANCH = codex/wp12-expanded-correlation
R2_CONTRACT_COMMIT = 8e007e8a379e5e0359cc9f744515cfa5cbdd4b83
R2_CONTRACT_SHA256 = f09dc422e251c355c3f351bc219ce18745eade0199853d2a31e64b913fff5d64
RUNNER_SHA = 69dbcb8c887456e0e1686bed605a6e80189a3273
PREFLIGHT_STATUS = FAIL_CLOSED_PREFLIGHT
FAILURE = Frozen contract_builder_sha differs from tracked source commit
CASES_STARTED = 0/144
DOCKER_RUNTIME_PROBE = NOT_STARTED
CODE_ASTER_PROCESSES = 0
RAW_OUTPUT_CREATED = NO
R2_CONTRACT_MODIFIED = NO
WP12_POINTS_CHANGED = NO
```

The machine-readable record is `qualification/0_2_9/wp12_external_vv_r3_6_diverse_r2_preflight_audit.json`. R2's output paths remain absent and reserved as historical, unexecuted paths; R3 must use separate paths.
