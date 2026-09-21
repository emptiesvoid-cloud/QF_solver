---
doc_id: DOC-029-WP10-OWNER-REVIEW
revision: 1.0
status: ready-for-owner-review
applicable_version: 0.2.9-development
---

# WP10 Owner review — bounded HEX8 coupled mechanics

## Decision status

```text
WP10_STATUS = READY_FOR_OWNER_REVIEW
WP10_CANDIDATE_POINTS = PENDING_OWNER
WP10_OFFICIAL_POINTS = 0/6
STRUCTURAL_SOLVES = M1/M2_COMPLETED
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
```

## Provenance

- execution branch: `codex/wp10-preparation`
- execution SHA: `9749236abf4acb0b04c98a8985e3480edad78a6a`
- runner implementation commit: `854815894f7ecc76cbdcbaf0c7f6a520087db028`
- contract source SHA: `854815894f7ecc76cbdcbaf0c7f6a520087db028`
- contract SHA-256 at execution: `5a3fa40224ed745d9ee807bdb78613d8ddf28901ed7cd554a39a3ecf46163eb5`
- policy scope: existing governing nonlinear policy; no policy edit

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| M1 no-contact HEX8 corotational J2 | PASS_CANDIDATE | `wp10_execution/m1_primary.json` |
| M1 observable reference | PASS | `wp10_execution/m1_reference.json` |
| M2 contact + J2 HEX8 | PASS_CANDIDATE | `wp10_execution/m2_primary.json` |
| M2 observable reference | PASS | `wp10_execution/m2_reference.json` |
| M3 fresh-process replay | PASS_REPLAY | `wp10_execution/m3_replay_audit.json` |

M1 used 8 nodes and 24 DOFs. M2 used 11 nodes and 33 DOFs. Both used four
accepted load increments and the corotational local-strain bound of 0.05.
M2 activated the fixed initial-search contact path and ended with a
recomputed/production gap absolute difference of `3.47e-18`. Replay final
displacement difference was exactly `0.0`.

The maximum recorded relative residual was `1.91e-8` for M1 and `4.94e-8`
for M2. Maximum equivalent plastic strain was `1.11e-3` for M1 and
`1.42e-2` for M2.

## Evidence interpretation

The independent check recomputes contact gap and penalty force from saved
displacements without importing the production contact assembler. It is not an
independent global FEM/Newton solve. The replay verifies deterministic output
from a fresh process. These results establish bounded composition evidence,
not general coupled-mechanics qualification.

## Retained limitations

- HEX8 only; no TET4, HEX20 or other family;
- one-element benchmark; no mesh-convergence gate yet;
- frictionless penalty contact with fixed initial search;
- no friction, finite sliding, updated search, MPI/PETSc or dynamics;
- no independent global FEM solve or Code_Aster coupled correlation;
- no general finite-strain plasticity claim;
- standalone WP07/WP09 acceptance is not substituted for coupled evidence.

## Owner decision requested

```text
OWNER_ACCEPTS_WP10_M1 = PENDING
OWNER_ACCEPTS_WP10_M2 = PENDING
OWNER_ACCEPTS_WP10_M3_REPLAY = PENDING
OWNER_AWARDS_WP10_POINTS = PENDING
```

The package is ready for Owner review. Any points awarded must be explicitly
bounded to this HEX8 coupled-composition scope.
