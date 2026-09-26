# WP08 area-supported contact — R1.10 diagnostic results

## Conclusion

The frozen serial R1.10 campaign completed all six M1/M2/M3 stick/slip cases, and every case passed its predeclared execution/physics diagnostic gates. This is **not** a formal WP08 qualification. The campaign does **not** establish mesh convergence for slip: the common-node displacement changes by about 24.5% at each refinement, and the M3 slip contact area falls to 87.5% of the nominal patch. The earlier refinement concern therefore remains unresolved.

```text
R1_10_EXECUTION = COMPLETED
M1_M2_M3_CASE_GATES = 6/6 PASS_DIAGNOSTIC_GATES
SLIP_REFINEMENT = CONCERN / NOT_CLASSIFIED (no frozen mesh-convergence threshold)
FORMAL_WP08_QUALIFICATION = NO
WP08_POINTS_AWARDED = NO
INDEPENDENT_GLOBAL_FEM_REFERENCE = NOT_RUN
FORMAL_REPLAY = NOT_RUN
FULL_TEST_SUITE = NOT_RUN
```

## Frozen provenance and execution

- Branch: `codex/wp08-area-contact-r1-10-candidate`
- Evidence HEAD after binding: `364a59dee0286696ab05666f31bcc08d5f74dd29`
- M1 runner/source anchor: `0bf33ccc2df717172bebc0a5fa23f99db7e99cb1`
- M2/M3 source anchor recorded by the binding: `bec629bddaea9f9821f38fb19cdd9f14ad77ce15`
- R1.10 source bundle SHA-256: `a6703a15b73991c2950688c545a4e371d51b72e0d969dc0d42d33bf613515e04`
- Source-manifest SHA-256: `676bf1924802be9aabe65b65b63a94839220c0daaee2d30f9528a89cc647a675` (977 source entries)
- M1 contract SHA-256: `67efb97074cb8cb1c5f442045b1c0e209b6413d676ad61568fb554586e2ee7f0`
- M2/M3 amendment contract SHA-256: `a988e5b04769c2c064a9a9846133db17892b39d932d8a818026b85f1891f4242`
- M2/M3 runner SHA-256: `86277c98378832eeb13818e94b1c5d7bb6804e3c412527ac1d0815d494a16688`
- Execution-binding canonical digest: `3b27170d36e79a30ccafb6da075a9f659bb16c4cc676234a9b7dc13dcac552dc`; binding file SHA-256: `10fb31c34dcaab5af9eb073ed07b078661f9fd9230a94039717d3ec72dd02b07`.

The source tree was unchanged after the M2/M3 source anchor: `git diff bec629...HEAD -- src scripts tests` is empty. The later binding commit records execution provenance only. The six cases ran serially; each process exited `0`. No R1.10 runner remains active. All 11 M1 artifact hashes recorded in the amendment and all 20 M2/M3 artifact/log hashes recorded by the result manifest were independently recomputed and matched. Four M2/M3 process manifests also match their result entries. All 35 JSON/JSONL files parsed, and serialized numeric values were finite.

The runtime binding records Python 3.12.3, NumPy 2.0.2 and SciPy 1.14.1. It records the governing policy digest as context only; the governing policy was not enforced for this experimental campaign. The results do not claim zero fallback: the result schema records the fallback counter as unavailable (`null`).

## Case results

All cases converged in eight load steps, retained a rank-2 active support and reached their intended terminal state. M1 requires all four slave nodes active; M2 and M3 use the frozen rank/state gates and do not require full patch activation.

| Mesh / case | Active slave nodes | Active area fraction | Terminal state | Result |
|---|---:|---:|---|---|
| M1 stick | 4/4 | 100% | stick | PASS_DIAGNOSTIC_GATES |
| M1 slip | 4/4 | 100% | slip | PASS_DIAGNOSTIC_GATES |
| M2 stick | 9/9 | 100% | stick | PASS_DIAGNOSTIC_GATES |
| M2 slip | 9/9 | 100% | slip | PASS_DIAGNOSTIC_GATES |
| M3 stick | 25/25 | 100% | stick | PASS_DIAGNOSTIC_GATES |
| M3 slip | 20/25 | 87.5% | slip | PASS_DIAGNOSTIC_GATES, with limitation |

The M3 slip case is especially important: it passed the frozen diagnostic gate, but only 20 of 25 slave nodes remained active (area `0.4375` of nominal `0.5 m²`). This is not silently upgraded to full-patch contact or convergence evidence.

## Refinement comparison

Values are descriptive comparisons over common nodes; the frozen R1.10 contract defines no mesh-convergence threshold, so these are **not** contract PASS/FAIL gates.

| Case / refinement | Common-node displacement Δ | Normal contact resultant Δ | Tangential resultant Δ | Reaction resultant Δ |
|---|---:|---:|---:|---:|
| Stick M1→M2 | 1.6518% | 0.5740% | 0.8146% | ~0 |
| Stick M2→M3 | 0.9726% | 0.2442% | 0.4211% | ~0 |
| Slip M1→M2 | 24.8832% | 0.1389% | 0.2429% | ~0 |
| Slip M2→M3 | 24.5409% | 1.1415% | 1.6451% | ~0 |

Slip displacement changes by `0.001991 m` from M1→M2 and `0.004785 m` from M2→M3. Meanwhile the integrated contact resultants and global reactions remain much closer. That mismatch means this run fixed the execution/root-solving issue sufficiently to pass its case gates, but **did not solve the slip-field mesh sensitivity**. The reduced active area at M3 is a plausible contributor, not a proven sole cause. No further parameter or threshold tuning was done after seeing these results.

## Change and validation scope

The R1.10 production change is limited to `src/solveur/contact/slip_root.py`: exact piecewise coupled-projection Jacobian including pressure-dependent residual normalization, continuation from the best finite active-slip candidate, and safeguarded semismooth refinement within the pre-existing iteration budget. The `1e-9` root gate, 25 active-set limit, geometry, meshes, material, loading, boundary conditions, contact stiffness, friction coefficient and fallback policy were not changed.

Before execution, the targeted contact/friction and R1.10 runner checks reported **96 passed**; Ruff, targeted mypy and compileall were PASS. These checks were not rerun after the solve because the frozen source did not change. The full repository suite was not run.

Historical R1.9 FAIL evidence remains preserved. No replay, independent global FEM solve, external-solver correlation, merge, push, ledger update or point award was performed. Per-case raw files remain local in the campaign directory and are excluded by the repository's generated-artifact ignore rules; the committed audit record binds their hashes. No external archive is claimed.

## Next decision

Treat R1.10 as successful **experimental execution**, but retain the slip refinement outcome as unresolved. Before making a formal WP08 claim, decide and freeze a follow-up investigation that checks the M3 loss of edge contact and explains the displacement discrepancy without changing acceptance thresholds after the fact. Any new mechanics or benchmark variant needs its own prospective binding and Owner authorization.

Machine-readable hashes and case bindings: [R1.10 final audit](../../../qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_10_20260926/r1_10_final_audit.json). The compact M2/M3 execution summary is [final.json](../../../qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_10_20260926/M2_M3/final.json).
