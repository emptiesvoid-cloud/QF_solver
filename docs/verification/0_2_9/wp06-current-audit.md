---
doc_id: DOC-029-WP06-CURRENT-AUDIT-001
revision: 1.0
status: controlled_evidence
applicable_version: 0.2.9-development
---

# WP06 current-state and stale-branch audit

## Disposition

WP06 remains **PREPARATION ONLY — 0/8 points**. Its historical structural
campaign remains `FAIL_CLOSED`; this audit does not rerun or replace it. The
WP06 preparation material is already present on the current governing branch.
Do **not** merge the remote `0.2.9-wp06-prep` branch: it is based on an older
tree and its whole-tree comparison would remove current WP05/WP07/WP08
artifacts. No structural solve, reference solve, replay, or mechanics change
was made for this audit.

## Provenance and branch audit

| Item | Value |
| --- | --- |
| Governing branch | `0.2.9-unified-nonlinear` |
| Governing SHA before this audit commit | `51e8d09c23a2f5ecaf61251cb308e025752b6d6b` |
| Remote preparation branch | `origin/0.2.9-wp06-prep` |
| Remote preparation HEAD | `b405b6c54d2f3505bc0b5a876ec4f5bf9914cfba` |
| Merge base | `12b5331bcbec49e38145ba4a6263df60b8bf4575` |

The preparation branch is 16 commits ahead and 134 commits behind the current
governing branch from that merge base. Its whole-tree comparison changes 525
paths and removes about 2.6 million lines of current tracked content. This is
stale-tree divergence, not a safe integration candidate. The WP06 contracts,
diagnostics, runner/checker helpers, and focused tests inspected in the
preparation branch already match the governing tree; the only difference in
the scoped WP06 comparison is the older document registry on the preparation
branch. The relevant preparation history is already represented in governing
history, including `77977e2e18f278d862e828b9fa35ed72fc4e3b48` and
`168e345b74f221fb1b975161faea841ca48d9c7c`.

The preparation branch's unique changes do not modify `src/` mechanics. Its
useful remaining work is evidence/tooling and historical diagnosis, not an
unmerged solver fix. No cherry-pick is required for the already-matching WP06
scope.

## Historical WP06-D Phase-1 result

The immutable raw record is
`qualification/0_2_9/wp06d_phase1_structural_raw.json` (SHA-256
`c482e54b06a4ee2a7edeb1f9e11a48d5ce4a57817a8c755708e85919406ae050`). The
forensic diagnosis is
`qualification/0_2_9/wp06d1/wp06d1_m2_failure_diagnostic.json` (SHA-256
`247e6c7f058566cf60c1fa8e31f3b146203db5c0f8146068b3bd9a76dcc8a2e0`).

- M1 passed and observed a local maximum at `q=0.8696694118`,
  `lambda=0.0356656084`.
- M2 completed 80 accepted increments without a numerical solve abort, but
  `lambda` remained strictly increasing through the frozen horizon. The
  required refined-mesh limit point was therefore **not demonstrated**.
- M2 force balance was `2.5391635e-17`; moment balance was
  `2.4381964e-05` against the frozen `1e-8` limit. This is a real gate failure,
  but its per-support cause cannot be reconstructed from the archived raw
  displacement state because the full accepted displacement vectors were not
  saved.
- The original runner monitored node 4 alone; the frozen R1 observable is the
  negative mean vertical displacement over crown nodes 2, 3, and 4. Thus the
  original M2 monitor is not valid evidence for the frozen refined-crown
  limit-point comparison.
- Two extended-horizon diagnostic attempts produced no usable records because
  the checkpoint-reader call did not match the baseline reader API. M3 was not
  run, as required by the fail-closed sequence.

The evidence does **not** establish that the arc-length mechanics are
incorrect. It establishes that the frozen qualification gates failed and the
available archive is insufficient to isolate the moment discrepancy. The
appropriate diagnosis is unresolved qualification failure, not a proven
mechanical root cause.

## Preparation remediation and test result

The already-integrated preparation tooling provides a strict mean-crown
monitor with no single-node fallback, a read-only checkpoint compatibility
adapter, lossless accepted-displacement archiving, and independent force/moment
reconstruction. The machine record is
`qualification/0_2_9/wp06_premerge_remediation.json` (SHA-256
`0b04aa80c688bf2bc5064281ad12b24985c9f2257e1079b8dc921ef44f9137da`). These
are instrumentation and evidence-quality improvements; they do not alter
solver mechanics, thresholds, or the historical result.

The targeted audit exposed one inherited WP04-F test assumption: it required
a generated raw file to remain absent in the current checkout even though the
frozen audit revision only established that it was absent at that historical
SHA. The assertion was corrected to test historical presence at the recorded
revision, without treating a descendant artifact as retroactive evidence.
Validation after that test-only correction:

- WP06 focused suites plus WP04-F closure regression: **92 passed**.
- WP07 ledger and E-closure regression checks: **11 passed**.
- No full repository suite was run.

## Next safe steps

1. Keep the historic D1 failure and all raw hashes immutable; keep the stale
   prep branch unmerged.
2. Before another qualification, bind a new execution contract and policy
   digest to the current governing SHA. Preserve the frozen physics and gates.
3. Use the corrected mean-crown observable and archive every accepted full
   displacement vector and state digest; independently reconstruct force and
   origin moment from raw nodal quantities.
4. Any structural requalification requires explicit execution authorization.
   Run only the predeclared sequence; M3 remains blocked until M1 and M2,
   including equilibrium, reference, and replay gates, pass.
5. Keep WP06 at 0/8 until a complete evidence package is accepted by the
   Owner. The global ledger remains **66/100**.

## Audit flags

```text
WP06_PREPARATION = ALREADY_PRESENT_ON_GOVERNING_BRANCH
WP06_FORMAL_STATUS = NOT_QUALIFIED
WP06_POINTS = 0/8
HISTORICAL_D_STATUS = FAIL_CLOSED
HISTORICAL_M2_NUMERICAL_ABORT = NO
HISTORICAL_M2_LIMIT_POINT_GATE = FAIL
HISTORICAL_M2_MOMENT_GATE = FAIL
HISTORICAL_M2_MONITOR_CONTRACT = INVALID
M3_HISTORICAL_STATUS = NOT_RUN_AFTER_M2_FAILURE
REMOTE_WP06_PREP_BRANCH = STALE_DO_NOT_MERGE
PRODUCTION_MECHANICS_CHANGED_BY_AUDIT = NO
THRESHOLDS_CHANGED = NO
STRUCTURAL_SOLVES_RUN_BY_AUDIT = NO
FULL_TEST_SUITE_RUN = NO
```
