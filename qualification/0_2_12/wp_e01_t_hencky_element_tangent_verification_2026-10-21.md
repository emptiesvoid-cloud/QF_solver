# WP-E01-T — Hencky TET4/HEX8 Element Tangent Verification

## Result

The isolated experimental TET4/HEX8 Hencky element tangent passed the frozen 34-case NUMERICAL_UNIT campaign after two test-infrastructure defects were corrected and the execution identity was re-frozen. The final supervisor accepted the exact collection receipt, then ran the same target once: **34 passed, 0 failed, 0 skipped, 0 xfailed, 0 xpassed**.

This is bounded local element-algebra evidence only. It does not establish global assembly, constrained reactions, Newton convergence, production solver integration, or scientific qualification. Numerical tolerances remain proposed.

| Status | Result |
|---|---|
| `HENCKY_MATERIAL_POINT_VNV` | `PREVIOUS_41_PASS_BOUNDED` |
| `HENCKY_CONSTITUTIVE_TANGENT_VNV` | `PREVIOUS_35_PASS_BOUNDED` |
| `HENCKY_ELEMENT_TANGENT` | `VERIFIED_BOUNDED` |
| `HENCKY_GLOBAL_FEM_ASSEMBLY` | `NOT_RUN` |
| `HENCKY_INCREMENTAL_NEWTON` | `NOT_RUN` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

## Repository and frozen identities

The requested starting identity was verified before work: branch `codex/qf-wp-e01-q-hencky-tangent-20261021`, origin `https://github.com/emptiesvoid-cloud/QF_solver.git`, HEAD `3b43c4e63580169d322047597651a85377e066da`, clean worktree.

The frozen execution source HEAD was `dc14ed745b92de58974e55bd7ae6a37e05eee7a0`. The final evidence commit changes documentation and execution evidence only; it does not change the source identity used by the run.

