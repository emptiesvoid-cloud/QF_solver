# WP10 TET4 extension — execution review

## Scope

This dossier extends WP10 from the already bounded HEX8 route to a separate
TET4 route. It does not modify, overwrite, or reinterpret the HEX8 evidence.
The route is limited to corotational J2, frictionless penalty contact with
initial search, a serial four-point load path, and the small bounded model
defined by `scripts/run_wp10_tet4_coupled.py`.

## Provenance

```text
BRANCH = codex/wp10-extension-preparation
EXECUTION_SHA = 1ac9005e01b5b53703ceaafc03e655500f9901ea
RUNNER_SHA = 8b86bd7f8b56a5327a31ce98757fe98e4c75a0c1
CONTRACT_SHA256 = d5d3ec4256a62e64fdfe55a312bebd50993314321234d428d8f323f77ea27313
POLICY_DIGEST = 93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac
ELEMENT_FAMILY = TET4
WORKING_TREE = DIRTY_UNTRACKED_GENERATED_ARTIFACTS_AT_AUDIT_TIME
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
```

The contract hash above is the SHA-256 of the committed extension contract.
The source runner is separately identified because the execution commit also
contains the contract binding and test/report artifacts.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| E1 serial TET4 production | PASS_CANDIDATE | `m1_primary.json` |
| E2 independent observable recomputation | PASS | `m1_reference.json`, `m2_reference.json` |
| E3 fresh replay / route audit | PASS_CANDIDATE | `m3_replay.json`, identical M2 payload |

### Primary results

- M1: 8 nodes, 5 TET4 elements, 24 DOFs, four accepted load steps, no contact.
- M2: 11 nodes, 5 TET4 elements, 33 DOFs, four accepted load steps, one active
  frictionless penalty contact, no fallback.
- M1 maximum recorded relative residual: `4.7654499468054744e-08`.
- M2 maximum recorded relative residual: `7.633468937985644e-08`.
- M2 maximum equivalent plastic strain: `0.028320612582323074`, below the
  frozen local-strain bound of `0.05` for this bounded route.
- Independent M2 gap recomputation error: `6.245004513516506e-17`.
- E3 replay displacement and step payload comparison: exact equality.

The reference is an independent recomputation of contact gap and penalty
observables from saved displacements. It is not an independent global FEM or
Newton solve and must not be described as one.

## Verification

- Targeted tests: `29 passed` (`test_wp10_tet4_extension`, corotational J2,
  frictionless contact).
- Compileall: PASS.
- `git diff --check`: PASS.
- Ruff: NOT EXECUTED; the `ruff` executable is unavailable in this clone.
- Full repository suite: NOT RUN.

## Limitations and decision

This is a TET4 extension candidate, not a formal change to the WP10 official
ledger. No three-level mesh convergence, external-solver correlation,
frictional contact, finite sliding, dynamics, MPI, or general coupled
mechanics claim is made. HEX8 remains the existing bounded WP10 scope.

```text
WP10_TET4_STATUS = PASS_CANDIDATE_READY_FOR_OWNER_REVIEW
WP10_TET4_POINTS = 0/EXTENSION_PENDING
WP10_OFFICIAL_POINTS = UNCHANGED
WP10_FORMAL_MERGE = NOT_PERFORMED
```
