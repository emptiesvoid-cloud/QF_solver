# WP-E01 Autonomous J2 Verification and Nonlinear Integration Campaign

**Date:** 2026-10-20
**Scope:** WP-E01-A checkpoint/retry stabilization and WP-E01-B small-strain J2 material-point verification
**Status:** Bounded synthetic verification only; WP-E01 remains OPEN / EXPERIMENTAL_TARGET.

## Executive result

The E01-A retry-ledger validation was strengthened to bind persisted rejection history to the accepted state, attempted interval, retry classification, chronology, and half-step schedule. A separate material-point change makes nonfinite and malformed J2 inputs and incoming states fail closed. The final authorized synthetic suites passed: 39 integrated E01-A cases, 25 combined E01-A policy/collection-safety cases, and 23 J2 material-point cases.

The campaign does **not** establish native FEM correctness, production material/contact retry support, crash durability, production Armijo certification, J2 tangent consistency, or scientific qualification. A separate read-only review found no P0/P1 findings and identified two P2 limitations: retry-evidence provenance is not fully persisted for independent restart audit, and extreme finite J2 inputs can still overflow corrected outputs or the tangent. A further cross-route source discrepancy in legacy energy-field semantics also remains unresolved.

## Verified baseline and scope

- Repository root: `C:\wpc01-frictionless-public-integration-wt\wp-e01`
- Branch: `codex/qf-wp-e01-a-implementation-20261020`
- Origin: `https://github.com/emptiesvoid-cloud/QF_solver.git`
- Starting HEAD: `b8dba1b36c686ce9e4fe6a2b1166db7cdd976185`
- The starting tree was clean. The canonical `qualification/0_2_12/ROADMAP.md` was present and was not modified.
- No WP-D01, WP-D02, roadmap, release, or qualification record was changed.

The frozen E01-A numerical parameters and transactional principles were preserved. The J2 tangent remains blocked, new public J2 energy fields remain deferred, and the production Armijo route-certificate registry remains empty.

## Corrections and source traceability

### E01-A rejection history and restart validation

`src/solveur/core/nonlinear/e01a.py:626` centralizes the global rejection-budget guard. The validator at `e01a.py:634` now checks ordered, unique ledger entries, accepted-state identity, finite positive attempted intervals, load-coordinate consistency, minimum/final-step rules, allowed retry reasons, per-base attempt identity and ordinal, and the exact factor-0.5 retry relationship. It reconciles the active write-ahead attempt with the terminal ledger row and refuses counted in-progress attempts, missing history, impossible transitions, and reordered or rehashed-but-inconsistent records.

`src/solveur/core/nonlinear/load_control.py:583` persists the accepted-state identity in interrupted-attempt ledger records. The global budget is checked before another attempt is proposed (`load_control.py:632-635`); a rejection is recorded once after rollback, while the same accepted state remains the retry base. Older WP10 v2 interruption rows that predate the identity field are accepted only through the narrow terminal-row exception when the matching active write-ahead record supplies that same identity. Other missing or incompatible E01-A metadata remains fail-closed.

The initial reported retry-checkpoint failure was an identity-field producer/validator mismatch: the active attempt carried its base accepted-state identity while an interrupted ledger entry did not. The producer/validator paths were reconciled and expanded with restart and semantic-tampering regressions. Current tests verify the tested synthetic routes; they do not prove crash durability or every production contributor's retry attestation.

### E01-B small-strain J2 input/state validation

`src/solveur/materials/solid.py:34` and `solid.py:108` reject nonfinite elastic and J2 material parameters. The material update at `solid.py:145` validates finite six-component strain, plastic strain and optional prior stress, supported material identity, finite/nonnegative accumulated equivalent plastic strain, and finite historical `plastic_dissipation`. Trial stress, yield state, and consistency modulus are checked before return mapping. Valid-path formulas and public output names were not changed.

**Remaining source limit:** the update does not perform a final finite-value check over every corrected plastic output and tangent. Extreme but finite inputs can still overflow those computed results; this is not established as fail-closed behavior.

### Hash-bound tests and safety

