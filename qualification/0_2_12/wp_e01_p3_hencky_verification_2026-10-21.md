# WP-E01-P3 — Registry Repair and Hencky Verification

Date: 2026-10-21

Worktree: `C:/wpc01-frictionless-public-integration-wt/wp-e01-m`

Branch: `codex/qf-wp-e01-m-logarithmic-strain-20261021`

## Outcome

The supervisor’s exact registry-schema mismatch was corrected, committed, and then exercised through the fixed-target Windows Job Object supervisor. The supervisor observed **41 authorized nodes** and ran them once: **41 passed, 0 failed, 0 skipped, 0 xfailed, 0 xpassed**. No retries occurred.

The numerical evidence supports bounded material-point objectivity and energy-gradient checks, plus the previously bounded TET4/HEX8 force-only algebra. It does not establish a Hencky consistent tangent, global FEM assembly, production Newton behavior, or scientific qualification.

The historical WP-E01-N result of **35 PASS / 1 FAIL** is preserved. The P2 registry mismatch rejected the manifest in preflight before pytest; it did not replace or alter that historical result.

## Registry-binding correction

The runtime manifest’s `safety_registry` binding contains exactly `path`, `sha256`, and `classification`. The supervisor had compared it with a two-field dictionary, so it rejected the valid frozen manifest. `_registry_binding_matches()` now requires the exact three-field object and the authorized values: `tests/conftest.py`, its pinned digest, and `NUMERICAL_UNIT`. Exact comparison rejects missing, extra, malformed, or incorrect fields; the manifest classification was retained.

Static source-extracted checks passed for seven registry cases and seven path-identity cases, including malformed and nonexistent inputs. The existing canonical Windows path check remains fail-closed. AST/syntax, manifest schema, diff, and source hash checks passed. The corrected manifest’s 26 source-map pins were checked before execution; the runtime preflight additionally recorded and matched 30 effective source hashes. No test, material, threshold, production kernel, or collection-guard content changed.

The correction and frozen execution identity were committed before launch:

| Item | Identity |
|---|---|
| Starting clean HEAD | `babcc63486525fbc9efb5eb1aef7703b81f16997` |
| Registry repair / execution HEAD | `13c063e65d35125c58675e2cf607f95eb207f49e` |
| Registry repair commit | `13c063e65d35125c58675e2cf607f95eb207f49e` |
| Supervisor SHA-256 | `53ab796de8015306c9d1bc81cc7433a7480865e7055bc7cdaa8382424e4abbbb` |
| Runtime manifest SHA-256 | `8d581b53742a0e9b6a419b103335e09f553e20bec17171f3fbcec0f63eb9dc16` |
| Static WP-E01-M manifest SHA-256 | `42ca471ba4ae6379efa819573ed1c19f743754f48b4d21213bbc2673fdde75ed` |

## Frozen executable identities

| Artifact | SHA-256 |
|---|---|
| Hencky production kernel | `b318dad553073f848b96528c61589ab2015c1eb1dd8fa52cb0bd52d13b09eab2` |
| Numerical-unit module | `cdd2651e9427c0e64284a75671d83d4f14cdd916a979759be0422f44dde84bfc` |
| Safety registry | `33304c38c2ef53aca2b3abc647e490db91245e56b1eb8d04963db1c86e9d8605` |
| Collection guard | `a9ff067c68887d2d0a291acaf847ee4be1548f4120ce789ca39395760caaa945` |
| Windows supervisor | `53ab796de8015306c9d1bc81cc7433a7480865e7055bc7cdaa8382424e4abbbb` |
| Pinned Job Object helper | `9bd8c75b19b49c758f9558cf9299eeedc18762b1e40dbd69968377a94d6c9090` |

The 26 manifest source-map entries and all 30 effective runtime-preflight source entries matched their pinned bytes. The runtime manifest recorded repository branch and execution HEAD `13c063e65d35125c58675e2cf607f95eb207f49e`.

## Supervised execution

Exactly one parent invocation was made from the verified worktree root:

```text
C:/Python313/python.exe -m experiments.wp_e01o_hencky_supervisor
```

