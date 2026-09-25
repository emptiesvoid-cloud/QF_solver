---
doc_id: DOC-029-CONTACT-ACTIVE-SET-REQUAL-001
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.9-development
---

# Frictional contact active-set remediation and WP07/WP08 reopening

## Decision summary

The reproduced failure is a real robustness defect in the bounded static
frictional-contact implementation. It is not evidence that the previously
accepted WP07/WP08 results were numerically wrong. The correction is implemented
on an isolated branch, and targeted regression evidence passes. WP07 and WP08
are reopened in the roadmap for scoped requalification; their previous Owner
awards and all historical evidence remain unchanged pending a new Owner
decision.

```text
GOVERNING_BASE_SHA = b2485f98260c7ca9892997eefa3a327637d83cd3
REMEDIATION_SHA = 4066b5ad4ac4595de64e9948f62a91140697b06a
EXECUTION_SHA = 4066b5ad4ac4595de64e9948f62a91140697b06a
BRANCH = codex/contact-active-set-remediation

WP07_PREVIOUS_OWNER_AWARD = 10/10 — preserved, not revoked
WP08_PREVIOUS_OWNER_AWARD = 8/8 — preserved, not revoked
GLOBAL_OFFICIAL_TOTAL = 95/100 — unchanged

WP07_REQUALIFICATION = OPEN_REGRESSION_REVIEW
WP08_REQUALIFICATION = OPEN_FRICTIONAL_MECHANICS_REQUALIFICATION
FORMAL_M1_M2_M3_REQUALIFICATION = NOT_RUN
FULL_TEST_SUITE = NOT_RUN
MERGE_OR_PUSH = NOT_PERFORMED
```

## What failed and why

The failure was reproduced on the unmodified governing source with:

```text
py -3.13 -m pytest -q tests/unit/test_frictional_contact_family_survey.py
2 failed in 3.81s
```

The `faceted_ramp_patch-L1` case enters direct active-set cycling. Its terminal
direct iterate reports normal contacts `[0, 2]` and tangential labels
`[slip, slip, stick]`. The frozen-mode root then starts with `[0, 1, 2]`, keeps
contact 2 artificially on the inherited stick branch, and alternates between
normal sets `[0, 1, 2]` and `[0, 1]`. The root fails closed with
`ACTIVE_SET_CYCLE_REPEATED` before the survey can write its evidence.

The defect is not insufficient iteration count. The tangential mode labels came
from a different direct iterate and were held fixed while the normal active set
changed. In the coupled solution, contact 2 must slide; fixing it as stick
changes the normal pressures/gaps enough to make the two normal sets cycle.

## Correction

After the existing direct and frozen-mode root routes fail, the solver now
attempts a bounded coupled recovery route:

- unknowns include both tangential force components for every active frictional
  contact;
- each residual evaluation solves the exact normal-contact KKT system;
- the tangential force is projected onto the pressure-dependent Coulomb disk,
  so stick/slip is reclassified from the current trial state rather than copied
  from the failed iterate;
- normal active-set candidates are visited deterministically and accepted only
  after gap, pressure, complementarity, and Coulomb admissibility checks pass;
- exhaustive enumeration is capped at eight contact operators. Above that cap,
  the route fails closed instead of attempting unbounded exponential work.

The prior direct and hybrid-root paths are unchanged and remain first in the
fallback chain. Material, loads, geometry, contact/search definitions, numeric
thresholds, tolerances, and the direct iteration limit are unchanged. The
fallback chain has changed: this new route is reached only after the existing
routes fail. Zero-pressure sliding remains zero-traction and updates only its
slip reference.

## Numerical evidence after the correction

The focused ramp regression now converges with all three contacts active and
sliding. Its contact gaps are zero to the frozen geometric tolerance, and each
tangential force equals its Coulomb limit:

| Contact | Pressure [N] | Friction limit [N] | Tangential force norm [N] | Gap [m] | State |
|---|---:|---:|---:|---:|---|
| 0 | 197.5282974147008 | 79.01131896588032 | 79.01131896588032 | 0 | slip |
| 1 | 159.3702622950870 | 63.74810491803479 | 63.74810491803479 | 0 | slip |
| 2 | 76.43795836880946 | 30.57518334752379 | 30.57518334752379 | 0 | slip |

The three-family, three-level diagnostic survey completed with `PASS_INTERNAL`
and all seven survey gates passing:

