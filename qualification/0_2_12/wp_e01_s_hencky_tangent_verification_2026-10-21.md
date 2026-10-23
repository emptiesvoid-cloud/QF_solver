# WP-E01-S — Registry Parser Repair and Hencky Tangent Verification

**Date:** 2026-10-21  
**Worktree:** `C:\wpc01-frictionless-public-integration-wt\wp-e01-q`  
**Branch:** `codex/qf-wp-e01-q-hencky-tangent-20261021`  
**Pre-correction HEAD:** `2c155e63ecc3fb8ece81887ec4165ac02c9f787d`  
**Frozen execution HEAD:** `89ecfbd54c7c279e47118adb9cdb18d3e8d4e3a0`

## Outcome

The collection failure was caused by a regex that did not accept the valid trailing comma in the pinned Python tuple registration. The collection guard now parses the registry with Python AST, reads only a unique literal module-level `REVIEWED_TEST_TIERS` dictionary, and checks the exact target tuple, `NUMERICAL_UNIT` classification, and frozen test digest. The Hencky kernel, tangent implementation, test module, registry contents, thresholds, and fixtures were not changed.

The corrected fixed-target supervisor accepted exactly the authorized 35 nodes and ran them once. **35 passed; 0 failed, skipped, xfailed, xpassed, or incomplete.** Both children were contained by the reviewed Windows Job Object. This is bounded material-point verification, not global FEM or Newton qualification.

| Status | Result |
|---|---|
| `HENCKY_MATERIAL_POINT_VNV` | `PREVIOUS_41_PASS_BOUNDED` |
| `REGISTRY_PARSER_DEFECT` | `CORRECTED_BY_SOURCE` |
| `HENCKY_TANGENT_COLLECTION` | `35_OBSERVED_ACCEPTED` |
| `HENCKY_TANGENT_NUMERICAL_VNV` | `VERIFIED_BOUNDED` |
| `HENCKY_TANGENT_CONVERGENCE` | `VERIFIED_BOUNDED` — observed (O(h^2)) region in six sampled sweeps |
| `TANGENT_CONVERGENCE_PLATEAU` | `NOT_ESTABLISHED` |
| `HENCKY_TANGENT_INDEPENDENT_REVIEW` | `PREVIOUS_COMPLETED`; current result also received a separate read-only review |
| `HENCKY_GLOBAL_FEM_ASSEMBLY` | `NOT_RUN` |
| `HENCKY_INCREMENTAL_NEWTON` | `NOT_RUN` |
| `FINITE_STRAIN_J2` | `NOT_IMPLEMENTED` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

## Parser defect and correction

`tests/conftest.py` contains the valid registration:

```python
"tests/unit/test_wp_e01q_hencky_tangent.py": (
    "NUMERICAL_UNIT",
    "...",
    "a99bcc6ea32bff3e2a669d2923380033f23e587aab95f612ab4047f98b7d7b50",
),
```

The old guard regex required the digest string to be followed immediately by `)`, so it rejected the Python-valid comma before the closing parenthesis. The correction in `experiments/wp_e01q_hencky_tangent_collection_guard.py` uses `ast.parse` and `ast.literal_eval` on the AST tuple only. It requires one module-level literal dictionary assignment, literal string keys, one target entry, a three-string tuple, and the exact classification and digest. It rejects missing/duplicate entries, dynamic or unpacked keys, dynamic values, malformed tuples, aliases, unsupported mapping access, and direct mutation. It never imports or evaluates the registry module.

The runtime manifest's guard pin was updated. The exact target test and registry hashes remained unchanged.

### Static regression checks

The extracted parser functions were checked in memory without importing the project, running pytest, or evaluating `tests/conftest.py`. All **18** expectations passed:

* Accepted: tuple without trailing comma; tuple with trailing comma; multiline/whitespace formatting; unrelated entries before and after a valid target entry.
* Rejected: missing target; duplicate target; wrong classification; unrelated path as a substitute; wrong digest; malformed tuple arity; non-tuple value; dynamic key; dynamic value; dictionary unpack; duplicate registry assignment; dynamic update; dictionary alias; `.get.__self__` alias.

Python AST syntax checks passed for the guard and supervisor. The runtime manifest parsed and matched all 18 listed source-identity hashes, all direct execution pins, the 35-node inventory, and the unchanged scientific hashes. `git diff --check` passed.

### Independent parser review

A separate read-only reviewer confirmed the `.get.__self__` alias is rejected and the exact pinned `tests/conftest.py` direct `.get(module_path)` access remains accepted. No P0/P1 blocker was found. The reviewer noted a generic-parser P2 limitation: code using `globals()` or `exec`/`eval` could mutate a mapping without a direct `REVIEWED_TEST_TIERS` AST name reference. Those constructs are absent from the exact hash-pinned registry; this does not affect the frozen execution identity. The guard is not claimed as a general sandbox for arbitrary Python source.

## Collection and supervised execution

**Command invoked once:**

```text
C:/Python313/python.exe -m experiments.wp_e01q_hencky_tangent_supervisor
```

