---
doc_id: DOC-NL-025-017
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 failure campaign report

## Controlled candidate

The machine-readable evidence is stored in
`results/vnv_0_2_5/g09_latest/summary.json` and
`results/vnv_0_2_5/g09_latest/evidence_manifest.json`. The manifest records
the exact source SHA, `dirty=false`, UTC timestamp, Python/NumPy/SciPy
versions, command and SHA-256 digest. Generated evidence is deliberately
kept outside the source revision; the manifest's `source_sha` is the
provenance authority.

## Result

| Field | Result |
|---|---|
| Gate | `025-G09` |
| Status | `PASS` |
| Evidence status | `PASS_INTERNAL_FAILURE_CONTRACT` |
| Cases | 22 |
| Passed | 22 |
| Failed | 0 |
| False convergence | 0 |
| Release claim | false |

## Covered cases

| Family | Cases |
|---|---|
| Full Newton | `MAX_ITERATIONS`, `SINGULAR_TANGENT`, `NAN_DETECTED`, `INF_DETECTED`, `LINE_SEARCH_FAILURE`, `INVALID_ELEMENT`, `MATERIAL_UPDATE_FAILURE`, `CONTACT_UPDATE_FAILURE`, `MIN_INCREMENT_REACHED` |
| Sparse correction | NaN correction, `+Inf` correction, `-Inf` correction |
| Transactions/retry | contact retry rollback, multi-step retry after a committed increment, state corruption |
| Contact | excessive penetration, penetration cutback/retry |
| Path solvers | arc-length failure, buckling failure |
| Checkpoints/backend | sparse linear solver failure, checkpoint corruption, checkpoint model mismatch |

Every case records the expected and observed reason, `converged=false` and
structured diagnostics. The correction classification rule is deterministic:
NaN-only payloads produce `NAN_DETECTED`; positive or negative infinity
produces `INF_DETECTED`; a mixed payload containing either NaN and Inf gives
`INF_DETECTED` because the infinite value is the more specific failure.

## Verification commands

The targeted replay on the candidate SHA passed:

```text
python -m pytest tests/unit/test_nonlinear_failure_modes.py \
  tests/unit/test_nonlinear_failure_campaign.py \
  tests/unit/test_nonlinear_load_path.py \
  tests/unit/test_nonlinear_state_transaction_contract.py \
  tests/unit/test_nonlinear_checkpoint.py -q
56 passed
```

The controlled campaign replay reported `22 passed / 0 failed`. Ruff passed
for all modified source and test files. No full regression, coverage run,
external solver campaign or other functional gate was rerun as part of this
G09-only lot.

## Gate limitation

This report closes only the failure-mode contract. It does not close G01,
G02, G03, G04, G05, G06, G08, G10, G11 or G12, and it does not qualify the
underlying contact, arc-length or buckling algorithms. Those dependent
functional gates retain their own evidence requirements.
