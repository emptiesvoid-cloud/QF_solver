# WP07-E closure — Owner review R2

**Status:** `PASS_CANDIDATE`

**WP07-E candidate:** `2/2`; official E points remain `0/2`

**WP07:** `8/10` current; `10/10` after Owner acceptance
**No WP07-D rerun, push, merge, or official ledger update was performed.**

## Provenance

- E branch / HEAD at verification: `codex/wp07e-closure-r2` / `bf3f1f6daeaf350b9da535a894b611af2dc8b3ee`
- Negative-case runner execution SHA: `f0a891e6b0bce514f1d0662e5b9d1dfd99f80f3d`
- Closure checker SHA / source SHA-256: `bf3f1f6daeaf350b9da535a894b611af2dc8b3ee` / `f40097b51f91d110805d1f7b6f3413a31a6f746b70a523cd1a8f7ec781d1db4c`
- Governing branch / SHA: `0.2.9-unified-nonlinear` / `168e345b74f221fb1b975161faea841ca48d9c7c`
- Accepted D execution SHA: `ed89446bb74d454ec40170a75c9252514ecc95e2`
- Contract SHA-256: `2a6292b3c90a645c752ad388f0c62dc6aa735d1e42225a3dd96333c1bbafcd88`
- Detached binding SHA-256: `892f2de802551107337f3e0eddbcce68294e15aad5080fa1c64b945710e95cec`
- Negative-case manifest SHA-256: `62b021f7c9b2594b43d8451751cdfacc83615957a6c6a332ca2fa9ca1c01c500`
- Contract semantic digest: `d1e2f5bdd76708987fec62fe4e337f9ad6547934ab43d4438ee555838359534d`
- Policy digest: `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`
- Working tree dirty at verification snapshot: `False` (The verification snapshot may include the newly generated, not-yet-committed WP07-E package; final commit cleanliness is checked separately.)

## WP07-D dependency

D is reused from its accepted R1 evidence; no structural rerun was performed.
- Owner acceptance: `YES`, points `3/3`
- Production M1/M2/M3 PASS: `True`
- Independent references M1/M2/M3 PASS: `True`
- Replays: `{"ACTIVE_SET": "PASS", "PENALTY": "PASS"}`
- D raw/control artifacts hash-checked: `80`
- D analysis / formal contract / execution binding / Owner decision SHA-256: `1a81e261eec99e201b6266a41dd87a8f452880dab4105b9a940087ab9e8854ab` / `b923f560a0d6719ee149ea31f912f46b6b7d32600df1cd7b80bf70a40562d7d7` / `ef223ee40ed1d4d9b1c60a20c2ee2958ea4e37acd8c0265058a4a12218fcf52d` / `17837563364304d41ecb9ec4308f455d673f06bd533dc588f7f9daaf85b434dc`
- D production status encodings: `['PASS', 'success']`. PENALTY stores production_status='success'; its case status is PASS, run status is COMPLETED, route aggregate is PASS, and the accepted Owner decision awards D 3/3. The raw encoding is retained.
- Independent reference static source audit: `PASS_STATIC_IMPORT_SCAN`

## Six WP07-E negative cases

| Case | Expected | Observed | Status | Evidence SHA-256 |
|---|---|---|---|---|
| reversed_orientation | `VALIDATION_FAILURE` | `VALIDATION_FAILURE` | `PASS` | `0e909b6d89474f6632ffc49dfe86a3d53dc074c3d6dd76918f3bc5dfdc3c04ba` |
| open_no_contact | `PASS_OPEN_NO_CONTACT` | `PASS_OPEN_NO_CONTACT` | `PASS` | `59926c797eaa5ed721b9411ea38624170ca13f5ca6a9344db98810849b2958c8` |
| excessive_penetration | `CONTACT_PENETRATION_EXCESSIVE, ROUTE_NATIVE_FAILURE` | `CONTACT_PENETRATION_EXCESSIVE` | `PASS` | `c34ad1f0846c7d9ef0853a4d3684defc79fbc1430ccab897e6964463bf70b00b` |
| unsupported_combination | `UNSUPPORTED_EXPLICIT` | `UNSUPPORTED_EXPLICIT` | `PASS` | `4d51a837d062368981fc286a09e947904191eaea4a90df17c46a1254e9c139f5` |
| nonfinite_observable | `EVIDENCE_VALIDATION_FAILURE` | `EVIDENCE_VALIDATION_FAILURE` | `PASS` | `d0555240a3f80588eeab9f9188df1d207562b362cd186ec9a62de57d71160111` |
| incompatible_restart_metadata | `RESTART_METADATA_MISMATCH` | `RESTART_METADATA_MISMATCH` | `PASS` | `247af693d8412ed753aa390449f4839e184210db6d8863877c5eaf6da1a2fe38` |

## Checker result

- Checker: `PASS`; derived gate: `WP07_PASS_BOUNDED`
- Missing evidence: `[]`
- Hash mismatches: `[]`
- Provenance failures: `[]`
- Negative-case failures: `[]`

## Decision state

`WP07E_EVIDENCE_PACKAGE = COMPLETE`

`WP07E_CLOSURE_STATUS = PASS_CANDIDATE`

`WP07E_OWNER_ACCEPTANCE = READY_FOR_OWNER_REVIEW`

`WP07E_CANDIDATE_POINTS = 2/2`

`WP07E_OFFICIAL_POINTS = 0/2`

The global total is intentionally not changed: the available Owner and local integrated ledgers report different baselines and require separate reconciliation.

**Historical evidence and decisions:** preserved unchanged.  
**Production mechanics / frozen thresholds changed by WP07-E:** no / no.

## Targeted validation

- Targeted tests: `67 passed`
- Ruff / mypy / compileall / JSON / diff-check: `PASS` / `PASS` / `PASS` / `PASS` / `PASS`
- Full repository suite: `NOT_RUN`

## Preserved checker iteration

The first R2 checker result remains archived as `FAIL_CLOSED_PRESERVED` at `qualification/0_2_9/wp07e_closure_r2/wp07e_closure_final_r2.json`. The initial R2 checker treated PENALTY production_status='success' as non-PASS despite case aggregate PASS and completed run evidence; corrected in a later checker revision without changing D evidence or E criteria.
