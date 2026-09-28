---
doc_id: DOC-029-WP08-AREA-SUPPORTED-CONTACT-R1-13-INTEGRATION
revision: 1.0
status: controlled_evidence
applicable_version: 0.2.9-development
reviewer: Owner
approver: Owner
---

# WP08 R1.13 governing integration record

**Status:** fast-forwarded and pushed after explicit Owner authorization on
2026-09-27. This record is additive; the earlier R1.13 evidence decision is
unchanged and remains experimental with limitations.

## Authorization and integration

- Governing branch: `0.2.9-unified-nonlinear`.
- Source branch: `codex/wp08-area-contact-r1-13`.
- Governing HEAD before integration: `cd69958909aabcd74649b92fde768a1a0422ed52`.
- Accepted source HEAD: `d96b91e8ecd5781e0bff4803e256a0976bd6a4db`.
- Integration method: fast-forward; no force push.
- The source lineage contains the WP08 area-contact R1.10–R1.13 work and
  associated historical diagnostics. Historical failures were preserved.
- The initial push was followed by `git fetch`; the remote governing HEAD
  matched `d96b91e8ecd5781e0bff4803e256a0976bd6a4db`.
- This separate authorization supersedes the earlier decision's then-current
  `governing_merge=false` / `governing_push=false` flags prospectively; that
  historical decision was not rewritten.

## Validation and score

- Owner accepted R1.13 as experimental evidence with limitations; no formal
  WP08 requalification was established.
- WP08 remains 8/8; this integration awards no points. Global official total
  remains 95/100.
- JSON records parsed successfully; code/documentation whitespace check passed
  when archived raw `.log` files were excluded.
- A full diff whitespace check reports trailing whitespace in preserved
  historical stderr logs. Those raw logs were not edited.
- No solver or full test suite was rerun during integration.

## Raw evidence and limitations

- Untracked raw R1.13 campaign folders in the source worktree were preserved;
  they were not staged or deleted by this integration. Only already committed
  files in the reviewed source lineage were pushed.
- Slip displacement mesh deltas remain 24.883% (M1→M2) and 24.541% (M2→M3);
  no mesh-convergence claim is made.
- Independent global FEM reference, solver replay, and external-solver
  correlation were not run; fallback count is not exposed.
- Historical R1.12 M4 `FAIL_CLOSED_NUMERICAL` remains preserved and
  unreclassified.