The fixed supervisor accepted no command-line arguments. It ran one guarded `--collect-only` child, compared all node IDs to the frozen allowlist, issued a `COLLECTION_SUCCESS` receipt, rechecked every frozen input, and then ran the same target once. It did not retry. Collection and run child commands used Python 3.13.1 with `-S`, explicit frozen import paths, pytest plugin autoload disabled, no parallel workers, and the exact module `tests/unit/test_wp_e01q_hencky_tangent.py`.

The collection receipt contains the full ordered node inventory and matches the manifest's 35-node allowlist exactly. The test functions cover identity and rigid-spin actions; volumetric compression/identity/extension; two Decimal diagonal cases; six PK1 directional sweeps; four rotation covariance cases; four Hessian-symmetry cases; repeated/clustered spectral cases; invalid base deformations and directions; response immutability; and three energy-Hessian cases.

| Phase | Child PID | Exit | Wall time | Peak process/job committed memory | Cleanup |
|---|---:|---:|---:|---:|---|
| Collection | `33396` | `0` | `1.123481 s` | `70,467,584 bytes` | No active PID; `VERIFIED_WINDOWS_JOB_CLOSED` |
| Run | `26296` | `0` | `1.236703 s` | `70,168,576 bytes` | No active PID; `VERIFIED_WINDOWS_JOB_CLOSED` |

Each Job Object reported process and job commit limits of `268,435,456 bytes`, active-process limit `1`, memory-limit flags enabled, kill-on-close enabled, and breakaway disabled. Each resumed phase showed only its authorized child PID; after exit, the active PID list was empty. Both phases completed under the 120-second parent deadline. These are committed-memory measurements, not RSS/working-set measurements. The parent invocation completed in approximately `2.99 s`.

The full collection receipt and exact node inventory are at `qualification/0_2_12/wp_e01_q_execution_2026-10-21/20261021T155439Z/collection_receipt.json` and `collection_nodes.json`. The supervisor's result is `PASS_35_OF_35`.

## Numerical results

### Analytic and independent reference cases

The analytic identity-state action, rigid-spin action, and three isotropic volumetric actions passed. Both independent 70-digit Decimal diagonal tangent cases passed, including the high-bulk-modulus case. The Decimal and closed-form assertions do not print their residual margins; their absolute and normalized errors are therefore **NOT_RECORDED**. These are independent references for their diagonal cases only.

All four directional rotation-covariance cases, four major Hessian-symmetry cases, three repeated/near-repeated spectral cases, three inadmissible deformation cases, three invalid direction cases, and the read-only response check passed. These test outcomes establish only their stated material-point assertions; numerical residuals for assertions that emitted no diagnostics are not inferred from pass labels.

### Centered PK1 derivative sweeps

All six parametrized cases used steps `2.0e-3, 1.0e-3, 5.0e-4, 2.5e-4, 1.25e-4, 6.25e-5, 3.125e-5`. The printed error decreased at each step. Halving (h) reduced the error by approximately four throughout, consistent with centered-difference (O(h^2)) truncation behavior over the sampled window. The final-step errors are still decreasing; no roundoff floor or turnover was observed.

| Case (mapped by test order) | κ/μ | Analytic action norm (Pa) | Absolute error, coarse → fine (Pa) | Normalized error, coarse → fine | Adjacent error-ratio range |
|---|---:|---:|---:|---:|---:|
| General stretch | 2 | `1.395271074508e11` | `2.119224202e5` → `5.034824995e1` | `1.518861991e-6` → `3.608492347e-10` | `3.9902–4.1194` |
| Repeated stretches | 2 | `1.057759773666e11` | `2.467875803e5` → `6.062823545e1` | `2.333115576e-6` → `5.731758473e-10` | `3.9779–4.0001` |
| Near-clustered stretches | 2 | `7.963422121139e10` | `1.992332259e5` → `4.857426098e1` | `2.501854389e-6` → `6.099671755e-10` | `3.9932–4.0137` |
| Rotated stretch | 2 | `1.790919164804e11` | `2.742326797e5` → `6.847579983e1` | `1.531239852e-6` → `3.823500310e-10` | `3.9301–4.0000` |
| 3D shear | 2 | `1.025758820956e11` | `4.856889184e5` → `1.176393135e2` | `4.734923146e-6` → `1.146851590e-9` | `3.9981–4.0333` |
| Near-incompressible isochoric | 2000 | `9.642111472341e13` | `3.229687855e8` → `7.761830949e4` | `3.349564941e-6` → `8.049928660e-10` | `4.0000–4.0622` |

The stdout labels the sweeps by κ/μ, not by parameter ID. Mapping the five `κ/μ=2` blocks to their case names relies on the frozen pytest parameter order. The independent reviewer confirmed that the measured factor-of-four behavior supports a bounded (O(h^2)) region for these sampled cases.

