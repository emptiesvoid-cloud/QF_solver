# WP12-V2-R1 — execution preflight stop, 2026-10-26

**OWNER_AUTHORIZATION_RECEIVED · SCIENTIFIC_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN · WP13_STATUS=OPEN**

**Disposition: DENY_EXECUTION at preflight. Scientific result: NOT_RUN. Attempts reserved/launched: 0/0.**

The Owner explicitly authorized one attempt under manifest SHA-256 `fe19d40bd46c0d8c1fc0fc6f49cb37e978b8132d5c5077d15b4ab8d9f46db77d`, accepted the numerical criteria, gamma INCONCLUSIVE protocol and the stated Windows local limitations. The authorization was received at 2026-10-26 14:26:23 UTC (attachment receipt metadata) and expires at 2026-10-27 14:26:23 UTC. The request SHA-256 is `ccc02d21edc6ea7b0d19999c63e19fe772d79ace20c248a58ef26a2ac0a12703`.

This mission followed the Owner's instruction to stop before execution upon a provenance/command/criteria discrepancy. A source-guard lifecycle incompatibility was established before invoking the scientific runner's `run` operation. No attempt was consumed, no campaign directory was created, and no pytest node, assembly, matrix-free product or solver ran. The previous preparation disposition READY_FOR_OWNER_EXECUTION_DECISION did not cover this collection-hook lifecycle defect; this stop report supplies the current launch disposition while preserving that historical preparation record.

## Observed preflight checks

The documented pinned runner `validate` CLI returned `VALIDATED_NOT_AUTHORIZED`. Its identity/environment checks are successful diagnostics, not a scientific result.