The E01-A policy source assertion that had searched a whole module was narrowed to verify the actual helper guard before increment proposal. It retains ordering and terminal-failure checks; its safety classification was not changed. The new J2 module is registered as `NUMERICAL_UNIT` with its exact digest.

The collection hook probes Gmsh only for the pre-existing optional mesh-test allowlist. The reviewed selected tests do not enter that allowlist. A static top-level import-closure review of the selected tests and package initialization found no reachable top-level Gmsh, `ctypes`, subprocess, worker, or native FEM load. The source tree contains function-local optional/native imports elsewhere; those were not reached by the selected test paths. The collection-safety guard and numerical-unit/public-solver deny rules remain intact.

## Executed verification

Only the three authorized test modules were selected. The initial combined policy/collection run is retained in the record rather than hidden.

| Command | Result | Runtime reported by pytest | Scope and limit |
|---|---:|---:|---|
| `python -m pytest -q tests/unit/test_wp_e01a_integrated_vnv.py` | **39 passed** | 2.13 s | Synthetic Newton, residual scaling, correction count, typed retry, rollback, endpoint, checkpoint/restart/ledger mutation, WP10 v2 compatibility, and test-only Armijo derivative schedule. |
| `python -m pytest -q tests/unit/test_wp_e01a_policy.py tests/unit/test_pytest_collection_safety.py` (first run) | **24 passed, 1 failed** | 1.64 s | The failing assertion searched for the former inline budget condition after the source correctly moved the guard into a helper. This was a stale source-structure assertion, not a runtime solver failure. |
| Same combined command after AST-scoped assertion correction and digest update | **25 passed** | 1.46 s | Policy invariants, helper-before-proposal ordering, test classification/hash binding, Gmsh demand-driven probe, unknown-test refusal, and public-solver denial. |
| `python -m pytest -q -s tests/unit/test_wp_e01b_j2_constitutive_oracles.py` | **23 passed** | 0.73 s | Independent tensor-form J2 material-point oracles and fixed-state tangent-direction study only; no elements, assembly, or public solver. |

The first combined-suite failure was preserved and explained; no assertion was weakened to obtain the later pass. A previous campaign result of 22 passed / 1 failed was not independently rerun and is not counted as current evidence. No numerical study, native FEM, Gmsh load, public solve, worker, or test child process was run.

### J2 reference and tangent observations

The material-point oracle uses its own tensor conversions, isotropic elasticity relation, and scalar consistency solve rather than production helper functions. It covers elastic and mixed multiaxial states, hydrostatic and near-zero deviatoric states, engineering shear, perfect plasticity (`H=0`), linear isotropic hardening, load/unload/reload/reversal, malformed state refusal, and input-state immutability.

For fixed incoming states, central finite differences were compared with the production tangent in three directions (mixed normal, engineering `xy` shear, and six-component), for `H=0` and `H=1500`, over geometric steps `h=10^-3,...,10^-7`. Error was normalized by `E ||p||`. Across the three directions, the largest reported error decreased from about `1.25e-3` to `1.39e-11` for `H=0`, and from about `1.25e-3` to `1.65e-11` for `H=1500`. The endpoint remained the best sample; neighboring-sample plateau behavior was not demonstrated. The test only requires the best sample to improve on the first and imposes no tangent acceptance threshold. Therefore this is a bounded derivative study, **not** tangent consistency evidence.

The yield-switch test reports one-sided engineering-shear slope norms of 400 MPa on the elastic side and approximately 30.769 MPa on the plastic side. It treats the switch as nonsmooth and does not use a centered derivative across it as a consistency gate.

The historical direct-material `plastic_dissipation` computation remains endpoint-trapezoidal stress work. It was not renamed or reclassified. No new public energy field was added.

## Independent read-only review

A separate reviewer inspected the combined changes without executing tests or solver code. This review shared the task history and was not blind. It reported **no P0/P1 findings** and confirmed the tested producer/validator agreement, half-step identity checks, independent tensor reference structure, and matching hashes for the test registrations.

Remaining reviewer findings:

