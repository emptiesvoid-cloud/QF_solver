# WP08 R1.13 — Owner decision

**Decision date:** 2026-09-27

**Decision ID:** `OD-029-WP08-AREA-R1.13-01`
**Status:** `CLOSED_OWNER_ACCEPTED_EXPERIMENTAL_WITH_LIMITATIONS`

## Decision

The Owner accepts the R1.13 area-supported contact M1/M2/M3 results as
**experimental, bounded evidence with the limitations below**. This decision
does not constitute formal WP08 requalification, does not change the prior
WP08 award, and does not authorize a merge or push.

```text
OWNER_ACCEPTS_R1_13_EXPERIMENTAL_EVIDENCE = YES
OWNER_ACCEPTS_R1_13_LIMITATIONS = YES
R1_13_EXPERIMENTAL_STATUS = ACCEPTED_WITH_LIMITATIONS
WP08_FORMAL_REQUALIFICATION = NOT_ESTABLISHED
WP08_OFFICIAL_POINTS = 8/8 — PRIOR OWNER AWARD PRESERVED; NO CHANGE
GLOBAL_OFFICIAL_TOTAL = 95/100 — NO CHANGE
GOVERNING_MERGE_AUTHORIZED = NO
GOVERNING_PUSH_AUTHORIZED = NO
```

## Accepted evidence and scope

The decision covers only the six R1.13 diagnostic cases on the frozen
execution source `b5dde151ff827f140e0431c3cf45a4c18871d5cd`: stick and slip on
M1, M2 and M3. Each case passed its per-case diagnostic gates and accepted all
8/8 load increments. The report and machine-readable audit are linked below.

## Limitations retained

- Slip displacement remains strongly mesh-sensitive: 24.883% for M1→M2 and
  24.541% for M2→M3 under the declared comparison metric. No mesh-convergence
  claim is accepted.
- M3 slip active contact area is 0.875 of the reference patch; this remains a
  reported diagnostic, not a convergence pass.
- The campaign does not provide an independent global FEM/Newton reference,
  a solver replay, or external-solver correlation.
- The result schema does not expose a reliable fallback count; zero fallback
  is not claimed.
- The historical R1.12 M4 `FAIL_CLOSED_NUMERICAL` result remains unchanged and
  is not resolved or reclassified by R1.13.
- The acceptance is experimental and limited to the frozen R1.13 cases and
  route. It does not assert general frictional-contact robustness or formal
  WP08 qualification.

The previous official WP08 `8/8` award and global `95/100` total are preserved
without modification. Any formal requalification, additional solves, merge,
push, or score change requires its own explicit scope and authorization.

## Provenance

```text
BRANCH = codex/wp08-area-contact-r1-13
EXECUTION_SHA = b5dde151ff827f140e0431c3cf45a4c18871d5cd
PRE_DECISION_EVIDENCE_REPORT_COMMIT = dc538b86bc5f1064c59201c627158640682f501c
R1_13_FINAL_AUDIT_SHA256 = c152a2cc0c27b91c1a14da9a27e78ce75a058a6f98a46259b153b108f8e03354
M1_CONTRACT_SHA256 = a81c9b07d9bfc457c8ef5ab48cfd9dcc1f4eab8430f6fc04136889c3229c790a
M2_M3_CONTRACT_SHA256 = 08c568984bd63f66bc7cf30be5407b190ac351cec6f3543f11cb839d09322b4f
```

Evidence: [R1.13 results report](wp08-area-supported-contact-r1-13-final-report.md)
and the [machine-readable R1.13 audit](../../../qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_13_newton_merit_20260927/r1_13_final_audit.json).