The supervisor performed collection first and launched RUN only after the collection receipt accepted the exact inventory. Each phase used one sequential pytest child, created suspended and assigned to its Job Object before resume. There was no ordinary pytest fallback, retry, parallel worker, or simultaneous child.

| Phase | Child PID | Exit | Elapsed | Peak process/job committed memory | Enforcement and cleanup |
|---|---:|---:|---:|---:|---|
| Collection | 17192 | 0 | 1.008 s | 35,987,456 B | 256 MiB process/job limits read back; active-process limit 1; kill-on-close; no breakaway; active PID list empty after exit; cleanup verified |
| Execution | 17912 | 0 | 1.140 s | 70,160,384 B | Same limits and controls; active PID list empty after exit; cleanup verified |

Both phases had a parent-enforced 120-second deadline and did not time out. The Job Object reported the process and job committed-memory caps enabled at 268,435,456 bytes. These values are **commitment** measurements, not RSS/working-set measurements. Stderr was empty in both phases. BLAS was limited to one thread; pytest parallelization and automatic retry were disabled.

### Collection receipt

Collection observed exactly 41 nodes for `tests/unit/test_wp_e01m_hencky_material_point.py`, matching the frozen authorized inventory. The complete node list and fixture mapping are in [`collection/collection_nodes.json`](wp_e01_o_runs/20261021T144944Z/collection/collection_nodes.json). It pins the exact test, kernel, and registry hashes above. The collection completed naturally with no errors, and the supervisor accepted the receipt before RUN.

### Execution counts

| Passed | Failed | Skipped | Xfailed | Xpassed | Incomplete |
|---:|---:|---:|---:|---:|---:|
| 41 | 0 | 0 | 0 | 0 | 0 |

No failed node or numerical discrepancy was reported. The raw node-level pytest report is preserved in [`run/pytest_results.json`](wp_e01_o_runs/20261021T144944Z/run/pytest_results.json).

## Numerical evidence

### Stress objectivity

For each proper left rotation `Q`, the six configurations exercised the expected transformation contracts:

```text
S(QF) = S(F)
P(QF) = Q P(F)
sigma(QF) = Q sigma(F) Q^T
```

The same tests also checked `C`, logarithmic strain, energy, determinant, and the logarithmic-strain-conjugate stress. The rotation was formed about axis `(1,-2,0.5)` with angle `0.81`; its orthogonality and determinant checks passed. The objectivity comparison was Frobenius-norm based:

```text
||actual - expected||_F <= 64 eps max(mu,kappa)
                           + 2e-13 max(||actual||_F, ||expected||_F)
```

The table gives absolute error, relative error (error divided by the comparison stress scale), and the actual proposed bound, in Pa. `S`, `P`, and Cauchy stress all passed in every row.

| Case | `cond(C)` / relative spectral gap | `||S||_F` Pa | PK2 error (relative) / bound Pa | PK1 error (relative) / bound Pa | Cauchy error (relative) / bound Pa |
|---|---:|---:|---:|---:|---:|
| General stretch | 1.8461 / 2.048e-1 | 4.9732e10 | 1.783e-5 (3.585e-16) / 1.222e-2 | 1.757e-5 (3.011e-16) / 1.394e-2 | 1.866e-5 (3.342e-16) / 1.344e-2 |
| Repeated stretch | 1.4938 / 0 | 3.0023e10 | 1.473e-4 (4.905e-15) / 8.278e-3 | 1.459e-4 (4.495e-15) / 8.767e-3 | 1.352e-4 (4.171e-15) / 8.755e-3 |
| Near-clustered stretch | 1.9931 / 2.000e-10 | 5.0201e10 | 5.402e-5 (1.076e-15) / 1.231e-2 | 5.579e-5 (9.297e-16) / 1.428e-2 | 5.885e-5 (1.002e-15) / 1.402e-2 |
| Simple shear | 2.2139 / 2.204e-1 | 5.1903e10 | 6.142e-5 (1.183e-15) / 1.265e-2 | 5.200e-5 (1.113e-15) / 1.162e-2 | 4.652e-5 (1.035e-15) / 1.127e-2 |
| General 3D shear | 1.7137 / 1.795e-1 | 3.5666e10 | 9.640e-5 (2.703e-15) / 9.407e-3 | 9.409e-5 (2.317e-15) / 1.039e-2 | 8.093e-5 (1.975e-15) / 1.047e-2 |
| Near-incompressible isochoric | 1.7280 / 0 | 3.1986e10 | 4.069e-3 (1.272e-13) / 2.280 | 3.905e-3 (1.177e-13) / 2.280 | 3.843e-3 (1.076e-13) / 2.281 |