1. **P2 — retry evidence in restart records:** the persisted ledger records the retry classification and failure reason, but not the typed increment-dependent evidence, criterion IDs/bounds, or finite-state diagnostics that supported retry. Runtime gating is strict; a restart cannot independently audit that original evidence. Resolving this requires an explicitly reviewed schema change; no schema expansion was made here.
2. **P2 — extreme J2 output range:** input and incoming-state validation is stronger, but all corrected outputs and tangent entries are not checked for overflow after the update. This remains a source limitation.
3. **Tangent evidence incomplete:** no finite-difference plateau was observed, and no threshold was applied. `J2_TANGENT_CONSISTENCY` remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`.

## Cross-route energy semantics requiring Owner review

Source inspection found a legacy cross-route mismatch that was not changed in this campaign:

- `VonMisesElastoplasticMaterial` accumulates `plastic_dissipation` using endpoint-trapezoidal stress work (`solid.py:213-226`).
- `src/solveur/elements/solid/corotational_j2.py:451` assigns the same named field as `yield_stress * alpha` and also emits `hardening_energy = 0.5 * H * alpha^2`.
- Existing result serializers filter `plastic_dissipation` but do not filter `hardening_energy` (`src/solveur/post/solid_results.py:515`, `src/solveur/core/nonlinear/material_state.py:243`).

The direct material-point tests do not cover the corotational element route. The same public field name therefore has route-dependent source semantics, and `hardening_energy` may already be serialized. Owner scientific review is required before any cross-route equivalence claim, field migration, or semantic reclassification.

## Results and remaining blockers

| Claim | Campaign result |
|---|---|
| E01-A integrated synthetic policy/checkpoint paths | **PASS on tested routes**; restart/crash durability not established. |
| E01-A rejection ledger and identity validation | **Verified synthetically** for tested valid/invalid records; persisted typed retry evidence remains a P2 audit limit. |
| E01-B J2 stress update and bounded constitutive cases | **PASS on tested material-point cases**. |
| J2 tangent finite-difference behavior | **INCOMPLETE**; no plateau or frozen threshold. |
| Production Armijo route certificate | **NOT VERIFIED**; registry remains empty. |
| Production J2/contact retry support | **NOT VERIFIED**. |
| Native FEM, public nonlinear solve, or FEM qualification | **NOT RUN / NOT ACQUIRED**. |
| Checkpoint abrupt-crash durability / filesystem atomicity | **NOT VERIFIED**. |
| WP-E01 status | **OPEN / EXPERIMENTAL_TARGET**. |

No further pytest was run after the third bounded verification cycle. The work stops here under the mandate's cycle limit. The next authorized work should address the two P2 source risks and obtain Owner review of the cross-route energy semantics before expanding the scientific claims. J2 tangent qualification, production Armijo certificates, native FEM V&V, and any qualification promotion require separate authorization and evidence.

## Changed-file SHA-256

| File | SHA-256 |
|---|---|
| `src/solveur/core/nonlinear/e01a.py` | `C0DC0EBFB56FC2DA52AFCA89550ADC922E2A52ED04C0B53A2F4A9022CC7BC139` |
| `src/solveur/core/nonlinear/load_control.py` | `4DB5F31AC68E07E1C469F4AD93FFBA75FD4CFA239A6A40B3B9791CEEFA07AFBC` |
| `src/solveur/materials/solid.py` | `8E9119618227DA1CA69386EF59B12403132CCA78C175FC965845AC78FAB0814D` |
| `tests/conftest.py` | `AA16CED1DE7C262ADDDC08FA9E2ABA8F1B6C203202CDDC30536A2E5F338288C4` |
| `tests/unit/test_wp_e01a_integrated_vnv.py` | `FDEEE40FBA5503996739298A3E282428CAE3823CDB983C62FC218B1FC48DB032` |
| `tests/unit/test_wp_e01a_policy.py` | `5DB69015B15B7CF757D70B7AE69C855C6BDB16DF7DC275450006FD82E0F58427` |
| `tests/unit/test_wp_e01b_j2_constitutive_oracles.py` | `73F834B93C556D724E150B91C10C4883FA054B1A510E2CF66BC533D274D3C30B` |