| File | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01t_hencky_element_tangent.py` | `b86d6ecb180ab01176502603aa02c3a2ba2b96652c3aefc47a14743e172bf599` |
| `src/solveur/verification/experimental_hencky_element_tangent.py` | `de61ce16f9ee117086ea8aa5d55eba2966649b39e289481a089430b630d374f3` |
| `src/solveur/materials/finite_strain_hencky.py` | `b87706cecfb036d3a4b31461c83da1b8af0b7aeb7098037e2cf7e65cdf466f50` |
| `src/solveur/materials/finite_strain_hencky_tangent.py` | `31109bbbf2353f9bbd86b7a7b0e5fe776016fdd1638550848b58b8bd4afef135` |
| `tests/conftest.py` | `08b570b244a131b25f5bb02d52c7ffa394b5a53e9281ac226aeb9d2204bb0d19` |
| `qualification/0_2_12/wp_e01_t_hencky_element_execution_manifest_2026-10-21.json` | `099e19a809eaccc752bc9ef00217ca7ffcc5134865a4d79006c05150473812d0` |
| `qualification/0_2_12/wp_e01_t_hencky_element_runtime_2026-10-21.json` | `d97cc35803ef40897f53886ee87d7e73053fb2820b719fab725409ca37e27ace` |
| `experiments/wp_e01t_hencky_element_supervisor.py` | `9e8a666f29750d60423e9e2ba7e4e2f214cfadbda88c3088fea807dbdad1d47d` |
| `experiments/wp_e01t_hencky_element_collection_guard.py` | `29f624440f8e995d5f2b2c9de34b88a87cf42c9d23e0e1301ff7b4ee666d390b` |
| `experiments/wpc01_exploratory_supervisor.py` | `9bd8c75b19b49c758f9558cf9299eeedc18762b1e40dbd69968377a94d6c9090` |

The static manifest contains 30 source pins; the runtime manifest contains 32. The four fixed supervisor-helper files are anchored in the committed static manifest, and the runtime supervisor rejects any binding that conflicts with an existing static pin. Final preflight verified every runtime source-map digest against file bytes. The test remained `NUMERICAL_UNIT`; the target and all 34 node IDs match the fixed allowlist.

The Hencky production material and constitutive tangent source files were not modified. The existing P3 41-pass material-point and S 35-pass constitutive-tangent results remain historical evidence; they were not rerun in this campaign.

## Element formulation

For each reference quadrature point, the adapter evaluates

\[
F=I+u^T\nabla_X N,\qquad \delta F=\delta u^T\nabla_X N,
\]

and the internal nodal force

\[
f_{ai}=\sum_q w_q\det(J_0)_q\,P_{iJ}\,N_{a,J}.
\]

The local action is

\[
\delta f_{ai}=\sum_q w_q\det(J_0)_q\,\mathbb A(F_q)[\delta F_q]_{iJ}N_{a,J}.
\]

It uses the Hencky material-point response and directional tangent, with the same reference configuration and quadrature as the existing force-only adapter: one constant-gradient point for TET4 and the full \(2\times2\times2\) Gauss rule for HEX8. From \(P=FS\),

\[
\delta P=\underbrace{F\,\delta S}_{\text{material}}+\underbrace{\delta F\,S}_{\text{geometric}}.
\]

The adapter returns total, material, and geometric actions without changing production element dispatch. Coordinates and displacements are metres, stresses/moduli are pascals, energy density is joules per cubic metre, internal force/action is newtons, and the element tangent is newtons per metre.

## Execution chronology and containment

The first supervisor invocation stopped at parent preflight because the runtime helper closure was absent from the static source map. It launched no child. The static manifest was updated to pin all four fixed helper imports, and supervisor/guard digest constants were refreshed.

The next collection launched under the Job Object and printed the 34 expected node IDs, but the guard failed while writing its collection inventory: it indexed nonexistent runtime fields `element_adapter`, `production_material`, and `production_tangent`. Pytest exited 3 with an internal collection error; test bodies did not run. This failed attempt is preserved at `qualification/0_2_12/wp_e01_t_execution_2026-10-21/20261021T162523Z/`. The guard was corrected to read those evidence hashes from the already byte-verified `source_identity_sha256` map. The test module, fixtures, thresholds, and allowlist did not change.

With the corrected guard hash and runtime manifest frozen, the final parent invocation collected and ran the exact module. Collection and RUN were separate single-child Job Object phases. Both phase receipts confirm suspended creation, assignment before resume, one active process, 256 MiB process and Job committed-memory caps, kill-on-close, no breakaway, no timeout, and verified empty active-PID lists after exit.

| Phase | PID | Exit | Wall time | Peak committed memory | Cleanup |
|---|---:|---:|---:|---:|---|
| Collection | 25728 | 0 | 1.273 s | 36,184,064 B process and Job | `VERIFIED_WINDOWS_JOB_CLOSED` |
| RUN | 39620 | 0 | 2.071 s | 70,234,112 B process and Job | `VERIFIED_WINDOWS_JOB_CLOSED` |

Both phases used the 120-second parent deadline, a one-process limit, one BLAS thread, no pytest parallel workers, and no automatic retry. Collection receipt accepted exactly 34 nodes. `run_results.json` records 34 passed, 0 failed, 0 skipped, 0 xfailed, 0 xpassed, 0 incomplete, and pytest exit 0. The complete observed node inventory is in `collection_nodes.json` and `collection_receipt.json`.

## Numerical results

### Independent affine force reference

For diagonal affine stretches \((1.12,0.94,1.03)\), the test constructs a closed-form diagonal Hencky response and independently coded TET4 gradients / HEX8 shape gradients and quadrature. Both elements report energy density `17,536,787.5517444 Pa`.

| Element | Reference force norm | Absolute force error | Normalized force error |
|---|---:|---:|---:|
| TET4 | 64,194,464.39091003 N | 4.0659457357e-8 N | 3.0494593018e-16 |
| HEX8 | 770,333,572.6909204 N | 2.0623065442e-6 N | 3.2223539753e-16 |

Force-only adapter parity is exact for both elements, but that parity comparison is not independent. The closed-form affine reference is the stronger check.

### Tangent directional derivatives

The ten fixed-history-independent elastic element cases use centered differences at \(h=(2,1,0.5,0.25,0.125)\times10^{-3}\) and compare them with the analytic element action. All five TET4 cases and all five HEX8 cases have three of the first three adjacent absolute-error ratios in the proposed `[3,5]` window; measured first-three ratio ranges are `3.99881–4.00128` for TET4 and `3.94354–4.03673` for HEX8. This is direct evidence of an \(O(h^2)\) region on these fixtures, not merely a minimum-error match.

| Element / state | Absolute error sequence (N), coarse to fine | Normalized error sequence | min det(F) | Resolved early order pairs |
|---|---|---|---:|---:|
| TET4 affine | 140.7221, 35.1804, 8.79519, 2.19894, 0.548971 | 5.6767e-7, 1.4192e-7, 3.5480e-8, 8.8705e-9, 2.2145e-9 | 1.084384 | 3 |
| TET4 nonuniform | 199.2120, 49.8031, 12.4508, 3.11256, 0.777357 | 6.3936e-7, 1.5984e-7, 3.9960e-8, 9.9897e-9, 2.4949e-9 | 0.957091 | 3 |
| TET4 repeated | 134.1374, 33.5341, 8.38379, 2.09528, 0.524755 | 5.6047e-7, 1.4012e-7, 3.5030e-8, 8.7548e-9, 2.1926e-9 | 1.110553 | 3 |
| TET4 near-repeat | 134.1372, 33.5343, 8.38355, 2.09641, 0.525675 | 5.6047e-7, 1.4012e-7, 3.5029e-8, 8.7595e-9, 2.1965e-9 | 1.110554 | 3 |
| TET4 shear | 103.9294, 25.9821, 6.49538, 1.62433, 0.407877 | 4.8216e-7, 1.2054e-7, 3.0134e-8, 7.5358e-9, 1.8923e-9 | 1.000000 | 3 |
| HEX8 affine | 2.07169, 0.517889, 0.130179, 0.0326980, 0.0113322 | 1.0790e-9, 2.6973e-10, 6.7802e-11, 1.7030e-11, 5.9022e-12 | 1.084384 | 3 |
| HEX8 nonuniform | 2.63391, 0.658508, 0.164605, 0.0409123, 0.0114628 | 1.3718e-9, 3.4297e-10, 8.5732e-11, 2.1309e-11, 5.9702e-12 | 0.963621 | 3 |
| HEX8 repeated | 1.99784, 0.499116, 0.124530, 0.0314308, 0.0120806 | 1.0405e-9, 2.5996e-10, 6.4859e-11, 1.6370e-11, 6.2920e-12 | 1.110553 | 3 |
| HEX8 near-repeat | 1.99774, 0.499261, 0.124364, 0.0315360, 0.00845885 | 1.0405e-9, 2.6003e-10, 6.4773e-11, 1.6425e-11, 4.4057e-12 | 1.110554 | 3 |
| HEX8 shear | 2.23166, 0.557674, 0.139623, 0.0345882, 0.0144838 | 1.1623e-9, 2.9046e-10, 7.2720e-11, 1.8015e-11, 7.5437e-12 | 1.000000 | 3 |

At the smallest HEX8 step some final adjacent ratios decrease to `2.39–3.73`, indicating the beginning of roundoff/finite precision influence, even while error continues to decrease. The TET4 final ratios remain near four for these cases. The run does not establish a roundoff plateau or a generally calibrated acceptance gate. The candidate directional tolerance `2e-7` and order-ratio interval remain proposed, not approved scientific limits.

### Material / geometric split and symmetry

At a single `5e-5` step, the geometric action was independently reconstructed from the closed-form diagonal PK2 stress. TET4 geometric error was `4.3842e-9 N`; HEX8 was `2.8026e-8 N`. The remaining material-action finite-difference errors were `0.08295 N` (normalized `3.47e-10`) and `0.01337 N` (normalized `1.04e-11`), respectively. The reported `total - material - geometric` errors (`2.67e-8 N`, `2.90e-8 N`) are algebraic identity checks because the adapter defines material as total minus geometric; they are not independent evidence.

The assembled local matrix raw skew was `0–1.4208e-6 N/m`; normalized Frobenius skew was `0–2.0324e-16` across six cases. This supports expected major symmetry numerically for the tested conservative material states.

### Rigid motion and geometry checks

Rigid-rotation force covariance errors were `7.94e-16` (TET4) and `2.87e-16` (HEX8); tangent covariance errors were `8.78e-16` and `5.25e-17`. Pure-rotation residual force norms were `7.25e-8 N` and `1.65e-6 N`. A common rigid translation produced `0 N` for TET4 and `1.91e-8 N` for HEX8 (normalized action `1.24e-18`). Mesh translation and 0.25x/4x coordinate scaling covariance diagnostics were exactly zero in binary64 for both fixtures. Inverted reference geometry and orientation-reversing deformation were rejected for both element types.

### Energy derivative

The independent diagonal work references were `7,010,971.9119710345 J` (TET4) and `336,526,651.7746097 J` (HEX8). Centered-difference errors across the same five steps were:

| Element | Absolute errors (J), coarse to fine | Adjacent ratios | Exact force/energy work discrepancy |
|---|---|---|---:|
| TET4 | 3.04566, 0.761415, 0.190361, 0.0475860, 0.0118851 | 3.99999, 3.99984, 4.00037, 4.00383 | 0 J |
| HEX8 | 146.191, 36.5479, 9.13736, 2.28413, 0.570500 | 3.99999, 3.99984, 4.00036, 4.00374 | 1.19209e-7 J |

All three early adjacent pairs for each element show the expected centered-difference second-order behavior. No energy-derivative roundoff plateau was reached in the tested range.

## Independent review and limitations

A separate read-only reviewer examined the implementation, frozen receipt, `run_results.json`, and numerical stdout. The reviewer confirmed the quadrature, reference gradients, force contraction, product-rule split, analytic diagonal reference, second-order trends, objectivity and symmetry observations. The review found no P0/P1 issue for the local element scope.

Review limitations/findings:

* The material/geometric total decomposition residual is tautological; independent evidence comes from the geometric reference and force finite differences instead.
* Directional finite differences compare the new analytic element action to the existing force-only Hencky mapping. The closed-form diagonal force/energy references reduce but do not eliminate shared constitutive-code risk.
* HEX8 admissibility was checked at its eight Gauss points, not between quadrature points.
* No global scatter, shared-node assembly, constraints, reactions, mesh-level energy, Newton path, checkpoint integration, or production FEM route was exercised.
* All test thresholds are candidate/proposed and are not Owner-frozen scientific acceptance criteria.

## Evidence and commits

Final successful execution directory:
`qualification/0_2_12/wp_e01_t_execution_2026-10-21/20261021T162711Z/`.

Key hashes:

| Evidence | SHA-256 |
|---|---|
| `collection_receipt.json` | `864444fceb69342efd0d301c650063a1afd103c401377ad6bcd972496b4374ee` |
| `collection_nodes.json` | `16715bafdf16d35c6d11abb86cdadd34fffa28856bedfb4b25fbe2bd29043755` |
| `run_results.json` | `0cc716acba145d82da748dab8ab691c709f18b21dc1f8e64ef0ac4f1ca706645` |
| `summary.json` | `e55a9e95487715bff92d61dda3e71901769921a2d154d1ffb84fb2859c5c0c08` |
| `evidence_hashes.json` | `47c70328cd74b195d8659679ff526162225e4448fef46b19df7b038793c97c72` |
| `run/stdout.log` | `22cb9505da9e1f44063c45989c2728a368cf751a79e7e00334fc3b32287f6eb2` |
| `run/phase_result.json` | `b235cc182a6a99d3229ea16d314289687760ebf7e7148f35c59ef0e30b0ad129` |
| Failed collection evidence manifest (prior attempt) | `18e54e7b82a830e7c683affd632d24deff5603e670e82ba33731dcee22f36dd3` |
| Initial preflight-blocked record | `42862b84ebcbe278d99faf4b27a843799731e0edfeb3461710387d63aa3a8588` |

All entries in both supervisor-generated evidence hash manifests were independently recomputed and matched their files.

Commits:

* `32d166845135148a19030e6365ba88399023c1dd` — isolated adapter, tests, registry, guard/supervisor, and static manifest.
* `6dd1a20222292a44f79e410eb641f02f77d578db` — statically pin the supervisor helper closure.
* `09c8fe6d77d7b68e1c6f358e0fcffef16ca56922` — reject runtime hashes conflicting with static pins.
* `dc14ed745b92de58974e55bd7ae6a37e05eee7a0` — read evidence source hashes from the verified source map.
* A final documentation/evidence commit records this report, frozen runtime manifest, and both failed and successful execution evidence.

The final implementation remains isolated in the verification adapter. The next milestone requires Owner review before any production FEM assembly integration; it should begin with a separately authorized global element scatter/constraint and reaction-balance campaign, not Newton activation.