The near-incompressible case uses `kappa = 1000` times the base bulk modulus. Its modulus-scaled absolute floor is about `2.274 Pa`, so that row’s bound is much less discriminating relative to the roughly `3.2e10 Pa` stress scale than the ordinary-modulus rows. Its observed errors are still about `0.004 Pa`. Across the checks, the largest error/bound fraction is 1.779% (repeated-stretch PK2); the largest absolute errors are 0.00407 Pa for PK2, 0.00391 Pa for PK1, and 0.00384 Pa for Cauchy, all in the near-incompressible case. The largest measured relative errors are `1.272e-13`, `1.177e-13`, and `1.076e-13`, respectively.

These results support the proposed comparison only for these six bounded fixtures and spectra (`cond(C)` about 1.49–2.21, including one `2e-10` relative spectral gap). The allowance is not an Owner-approved universal stress tolerance.

### PK1 energy derivative

The three general-deformation directional sweeps used ten centered-difference steps from `1.024e-3` through `2e-6`. They compared differences of the kernel’s returned energy with the same kernel’s returned `P(F):D`; this is a **self-consistency check**, not an independent tangent oracle. At the preserved `h=2e-6` gate, normalized errors were:

| Direction | Absolute error at `h=2e-6` | Legacy relative error | Existing limit | Best sweep error (absolute / normalized) |
|---|---:|---:|---:|---:|
| Axial entry | 1.1853 Pa | 4.584e-11 | 2e-7 | 1.1853 Pa / 3.445e-11 at `2e-6` |
| Simple-shear entry | 2.1734 Pa | 2.736e-10 | 2e-7 | 0.07236 Pa / 2.103e-12 at `1.6e-5` |
| Mixed 3D | 0.5505 Pa | 4.207e-11 | 2e-7 | 0.2525 Pa / 7.339e-12 at `8e-6` |

Coarse-step estimates show approximately second-order decay. The fine-step values depart from that trend as energy subtraction and roundoff become material; the simple-shear and mixed directions flag estimated plateaus in the fine-step region. All perturbed states remained admissible: the reported minimum `J` across these sweeps was at least `1.1120`, the minimum eigenvalue of `C` remained about `0.85`, and `cond(C)` stayed near `1.52`. These printed sweeps are diagnostics; they add no new acceptance gate.

The separate uniaxial reference is analytically independent of the returned PK1 transformation. For `mu=80 GPa`, `kappa=160 GPa`, and `lambda=1.17`,

```text
W(lambda) = (2 mu/3 + kappa/2) log(lambda)^2
dW/dlambda = P11 = (4 mu/3 + kappa) log(lambda)/lambda
```

The analytic derivative is about `3.578433021e10 Pa`. A ten-step centered-difference sweep of the evaluated energies reduced absolute error from `7.8156e4 Pa` (`2.1841e-6` normalized) at `h=1.024e-3` to `0.7562 Pa` (`2.1132e-11` normalized) at `h=2e-6`. Halving from `6.4e-5` to `3.2e-5` reduced error from `305.27 Pa` to `76.28 Pa`, consistent with the expected `O(h^2)` regime. At the finest steps, the estimated subtraction-roundoff floor is visible. The closed-form energy, PK2, and PK1 checks passed. The perturbed energy values still come from the implementation, so this is an independent analytic derivative reference applied to kernel energy evaluations, not independent energy code.

### TET4 / HEX8 force-only checks

The TET4 and HEX8 affine-deformation and uniform-PK1 force-adapter cases passed. The invalid/inverted reference-geometry refusal cases also passed. The test output does not emit force-error magnitudes, so those values are **NOT_RECORDED** here; they are not reconstructed from pass labels. This is local element algebra only and supplies no global FEM or tangent evidence.