| Check | Observation |
|---|---|
| Manifest | Exact approved SHA-256; unchanged. |
| Science | Clean commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`. |
| Tests R1 | Clean commit `67813b4a36a057bbaa9e5fba32bcdea66ddf4df3`, tree `ffee889f0cd70b089ec8e1719b84a667babfa1be`. |
| Runner R1 | Clean commit `a9dcd5ac2b13e02db7e1fe2bc6fb940fbb490a09`, tree `fd4ea17d7a25452f72faa58a62704daa51b62fab`. |
| Inventory | All 34 SHA-256/Git OID entries match. H1 and derived U3 inputs unchanged. |
| Python | Dedicated 3.13.17 interpreter, expected environment; package versions match. |
| Scientific import | Non-numerical diagnostic imports resolve to the frozen science checkout; no installed qf-solver distribution is selected. |
| Native BLAS | OpenBLAS 0.3.29, one observed thread; DLL SHA-256 `6547e9fb966e9773caee2755e91a8bf4d6f3a2f0eebf9646b0158f8675ea4ab5`. |
| Threads | The separate diagnostic child observed all six approved variables set to `1`. |
| Command | Full constructed argv matches the frozen preview, including `-s`, fixed provenance plugin, conftest/plugin restrictions and exact nodeid. |
| Destination | The R1 campaign directory and reservation do not exist. No output destination was reserved. |
| Collection source guard | Incompatible with this test's delayed imports: block before attempt. |

The detailed, sanitized [provenance record](PREFLIGHT_PROVENANCE.json) contains the environment, full command preview, identity results and hashes of the local records. Raw Owner text and full diagnostic records remain local. Their hashes preserve the reference without publishing the local attachment path, account details, credentials or unrelated archives.

## Proven source-guard lifecycle blocker

The [frozen provenance plugin](../../../../../../scripts/local_vv_pytest_plugin.py) implements `pytest_collection_finish` (line 13). It reads `sys.modules.get("solveur")` (line 21), obtains `__file__`, compares it with the expected source root and exits if absent or different. It does not import solveur itself.

The [exact prospective test](../../../../../../tests/unit/test_wp12_v2_tet4_operator_audit.py) imports standard-library modules and pytest at module level. Its solveur imports occur inside `test_tet4_h1_operator_audit_002` (lines 335–344), after collection finishes. Neither `tests/__init__.py` nor `tests/unit/__init__.py` exists. Conftest loading and automatic plugins are disabled. Setting PYTHONPATH does not import a module. The earlier import-origin probe is a separate process and cannot populate the future pytest child's `sys.modules`.

Therefore, in the approved command, the collection hook would observe no solveur module, write a non-matching selection record and exit with a usage error before the test function. No JUnit or pytest usage error was actually produced in this mission, because this deterministic source-based blocker was identified before launch. Confidence is high. A separate read-only worker confirmed the lifecycle reasoning and found no other guaranteed serialization blocker. This was a targeted compatibility review, not an independent mechanical validation.

The manifest remaining `PREPARED_NOT_AUTHORIZED` with `execution_authorized=false` is intentional: the local runner requires that immutable preparation state and checks a separate Owner decision. It is not the cause of this stop. The Owner's approval is valid and was recorded locally; the operational record was marked `BLOCKED_PREFLIGHT`, so it cannot satisfy the runner's executable-decision status check.

## Scientific quantities and verdict

| Requested result | Current-campaign status |
|---|---|
| Global K-Kᵀ, elements 0/8/9 and scalar/batch values | NOT_ACQUIRED |
| Gamma comparisons and hypotheses | NOT_ACQUIRED; no gamma evaluation occurred. |
| All 24 matrix-free columns, differences and norms | NOT_ACQUIRED |
| Rational-reference comparisons and mapping checks | NOT_ACQUIRED |
| Residuals, reactions, force/moment balance | NOT_ACQUIRED |
| Energy/work and archived displacement comparison | NOT_ACQUIRED |
| pytest_execution_status | NOT_RUN |
| gamma_scientific_status | NOT_ACQUIRED |
| overall_scientific_status | NOT_RUN |

There is no new scientific PASS, FAIL or INCONCLUSIVE result. Expected future gamma INCONCLUSIVE behavior is a property of the frozen protocol, not an observed result here. Historical values are not relabeled as current evidence. U3 remains FAIL. The source/fixture hash checks establish identity, not operator equivalence or continuum accuracy.

## Operator diagnostic incident

An initial diagnostic wrapper called `validate_all_cases` from Python stdin. The runner's entrypoint check rejected `sys.argv[0] == "-"`; it was intended to be called through its pinned script. This occurred before any scientific invocation or reservation. The documented pinned `validate` CLI was then invoked successfully. The guard was respected; no source, argv identity or check was overridden. This incident is recorded separately from the source-guard blocker and from scientific results.

## Minimal correction needed before an executable candidate

The provenance plugin should explicitly import the solveur package in the actual pytest child and then verify its resolved source path, rather than depend on a test's module-level import style. The frozen scientific package's initializer is lazy; the correction must preserve that source-origin guard and must not invoke FEM. A synthetic lifecycle test with an initially absent solveur module should demonstrate the behavior before another freeze. Changing the test to force a module-level import is an alternative; the plugin-owned check is the recommended narrower responsibility.

No correction was applied under this execution authorization. The scientific and test identities can remain unchanged if only the plugin is corrected. The corrected runner needs its own commit/tree, plugin inventory hashes and a new prospective manifest SHA-256. The Owner's current authorization explicitly covers only `fe19d40...f46db77d`; it cannot be silently transferred to a different runner or manifest. Previously accepted local limitations need not be re-audited, but the new exact identities/hash require explicit binding before any attempt.

WP12-W remains PREPARED_NOT_AUTHORIZED. Its existing preparation can be retained. No W1/W2 execution is recommended on the basis of this stop: first obtain the intended bounded H1 operator measurements with the corrected launch protocol, then review the quantitative non-gamma controls and any gamma INCONCLUSIVE reserve. No additional audit framework, numerical threshold, solve, mesh or physics change is needed for the launch correction.

All scientific sources, original manifests, U1/U2/U3 tests and WP12-S/U evidence are unchanged. No maturity or WP status changed. Only this report and appropriate provenance metadata are delivered to the branch.
