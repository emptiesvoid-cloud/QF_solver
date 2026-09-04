---
doc_id: DOC-027-WP13-001
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 WP13 Golden Numerical Baseline

Status: `PASS`  
Gate: `LUP-027-G13`  
Execution source snapshot: `94ce10a53e31ad6884383c7ec8ce1761d9533eff`
Evidence: `qualification/0_2_7/golden/evidence.json`

WP13 establishes a small, fast, deterministic reference set for detecting
numerical drift during the Level-Up work. It is a controlled proof set, not a
new qualification campaign and not a public maturity promotion.

## Cases

| Case | Route | Oracle | Verdict |
| --- | --- | --- | --- |
| `WP13-STATIC-TET4` | linear static | equilibrium residual | `PASS` |
| `WP13-STATIC-TET10` | linear static | equilibrium residual | `PASS` |
| `WP13-STATIC-HEX8` | linear static | equilibrium residual | `PASS` |
| `WP13-STATIC-HEX20` | linear static | equilibrium residual | `PASS` |
| `WP13-WEDGE6-STATIC` | experimental static slice | equilibrium residual | `PASS` |
| `WP13-WEDGE6-MODAL` | bounded modal route | modal residual | `PASS` |
| `WP13-J2-SMALL-STRAIN` | existing material campaign | campaign status | `PASS` |
| `WP13-BUCKLING-BOUNDED` | bounded linear buckling | eigenpair residual | `PASS` |
| `WP13-PREFLIGHT-UNKNOWN-ELEMENT` | fail-closed preflight | expected error | `EXPECTED_FAILURE_PASS` |

Eight positive cases passed and one controlled failure was correctly classified.
All cases were replayed twice with identical result digests. The catalog and
runner are directly replayable with:

```text
python scripts/run_wp13_golden.py
python scripts/run_wp13_golden.py --replay
```

The runner records source SHA, input digest, result digest, environment,
observables, oracle, predeclared tolerance and artifact classification. The
positive checks reuse existing residual policies; no WP13 tolerance was tuned
after observing results. Raw eigensolver observables are canonicalized to 12
decimal places in the persisted record to remove harmless floating-point ulps;
this does not alter solver output. A source SHA mismatch is an explicit replay
failure.

## Release truth

The baseline keeps three roles separate:

* `qualification_snapshot_026`: `93561c2c0ae1c173deb81e47c3fa3852643275cb`;
* `release_source_snapshot_026`: `e839373b6aef291a93292186d7553ba5cd12af55`;
* `current_development_head_at_execution`: `94ce10a53e31ad6884383c7ec8ce1761d9533eff`.

WP14 through WP18 are only checked for references to the Level-Up contracts;
no large-scale benchmark was launched by WP13.
