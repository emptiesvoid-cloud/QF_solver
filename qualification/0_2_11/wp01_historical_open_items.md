# WP01 — Historical open-item audit (0.2.11 planning)

Audit baseline: `c37179dae53604126aa6aa0d834770dfa4d2db37`; published immutable
baseline: `v0.2.10` → `e535ff63464ddd7d76c2898df25470350b5154f1`.

This is an inventory and recommendation for later planning only. WP01 does not
repair, close, reclassify, promote, or rewrite any item below. “Root cause” is
limited to what the cited record actually establishes; an unresolved cause is
explicitly left unresolved.

| Item | 0.2.10 status | Root cause / bounded finding | Cost | Risk | Value | 0.2.11 decision |
|---|---|---|---|---|---|---|
| G03 whole-repository archive | `FAIL_PRESERVED`; whole repository not cleared | The strict public-surface history records findings in historical qualification material; R4.7 separately clears only selected package sources and selected public docs, not the whole repository. Do not infer or silently remove historical findings. | Very high; archive-wide review/reconstruction | High, including evidence/history loss | Low for solver capability; essential scope disclosure | `KEEP_AS_IS` |
| WP14 release qualification | `HOLD`; 0 points validated; not promoted | Owner-scoped release direction accepted bounded public surfaces, while WP14 closure/review requirements remain unmet. Recovered-evidence targeted CI PASS is evidence recovery, not WP14 qualification closure. | High | High governance/release risk if promoted prematurely | Low to numerical product scope | `KEEP_AS_IS` |
| WP06-D/E/F postbuckling path | D is bounded `EXPERIMENTAL`, 0/2 formal points; E/F blocked by formal dependencies; WP06 remains 4/8 | The 160-state D path found no limit point; only local axial refinement (transverse 4×4), no independent nonlinear path solve or second production replay. Historical M2 fail-closed remains. | High; formal structural path and independent evidence | High formulation/requalification risk | Scientific, but not necessary to 0.2.11 gyro foundation | `DEFER_0_3_X` |
| WP08 approved frictional-contact scope | Owner-approved with limitations (8/8); not general contact | Accepted scope is serial/direct `linear_static`, small displacement, fixed initial search/face/normal and bounded positive-friction settings. Updated search, finite sliding, general nonlinear contact, restart, dynamics, and MPI/PETSc are expressly outside the decision. | High for extensions | High | Preserve current accepted limited route | `KEEP_AS_IS` |
| WP08 R1.13 area-supported diagnostic | Experimental diagnostic accepted with limitations; no formal WP08 requalification from R1.13 | Six diagnostics passed their per-case gates, but reported slip deltas 24.883% and 24.541% on successive meshes; M4 remains `FAIL_CLOSED_NUMERICAL`; no global oracle/zero-fallback claim. The report identifies raw NPZ as local/untracked; they are absent from the clean baseline checkout. | Medium/high to recover/re-run | High if overinterpreted | Useful diagnostic only if exact raw/run inputs are recovered | `RETEST_ONLY` |
| WP07 normal/frictionless contact | Bounded accepted routes with limitations | Existing acceptance does not cover general search, self-contact, impact, finite sliding, or arbitrary nonlinear coupling; preserve its exact static/small-displacement contract. | High for broad extension | High | No change needed for WP01 | `KEEP_AS_IS` |
| Contact active-set incident preceding R1.13 | Original remediation cause recorded as `STALE_FROZEN_TANGENTIAL_MODE_CAUSES_NORMAL_ACTIVE_SET_CYCLE`; later scoped diagnostics do not generalize the remedy | The historical active-set cycle is tied to the recorded stale frozen tangential mode. Preserve original R1.12 M4 fail-closed result and distinguish subsequent R1.13 evidence. | Medium/high | High | Diagnostic history is useful; broad contact requalification is not | `KEEP_AS_IS` |
| MITC4 modal large/extended case | Selected modal scopes have case-specific evidence; broad/high-DOF modal gate remains blocked/failed in historical record | The 200×50/10k external-correlated case had a Code_Aster reference but QF eigensolver attempts (`eigsh`, `LOBPCG`) did not converge. This is not a failure of every MITC4 modal case. | High | High if solver/eigenvalue filtering changes | Retain bounded modal regression and explicitly preserve the failed large case | `RETEST_ONLY` |
| Discrete Newmark | Owner gate `REJECTED`; runtime route remains `EXPERIMENTAL` | The governing WP03 decision rejects the `COMB-DISCRETE-newmark_transient` qualification combination. Existing dynamic replay does not override that rejection; the exact historical rejection record controls. | Medium/high to identify and close accepted physical scope | Medium/high | Low unless discrete transient is chosen for product scope | `KEEP_AS_IS` |
| WEDGE6 transient/harmonic route | `EXPERIMENTAL_ROUTE`; no registry combination | The 0.2.8 evidence explicitly reports no accepted registry combination for these analyses. Implementation or a passing component test cannot fill that gap. | Medium/high | Medium/high | Low for 0.2.11 gyro scope | `DEFER_0_3_X` |
| WP10 M2 moment balance | Bounded owner acceptance with limitation; no frozen equilibrium threshold for this observable | Owner accepted the bounded family result while retaining the M2 moment limitation; an acceptance threshold was not frozen. Do not invent one post hoc. | Medium | High if a threshold is retrofitted to historical data | Moderate only if the exact case changes | `KEEP_AS_IS` |
| PETSc/MPI mixed runtime and physical gates | Earlier attempts include `FAIL_RUNTIME`, `FAIL_PHYSICAL_GATE`, and dependency-blocked records; later WP11/WP13 acceptance is bounded | The record set contains distinct failures: e.g. `petsc4py unavailable` on a dependency gate and separate runtime/physical convergence failures. A single universal root cause is not established. Later acceptance covers only specified bounded linear/static cases. | High | High | Preserve bounded accepted case; general distributed nonlinear capability is not necessary to 0.2.11 | `KEEP_AS_IS` |
| Historical refinement/convergence gates | `BLOCKED`/`FAIL` records remain for named cases; selected later bounded decisions do not erase them | Named tests retain over-limit refinement or terminal-increment results (for example the stable refinement evidence suite); these are case-specific, and no global numerical cause may be inferred. | Medium/high per case | High | Useful negative regression evidence when that exact route changes | `RETEST_ONLY` |
| WP04-D original raw capture | Original capture `MISSING`; reconstructed manifest exists | `wp04d_reproduced_manifest.json` records reconstructed material, not the original unavailable capture. Matching a replay does not make it the original source evidence. | High to obtain/repeat equivalent independent source campaign | High provenance risk | Low for 0.2.11 baseline | `KEEP_AS_IS` |
| WP12 Code_Aster raw gallery/runtime | Bounded external correlation accepted; raw R4 gallery archived separately/local-only and executable optional | Same-mesh solver correlation is not physical validation; a normal CI runner does not guarantee Code_Aster or the raw external gallery. | High/externally dependent | Medium | Moderate only if an exact case changes | `RETEST_ONLY` |
| WP11 PETSc/MPI | Owner-accepted bounded linear-static multi-family scope; no general scaling/nonlinear/dynamic claim | Evidence is one-element bounded cases with root-side assembly/replicated input; no strong/weak scaling, contact/friction, dynamics, or external solver correlation. | Medium/high for scaling/generalization | High | Low beyond preserving bounded route | `KEEP_AS_IS` |
| Legacy V&V v0.26 resume identity | Limitation remains in implementation | Legacy resume keys on source SHA rather than the full run identity (case/input/reference/tolerance/environment); matching SHA alone is insufficient for robust provenance. | Medium | Medium; risk is evidence reuse, not solver numerics | High for reproducibility | `FIX_0_2_11` (prospective V&V-only; no historical rewrite) |
| Legacy `expected_failure` behavior | Broad catch remains in legacy runner | The historical implementation can classify a broad exception as an expected failure; the v2 path has stricter case behavior, but legacy semantics still need explicit characterization. | Low/medium | Medium evidence-classification risk | High for truthful future reports | `FIX_0_2_11` (prospective strict classification, with backward-compatible history) |
| V&V v2 external-file identity | Partial identity binding | Case/model-input digest exists, but it does not necessarily hash every external file’s actual bytes; tests of framework contracts do not establish each case’s external payload. | Medium | Medium provenance risk | High for new 0.2.11 runs | `FIX_0_2_11` (bind new runs to actual input/reference digests) |
| 0.2.10 selected package and citation | Published and verified; historical-only as 0.2.11 source evidence | The e535 contract binds immutable 0.2.10 artifacts and the selected scope. Reuse the record for history only; it is not a 0.2.11 package audit. | Low | High if version bytes are reused | Preserve release provenance | `KEEP_AS_IS` |
| Nonlinear mixed-family high-order/contact extensions | Bounded owner-accepted subsets; remaining routes experimental/not validated | Existing decisions are family-, loading-, observable- and contact-policy-specific. A component or neighboring family’s acceptance does not transfer. | High | High | Moderate research value, not required for initial gyro | `DEFER_0_3_X` |
| Expected failures and archived blocked V&V cases | Historical `EXPECTED_FAILURE`, `PARTIAL`, `BLOCKED` records remain | These represent their original case status and must remain visible; green meta-tests only verify preservation, not success of the underlying physical case. | Varies | Very high if reclassified | Preserve as negative/limitation evidence | `KEEP_AS_IS` |

