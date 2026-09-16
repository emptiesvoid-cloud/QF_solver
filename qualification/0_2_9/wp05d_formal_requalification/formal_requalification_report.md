# WP05-D formal HEX20 requalification

## Decision

`FORMAL_STATUS = PASS_CANDIDATE_OWNER_REVIEW_REQUIRED`

The run used the Owner-authorized candidate stress observable. Historical
WP05-D `FAIL_CLOSED` evidence is preserved and remains available for audit.

## Provenance

- `AUTHORIZED_BASE_SHA = a670f106f4eef88a3cfe5ca65a09ed55cdcc19fe`
- `REMEDIATION_SHA = 817b5d098b280fbd0b7fa2938c3204d859f20b0c`
- `EXECUTION_SHA = 72282a6ca6e6574a32c6182eccb001d9816febbc`
- `EVIDENCE_COMMIT_SHA = NOT_YET_COMMITTED`
- `FINAL_SHA = NOT_YET_COMMITTED`
- `REMOTE_HEAD = NOT_PUSHED`
- branch: `codex/wp05d-formal-requalification`
- candidate contract SHA-256: `b5c05bc59d70ea53fdb0b480f4734c0dd53451b75c889e16e750c9fc6e7c12da`
- historical contract SHA-256: `e8ce5ed095bf3f142b64d5a5838682c638478a5a92c8330a10af88584f52d680`
- frozen policy-code digest: `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`
- runtime policy-binding digest: `895d3c932278c0207b207318216c263a427636d57738bef730917fdc7d9b0ef5`

The policy-code digest and runtime binding digest are deliberately
reported as separate identifiers; neither was silently substituted.

## Production and reference results

- production H1/H2/H3: `PASS_CANDIDATE`
- independent observable reference: `PASS`
- H1 replay: `PASS`
- H2→H3 gates: `True`

H2→H3 relative deltas:

- displacement: `0.005642082627288242`
- reaction resultant: `2.968302909120517e-14`
- reaction moment: `1.48970233727858e-05`
- strain energy: `0.005636870399786231`
- candidate representative sigma_xx: `1.837900404751696e-05`

The candidate representative stress values are stored in each production
result and are independently recomputed from the raw NPZ files by the
NumPy-only reference.

## Governance

- `WP05D_CANDIDATE_POINTS = 1/1`
- `WP05D_FORMAL_POINTS = 1/1`
- `WP05D_OFFICIAL_POINTS = 0/1_OWNER_REVIEW_PENDING`
- `OFFICIAL_TOTAL = 58/100`
- `WP05E_STATUS = NOT_RUN_DEPENDENCY_AND_SCOPE_SEPARATE`
- production mechanics changed: `NO`
- thresholds changed: `NO`
- full test suite: `NO`

A successful execution is evidence for Owner review; it does not itself
rewrite the official ledger. WP05-E is not started automatically.

## Fail-closed rule

Any missing artifact, provenance mismatch, reference mismatch, replay
failure, equilibrium failure, envelope failure, or threshold failure
classifies the run as `FAIL_CLOSED` and awards no point.
