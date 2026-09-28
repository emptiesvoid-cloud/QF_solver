---
doc_id: "DOC-MARKDOWN-A507B913973677AE"
revision: "0.1"
status: "controlled_evidence"
applicable_version: "0.2.9"
reviewer: ""
approver: ""
---
# WP08 area-supported contact — R1.10 remediation candidate

## Purpose and status

This note records a source-level remediation candidate following the immutable
R1.9 diagnostic run. It is not a qualification report, does not supersede R1.9,
and awards no WP08 points.

```text
R1_9_STATUS = M1_M2_PASS; M3_STICK_PASS; M3_SLIP_FAIL_CLOSED
R1_10_STATUS = IMPLEMENTED_AND_TARGETED_TESTED; NOT_STRUCTURALLY_EXECUTED
WP08_FORMAL_STATUS = NOT_QUALIFIED
WP08_POINTS = UNCHANGED
```

Candidate provenance:

```text
BRANCH = codex/wp08-area-contact-r1-10-candidate
BASE_SHA = af8de1009268b2a9503373cc7cea2d99c0df28c9
IMPLEMENTATION_SHA = e29f2f9204727412275f7a7a04cd185ab7f36d0b
SLIP_ROOT_SOURCE_SHA256 = 9f80875f368136b0d1f926a301f0f9a8bc17beda02f0c769756e08cefa884b42
REGRESSION_TEST_SHA256 = 7d645ed58bafd016282ca47238345e1f75212c7cc4b13d2990f193414ab3494a
```

## R1.9 failure evidence

R1.9 M3/slip failed at load step 8 and rolled back. The preserved failure record
reports:

- the direct active-set route cycled at its existing 25-iteration limit;
- the frozen-mode trust-region solver stopped on `xtol`, with maximum
  per-contact scaled residual `1.5001347413695734e-9` against the unchanged
  `1e-9` gate;
- after normal-set correction from 15 to 20 contacts, the coupled route also
  stopped on `xtol`, with scaled local residual `2.144076198589106e-9`;
- no wider contact-set search, threshold relaxation, retry, or parameter edit
  was performed after that campaign failed.

The R1.9 failure record remains at
`qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_9_20260926/M2_M3/M3/slip_target/failure.json`
with SHA-256
`ce824e409e4dc27722e122173c1aff17666d745bc3425f51173e7bd0561f5ffe`; its
telemetry SHA-256 is
`b97a03cf5c26629a846f6b034f3fbd1f71a617d00ea71f8216539fd3b53d6fcf`.

The R1.9 source contained two relevant numerical weaknesses: the active-slip
semismooth retry restarted from the original seed instead of the latest
`root()` candidate, and the coupled projection's trust-region Jacobian was
finite-differenced even though the frozen linear contact system admits exact
unit-force sensitivities.

## R1.10 candidate changes

The code/test changes touch `src/solveur/contact/slip_root.py` and the targeted
regression module; this note records the candidate and its current gate.

1. The active-slip retry now starts from the best finite iterate among the
   hybrid root result and the semismooth attempt. Failed semismooth attempts
   retain their last candidate and consumed iteration count for the next
   bounded stage.
2. The coupled stick/slip projection now forms its piecewise-consistent
   Jacobian from exact linear displacement and pressure sensitivities. The
   derivative follows the actual stick or slip projection branch and includes
   the derivative of the per-contact pressure-based residual scale.
3. Trust-region solves use that Jacobian. If SciPy terminates on `xtol` while
   the frozen local residual gate is still exceeded, a safeguarded Newton
   correction starts at the optimizer's best candidate, using only the unused
   portion of the existing 30-iteration semismooth budget.
4. Failure diagnostics preserve the optimizer termination, local residuals,
   refinement outcome, and worst-contact context. The same physical
   per-contact `1e-9` acceptance gate remains authoritative.

No mesh, contact area, `kappa`, material, load, boundary condition, friction
coefficient, threshold, active-set iteration limit, fallback policy, or
benchmark scope was changed. R1.9 evidence is preserved independently and was
not rewritten.

## Validation performed

- Targeted contact/friction suites: **67 passed**.
- Ruff: **PASS** for the changed source and regression module.
- Mypy: **PASS** for `slip_root.py`.
- Compile check and `git diff --check`: **PASS**.
- Full repository suite: **NOT RUN**.
- New M1/M2/M3 structural campaign: **NOT RUN**.

The new tests compare the analytic scaled Jacobian against centered numerical
differences on both stick and slip branches, include pressure-dependent
normalization, demonstrate correction of an `xtol`-stopped candidate that is
above the physical gate, and confirm that a stalled correction remains
fail-closed.

## Owner authorization and runner readiness

The Owner subsequently gave explicit authorization to freeze the R1.10
runner and execute one serial M1/M2/M3 campaign. The prospective runner copies
the R1.10 source into versioned runner files, binds a dedicated source
inventory, verifies the immutable R1.9 failure bundle by SHA-256, and stops
downstream cases at the first failed gate. Raw per-case outputs are excluded
from Git while compact contracts, manifests, and final summaries remain
versionable.

Runner-specific tests and targeted mechanics tests were executed after the
runner correction: 96 passed. Ruff, mypy on `slip_root.py`, compileall, and the
12-file R1.9 hash audit passed. The full repository test suite was not run.

At the point this preparation note is committed, no R1.10 contract has yet
been frozen and no R1.10 structural solve has started. The next operation is
to commit this runner freeze, create the unique R1.10 output binding, then run
M1; M2 and M3 may proceed only when their preceding frozen gates pass.

```text
R1_10_OWNER_AUTHORIZATION = GRANTED_FOR_ONE_SERIAL_PROSPECTIVE_CAMPAIGN
R1_10_CONTRACT = NOT_FROZEN_AT_REPORT_TIME
R1_10_STRUCTURAL_EXECUTION = NOT_STARTED_AT_REPORT_TIME
NEXT_STEP = COMMIT_RUNNER_FREEZE_THEN_CREATE_CONTRACT_AND_START_M1
```
