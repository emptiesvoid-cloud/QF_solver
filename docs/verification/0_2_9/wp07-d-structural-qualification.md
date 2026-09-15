---
doc_id: DOC-029-WP07D-STRUCTURAL-QUALIFICATION-001
revision: 0.1
status: invalid_contract
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP07-D — structural qualification preflight

## Result

`WP07D_STATUS = INVALID_CONTRACT`.

No structural solve was started. The required governing SHA and remote head
were both verified as
`a670f106f4eef88a3cfe5ca65a09ed55cdcc19fe` on the isolated branch
`0.2.9-wp07d-qualification`. The targeted no-solve contract checks passed
(`19 passed`) and the input JSON files parsed successfully.

## Blocking contract facts

At the required SHA,
`qualification/0_2_9/wp07d_structural_vnv_contract.json` declares:

- `status = PREPARATION_ONLY`;
- `execution_policy.structural_solves_allowed = false`;
- `execution_policy.status = PENDING_GOVERNING_BRANCH_INTEGRATION`;
- the penalty termination policy and linear backend are supplied later by a
  governing execution policy;
- the governing integration audit records
  `wp07d_execution_authorized = false`.

The expected WP07-D contract digest is
`93c7741ecafd72cfa20e29e323b92ea9356fb93dacaff09a8347789bad9c9ed2` and is
present in the governing provenance record. The raw JSON file SHA-256 is
`a31f32d45bfa65f5aaaac62034cdc94cfafae3d59a7fbc1ce8ce8489d7cae3e9`; these
are distinct because the recorded contract digest uses the repository's
ordered path-name/file-byte provenance scheme.

Running ACTIVE_SET or PENALTY here would require overriding the frozen
execution guard or inventing the missing governing penalty policy. That is
outside this task and would invalidate the evidence.

## Campaign disposition

| Item | Status |
| --- | --- |
| ACTIVE_SET M1/M2/M3 | NOT RUN |
| PENALTY M1/M2/M3 | NOT RUN |
| independent references | NOT RUN |
| replay/determinism | NOT RUN |
| WP07-E | NOT RUN — invalid-contract dependency |
| WP07-D candidate points | `0/3` |
| WP07 official points | `5/10` |
| official total | `58/100` |
| full repository suite | NOT RUN |

No production mechanics, thresholds, solver parameters or fallback policy
were changed. WP05, WP06 and WP08 were not touched.

## Validation and provenance

```text
GOVERNING_SHA = a670f106f4eef88a3cfe5ca65a09ed55cdcc19fe
EXECUTION_SHA = a670f106f4eef88a3cfe5ca65a09ed55cdcc19fe
BRANCH = 0.2.9-wp07d-qualification
POLICY_DIGEST = 93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac
WP07D_CONTRACT_DIGEST = 93c7741ecafd72cfa20e29e323b92ea9356fb93dacaff09a8347789bad9c9ed2
TARGETED_CONTRACT_TESTS = 19 passed
JSON_VALIDATION = PASS
STRUCTURAL_SOLVES_RUN = NO
WP07E_RUN = NO
```

## Required next step

Owner review is required to freeze and bind an executable WP07-D policy. No
qualification result or point can be claimed from this preflight.
