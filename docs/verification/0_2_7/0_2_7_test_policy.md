---
doc_id: DOC-027-004
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Test Policy

The test level follows the risk of the change. A green lower level does not
substitute for a required higher level.

| Level | Use | Typical commands/evidence | When required |
| --- | --- | --- | --- |
| T0 | Smoke and import health | package import, CLI help/version, minimal maintained example | every work session or handoff |
| T1 | Targeted changed-code tests | focused unit/integration tests for modified modules and contracts | every code or harness patch |
| T2 | Focused checkpoint | cross-family, cross-route or gate-specific replay with manifests | coherent lot end, cross-cutting change, before promotion |
| T3 | Full regression and coverage | full pytest, coverage, package/docs/release checks | important WP close, major integration, WP14 final sweep |

## Execution rules

1. During ordinary WP work, run T0 and T1. Do not run global coverage or full
   pytest after every small patch.
2. Run T2 when a change crosses registry, descriptors, V&V harness or several
   element-analysis routes.
3. Run T3 only at a declared checkpoint. Record the exact command, environment,
   counts, skips and failures.
4. A test that is `PLANNED` is not executable evidence. A `READY` case is not
   a qualified case until its result and acceptance policy are recorded.
5. External tools, slow campaigns and resource-scale probes may be skipped
   only with an explicit reason and a non-PASS classification.
6. Any functional numerical source change requires targeted tests first and a
   risk-based decision on T2/T3. A documentation-only change does not trigger
   numerical regression by itself.

## Evidence minimum

Every T2/T3 result must record source SHA, dirty state, version, command,
environment, configuration, policy identifiers, result counts and artifact
digests. A failed or resource-limited run remains part of the evidence. No
policy may be weakened because a higher level is expensive.

## Initial foundation state

The foundation pack itself changes no numerical source and requires no full
regression. The first implementation lot must establish its own T0/T1 record.
The planned full regression remains `NOT_RUN` until WP14 or an explicitly
approved high-risk checkpoint.
