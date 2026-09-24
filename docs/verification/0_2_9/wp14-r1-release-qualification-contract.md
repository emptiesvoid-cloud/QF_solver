---
doc_id: DOC-029-WP14-R1-CONTRACT
revision: 1.0
status: controlled
applicable_version: 0.2.9-development
---

# WP14 R1 — release qualification contract

Contract ID: `QF-029-WP14-RELEASE-QUALIFICATION-R1`  
Governing source: `0.2.9-unified-nonlinear` at
`b2485f98260c7ca9892997eefa3a327637d83cd3`  
Active WP14 allocation: `1 point`, under Owner decision
`OD-029-WP13-R2.1-01`.

This prospective contract prepares WP14 for Owner review. It evaluates the
0.2.9-development qualification record and the repository's existing quality,
engineering, documentation, package, and public-source gates. It is not an
authorization to publish a new package.

## Frozen acceptance gates

1. **Provenance and integrity:** exact governing baseline, resolvable freeze
   and execution SHAs, clean final evidence tree, and matching SHA-256 hashes.
2. **Ledger reconciliation:** `progress.json`, `progress.md`, and
   `owner_decisions.json` agree on `95/100` before WP14, WP14 `0/1`, and the
   active `WP13/WP14/WP15 = 1/1/2` allocation. The historical roadmap remains
   unchanged.
3. **Claims and registries:** public maturity and qualification claims remain
   no broader than accepted, bounded evidence; references resolve; known
   limitations and historical failures remain visible.
4. **Standard quality:** execute the commands in the current
   `.github/workflows/quality.yml` standard job on available Windows/Python
   3.13. This includes Ruff, progressive mypy, unit/integration coverage at
   least 80%, the P0 traceability coverage gate, compileall, and quick checks.
5. **Engineering:** run the existing full MITC4 verification and
   `verify-all --profile engineering` gates.
6. **Documentation and packaging:** run the workflow's controlled benchmark,
   engineering documentation generation, evidence-enabled documentation
   tests, strict MkDocs build, and packaging integration tests.
7. **Public-source/package hygiene:** build wheel and sdist without upload;
   audit public source, generated archive and reachable history.
8. **Platform scope:** only executed platform/Python legs may be reported as
   PASS. The GitHub matrix (Windows and Ubuntu, Python 3.10 and 3.13) is not
   inferred from a local run.

## Explicitly outside this execution

- No solver mechanics, numerical thresholds, maturity status, or historical
  evidence are changed.
- No public package version/date/citation update, release tag, upload, or
  publication is performed.
- No governing merge, push, ledger update, or official WP14 point award is
  performed.
- The package's currently published metadata remains 0.2.8 until a separate
  Owner release decision. An untagged 0.2.9 development branch is not claimed
  to be a publishable 0.2.9 release.

The machine-readable, frozen gates and command list are in
[`qualification/0_2_9/wp14/wp14_r1_release_contract.json`](../../../qualification/0_2_9/wp14/wp14_r1_release_contract.json).
Any failed or missing required gate is reported as HOLD; there is no threshold
relaxation or implicit PASS. Passing local gates yields only
`PASS_CANDIDATE_WITH_LIMITATIONS`, pending Owner review.