The test assertion itself accepts the minimum error in each sweep; it does not require order or a plateau. Thus the measured sequences demonstrate a second-order region, but **a roundoff plateau is not established**, and no revised gate is activated. These non-diagonal sweeps compare the separate analytic tangent implementation with centered differences of `ExperimentalHenckyElastic.evaluate(...).first_piola_kirchhoff_stress`; they demonstrate derivative consistency with that response, not an independent proof of the constitutive law.

### Energy Hessian comparisons

Three comparisons used a single step `h=2.0e-4`; they establish one-step consistency only, not a convergence order or roundoff floor.

| Case | Tangent contraction (Pa) | Centered energy difference (Pa) | Absolute error (Pa) | Normalized error |
|---|---:|---:|---:|---:|
| General stretch | `7.814351539797e10` | `7.814351539612e10` | `1.848541260` | `2.36557218e-11` |
| Repeated stretches | `8.852955293070e10` | `8.852955348492e10` | `554.215317` | `6.26022948e-9` |
| Near-clustered stretches | `4.484264395753e10` | `4.484264416695e10` | `209.412804` | `4.66994774e-9` |

The energy finite difference and tangent contraction are mutually consistent checks, not an independent energy-Hessian oracle. No consistent tangent was enabled in the material response, elements, global assembly, or Newton/Armijo routes.

## Evidence and identities

Execution evidence directory: `qualification/0_2_12/wp_e01_q_execution_2026-10-21/20261021T155439Z/`.

| File | SHA-256 |
|---|---|
| `summary.json` | `fbf11f5f093897c17d68b4caf71d6a8f86d6690ec96207005ecfcfe266c1cf21` |
| `evidence_hashes.json` | `07ebd268d88c6cb9f8499213a6f9ab59d39092485d32547a559d1f40c352124b` |
| `preflight.json` | `38271f15af5df3fe83e5542e87278283b6ceb77b2841f60746d1a286a84512ff` |
| `collection_receipt.json` | `c4bdbab12fe3ec713df9f0411c59d183d3d4d25bfd0e7730093ef10e99172aeb` |
| `collection_nodes.json` | `974691ad77bd5956d8dba60f75d8e1b9b9f59fe940fc205e7a5e4fe023b27f0a` |
| `collect/phase_result.json` | `7bdd5d6589e0e43e9e632817ec4ddc040e6d5425bbff828905412ded9d2d0ab3` |
| `collect/stdout.log` | `60ebdb44bfe8812dad2e2411e5d4deb8428f69bdaa0b96fbff221a1ca253d2b1` |
| `collect/stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty) |
| `run/phase_result.json` | `50b665ea7893e820a910f465e922516cadf431b54883ce4696acf9bad8540b95` |
| `run_results.json` | `d80eabce80a030256f1b8681d4888bcd7cbaa03fe6b7b42070c7707261c3f615` |
| `run/stdout.log` | `5e9cf4fe0ab3721afc3c39183a26e4f2353bebb8df828c1ecd5fed04fff6a1a4` |
| `run/stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty) |

Frozen execution identity at run time:

| File | SHA-256 |
|---|---|
| `experiments/wp_e01q_hencky_tangent_collection_guard.py` | `12fa1e05519bb6df39619c4881f0858c7f03007904a9504d41b23c8ba7ae4463` |
| `qualification/0_2_12/wp_e01_q_hencky_tangent_runtime_execution_2026-10-21.json` | `ca7bda50c86a9265c1d321f056bf081f5753e899e4e607f609ea2585a4ecee48` |
| `experiments/wp_e01q_hencky_tangent_supervisor.py` | `dd06c9c427ff915c3d9a6a23aebde5828c69ec9a645c47ca539e56e491998f89` |
| `experiments/wpc01_exploratory_supervisor.py` | `9bd8c75b19b49c758f9558cf9299eeedc18762b1e40dbd69968377a94d6c9090` |
| `src/solveur/materials/finite_strain_hencky_tangent.py` | `31109bbbf2353f9bbd86b7a7b0e5fe776016fdd1638550848b58b8bd4afef135` (unchanged) |
| `tests/unit/test_wp_e01q_hencky_tangent.py` | `a99bcc6ea32bff3e2a669d2923380033f23e587aab95f612ab4047f98b7d7b50` (unchanged) |
| `tests/conftest.py` | `23db87ce25e78f54bb23e382014d69e322fdf2cbe68823914930c8d6d8969305` (unchanged) |
| Preparation manifest | `22dfce5f7daac1a1c96628a6d93c82381880a934f11639927f3bf6d6f8ee1e55` (unchanged) |

## Commits and remaining scope

Parser correction and runtime-manifest pin: `89ecfbd54c7c279e47118adb9cdb18d3e8d4e3a0` (`Fix Hencky tangent collection registry parsing`). The report is committed separately after the frozen execution. The run used the clean frozen HEAD above.

The next scientific step is a bounded total-Lagrangian element-level Hencky tangent study with independently assembled TET4 and HEX8 force/tangent references. Before that, the multistep candidate gate should record direction IDs and explicitly test a sequence-order criterion and any roundoff turnover; current successful minimum-error assertions are not a frozen acceptance criterion. No global FEM, incremental Newton, or native backend execution is claimed here.
