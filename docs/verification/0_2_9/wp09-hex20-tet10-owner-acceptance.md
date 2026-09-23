# WP09 — Owner acceptance HEX20 and TET10 extensions

## Decision

The Owner accepts the HEX20 and TET10 WP09 extension dossiers within their
explicit bounded scope. This decision does not add points to the official
WP09 score: the official score remains the previously accepted HEX8 `8/8`.

```text
OWNER_ACCEPTS_WP09_HEX20 = YES
OWNER_ACCEPTS_HEX20_LIMITATIONS = YES
OWNER_ACCEPTS_WP09_TET10 = YES
OWNER_ACCEPTS_TET10_LIMITATIONS = YES

HEX20_EXTENSION_STATUS = ACCEPTED_WITH_LIMITATIONS_NON_SCORING
TET10_EXTENSION_STATUS = ACCEPTED_WITH_LIMITATIONS_NON_SCORING
WP09_OFFICIAL_POINTS = 8/8
LEDGER_IMPACT = NONE
```

## Verification performed before integration

The raw primary and replay JSON files were verified read-only in their source
worktrees against the SHA-256 values recorded by their manifests:

- HEX20: all six H1/H2/H3 primary and replay files, plus the independent
  observable-recomputation summary: PASS;
- TET10: all six H1/H2/H3 primary and replay files, plus the historical and
  corrected independent-reference summaries: PASS;
- no structural solve was rerun;
- no raw result was modified;
- no production source change is introduced by either extension;
- the historical TET10 reference-tooling `FAIL_CLOSED` record remains
  preserved alongside the corrected reference evidence.

The large primary/replay files remain local ignored evidence as specified by
the repository artifact policy. Versioned contracts, manifests, reports and
independent-reference summaries are integrated here; the local evidence
locations and their hashes remain recorded by the extension audit dossiers.

## Accepted technical scope

- HEX20 and TET10 family-specific qualification extensions only;
- bounded corotational J2 route with the declared local-small-strain bound;
- frozen consistent surface traction and family-specific mesh hierarchy;
- reference evidence is an independent observable recomputation, not an
  independent global FEM/Newton solve;
- no Code_Aster/CalculiX correlation is claimed;
- no general finite-strain plasticity, contact/friction, dynamics,
  MPI/PETSc, or cross-family qualification claim is created;
- full repository test suite was not run for these extensions.

## Provenance

```text
GOVERNING_BASE_SHA = 3e4f79161c0484563387a55d3de9c19c5389f9b3
HEX20_BRANCH_HEAD = 85bb719980705d8c7214ab56ab331c6a52aeae63
HEX20_EXECUTION_SHA = eea9b3b4f8e6e4b8bcce4626c7f301911aeb4f7e
TET10_BRANCH_HEAD = 7257eb86155a4a9aa115fdbd9982cb22625b5152
TET10_EXECUTION_SHA = 338a75eaced8866b87f935ee5d7753a4bf8cc473
TET10_REFERENCE_REMEDIATION_SHA = 404e35b55155f6bb5d1c116fda362831750609f3
CONTRACT_AND_POLICY_DIGESTS = recorded in the merged audit JSON files
```

This document records the Owner decision and the integration of the accepted
non-scoring extensions. It does not revise the official ledger or overwrite
historical evidence.