## WP04 planning recommendation (not execution authorization)

Keep the historical-remediation budget at about 10%. The only low-numerical-risk
candidates worth carrying forward are prospective V&V run identity and precise
expected-failure semantics, subject to WP02/WP03 architecture and a fresh scoped
test plan. Do not use that allocation to promote WP06/WP08, repair G03, or reopen
the MITC4/Newmark numerical issues automatically. Those remain separate,
explicitly bounded decisions.

## Governing records

- `qualification/0_2_9/progress.json`
- `qualification/0_2_9/owner_decisions.json`
- `qualification/0_2_9/wp06d_owner_bounded_experimental_decision.json`
- `qualification/0_2_9/wp13_02a2_wedge6_dynamic_evidence.json`
- `qualification/0_2_9/wp10_owner_acceptance.json`
- `qualification/0_2_8/wp13_01a_mixed_petsc_evidence.json`
- `qualification/0_2_8/wp13_01c_r4_native_physical_convergence_verified/evidence.json`
- `qualification/0_2_8/wp13_01c_r4_native_physical_convergence_verified/scale_a_3r.json`
- `tests/verification/test_stable_refinement_evidence.py`
- `qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_13_newton_merit_20260927/r1_13_final_audit.json`
- `docs/verification/0_2_9/wp08-area-supported-contact-r1-13-final-report.md`
- `qualification/0_2_9/wp14/wp14_owner_scoped_release_direction_20260930.json`
- `qualification/0_2_10/authorized_selected_package_release_contract_e535ff.json`
- `docs/verification/code_aster_correlation_campaign_2026-08-14.md`