## Independent review and limitations

A separate read-only reviewer examined the recorded diagnostics and test contract without running tests or changing files. The reviewer agreed that the six cases support bounded PK2/PK1/Cauchy objectivity and that the coarse-to-fine energy sweeps show truncation-to-roundoff transition. The reviewer emphasized that one common rotation and six configurations are representative rather than exhaustive, that the high-bulk absolute tolerance is less discriminating, and that the generic energy sweeps are self-consistency checks.

The reviewer estimated the largest error/bound fraction from the displayed rows as about 1.03% for general-3D-shear PK2. A direct scan of all six logged rows gives a larger maximum, 1.779%, for repeated-stretch PK2; this arithmetic difference does not change any pass/fail or scientific conclusion. No qualitative disagreement remains.

## Evidence and hashes

All raw output is retained under [`wp_e01_o_runs/20261021T144944Z`](wp_e01_o_runs/20261021T144944Z). The collection file contains all 41 authorized node IDs and fixtures. `summary.json` links the exact counts, phase receipts, and hashes. `evidence_hashes.json` hashes the phase receipts, collection list, preflight, pytest results, and complete stdout/stderr.

| Evidence artifact | SHA-256 |
|---|---|
| `summary.json` | `ab9fba872be75d6d9780f7b085a3a69c306aa40d8615cc52200bffa04fdc06e1` |
| `evidence_hashes.json` | `58225b5bb0ebd1b5237810bfe883211973d691da7843f4c8e88790a753dc5385` |
| `preflight.json` | `3e35d4a09ea69b84e246d12e85ecf3c4d27dcf09149921fcb840b99f3e205371` |
| `collection/collection_nodes.json` | `08a2036ee9ee2af52a083ffca69bbfd5f2464d698bf9306877d693c348047c88` |
| `collect/phase_result.json` | `eb5e4c0d3703f072c208c75e26fe218d600f2a31896beb9b599cda01bdda7287` |
| `collect/stdout.log` | `ef7f83a07fd8af86ad47813bb14753adf4d4cdc0f450827313cb3e3eb338024b` |
| `collect/stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run/phase_result.json` | `1699d5f27438e0d87c43edad79176c842d83b99459c6eb42af68e79197d26b35` |
| `run/pytest_results.json` | `f65cf3eb55238b3d35d5d816d8aa503389d92d7f064ecedc80341d5683812911` |
| `run/stdout.log` | `5c5380d3f4e18f4fe4a53a7965f77fbd3fd3f1ae84a11a73fbb098e665d1ecd9` |
| `run/stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Status

| Gate | Result |
|---|---|
| `REGISTRY_BINDING_DEFECT` | `CORRECTED_BY_SOURCE` |
| `SUPERVISOR_RUNTIME_VNV` | `VERIFIED_FOR_CAMPAIGN` |
| `WP_E01_P3_COLLECTION` | `41_OBSERVED` |
| `WP_E01_P3_EXECUTION` | `41 PASS / 0 FAIL` |
| `HENCKY_HISTORICAL_VNV` | `35_PASS_1_FAIL_PRESERVED` |
| `PK2_OBJECTIVITY` | `VERIFIED_BOUNDED` |
| `PK1_CAUCHY_OBJECTIVITY` | `VERIFIED_BOUNDED` |
| `PK1_ENERGY_DERIVATIVE` | `VERIFIED_BOUNDED` |
| `TET4_HEX8_FORCE_REFERENCE` | `PREVIOUS_VERIFIED_BOUNDED` |
| `HENCKY_CONSISTENT_TANGENT` | `NOT_IMPLEMENTED` |
| `GLOBAL_HENCKY_FEM_ASSEMBLY` | `NOT_RUN` |
| `FINITE_STRAIN_J2` | `NOT_IMPLEMENTED` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

Next milestone: independently verify a mathematically consistent Hencky material tangent `A=dP/dF` at the material point, including repeated/clustered principal stretches and first/second Fréchet derivatives of `log(C)`. Only after that evidence should a separately authorized total-Lagrangian element tangent campaign be prepared. Do not infer Newton or global FEM readiness from this run.