| Gate | Observed | Limit | Result |
|---|---:|---:|---|
| Geometry families | 3 | ≥3 | PASS |
| Mesh levels per family | 3 | ≥3 | PASS |
| Finite response | true | true | PASS |
| Maximum absolute gap | `9.159339953157541e-16 m` | `1e-9 m` | PASS |
| Maximum Coulomb cone excess | `1.4210854715202004e-14 N` | `1e-8 N` | PASS |
| Stick/slip states only | true | true | PASS |
| Sliding exercised | true | true | PASS |

The faceted ramp is slip at L1/L2/L3; the dual-stop family is slip at all three
levels; the deformable TET4 two-slave family is stick at all three levels. The
survey is internal diagnostic evidence, not an independent FEM solve or a
formal WP08 qualification.

## Regression and static checks

The frozen post-remediation command was run on `EXECUTION_SHA` and archived as
JUnit XML:

```text
81 passed, 0 failures, 0 errors
Ruff = PASS
Mypy = PASS (3 files)
Compileall = PASS
git diff --check = PASS
```

The targeted selection covered the frictional family survey, frictional
structural convergence, frictionless contact, WP08-B/C/D friction identities,
rollback and active-set regressions, and WP07 governing integration checks. It
did not run the repository-wide suite or the formal WP07/WP08 qualification
campaigns.

After reopening WP07/WP08 in the progress records, the focused ledger,
Owner-award, public-claims, packaging-compatibility, performance-regression,
and documentation-generation tests passed: **40 passed, 2 skipped**. This
selection verified that the historical awards and 95/100 score remain intact
while the new requalification overlay is visible. One stale assertion that
compared the current 95/100 total to the historical 66/100 WP07-E checkpoint
was corrected to check chronological monotonicity instead.

The authoritative `docs/document_registry.json` now indexes this report and
its evidence. The generated registry view was not refreshed: the existing
publisher gate stops first on missing `reviewer` metadata in the unrelated
`DOC-029-WP04-F-001` record. No metadata was fabricated to bypass that gate.

The copied diagnostic artifacts retain their original CRLF bytes so their
manifest hashes remain valid. A default `git diff --check` treats those CRLF
terminators as trailing whitespace; the CRLF-aware check
`git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --cached --check`
passes while still checking ordinary trailing blanks and whitespace errors.

## Impact and next gates

- **WP07:** its accepted qualification is frictionless, and the new recovery
  route is reachable only from the frictional solve path. The frictionless
  targeted regressions pass. WP07 is reopened only for regression review; the
  prior 10/10 award remains recorded, with no demonstrated invalidation.
- **WP08:** the issue concerns frictional contact and therefore warrants a new
  qualification against the post-fix source. The prior 8/8 evidence and
  limitations are preserved, but no formal M1/M2/M3 results on this source are
  claimed.
- No points or official total were changed. No WP05/WP06 work, merge, push, or
  publication was performed.

Before formal WP08 requalification, freeze a prospective contract bound to
`REMEDIATION_SHA`, bind the actual runner/policy and archived evidence paths,
and obtain the runner-required execution authorization for the intended meshes,
independent reference, and replay. Reuse of the old M1/M2/M3 artifacts without
that rebind is not permitted. Reassess WP07's score only if the scoped
frictionless regression review finds a concrete impact; none is demonstrated
here.

## Artifact integrity

The archived diagnostic survey files are under
`qualification/0_2_9/contact_robustness_requalification/diagnostic_survey_r1/`.
Its V&V manifest records the exact execution SHA, runtime, command, and source
tree as clean at execution. SHA-256 values:

| Artifact | SHA-256 |
|---|---|
| `summary.json` | `3f374c751f01b4b4fb931a639f3821e0272893b6f572353538a42f54724fac0b` |
| `report.md` | `db3262b25110e65b2f028208341f27a434d9c41423cfd16b7ab51d72020f5710` |
| `frictional_contact_family_survey.png` | `271c4a3debca67265b592380063736f36665448984b2ac649e2f4c2f052649ff` |
| `vnv_manifest.json` | `55cf70ca771afb405b725bf0c87f44b89ff4f86cc1f70c12f42b9baf14bbb2f3` |
| `targeted_contact_regression_r1.xml` | `263167477f8435e61e6695e5a97039f26176a6a38aabf29fe3f54aa44492ed10` |

The V&V manifest hash above is the SHA-256 of the archived manifest file; its
own file list intentionally hashes the three survey outputs and excludes the
manifest itself.
